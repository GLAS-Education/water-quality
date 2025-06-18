import machine, ds18x20, onewire
from base import BaseModule
from logging import log

class Module(BaseModule):
    def __init__(self):
        super().__init__("temperature")
        self.pin = machine.Pin(13)
        self.sensor = None
        self.roms = []
        self.initialized = False
        
    def _init_sensor(self):
        """Initialize the temperature sensor if not already done"""
        if not self.initialized:
            self.sensor = ds18x20.DS18X20(onewire.OneWire(self.pin))
            self.roms = self.sensor.scan()
            if len(self.roms) == 0:
                raise Exception("Could not find any configured temperature sensor.")
            elif len(self.roms) != 4:
                raise Exception("Could not find one or more configured temperature sensors; next startup will be allowed anyways, since at least one is present.")
            self.initialized = True
        elif len(self.roms) != 4:
            log("Starting with less than 4 sensors...", "info", self.id)
        log("Setup complete!", "success", self.id)

    def read(self) -> dict:
        self._init_sensor()
        
        self.sensor.convert_temp()
        
        temp1 = None
        temp2 = None
        temp3 = None
        temp4 = None
        
        for rom in self.roms:
            if rom == bytearray(b'(\xb8\xce\x81\xe3\xee<\xf9'):
                temp1 = round(self.sensor.read_temp(rom), 2)
            if rom == bytearray(b'(\xbb\x19I\xf6\x13<\xe5'):
                temp2 = round(self.sensor.read_temp(rom), 2)
            if rom == bytearray(b'(\xbd\x17\xd9\x0e\x00\x00\x18'):
                temp3 = round(self.sensor.read_temp(rom), 2)
            elif rom == bytearray(b'(\r\xe9\xd0\x0e\x00\x00\x88'):
                temp4 = round(self.sensor.read_temp(rom), 2)
        
        return {
            "sensor1_celsius": temp1,
            "sensor2_celsius": temp2,
            "sensor3_celsius": temp3,
            "sensor4_celsius": temp4
        }

    def pretty_print(self, data: dict) -> str:
        temp1 = data.get('sensor1_celsius')
        temp2 = data.get('sensor2_celsius')
        temp3 = data.get('sensor3_celsius')
        temp4 = data.get('sensor4_celsius')
        
        result = ""

        if temp1 is not None:
            result += f"Depth 1 = {temp1}°C\n"
        else:
            result += f"Depth 1 = No reading\n"
            
        if temp2 is not None:
            result += f"Depth 2 = {temp2}°C\n"
        else:
            result += f"Depth 2 = No reading\n"

        if temp3 is not None:
            result += f"Depth 3 = {temp3}°C\n"
        else:
            result += f"Depth 3 = No reading\n"

        if temp4 is not None:
            result += f"Depth 4 = {temp4}°C"
        else:
            result += f"Depth 4 = No reading"
            
        return result
