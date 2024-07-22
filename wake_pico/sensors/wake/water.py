import machine, board, time
from structs import Sensor, SensorID


class WaterLevel(Sensor):
    def __init__(self):
        super().__init__(SensorID.water_level)
        self.adc = machine.ADC(machine.Pin(26))

    def init(self):
        try:
            self.adc.read_u16() # Catching if this line errors during initialization!
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            return self.adc.read_u16()
        except Exception as err:
            return err



