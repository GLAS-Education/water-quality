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
            print(self.roms)
            if len(self.roms) != 4:
                raise Exception("Could not find one or more configured temperature sensor.")
            self.read()
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            self.sensor.convert_temp()
            for rom in self.roms:
                if rom == bytearray(b'(Pl\x81\xe3j<\xd5'):
                    temp1 = round(self.sensor.read_temp(rom), 2)
                if rom == bytearray(b'(\xff\xa6v\x90\x15\x03\x9f'):
                    temp2 = round(self.sensor.read_temp(rom), 2)
                if rom == bytearray(b'(.oI\xf6b<<'):
                    temp3 = round(self.sensor.read_temp(rom), 2)
                elif rom == bytearray(b'(h\x8du@$\x0b\x99'):
                    temp4 = round(self.sensor.read_temp(rom), 2)
            return f"{temp1},{temp2},{temp3},{temp4}"
        except Exception as err:
            return err



