import machine
import time
from base import BaseModule
from logging import log

class Module(BaseModule):
    def __init__(self):
        super().__init__("microphone")
        self.adc = None
        self.conversion_factor = 3.3 / (4096)
        self.sound_divisor = 2
        self.activity_threshold = 3
        self.last_loud = None
        self.initialized = False
        self._init_sensor()
        
    def _init_sensor(self):
        """Initialize the microphone sensor if not already done"""
        if not self.initialized:
            self.adc = machine.ADC(28)
            
            # Test sensor by taking a reading
            try:
                self.adc.read_u16()
                self.initialized = True
                log("Setup complete!", "success", self.id)
            except Exception as e:
                raise Exception(f"Could not initialize microphone sensor: {e}")

    def read(self) -> dict:
        sound_reading = None
        
        try:
            mic_readings = []
            for _ in range(50):  # collect data for 50ms
                raw_value = self.adc.read_u16()
                std_value = raw_value * self.conversion_factor
                mic_readings.append(std_value)
                time.sleep_ms(1)
            
            min_read = min(mic_readings)
            max_read = max(mic_readings)
            sound_reading = (max_read - min_read) / self.sound_divisor
            
            if sound_reading > self.activity_threshold:            
                self.last_loud = time.mktime(time.localtime())
                
        except Exception as e:
            log(f"Error reading microphone sensor: {e}", "error", self.id)
        
        return {
            "value": sound_reading
        }

    def pretty_print(self, data: dict) -> str:
        sound_reading = data.get("value")
        
        if sound_reading is not None:
            return f"{sound_reading}"
        else:
            return f"No reading"
