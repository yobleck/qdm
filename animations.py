# functions that define how animations work
# init_name for starting values
import random
import sys
import time

def init_text_rain(w:int, h: int) -> list:
    frame = [[" " for i in range(h)] for j in range(w)]
    for x in range(w):
        for y in range(h):
            frame[x][y] = random.choice(["|", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " ", " "])
    return frame

def text_rain(w:int, h:int, frame: list) -> list:
    for x in reversed(range(w)):
        for y in reversed(range(h)):
            if frame[x][y] == "|":
                if x < w-1:
                    frame[x][y] = " "
                    frame[x+1][y] = "|"
                else:
                    frame[x][y] = " "
                    frame[0][y] = "|"
    return frame


def init_still_image(w: int, h:int) -> list:
    frame = []
    with open("./still_image.txt", "r") as f:
        for l in f.readlines():
            frame.append([])
            for c in l:
                frame[-1].append(c)
    return frame

def still_image(w:int, h:int, frame: list) -> list:
    #no op since the frame never changes
    return frame


# for testing
if __name__ == "__main__":
    import shutil
    w, h = shutil.get_terminal_size()
    print("\x1b[2J\x1b[H", end="")
    """a = init_text_rain(h, w)
    for x in a:
        for y in x:
            print(y, end="")
        print()
    while True:
        print("\x1b[2J\x1b[H", end="")
        a = text_rain(h, w, a)
        for x in a:
            for y in x:
                print(y, end="")
            print()
        time.sleep(0.1)"""

    a = init_still_image(h, w)
    for x in a:
        for y in x:
            print(y, end="")
