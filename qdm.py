import crypt
import json
import shlex
import shutil
import subprocess
import sys
import termios
import time

import os  # temporary for password testing without root

import animations

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
            if k in ["5","6"]:
                getch(False)  # eat useless ~ char
            return esc_chars[k]
        return "esc[ error: " + a + k
    return "esc"


def menu_frmt(w: int, s: str, hi: bool) -> str:
    """Adds border, space padding and highlights line (hi).
    TODO add colors
    """
    if len(s) < w:
        return "\u2502" + "\x1b[7m"*(int(hi)) + s + "\x1b[27m"*(int(hi)) + " "*(w - len(s)) + "\u2502"
    else:
        return "\u2502" + s[:w] + "\u2502"


def draw_menu(w: int, h2: int, cfg: dict, foc: int, cv: list, ps: int, er: str) -> None:
    # TODO move to animations and add diff version that appends to the animation diff frame
    print("\x1b[H", end="")  # reset cursor
    foc += 1  # to account for header offset
    w4 = w//4  # avoid repeating math
    cw = w//2-w4//2  # center of screen
    print("\x1b[" + str(h2-1) + ";" + str(cw) + "H\u250c" + "\u2500"*(w4) + "\u2510", end="")  # box top
    for i, x in enumerate(["QDM: vt" + str(cfg["vt"]),
                           "XSession: " + str(cfg["xsessions"][cv[0]][0]),
                           "Username: " + str(cfg["usernames"][cv[1]]),
                           "Password: " + ps*"*",
                           er]):
        print("\x1b[" + str(h2+i) + ";" + str(cw) + "H" + menu_frmt(w4, x, (i == foc)))

    print("\x1b[" + str(h2+i+1) + ";" + str(cw) + "H\u2514" + "\u2500"*(w4) + "\u2518")  # box bottom


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

    pass_hash = crypt.crypt(psswd, salt)  # actual pswd hashing

    if pass_hash == salt_pass_from_file:
        del salt_pass_from_file
        del salt
        del pass_hash
        return True
    else:
        del salt_pass_from_file
        del salt
        del pass_hash
        return False


def main() -> int:
    with open("/home/yobleck/qdm/config.json", "r") as f:
        # TODO grep list of .desktop files from /usr/share/xsessions
        config = json.load(f)

    w, h = shutil.get_terminal_size()
    h2 = h//2

    error_msg = ""
    password = ""
    field_in_focus = 0  # 0-2 xsess, username, password
    config_values = [0,0]  # xsess, username TODO hacky fix this

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

        draw_menu(w, h2, config, field_in_focus, config_values, len(password), error_msg)

        char = getch(True)  # TODO keys for shutdown/reboot/switch to agetty

        if char:
            if char == "\x1b":
                char = handle_esc()

                if char == "esc":
                    break

                elif char == "up" and field_in_focus > 0:
                    field_in_focus -= 1
                elif char == "dn" and field_in_focus < 2:
                    field_in_focus += 1

                elif char == "rt" and field_in_focus <= 1:
                    if config_values[field_in_focus] < len(list(config.values())[field_in_focus+1])-1:
                        config_values[field_in_focus] += 1
                elif char == "lf" and field_in_focus <= 1:
                    if config_values[field_in_focus] > 0:
                        config_values[field_in_focus] -= 1

            elif field_in_focus == 2 and char in ["\b", "\x08", "\x7f"]:  # \x08=ctrl+h
                password = password[:-1]  # backspace password

            elif field_in_focus == 2 and len(char) == 1 and char not in ["\n", "\r", "\t"]:
                # line above tries to eliminate non text inputs
                password += char  # password input

            # verify password
            elif char in ["\n", "\r"]:
                can_pass = check_pass(config["usernames"][config_values[1]], password)
                if can_pass:
                    error_msg = "success"
                    password = ""
                    print("\x1b[2J\x1b[H", end="")
                    print("\x1b[?25h", end="")  # unhide cursor
                    # set env vars. TODO more stuff from printenv
                    os.setuid(1000)
                    os.setgid(1000)
                    os.putenv("QT_QPA_PLATFORMTHEME", "qt5ct")
                    os.putenv("XCURSOR_THEME", "breeze_cursors")
                    os.putenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
                    os.putenv("HOME", "/home/yobleck")
                    os.putenv("PWD", "/home/yobleck")
                    os.chdir("/home/yobleck")
                    os.putenv("USER", "yobleck")
                    os.putenv("LOGNAME", "yobleck")
                    os.putenv("DISPLAY", ":1")
                    os.putenv("XAUTHORITY", "/home/yobleck/.lyxauth")
                    # TODO create .Xauthority file
                    #os.putenv("XAUTHORITY", "/home/yobleck/.qdm_xauth")
                    #os.system("/usr/bin/xauth add :1 . `/usr/bin/mcookie`")  # /usr/bin/bash -c
                    #os.putenv("XDG_", "")
                    os.system(config["xsessions"][config_values[0]][1])
                    #os.system("startx /usr/bin/qtile start")
                    #os.system("/usr/bin/bash --login 2>&1")  # subprocess?
                    #os.system("/usr/bin/login -p -f yobleck")
                    #os.execl("/usr/bin/bash", "/usr/bin/bash", ">", "/dev/tty3", "2>&1")
                    # https://wiki.archlinux.org/title/systemd/User
                    # actually run *.desktop file or just run start command from config file?
                    #https://unix.stackexchange.com/questions/170063/start-a-process-on-a-different-tty
                    #setsid sh -c -f 'exec python /home/yobleck/qdm/qdm.py <> /dev/tty3 >&0 2>&1'
                    # https://www.gulshansingh.com/posts/how-to-write-a-display-manager/
                    print("\x1b[?25l", end="")
                else:
                    error_msg = "wrong password, try again"
                    password = ""

    # exit stuff
    # TODO keep running in background when de/wm is running
    del password  # security?
    print("\x1b[2J\x1b[H", end="")
    return 0


if __name__ == "__main__":
    # if os.getuid() == 0: ?
    main()
