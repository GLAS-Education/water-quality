import machine
from base import BaseModule
from logging import log

class Module(BaseModule):
    def __init__(self):
        super().__init__("ph")
        self.uart = None
        self.initialized = False
        
    def _init_sensor(self):
        """Initialize the pH sensor if not already done"""
        if not self.initialized:
            self.uart = machine.UART(1, baudrate=9600, tx=machine.Pin(8), rx=machine.Pin(9))
            self.uart.init(bits=8, parity=None, stop=1)
            # self.uart.write(b"*IDN?\n")
            
            # Wait a moment for sensor to be ready and try to get initial reading
            import time
            time.sleep(1)
            
            # Validate sensor is responding
            if not self.uart.any():
                raise Exception("Could not find configured pH sensor - no data available")
            
            self.initialized = True
            log("Setup complete!", "success", self.id)

    def read(self) -> dict:
        self._init_sensor()
        
        ph_value = None
        
        if self.uart.any():
            raw_data = str(self.uart.read()).split("\\r")[-2].replace("b'", "")
            ph_value = float(raw_data)
        
        return {
            "level": ph_value
        }

    def pretty_print(self, data: dict) -> str:
        ph_value = data.get('level')
        
        if ph_value is not None:
            return f"{ph_value}"
        else:
            return f"No reading"
