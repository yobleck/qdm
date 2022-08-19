# functions that define how animations work
# init_name for starting values
import random
import sys
import time

def draw_animation(frame: list) -> None:
    print("\x1b[2J\x1b[H", end="")
    #fb = ""
    for w in frame:
        #print("".join(w), end="")
        #fb += "".join(w)
        for h in w:
            print(h, end="")
    #print(fb, end="")


def draw_animation_diff(frame: list) -> None:
    #print("\x1b[2J\x1b[H", end="")
    for i in frame:
        print("\x1b[" + str(i[1]) + ";" + str(i[0]) + "H" + i[2], end="")


def text_rain_init(w:int, h: int) -> list:
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


def text_rain_diff_init(w:int, h:int) -> list:
    frame = []
    for line in range(h):
        for col in range(w):
            if random.random() > 0.8:
                frame.append([col, line, "|"])
    return frame

def text_rain_diff(w:int, h: int, frame: list) -> list:
    # BUG number of lines is 3 more than it should be but doesn't cause scroll issues so it's minor
    new_frame = []
    for i in frame:
        if i[2] == "|":
            new_frame.append([i[0], i[1], " "])
            if i[1] >= h:
                new_frame.append([i[0], 0, "|"])
            else:
                new_frame.append([i[0], i[1]+1, "|"])
    return new_frame


def still_image_init(w: int, h:int) -> list:
    frame = []
    with open("/home/yobleck/qdm/still_image.txt", "r") as f:
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

    a = still_image_init(h, w)
    for x in a:
        for y in x:
            print(y, end="")
