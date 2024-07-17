import typing, os

from struct import Sensor, ProbeID, LogFormat


class Probe:
    id: ProbeID
    sensors: typing.Dict[str, Sensor]

    def __init__(self, id: ProbeID):
        self.id = id
        self.sensors = {}
        self.delay = 1  # second(s)

        # Add sensors from probe directory
        for name in os.listdir(f"./sensors/{self.id.name}"):
            if name.endswith(".py"):
                module_name = f"sensors.{self.id.name}.{name[:-3]}"
                sensor = __import__(module_name, fromlist=["sensor"]).sensor
                self.sensors[sensor.id.name] = sensor

        self.init()
        while True:
            data = self.read_loop()
            self.save_data(data)

    def init(self):
        for sensor in self.sensors.values():
            result = sensor.init()
            if result and isinstance(result, bool):
                # Succeeded
                print(
                    f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}Sensor {LogFormat.Foreground.LIGHT_GREY}{sensor.id.name}{LogFormat.RESET} has been initialized!")
            else:
                # Errored
                print(
                    f"{LogFormat.Foreground.RED}X {LogFormat.RESET}Sensor {LogFormat.Foreground.LIGHT_GREY}{sensor.id.name}{LogFormat.RESET} has errored during initialization:")
                for err in result:
                    print(f"{LogFormat.Foreground.DARK_GREY}  > {err[:-2].replace("\n", "\n    ")}{LogFormat.RESET}")

    def read_loop(self) -> typing.Dict[str, typing.Any]:
        pass

    def save_data(self, data: typing.Dict[str, typing.Any]) -> None:
        pass


if __name__ == "__main__":
    Probe(ProbeID.main)
