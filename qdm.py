import crypt
import json
import shutil
import subprocess
import sys
import termios

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


def draw_animation():
    pass


def draw_menu(w: int, h: int, c: dict, f: int, v: list, p: int, e: str) -> None:
    print("\x1b[2J\x1b[H")
    f += 1  # to account for header offset
    for i, x in enumerate(["QDM: vt" + str(c["vt"]),
                           "XSession: " + str(c["xsessions"][v[0]]),
                           "Username: " + str(c["usernames"][v[1]]),
                           "Password: " + p*"*",
                           e]):
        if i == f:
            print("\x1b[" + str(h//2+i) + ";" + str(w//2) + "H\x1b[7m" + x + "\x1b[27m")
        else:
            print("\x1b[" + str(h//2+i) + ";" + str(w//2) + "H" + x)


def check_pass(p) -> bool:
    with open("./p.json", "r") as f:
        test = json.load(f)
    pass_hash = crypt.crypt(p, test["salt"])
    # TODO GET FROM /etc/shadow
    if pass_hash == test["pass"]:
        del test
        del pass_hash
        return True
    else:
        del test
        del pass_hash
        return False
    


def main() -> int:
    with open("./config.json", "r") as f:
        # TODO grep list of .desktop files from /usr/share/xsessions
        config = json.load(f)
    #[print(x) for x in config.items()]

    w, h = shutil.get_terminal_size()
    #print(w,h)

    error_msg = ""
    password = "test"  # TODO ACTUAL SECURE PASSWORD HANDLING
    field_in_focus = 0  # 0-2 xsess, username, password
    config_values = [0,0]

    print("\x1b[2J\x1b[H")

    while True:
        draw_menu(w, h, config, field_in_focus, config_values, len(password), error_msg)
        char = getch(True)

        if char == "\x1b":
            char = handle_esc()

            if char == "esc":
                break
            
            elif char == "up" and field_in_focus > 0:
                field_in_focus -= 1
            elif char == "dn" and field_in_focus < 2:
                field_in_focus += 1
            # TODO fix list out of bound error
            elif char == "rt" and field_in_focus <= 1:
                config_values[field_in_focus] += 1
            elif char == "lf" and field_in_focus <= 1:
                config_values[field_in_focus] -= 1
        
        # input password
        if field_in_focus == 2 and len(char) == 1 and char not in ["\n", "\r", "\t"]:
            if char in ["\b", "\x08", "\x7f"]:
                password = password[:-1]
            else:
                password += char
        
        if char in ["\n", "\r"]:
            can_pass = check_pass(password)
            if can_pass:
                error_msg = "succ"
                password = ""
                #subprocess.Popen([])
                # break
            else:
                error_msg = "wrong password, try again"
                password = ""

    # exit stuff
    del password
    with open("./config.json", "w") as f:
        json.dump(config, f)
    print("\x1b[2J\x1b[H", end="")
    return 0


if __name__ == "__main__":
    main()
