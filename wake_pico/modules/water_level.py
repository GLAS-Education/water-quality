import machine
from base import BaseModule
from logging import log

class Module(BaseModule):
    def __init__(self):
        super().__init__("water_level")
        self.adc = None
        self.initialized = False
        self._init_sensor()
        
    def _init_sensor(self):
        """Initialize the water level sensor if not already done"""
        if not self.initialized:
            self.adc = machine.ADC(machine.Pin(26))
            
            # Test sensor by taking a reading
            try:
                self.adc.read_u16()
                self.initialized = True
                log("Setup complete!", "success", self.id)
            except Exception as e:
                raise Exception(f"Could not initialize water level sensor: {e}")

    def read(self) -> dict:
        water_level = None
        
        try:
            # Read the raw ADC value (0-65535)
            raw_value = self.adc.read_u16()
            water_level = raw_value
        except Exception as e:
            log(f"Error reading water level sensor: {e}", "error", self.id)
        
        return {
            "value": water_level
        }

    def pretty_print(self, data: dict) -> str:
        water_level = data.get("value")
        
        if water_level is not None:
            return f"{water_level}"
        else:
            return f"No reading"
