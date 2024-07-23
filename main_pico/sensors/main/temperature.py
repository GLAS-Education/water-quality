import machine, ds18x20, onewire
from structs import Sensor, SensorID


class Temperature(Sensor):
    def __init__(self):
        super().__init__(SensorID.temperature)
        self.pin = machine.Pin(13)

    def init(self):
        try:
            self.sensor = ds18x20.DS18X20(onewire.OneWire(self.pin))
            self.roms = self.sensor.scan()
            if len(self.roms) != 2:
                raise Exception("Could not find one or more configured temperature sensor.")
            self.read()
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            for rom in self.roms:
                if rom == bytearray(b'(\x99\xb2\x96\xf0\x01<I'):
                    temp1 = round(self.sensor.read_temp(rom), 2)
                elif rom == bytearray(b'(/\xbcI\xf6\xcf<|'):
                    temp2 = round(self.sensor.read_temp(rom), 2)
            return f"{temp1},{temp2}"
        except Exception as err:
            return err



