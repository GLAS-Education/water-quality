import random
from structs import Sensor, SensorID


class TesterSensor(Sensor):
    def __init__(self):
        super().__init__(SensorID.tester)

    def init(self):
        try:
            return True
            # raise Exception("Something went wrong!")
        except Exception as err:
            return err

    def read(self):
        try:
            raise Exception("Something went wrong while reading!")
            # return random.randrange(1, 100)
        except Exception as err:
            return err

