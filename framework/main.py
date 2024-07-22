import bluetooth, time, json, uos, os, sdcard
from structs import Sensor, ProbeID, SensorID, LogFormat
from sensors.demo.tester import TesterSensor
from btlib.ble_simple_peripheral import BLESimplePeripheral


class Probe:
    def __init__(self, id):
        self.id = id
        self.sensors = {}
        self.delay = 1  # second(s)

        # Add sensors from probe directory
        self.sensors[SensorID.tester] = TesterSensor()

        # Connect to Bluetooth
        ble = bluetooth.BLE()
        self.ble_sp = BLESimplePeripheral(ble)
        
        # Setup SD card
        cs = machine.Pin(1, machine.Pin.OUT)
        spi = machine.SPI(0, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=machine.SPI.MSB, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
        sd = sdcard.SDCard(spi, cs)
        vfs = uos.VfsFat(sd)
        uos.mount(vfs, "/sd")
        
        print(f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}Accessory {LogFormat.Foreground.LIGHT_GREY}SD_CARD{LogFormat.RESET} has been initialized!")

        self.init()
        while True:
            data = self.read_loop()
            self.save_data(data)
            time.sleep(self.delay)

    def init(self):
        print(f"{LogFormat.Foreground.ORANGE}~ {LogFormat.RESET}Initializing sensors for {LogFormat.Foreground.LIGHT_GREY}{self.id}{LogFormat.RESET} probe...")
        for sensor in self.sensors.values():
            result = sensor.init()
            if result and isinstance(result, bool):
                # Succeeded
                print(f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}Sensor {LogFormat.Foreground.LIGHT_GREY}{sensor.id}{LogFormat.RESET} has been initialized!")
            else:
                # Errored
                print(f"{LogFormat.Foreground.RED}X {LogFormat.RESET}Sensor {LogFormat.Foreground.LIGHT_GREY}{sensor.id}{LogFormat.RESET} has errored during initialization:")
                print(result)
        print(f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}Data intake loop task has started!")

    def read_loop(self):
        data = {}
        for sensor in self.sensors.values():
            value = sensor.read()
            if not isinstance(value, Exception):
                # Succeeded
                data[sensor.id] = value
            else:
                # Errored
                print(f"{LogFormat.Foreground.RED}X {LogFormat.RESET}Sensor {LogFormat.Foreground.LIGHT_GREY}{sensor.id}{LogFormat.RESET} has errored during initialization:")
                print(LogFormat.Foreground.DARK_GREY + "  > " + str(value))
        return data

    def save_data(self, data):
        cur_time = time.localtime()

        # Save to SD card
        with open("/sd/data.txt", "a") as file:
            file.write(f"{cur_time}: {data}\n")

        # Send over Bluetooth
        ble_fields = list(map(lambda x: str(x).replace(";", "~"), [",".join(list(map(lambda x: str(x), list(cur_time))))] + list(data.values())))
        ble_payload = ";".join(ble_fields)
        if self.ble_sp.is_connected():
            self.ble_sp.send(ble_payload)

        # Print for debugging
        print()
        print(LogFormat.Foreground.DARK_GREY + "-----------------------------------")
        print(LogFormat.Foreground.LIGHT_GREY + "Time: " + LogFormat.Foreground.LIGHT_GREEN + str(cur_time) + LogFormat.Foreground.DARK_GREY)
        print(LogFormat.Foreground.LIGHT_GREY + "BLE: " + LogFormat.Foreground.LIGHT_BLUE + ("" if self.ble_sp.is_connected() else LogFormat.STRIKETHROUGH) + ble_payload + LogFormat.RESET + LogFormat.Foreground.DARK_GREY)
        print()
        print(LogFormat.Foreground.DARK_GREY + json.dumps(data))
        print(LogFormat.Foreground.DARK_GREY + "-----------------------------------")


if __name__ == "__main__":
    Probe(ProbeID.demo)
