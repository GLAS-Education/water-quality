import machine, board, time, busio, adafruit_bno055
from structs import Sensor, SensorID


class AbsoluteOrientation(Sensor):
    def __init__(self):
        super().__init__(SensorID.absrot)
        self.forced_error_value = "-1,-1,-1"

    def init(self):
        try:
            self.i2c = i2c = busio.I2C(scl=board.GP19, sda=board.GP18)
            self.sensor = adafruit_bno055.BNO055_I2C(i2c)
            return True
        except Exception as err:
            return err
    
    def read(self):
        sensor = self.sensor
        try:
            return f"{sensor.euler[0]},{sensor.euler[1]},{sensor.euler[2]},{sensor.acceleration[0]},{sensor.acceleration[1]},{sensor.acceleration[2]},{sensor.gyro[0]},{sensor.gyro[1]},{sensor.gyro[2]},{sensor.quaternion[0]},{sensor.quaternion[1]},{sensor.quaternion[2]},{sensor.quaternion[3]},{sensor.linear_acceleration[0]},{sensor.linear_acceleration[1]},{sensor.linear_acceleration[2]}"
        except Exception as err:
            return err


