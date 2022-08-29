import json
import os
import shlex  # from shlex import split?
import shutil  # from shutil import get_terminal_size()?
import subprocess
import sys
import termios
import time

import pam

import animations
# TODO change process name

INSTALL_PATH = "/home/yobleck/qdm"  # replace with read from config
ETC_PATH = "/home/yobleck/qdm/etc/qdm"  # how to get this without knowing where it is?


def log(i):
    with open(f"{INSTALL_PATH}/test.log", "a") as f:
        f.write(f"{time.asctime()}: {str(i)}\n")


def getch(blocking: bool = True, bytes_to_read: int = 1) -> str:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    new = list(old_settings)
    new[3] &= ~(termios.ICANON | termios.ECHO)
    new[6][termios.VMIN] = 1 if blocking else 0
    new[6][termios.VTIME] = 1  # 0 is faster but inputs appear on screen?
    termios.tcsetattr(fd, termios.TCSADRAIN, new)
    try:
        ch = sys.stdin.read(bytes_to_read)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


esc_chars = {"[A": "up", "[B": "dn", "[C": "rt", "[D": "lf", "[F": "end", "[H": "home", "[[A": "F1",
            "[[B": "F2", "[[C": "F3", "OS": "F4", "[Z": "shft+tb", "[5~": "pgup", "[6~": "pgdn", # "OR": "F3"
            "[15~": "F5", "[17~": "F6", "[18~": "F7", "[19~": "F8", "[20~": "F9", "[21~": "F10",
            "[23~": "F11", "[24~": "F12"}  # TODO fix more F keys


def handle_esc() -> str:
    """https://en.wikipedia.org/wiki/ANSI_escape_code
    I don't know if this holds across all computers/keyboards
    or if my setup just weird?
    BUG: holding down key that uses less than 4 esc chars will capture
    first char of next sequence early so next characters are captured as plain text"""
    a = getch(False, 4)
    if a in esc_chars.keys():
        log("key: " + a)
        return esc_chars[a]
    elif a == "":
        return "esc"
    log("failed " + a)
    return ""


class Menu:
    def __init__(self, screen_width: int, screen_height: int, config: dict):
        self.config = config  # pass by reference
        log(self.config)

        # precalculate size of menu box
        self.w4: int = screen_width//4
        self.cntr_scrn: int = screen_width//2 - self.w4//2
        self.h2: int = screen_height//2

        # what has been selected.
        # NOTE these values will be changed from outside the object cause I don't feel like implementing getters/setters
        self.fields: list = ["sessions", "usernames", "password"]
        self.config_values: list = [self.config["default_session"],
                                    self.config["default_username"]]  # [session, username]
        self.field_in_focus: int = 0  # session, username or password
        if self.config_values[0] != 0 and self.config_values[1] != 0:
            self.field_in_focus = 2
        self.password_len: int = 0
        self.error_msg: str = ""

        # static values of contents of menu box
        self.f_keys: str = f"\x1b[HF1 Poweroff, F2 Reboot, F3 Restart QDM"
        self.top_border: str = f"\x1b[{self.h2-1};{self.cntr_scrn}H\u250c{'─'*self.w4}\u2510"  # ─ = \u2500 unicode character
        self.vt: str = f"\x1b[{self.h2};{self.cntr_scrn}H{self.menu_frmt('QDM vt:' + str(self.config['vt']), False)}"
        self.bottom_border: str = f"\x1b[{self.h2+5};{self.cntr_scrn}H\u2514{'─'*self.w4}\u2518"

    def draw(self) -> None:
        print(self.config["menu_color"], end="")
        print(self.f_keys)
        print(self.top_border)
        print(self.vt)
        print(f"\x1b[{self.h2+1};{self.cntr_scrn}H"
              f"{self.menu_frmt('Session: ' + str(self.config['sessions'][self.config_values[0]][0]), (self.field_in_focus == 0))}")
        print(f"\x1b[{self.h2+2};{self.cntr_scrn}H"
              f"{self.menu_frmt('Username: ' + str(self.config['usernames'][self.config_values[1]]), (self.field_in_focus == 1))}")
        print(f"\x1b[{self.h2+3};{self.cntr_scrn}H"
              f"{self.menu_frmt('Password: ' + '*'*self.password_len, (self.field_in_focus == 2))}")
        print(f"\x1b[{self.h2+4};{self.cntr_scrn}H{self.menu_frmt(self.error_msg, False)}")
        print(self.bottom_border)
        print("\x1b[0m")

    def menu_frmt(self, line: str, is_hilite: bool) -> str:
        """Adds border, space padding and highlights line (hi).
        TODO change to f strings
        """
        if len(line) < self.w4:
            return "\u2502" + "\x1b[7m"*(int(is_hilite)) + line + "\x1b[27m"*(int(is_hilite)) + " "*(self.w4 - len(line)) + "\u2502"
        else:
            return "\u2502" + "\x1b[7m"*(int(is_hilite)) + line[:self.w4] + "\x1b[27m"*(int(is_hilite)) + "\u2502"


