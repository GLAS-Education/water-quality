def log(message: str, type: str = None, module: str = None):
    text = ""

    if type == "success":
        text += LogFormat.Foreground.GREEN + "✓ " + LogFormat.RESET
    elif type == "error":
        text += LogFormat.Foreground.RED + "✕ " + LogFormat.RESET
    elif type == "warning":
        text += LogFormat.Foreground.YELLOW + "⚠ " + LogFormat.RESET
    elif type == "info":
        text += LogFormat.Foreground.BLUE + "ⓘ " + LogFormat.RESET
    elif type == "debug":
        text += LogFormat.Foreground.PINK + "⚙ " + LogFormat.RESET
    
    if module:
        text += LogFormat.Foreground.LIGHT_GREY + "[" + module + "] " + LogFormat.RESET
    
    text += message

    print(text)


# https://stackoverflow.com/a/26445590
class LogFormat:
    RESET = "\033[0m"
    BOLD = "\033[01m"
    DISABLE = "\033[02m"
    UNDERLINE = "\033[04m"
    REVERSE = "\033[07m"
    STRIKETHROUGH = "\033[09m"
    INVISIBLE = "\033[08m"

    class Foreground:
        BLACK = "\033[30m"
        RED = "\033[31m"
        GREEN = "\033[32m"
        ORANGE = "\033[33m"
        BLUE = "\033[34m"
        PURPLE = "\033[35m"
        CYAN = "\033[36m"
        LIGHT_GREY = "\033[37m"
        DARK_GREY = "\033[90m"
        LIGHT_RED = "\033[91m"
        LIGHT_GREEN = "\033[92m"
        YELLOW = "\033[93m"
        LIGHT_BLUE = "\033[94m"
        PINK = "\033[95m"
        LIGHT_CYAN = "\033[96m"

    class Background:
        BLACK = "\033[40m"
        RED = "\033[41m"
        GREEN = "\033[42m"
        ORANGE = "\033[43m"
        BLUE = "\033[44m"
        PURPLE = "\033[45m"
        CYAN = "\033[46m"
        LIGHT_GREY = "\033[47m"
