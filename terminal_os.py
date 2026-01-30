
import os 
def key_pressed():
    if os.name == "nt":
        # for window user
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getwch()
        return None
    else:
        # for linux
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setcbreak(fd)  # non-blocking, no Enter needed
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                return sys.stdin.read(1)
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)



def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")