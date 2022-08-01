import crypt  # WARNING deprecated
import json
import os
import shutil
import sys
import termios
import time

import animations
import dbus

# WARNING BUG user input shows up on left side of screen
# even though termios.ECHO is turned off and screen is being cleared
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
        self.field_in_focus: int = 0  # 0-2 xsess, username, password
        self.config_values: list = [0, 0]  # xsess, username
        self.password_len: int = 0
        self.error_msg: str = "er"

        # static values of contents of menu box
        self.top_border: str = f"\x1b[{self.h2-1};{self.cntr_scrn}H\u250c{'─'*self.w4}\u2510"  # ─ = \u2500 unicode character
        self.vt: str = f"\x1b[{self.h2};{self.cntr_scrn}H{self.menu_frmt('QDM: vt' + str(self.config['vt']), False)}"
        self.bottom_border: str = f"\x1b[{self.h2+5};{self.cntr_scrn}H\u2514{'─'*self.w4}\u2518"

    def draw(self) -> None:
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

    def menu_frmt(self, line: str, is_hilite: bool) -> str:
        """Adds border, space padding and highlights line (hi).
        TODO add colors
        """
        if len(line) < self.w4:
            return "\u2502" + "\x1b[7m"*(int(is_hilite)) + line + "\x1b[27m"*(int(is_hilite)) + " "*(self.w4 - len(line)) + "\u2502"
        else:
            return "\u2502" + "\x1b[7m"*(int(is_hilite)) + line[:self.w4] + "\x1b[27m"*(int(is_hilite)) + "\u2502"

def check_pass(uname: str, psswd: str) -> bool:
    """Search for username in /etc/shadow
    then compare user inputted password
    to the one on file
    """
    if os.getuid != 0:  # NOTE temporary for testing without root. please delete p.json when done
        with open("/home/yobleck/qdm/p.json", "r") as f:
            test = json.load(f)
            salt = test["salt"]
            salt_pass_from_file = test["pass"]
            del test
    elif os.getuid == 0:  # NOTE root only
        with open("/etc/shadow", "r") as f:
            for l in f.readlines():
                i = l.split(":")
                if i[0] == uname:
                    salt_pass_from_file = i[1]
                    salt = salt_pass_from_file.rsplit("$", maxsplit=1)[0]

    if crypt.crypt(psswd, salt) == salt_pass_from_file:  # actual pswd hashing
        del salt_pass_from_file
        del salt
        return True
    else:
        del salt_pass_from_file
        del salt
        return False


def main() -> int:

    with open("/home/yobleck/qdm/config.json", "r") as f:
        # TODO grep list of .desktop files from /usr/share/xsessions
        config = json.load(f)

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

                elif char == "rt" and menu.field_in_focus <= 1:
                    if menu.config_values[menu.field_in_focus] < len(list(config.values())[menu.field_in_focus+1])-1:
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
                can_pass = check_pass(config["usernames"][menu.config_values[1]], password)
                if can_pass:
                    menu.error_msg = "success"
                    password = ""
                    menu.password_len = 0
                    print("\x1b[2J\x1b[H", end="")
                    print("\x1b[?25h", end="")  # unhide cursor

                    pid = os.fork()

                    if pid > 0:
                        dbus.sys_test(pid)  # TODO PAM
                        os.waitpid(pid, 0)

                    elif pid == 0:
                        time.sleep(0.5)
                        # set env vars. TODO more stuff from printenv
                        os.setgid(1000)
                        os.setuid(1000)

                        with open("/home/yobleck/qdm/envars.json", "r") as f:
                            envars = json.load(f)
                            for key, value in envars.items():
                                os.putenv(key, value)

                        # create .Xauthority file https://github.com/fairyglade/ly/blob/609b3f9ddcb8e953884002745eca5fde8480802f/src/login.c#L307
                        os.chdir("/home/yobleck")
                        os.system("/usr/bin/xauth add :1 . `/usr/bin/mcookie`")  # /usr/bin/bash -c

                        # start DE/WM TODO systemd pam
                        #os.system("startx /usr/bin/qtile start")
                        os.system("xinit /usr/bin/qtile start $* -- :1 vt3")  # TODO other sessions as well
                        #os.system("/usr/bin/bash --login 2>&1")  # subprocess?

                        #os.system("/usr/bin/bash /home/yobleck/qdm/xsetup.sh " + config["sessions"][config_values[0]][1])
                        #os.system(config["sessions"][config_values[0]][1])
                        #os.system("systemd-run --no-ask-password --slice=user --user startx /usr/bin/qtile start")
                        #os.system("/usr/bin/login -p -f yobleck")
                        #os.execl("/usr/bin/bash", "/usr/bin/bash", ">", "/dev/tty3", "2>&1")
                        break

                    # https://wiki.archlinux.org/title/systemd/User
                    # actually run *.desktop file or just run start command from config file?
                    # https://unix.stackexchange.com/questions/170063/start-a-process-on-a-different-tty
                    # setsid sh -c -f 'exec python /home/yobleck/qdm/qdm.py <> /dev/tty3 >&0 2>&1'

                    # https://www.gulshansingh.com/posts/how-to-write-a-display-manager/
                    # https://www.freedesktop.org/software/systemd/man/systemd.directives.html
                    # /usr/lib/systemd/systemd --unit=qdm.service ?
                    # systemd-run https://www.freedesktop.org/software/systemd/man/systemd-run.html
                    # systemd-user-[runtime-dir, sessions start]  https://www.freedesktop.org/software/systemd/man/user@.service.html#user-
                    # /usr/lib/systemd/systemd-logind
                    # systemctl --user start qdm.target ?
                    # https://www.freedesktop.org/software/systemd/python-systemd/
                    # https://linuxconfig.org/how-to-run-x-applications-without-a-desktop-or-a-wm

                    # List of TODO
                    # move check pass and all auth/login/startup stuff to auth.py
                    # systemd and non systemd options
                    # add to config systemd or not, lists of env vars, list of commands to be run
                    # change menu to be object that is built from config with proper methods and stuff
                    # access logind via dbus org.freedesktop.login1.Manager method CreateSession via pam_ssytemd
                    #   https://www.freedesktop.org/wiki/Software/systemd/logind/
                    #   https://wiki.freedesktop.org/www/Software/systemd/dbus/
                    # try pip install python-pam
                    print("\x1b[?25l", end="")
                else:
                    menu.error_msg = "wrong password, try again in 3s"  # TODO sleep for X seconds on every fail
                    password = ""
                    menu.password_len = 0
                    #time.sleep(3)

    # exit stuff
    # TODO keep running in background when de/wm is running
    del password  # security?
    print("\x1b[2J\x1b[H", end="")
    return 0


if __name__ == "__main__":
    # if os.getuid() == 0: ?
    main()
