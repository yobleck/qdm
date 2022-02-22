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
    new[6][termios.VTIME] = 0
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


def draw_menu(w: int, h2: int, cfg: dict, foc: int, v: list, ps: int, er: str) -> None:
    print("\x1b[H", end="")  # reset cursor
    foc += 1  # to account for header offset
    w4 = w//4  # avoid repeating math
    cw = w//2-w4//2  # center of screen
    print("\x1b[" + str(h2-1) + ";" + str(cw) + "H\u250c" + "\u2500"*(w4) + "\u2510", end="")  # box top
    for i, x in enumerate(["QDM: vt" + str(cfg["vt"]),
                           "XSession: " + str(cfg["xsessions"][v[0]][0]),
                           "Username: " + str(cfg["usernames"][v[1]]),
                           "Password: " + ps*"*",
                           er]):
        print("\x1b[" + str(h2+i) + ";" + str(cw) + "H" + menu_frmt(w4, x, (i == foc)))

    print("\x1b[" + str(h2+i+1) + ";" + str(cw) + "H\u2514" + "\u2500"*(w4) + "\u2518")  # box bottom
    #print("\x1b[F", end="")
    #print("\x1b[" + str(h2*2-2) + ";" + str(w) + "H", end="")


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
            # TODO input chars showing up on screen when getch(False)
        draw_menu(w, h2, config, field_in_focus, config_values, len(password), error_msg)

        char = getch(False)  # TODO keys for shutdown/reboot/switch to agetty

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

            # input password
            if field_in_focus == 2 and len(char) == 1 and char not in ["\n", "\r", "\t"]:
                # line above tries to eliminate non text inputs
                if char in ["\b", "\x08", "\x7f"]:  # backspace
                    password = password[:-1]
                else:
                    password += char

            # verify password
            if char in ["\n", "\r"]:
                can_pass = check_pass(config["usernames"][config_values[1]], password)
                if can_pass:
                    error_msg = "succ"
                    password = ""
                    #subprocess.run(["chromium"])
                    #subprocess.Popen(shlex.split(config["xsessions"][config_values[0]][1]))
                    # actually run *.desktop file or just run start command from config file?
                    #https://unix.stackexchange.com/questions/170063/start-a-process-on-a-different-tty
                    #setsid sh -c -f 'exec python /home/yobleck/qdm/qdm.py <> /dev/tty3 >&0 2>&1'
                    # break or use subprocess.run() so qdm can popback up when DE/WM is killed
                else:
                    error_msg = "wrong password, try again"
                    password = ""

    # exit stuff
    # TODO keep running in background when de/wm is running
    del password
    #with open("/home/yobleck/qdm/config.json", "w") as f:
        #json.dump(config, f)
    print("\x1b[2J\x1b[H", end="")
    return 0


if __name__ == "__main__":
    # if os.getuid() == 0: ?
    main()
