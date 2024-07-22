import machine, time
from structs import Sensor, SensorID


class Hydrophone(Sensor):
    def __init__(self):
        super().__init__(SensorID.hydrophone)
        self.adc = machine.ADC(28)
        self.conversion_factor = 3.3 / (4096)
        self.sound_divisor = 2
        self.activity_threshold = 3
        self.last_loud = None

    def init(self):
        try:
            self.adc.read_u16() # Catching if this line errors during initialization!
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            mic_readings = []
            for _ in range(50): # collect data for 50ms
                raw_value = self.adc.read_u16()
                std_value = raw_value * self.conversion_factor
                mic_readings.append(std_value)
                time.sleep_ms(1)
            min_read = min(mic_readings)
            max_read = max(mic_readings)
            sound_reading = (max_read - min_read) / self.sound_divisor
            if sound_reading > self.activity_threshold:            
                self.last_loud = time.mktime(time.localtime())
            return sound_reading
        except Exception as err:
            return err


