import json
import os
import pam
import shutil
import subprocess
import sys
import termios
import time


import animations


def log(i):
    with open("/home/yobleck/qdm/test.log", "a") as f:
        f.write(str(i) + "\n")

# WARNING BUG user input shows up on left side of screen
# even though termios.ECHO is turned off and screen is being cleared
# update: possibly fixed
def getch(blocking: bool = True) -> str:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    new = list(old_settings)
    new[3] &= ~(termios.ICANON | termios.ECHO)
    new[6][termios.VMIN] = 1 if blocking else 0
    new[6][termios.VTIME] = 1  # 0 is faster but causes bytes to slip through the cracks?
    termios.tcsetattr(fd, termios.TCSADRAIN, new)
    try:
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


esc_chars = {"A": "up", "B": "dn", "C": "rt", "D": "lf", "Z": "shft+tb", "5": "pgup", "6": "pgdn"}


def handle_esc() -> str:
    a = getch(False)
    if a == "[":
        k = getch(False)  # assuming 3 bytes for now
        if k in esc_chars.keys():
            if k in ["5", "6"]:
                getch(False)  # eat useless ~ char
            return esc_chars[k]
        return "esc[ error: " + a + k
    return "esc"


class Menu:
    def __init__(self, screen_width: int, screen_height: int, config: dict):
        self.config = config  # pass by reference
        # precalculate size of menu box
        self.w4: int = screen_width//4
        self.cntr_scrn: int = screen_width//2 - self.w4//2
        self.h2: int = screen_height//2

        # what has been selected.
        # NOTE these values will be changed from outside the object cause I don't feel like implementing getters/setters
        self.fields: list = ["sessions", "usernames", "password"]
        self.field_in_focus: int = 0
        self.config_values: list = [0, 0]  # xsess, username
        self.password_len: int = 0
        self.error_msg: str = ""

        # static values of contents of menu box
        self.top_border: str = f"\x1b[{self.h2-1};{self.cntr_scrn}H\u250c{'─'*self.w4}\u2510"  # ─ = \u2500 unicode character
        self.vt: str = f"\x1b[{self.h2};{self.cntr_scrn}H{self.menu_frmt('QDM vt:' + str(self.config['vt']), False)}"
        self.bottom_border: str = f"\x1b[{self.h2+5};{self.cntr_scrn}H\u2514{'─'*self.w4}\u2518"

    def draw(self) -> None:
        print("\x1b[34m", end="")  # TODO get color from config
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
        TODO add colors
        """
        if len(line) < self.w4:
            return "\u2502" + "\x1b[7m"*(int(is_hilite)) + line + "\x1b[27m"*(int(is_hilite)) + " "*(self.w4 - len(line)) + "\u2502"
        else:
            return "\u2502" + "\x1b[7m"*(int(is_hilite)) + line[:self.w4] + "\x1b[27m"*(int(is_hilite)) + "\u2502"


def load_users_and_sessions():
    vt = os.ttyname(0)[-1]  # /dev/ttyX -> X
    # get list of valid logins from /etc/passwd
    users = []
    uids = []
    gids = []
    with open("/etc/passwd", "r") as f:
        for line in f:
            split = line.split(":")
            if split[-1] not in ["/bin/false\n", "/usr/bin/nologin\n"]:
                users.append(split[0])
                uids.append(int(split[2]))
                gids.append(int(split[3]))
    # get sessions and their launch commands
    # TODO wayland-sessions
    sessions = []
    for x in os.listdir("/usr/share/xsessions"):
        name = ""
        exec_cmd = ""
        if x.split(".")[-1] == "desktop":
            with open("/usr/share/xsessions/" + x, "r") as f:
                for l in f:
                    v = l.split("=")
                    if v[0] == "Name":
                        name = v[1].strip()
                    elif v[0] == "Exec":
                        exec_cmd = v[1].strip()
            sessions.append([name, exec_cmd])

    return {"vt": vt, "usernames": users, "uids": uids,
    "gids": gids, "sessions": sessions}


def load_envars(menu) -> None:
    """Load environment variables"""
    # TODO put envars in dict and pass to pam.authenticate?
    # TODO gtk modules envars? and start xdg-desktop.service?
    os.setgid(menu.config["gids"][menu.config_values[1]])
    os.setuid(menu.config["uids"][menu.config_values[1]])

    for x in range(10):
        if not os.path.exists(f"/tmp/.X{x}-lock"):
            break
    os.environ["DISPLAY"] =  f":{x}"
    os.environ["XAUTHORITY"] = "/home/yobleck/.qdm_xauth"
    os.environ["XDG_VTNR"] = menu.config["vt"]
    with open(f"/proc/{os.getpid()}/sessionid", "r") as f:
        os.environ["XDG_SESSION_ID"] = f.readline().strip()

    # misc other envars
    with open("/home/yobleck/qdm/envars.json", "r") as f:  # TODO move envars list and xsetup.sh and stuff to /etc/qdm/
        # TODO dynamically get session_id
        envars = json.load(f)
        for key, value in envars.items():
            os.environ[key] = value

    # create .Xauthority file https://github.com/fairyglade/ly/blob/master/src/login.c
    os.chdir("/home/yobleck")
    os.system(f"/usr/bin/xauth add :{x} . `/usr/bin/mcookie`")  # replace with subprocess?


def main() -> int:
    config = load_users_and_sessions()
    log(config)

    w, h = shutil.get_terminal_size()
    menu = Menu(w, h, config)

    password = ""

    print("\x1b[2J\x1b[H", end="")  # clear screen
    print("\x1b[?25l", end="")  # hide cursor
    #frame = animations.text_rain_init(h, w)
    frame = animations.text_rain_diff_init(w, h); animations.draw_animation_diff(frame)
    #frame = animations.still_image_init(h, w); animations.draw_animation(frame)
    now = time.monotonic()

    while True:
        if time.monotonic() - now > 0.0694:  # NOTE: fullscreen redraws cause flickering. framerate config var?
            now = time.monotonic()
            #frame = animations.text_rain(h, w, frame)
            #animations.draw_animation(frame)
            frame = animations.text_rain_diff(w, h, frame)
            animations.draw_animation_diff(frame)

        menu.draw()

        char = getch(True)  # TODO keys for shutdown/reboot/switch to agetty

        if char:
            if char == "\x1b":
                char = handle_esc()

                if char == "esc":
                    break

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
                pam_obj = pam.PamAuthenticator()
                if pam_obj.authenticate(menu.config["usernames"][menu.config_values[1]], password, call_end=True):
                    #pam_obj.open_session()
                    menu.error_msg = "success"
                    menu.password_len = 0
                    print("\x1b[2J\x1b[H", end="")
                    print("\x1b[?25h", end="")  # unhide cursor

                    pid = os.fork()
                    if pid > 0:
                        password = ""
                        os.waitpid(pid, 0)

                    elif pid == 0:
                        pam_obj.authenticate(menu.config["usernames"][menu.config_values[1]], password, call_end=False)  # TODO load envars here?
                        password = ""
                        pam_obj.open_session()

                        # set env vars. TODO more stuff from printenv
                        load_envars(menu)

                        # start DE/WM
                        xorg = subprocess.Popen(["/usr/bin/X", f"{os.environ['DISPLAY']}", f"vt{os.environ['XDG_VTNR']}"])
                        time.sleep(0.5)  # should use xcb.connect() to verify connection is possible but too lazy
                        # TODO other sessions as well. os.system("/usr/bin/bash --login 2>&1")  # subprocess?
                        qtile = subprocess.Popen(["/usr/bin/sh", "/home/yobleck/qdm/etc/qdm/xsetup.sh", "/usr/bin/qtile", "start"])
                        qtile.wait()
                        xorg.terminate()
                        pam_obj.close_session()
                        pam_obj.end()
                        break

                    # List of TODO
                    # non systemd option?
                    print("\x1b[?25l", end="")
                else:
                    menu.error_msg = "wrong password, try again in 3s"  # TODO sleep for X seconds on every fail
                    password = ""
                    menu.password_len = 0
                    time.sleep(3)  # TODO doesn't stop user input

    # exit stuff
    del password  # security?
    print("\x1b[2J\x1b[H", end="")
    return 0


if __name__ == "__main__":
    # if os.getuid() == 0: ?
    main()
