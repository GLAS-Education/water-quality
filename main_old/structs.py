def enum(**enums: int):
    return type('Enum', (), enums)


SensorID = enum(
    tester = "TESTER",
    status_led = "STATUS_LED",
    voltage = "BATTERY_VOLTAGE",
    temperature = "TEMPERATURE",
    turbidity = "TURBIDITY",
    ph = "PH"
)

IntentionalNull = "-1"
IntentionalUndefined = "__UNDEFINED__"


class Sensor:
    def __init__(self, id):
        self.id = id

    def init(self):
        pass

    def read(self):
        pass


ProbeID = enum(main="MAIN", wake="WAKE", demo="DEMO")


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