def load_users_and_sessions() -> dict:
    return_val: dict = {}
    return_val["vt"] = os.ttyname(0)[-1]  # /dev/ttyX -> X
    # get list of valid logins from /etc/passwd
    return_val["usernames"] = []
    return_val["uids"] = []
    return_val["gids"] = []
    with open("/etc/passwd", "r") as f:
        for line in f:
            split = line.split(":")
            if split[-1] not in ["/bin/false\n", "/usr/bin/nologin\n", "/usr/bin/git-shell\n"]:
                return_val["usernames"].append(split[0])
                return_val["uids"].append(int(split[2]))
                return_val["gids"].append(int(split[3]))

    # get sessions and their launch commands
    # TODO wayland-sessions
    return_val["sessions"] = []
    for x in os.listdir("/usr/share/xsessions"):
        name = ""
        exec_cmd = ""
        if x.split(".")[-1] == "desktop":
            with open("/usr/share/xsessions/" + x, "r") as f:
                for line in f:
                    v = line.split("=")
                    if v[0] == "Name":
                        name = v[1].strip()
                    elif v[0] == "Exec":
                        exec_cmd = v[1].strip()
            return_val["sessions"].append([name, exec_cmd])

    # get default username and session from config
    with open(f"{ETC_PATH}/config.json", "r") as f:
        defaults = json.load(f)
    if defaults["default_username"] in return_val["usernames"]:
        return_val["default_username"] = return_val["usernames"].index(defaults["default_username"])
    else:
        return_val["default_username"] = 0
    temp_sess = [s[0] for s in return_val["sessions"]]
    if defaults["default_session"] in temp_sess:
        return_val["default_session"] = temp_sess.index(defaults["default_session"])
    else:
        return_val["default_session"] = 0
    return_val["menu_color"] = defaults["menu_color"]

    return return_val


def load_envars(menu) -> None:
    """Load environment variables"""
    # TODO put envars in dict and pass to pam.authenticate?
    os.setgid(menu.config["gids"][menu.config_values[1]])
    os.setuid(menu.config["uids"][menu.config_values[1]])

    for x in range(10):
        if not os.path.exists(f"/tmp/.X{x}-lock"):
            break
    os.environ["DISPLAY"] =  f":{x}"
    os.environ["XDG_VTNR"] = menu.config["vt"]
    with open(f"/proc/{os.getpid()}/sessionid", "r") as f:
        os.environ["XDG_SESSION_ID"] = f.readline().strip()

    # misc other envars
    with open(f"{ETC_PATH}/envars.json", "r") as f:
        envars = json.load(f)
    for key, value in envars.items():
        os.environ[key] = value

    # create .Xauthority file https://github.com/fairyglade/ly/blob/master/src/login.c
    os.chdir(envars["HOME"])
    os.system(f"/usr/bin/xauth add :{x} . `/usr/bin/mcookie`")


