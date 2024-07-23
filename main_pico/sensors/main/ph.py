import machine
from structs import Sensor, SensorID, IntentionalNull


class pH(Sensor):
    def __init__(self):
        super().__init__(SensorID.ph)

    def init(self):
        try:
            self.uart = machine.UART(1, baudrate=9600, tx=machine.Pin(8), rx=machine.Pin(9))
            self.uart.init(bits=8, parity=None, stop=1)
            self.uart.write(b"*IDN?\n")
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            if self.uart.any():
                return self.uart.read().split("\r")[0]
            else:
                return IntentionalNull
        except Exception as err:
            return err



