import machine, time
from structs import Sensor, SensorID


class BatteryVoltage(Sensor):
    def __init__(self):
        super().__init__(SensorID.voltage)
        self.adc = machine.ADC(28)
        self.conversion_factor = 6.6 / 4096

    def init(self):
        try:
            self.adc.read_u16()
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            raw_value = self.adc.read_u16()
            voltage_dec = raw_value * self.conversion_factor
            voltage = round(voltage_dec, 2)
            return voltage
        except Exception as err:
            return err