def main() -> int:
    w, h = shutil.get_terminal_size()
    log("size: " + str(w) + ", " + str(h))
    menu = Menu(w, h, load_users_and_sessions())
    os.system(f"chvt {menu.config['vt']}")  # change vt focus

    password = ""

    print("\x1b[2J\x1b[H", end="")  # clear screen
    print("\x1b[?25l", end="")  # hide cursor
    #frame = animations.text_rain_init(h, w)
    #frame = animations.text_rain_diff_init(w, h); animations.draw_animation_diff(frame)
    frame = animations.still_image_init(h, w); animations.draw_animation(frame)
    old_time = time.monotonic()

    while True:
        if time.monotonic() - old_time > 0.0694:  # NOTE: fullscreen redraws cause flickering. framerate config var?
            old_time = time.monotonic()
            #frame = animations.text_rain(h, w, frame)
            #animations.draw_animation(frame)
            #frame = animations.text_rain_diff(w, h, frame)
            #animations.draw_animation_diff(frame)

        menu.draw()

        char = getch(True)  # TODO keys for shutdown/reboot/switch to agetty

        if char:
            if char == "\x1b":
                char = handle_esc()

                if char == "esc":
                    break

                elif char == "F1":
                    subprocess.run(["systemctl", "poweroff"])
                elif char == "F2":
                    subprocess.run(["systemctl", "reboot"])
                elif char == "F3":
                    subprocess.run(["systemctl", "restart", "qdm.service"])

                elif char == "up" and menu.field_in_focus > 0:
                    menu.field_in_focus -= 1
                elif char == "dn" and menu.field_in_focus < 2:
                    menu.field_in_focus += 1

                elif char == "rt" and menu.field_in_focus <= 1:  # TODO refactor this whole block
                    if menu.config_values[menu.field_in_focus] < len(menu.config[menu.fields[menu.field_in_focus]])-1:
                        menu.config_values[menu.field_in_focus] += 1
                elif char == "lf" and menu.field_in_focus <= 1:
                    if menu.config_values[menu.field_in_focus] > 0:
                        menu.config_values[menu.field_in_focus] -= 1

            elif menu.field_in_focus == 2 and char in ["\b", "\x08", "\x7f"]:  # \x08=ctrl+h
                password = password[:-1]  # backspace password
                menu.password_len -= 1 if menu.password_len > 0 else 0

            elif menu.field_in_focus == 2 and len(char) == 1 and char not in ["\n", "\r", "\t", "\v", "\a"]:
                # line above tries to eliminate non text inputs
                password += char  # password input
                menu.password_len += 1

            # verify password
            elif char in ["\n", "\r"]:
                menu.error_msg = "Checking..."
                menu.draw()
                pam_obj = pam.PamAuthenticator()
                if pam_obj.authenticate(menu.config["usernames"][menu.config_values[1]], password, call_end=True):
                    menu.error_msg = "Success"
                    menu.draw()
                    menu.password_len = 0
                    print("\x1b[2J\x1b[H", end="")
                    print("\x1b[?25h", end="")  # unhide cursor

                    pid = os.fork()
                    if pid > 0:
                        password = ""
                        os.waitpid(pid, 0)
                        menu.error_msg = "logged out"
                        menu.draw()
                        time.sleep(2)  # TODO terminal has to be ready for user input. What's the trigger?

                    elif pid == 0:
                        pam_obj.authenticate(menu.config["usernames"][menu.config_values[1]], password, call_end=False)
                        password = ""
                        pam_obj.open_session()
                        # set env vars. TODO more stuff from printenv
                        load_envars(menu)

                        # start DE/WM
                        xorg = subprocess.Popen(["/usr/bin/X", f"{os.environ['DISPLAY']}", f"vt{os.environ['XDG_VTNR']}"])
                        time.sleep(0.2)  # should use xcb.connect() to verify connection is possible but too lazy
                        # TODO Bash session as well. os.system("/usr/bin/bash --login 2>&1")
                        dewm = subprocess.Popen(["/usr/bin/sh", f"{ETC_PATH}/xsetup.sh"] +
                                                shlex.split(menu.config["sessions"][menu.config_values[0]][1]))
                        dewm.wait()
                        xorg.terminate()
                        pam_obj.close_session()
                        pam_obj.end()
                        break

                    print("\x1b[?25l", end="")
                else:  # Handle wrong password
                    password = ""
                    menu.password_len = 0
                    menu.error_msg = "Wrong password. Try again in 3s"
                    menu.draw()
                    timeout = time.monotonic() + 3
                    while time.monotonic() < timeout:
                        getch(False)
                    menu.error_msg = ""

    # exit stuff
    del password  # security?
    print("\x1b[2J\x1b[H", end="")
    return 0


if __name__ == "__main__":
    main()
