import machine
from structs import Sensor, SensorID, IntentionalNull
import time

class pH(Sensor):
    def __init__(self):
        super().__init__(SensorID.ph)

    def init(self):
        try:
            self.uart = machine.UART(1, baudrate=9600, tx=machine.Pin(8), rx=machine.Pin(9))
            self.uart.init(bits=8, parity=None, stop=1)
            # self.uart.write(b"*IDN?\n")
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            self.uart.write("R\r")
            time.sleep(1)
            if self.uart.any():
                return float(str(self.uart.read())[2:].split("\\")[0])
            else:
                return IntentionalNull
        except Exception as err:
            return err
