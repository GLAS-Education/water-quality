import typing, random, traceback
from struct import Sensor, SensorID


class TesterSensor(Sensor):
    def __init__(self):
        super().__init__(SensorID.tester)

    def init(self) -> typing.Union[bool, list[str]]:
        try:
            raise Exception("Something went wrong!")
        except Exception as err:
            return traceback.format_exception(err)

    def read(self) -> typing.Any:
        return random.randrange(0, 100)


sensor = TesterSensor()
