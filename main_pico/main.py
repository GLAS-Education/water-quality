import bluetooth, math, time, json, uos, os, sdcard
from structs import Sensor, ProbeID, SensorID, LogFormat, IntentionalUndefined
from btlib.ble_simple_peripheral import BLESimplePeripheral

from sensors.main.led import StatusLED
from sensors.main.voltage import BatteryVoltage
from sensors.main.temperature import Temperature
from sensors.main.turbidity import Turbidity
from sensors.main.ph import pH


class Probe:
    def __init__(self, id):
        self.id = id
        self.sensors = {}
        self.iterations = 0

        # Add sensors from probe directory
        self.sensors[SensorID.status_led] = StatusLED()
        self.sensors[SensorID.voltage] = BatteryVoltage()
        self.sensors[SensorID.temperature] = Temperature()
        self.sensors[SensorID.turbidity] = Turbidity()
        self.sensors[SensorID.ph] = pH()

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
        print(f"{LogFormat.Foreground.ORANGE}↓ {LogFormat.RESET}Data intake loop task is about to start...")
        time.sleep(5)
        
        while True:
            data = self.read_loop()
            self.save_data(data)
            
            def check_scheduled_reboot():
                if time.localtime()[3] == 23 and time.localtime()[4] == 54 and time.localtime()[5] >= 45 and time.localtime()[5] <= 59:
                    print(LogFormat.Foreground.RED + "About to perform scheduled reboot...")
                    self.save_data(data, -10) # -10 is code for about to run a scheduled reboot
                    machine.reset()
            
            if self.iterations >= 20:
                # Scheduled reboot
                check_scheduled_reboot()
                
                # Custom: sleep time dynamic to voltage    
                if data[SensorID.voltage] >= 4.10:
                    for i in range(60):
                        self.save_data(data, 60 - i)
                        check_scheduled_reboot()
                        time.sleep(1)
                elif data[SensorID.voltage] >= 4.00:
                    for i in range(90):
                        self.save_data(data, 90 - i)
                        check_scheduled_reboot()
                        time.sleep(1)
                else:
                    for i in range(150):
                        self.save_data(data, 150 - i)
                        check_scheduled_reboot()
                        time.sleep(1)
            else:
                time.sleep(10)

    def init(self):
        time.sleep(10)
        print(f"{LogFormat.Foreground.ORANGE}~ {LogFormat.RESET}Initializing sensors for {LogFormat.Foreground.LIGHT_GREY}{self.id}{LogFormat.RESET} probe...")
        for sensor in self.sensors.values():
            result = sensor.init()
            if result and isinstance(result, bool):
                # Succeeded
                print(f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}Accessory {LogFormat.Foreground.LIGHT_GREY}{sensor.id}{LogFormat.RESET} has been initialized!")
            else:
                # Errored
                print(f"{LogFormat.Foreground.RED}X {LogFormat.RESET}Accessory {LogFormat.Foreground.LIGHT_GREY}{sensor.id}{LogFormat.RESET} has errored during initialization:")
                print(result)

    def read_loop(self):
        data = {}        
        for sensor in list(self.sensors.values()):
            value = sensor.read()
            if not isinstance(value, Exception):
                # Succeeded
                if value != IntentionalUndefined:
                    data[sensor.id] = value
            else:
                # Errored
                data[sensor.id] = "-9"
                print(f"{LogFormat.Foreground.RED}X {LogFormat.RESET}Sensor {LogFormat.Foreground.LIGHT_GREY}{sensor.id}{LogFormat.RESET} has errored during runtime:")
                print(LogFormat.Foreground.DARK_GREY + "  > " + str(value))
        
        self.iterations += 1
        return data

    def save_data(self, data, refresh_countdown = 0):
        cur_time = time.localtime()

        # Save to SD card
        if refresh_countdown != 0:
            data["_REFRESH_COUNTDOWN"] = refresh_countdown
            with open("/sd/data.txt", "a") as file:
                file.write(f"{cur_time}: {data}\n")

        # Send over Bluetooth
        ble_payload = ";".join([
            self.id,
            str(self.iterations),
            "/".join(list(map(lambda x: str(x), list(cur_time)))),
            str(data[SensorID.voltage]),
            data[SensorID.temperature].replace(",", ";"),
            str(data[SensorID.ph]),
            str(data[SensorID.turbidity]),
            str(refresh_countdown)
        ])
        if self.ble_sp.is_connected():
            self.ble_sp.send(ble_payload)

        # Print for debugging
        data["_ITERATIONS"] = self.iterations
        print()
        print(LogFormat.Foreground.DARK_GREY + "-----------------------------------")
        print(LogFormat.Foreground.LIGHT_GREY + "Time: " + LogFormat.Foreground.LIGHT_GREEN + str(cur_time) + LogFormat.Foreground.DARK_GREY)
        print(LogFormat.Foreground.LIGHT_GREY + "BLE: " + LogFormat.Foreground.LIGHT_BLUE + ("" if self.ble_sp.is_connected() else LogFormat.STRIKETHROUGH) + ble_payload + LogFormat.RESET + LogFormat.Foreground.DARK_GREY)
        print()
        print(LogFormat.Foreground.DARK_GREY + json.dumps(data).replace("{", "{\n    ").replace("}", "\n}").replace(", ", ", \n    ").replace("\"-1\"", "None").replace("\"-1,1\"", "None").replace("\"-1,-1,-1\"", "None"))
        print(LogFormat.Foreground.DARK_GREY + "-----------------------------------")


if __name__ == "__main__":
    Probe(ProbeID.main)

