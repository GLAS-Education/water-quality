import bluetooth, math, time, json, uos, os, sdcard, machine
from structs import Sensor, ProbeID, SensorID, LogFormat, IntentionalUndefined
from btlib.ble_simple_peripheral import BLESimplePeripheral
from machine import I2C, RTC, Pin
import ds1307

from sensors.wake.led import StatusLED
from sensors.wake.audio import Hydrophone
from sensors.wake.absrot import AbsoluteOrientation
from sensors.wake.water import WaterLevel


class Probe:
    def __init__(self, id):
        self.id = id
        self.sensors = {}
        self.sensor_order = [
            SensorID.status_led,
            SensorID.hydrophone,
            SensorID.absrot,
            SensorID.water_level
        ]
        self.delay = 0.25  # second(s)
        self.iterations = 0
        self.last_rot = (0.0, 0.0, 0.0) # Unique to `absrot`

        # Add sensors from probe directory
        self.sensors[SensorID.status_led] = StatusLED()
        self.sensors[SensorID.hydrophone] = Hydrophone()
        self.sensors[SensorID.absrot] = AbsoluteOrientation()
        self.sensors[SensorID.water_level] = WaterLevel()

        # Connect to Bluetooth
        ble = bluetooth.BLE()
        self.ble_sp = BLESimplePeripheral(ble)
        
        # Setup RTC
        i2c = I2C(0, scl=Pin(17), sda=Pin(16))
        ds = ds1307.DS1307(i2c)
        ds = ds.datetime()
        self.rtc = RTC()
        self.rtc.datetime((ds[0], ds[1], ds[2], ds[3]+1, ds[4], ds[5], ds[6], 0))
        print(f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}Accessory {LogFormat.Foreground.LIGHT_GREY}RTC{LogFormat.RESET} has been initialized!")
        
        # Setup SD card
        cs = machine.Pin(1, machine.Pin.OUT)
        spi = machine.SPI(0, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=machine.SPI.MSB, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
        sd = sdcard.SDCard(spi, cs)
        vfs = uos.VfsFat(sd)
        uos.mount(vfs, "/sd")
        
        print(f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}Accessory {LogFormat.Foreground.LIGHT_GREY}SD_CARD{LogFormat.RESET} has been initialized!")

        self.init()
        print(f"{LogFormat.Foreground.GREEN}↓ {LogFormat.RESET}Data intake loop task is about to start...")
        time.sleep(5)
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

    def read_loop(self):
        data = {}
        force_error = False
        read_all_sensors = True  # Toggle: Set to False to use hydrophone activation logic
        sorted_sensors = [None] * len(list(self.sensors.keys()))
        for key, value in list(self.sensors.items()):
            sorted_sensors[self.sensor_order.index(key)] = value
        
        for sensor in sorted_sensors:
            value = sensor.read()
            if not force_error and not isinstance(value, Exception):
                # Succeeded
                if value != IntentionalUndefined:
                    data[sensor.id] = value
                    
                # [Custom]: Hydrophone activation reliance
                if isinstance(sensor, Hydrophone) and not read_all_sensors:
                    # Don't read other sensors if it's been >600 seconds since the last loud noise
                    if not sensor.last_loud or time.mktime(time.localtime()) - sensor.last_loud > 600:
                        force_error = True
            else:
                # Errored
                if force_error:                
                    data[sensor.id] = self.sensors[sensor.id].forced_error_value
                else:
                    data[sensor.id] = "-9"
                    print(f"{LogFormat.Foreground.RED}X {LogFormat.RESET}Sensor {LogFormat.Foreground.LIGHT_GREY}{sensor.id}{LogFormat.RESET} has errored during runtime:")
                    print(LogFormat.Foreground.DARK_GREY + "  > " + str(value))
        
        self.iterations += 1
        return data

    def save_data(self, data):
        cur_time = self.rtc.datetime()

        # Save to SD card
        with open("/sd/data.txt", "a") as file:
            file.write(f"{cur_time}: {data}\n")
        
        # Send over Bluetooth
        radian_rot = ",".join(list(map(lambda x: str((math.pi / 180) * float(x)), data[SensorID.absrot].split(","))))
        ble_payload = ";".join([
            self.id,
            str(self.iterations),
            "/".join(list(map(lambda x: str(x), list(cur_time)))),
            str(min(data[SensorID.hydrophone], 3)),
            str(data[SensorID.water_level]),
            ";".join(["-1"] if data[SensorID.absrot] == -1 else radian_rot.split(",")[0:3]),
            str(min(abs((self.last_rot[0] - float(radian_rot.split(",")[0])) + (self.last_rot[1] - float(radian_rot.split(",")[1])) + (self.last_rot[2] - float(radian_rot.split(",")[2]))), 40))
        ])
        self.last_rot = list(map(lambda x: float(x if x != -1 else 0), radian_rot.split(",")))[0:3]
        if self.ble_sp.is_connected():
            self.ble_sp.send(ble_payload)

        # Print for debugging
        print()
        print(LogFormat.Foreground.DARK_GREY + "-----------------------------------")
        print(LogFormat.Foreground.LIGHT_GREY + "Time: " + LogFormat.Foreground.LIGHT_GREEN + str(cur_time) + LogFormat.Foreground.DARK_GREY)
        print(LogFormat.Foreground.LIGHT_GREY + "BLE: " + LogFormat.Foreground.LIGHT_BLUE + ("" if self.ble_sp.is_connected() else LogFormat.STRIKETHROUGH) + ble_payload + LogFormat.RESET + LogFormat.Foreground.DARK_GREY)
        print()
        print(LogFormat.Foreground.DARK_GREY + json.dumps(data).replace("{", "{\n    ").replace("}", "\n}").replace(", ", ", \n    ").replace("\"-1\"", "None").replace("\"-1,1\"", "None").replace("\"-1,-1,-1\"", "None"))
        print(LogFormat.Foreground.DARK_GREY + "-----------------------------------")


if __name__ in ["main", "__main__"]: # mpremote exec, startup
    Probe(ProbeID.wake)