import machine, time
from structs import Sensor, SensorID
from max1704x import max1704x


class Battery(Sensor):
    def __init__(self):
        super().__init__(SensorID.voltage)
        # Initialize max17043/max17048 with I2C pins
        # RP2040 pins: SDA=16, SCL=17
        self.sensor = max1704x(0, sda_pin=16, scl_pin=17)

    def init(self):
        try:
            # Test reading to ensure sensor is working
            self.sensor.getSoc()
            # Perform a quick start reset of the sensor
            self.sensor.quickStart()
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            # Get the state of charge as percentage
            battery_percentage = self.sensor.getSoc()
            return round(battery_percentage, 2)
        except Exception as err:
            return err


