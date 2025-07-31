import math, time, json, uos, os, sdcard, ds1307, network, urequests
from structs import Sensor, ProbeID, SensorID, LogFormat, IntentionalUndefined
from machine import I2C, Pin, RTC
import machine
# from sensors.main.led import StatusLED
from sensors.main.battery import Battery
from sensors.main.temperature import Temperature
# from sensors.main.turbidity import Turbidity
from sensors.main.ph import pH
from sensors.main.tds import TDS

EXPERIMENT_ID = ""
API_ENDPOINT = ""
API_KEY = ""
WIFI_NAME = ""
WIFI_PASSWORD = ""


class Probe:
    def __init__(self, id):
        self.id = id
        self.sensors = {}
        self.iterations = 0

        # Add sensors from probe directory
        # self.sensors[SensorID.status_led] = StatusLED()
        self.sensors[SensorID.voltage] = Battery()
        self.sensors[SensorID.temperature] = Temperature()
        # self.sensors[SensorID.turbidity] = Turbidity()
        self.sensors[SensorID.ph] = pH()
        self.sensors[SensorID.tds] = TDS()

        # Connect to WiFi
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.api_url = API_ENDPOINT
        self.api_key = API_KEY
        
        self.connect_wifi()
        
        # Setup RTC
        i2c = I2C(1, scl=Pin(11), sda=Pin(10))
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
        print(f"{LogFormat.Foreground.ORANGE}↓ {LogFormat.RESET}Data intake loop is about to start...")
        time.sleep(5)
                
        while True:
            data = self.read_loop()
            self.save_data(data)
            
            def check_scheduled_reboot():
                if self.rtc.datetime()[3] == 23 and self.rtc.datetime()[4] == 54 and self.rtc.datetime()[5] >= 45 and self.rtc.datetime()[5] <= 59:
                    print(LogFormat.Foreground.RED + "About to perform scheduled reboot...")
                    self.save_data(data, -10) # -10 is code for about to run a scheduled reboot
                    machine.reset()
            
            if self.iterations >= 20:
                # Scheduled reboot
                check_scheduled_reboot()
                
                # Custom: sleep time dynamic to battery percentage
                if data[SensorID.voltage] >= 90.0:  # 90% battery
                    for i in range(60):
                        self.save_data(data, 60 - i)
                        check_scheduled_reboot()
                        time.sleep(1)
                elif data[SensorID.voltage] >= 80.0:  # 80% battery
                    for i in range(90):
                        self.save_data(data, 90 - i)
                        check_scheduled_reboot()
                        time.sleep(1)
                else:  # Low battery
                    for i in range(150):
                        self.save_data(data, 150 - i)
                        check_scheduled_reboot()
                        time.sleep(1)
            else:
                for i in range(10):
                   self.save_data(data, 10 - i)
                   time.sleep(1)
    
    def connect_wifi(self):
        """Connect to WiFi network"""
        print(f"{LogFormat.Foreground.ORANGE}~ {LogFormat.RESET}Connecting to WiFi...")
        
        if not self.wlan.isconnected():
            self.wlan.connect(WIFI_NAME, WIFI_PASSWORD)
            
            # Wait for connection with timeout
            timeout = 30  # 30 seconds timeout
            start_time = time.time()
            
            while not self.wlan.isconnected():
                if time.time() - start_time > timeout:
                    print(f"{LogFormat.Foreground.RED}X {LogFormat.RESET}WiFi connection timeout!")
                    return False
                time.sleep(1)
        
        print(f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}WiFi connected!")
        print(f"{LogFormat.Foreground.LIGHT_GREY}IP address: {self.wlan.ifconfig()[0]}{LogFormat.RESET}")
        return True
    
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

    def send_to_api(self, api_data):
        """Send data to the API via HTTP POST"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        try:
            # Check WiFi connection and reconnect if needed
            if not self.wlan.isconnected():
                print(f"{LogFormat.Foreground.ORANGE}~ {LogFormat.RESET}WiFi disconnected, attempting to reconnect...")
                if not self.connect_wifi():
                    return False
            
            response = urequests.post(
                self.api_url,
                json=api_data,
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"{LogFormat.Foreground.GREEN}✓ {LogFormat.RESET}Data sent to API successfully")
                response.close()
                return True
            else:
                print(f"{LogFormat.Foreground.RED}X {LogFormat.RESET}API request failed: {response.status_code}")
                response.close()
                return False
                
        except Exception as e:
            print(f"{LogFormat.Foreground.RED}X {LogFormat.RESET}Error sending to API: {e}")
            return False

    def save_data(self, data, refresh_countdown = 0):
        cur_time = self.rtc.datetime() #Sometimes wants ()(), if getting tuple error reduce to ()

        # Save to SD card
        data["_ITERATIONS"] = self.iterations
        data[SensorID.turbidity] = -5 # TEMP/TODO
        if refresh_countdown != 0:
            data["_REFRESH_COUNTDOWN"] = refresh_countdown
        else:
            with open("/sd/data.txt", "a") as file:
                file.write(f"{cur_time}: {data}\n")

        # Prepare data for API
        # Parse temperature data (assuming it's comma-separated for 4 sensors)
        temp_values = str(data.get(SensorID.temperature, "-1,-1,-1,-1")).split(",")
        while len(temp_values) < 4:
            temp_values.append("-1")
        
        api_payload = {
            "experiment_id": EXPERIMENT_ID,
            "temperature_1": float(temp_values[0]) if temp_values[0] != "-9" else None,
            "temperature_2": float(temp_values[1]) if temp_values[1] != "-9" else None,
            "temperature_3": float(temp_values[2]) if temp_values[2] != "-9" else None,
            "temperature_4": float(temp_values[3]) if temp_values[3] != "-9" else None,
            "ph": float(data.get(SensorID.ph, -1)) if data.get(SensorID.ph, -1) != "-9" else None,
            "battery_level": float(data.get(SensorID.voltage, -1)) if data.get(SensorID.voltage, -1) != "-9" else None,
            "tds": float(data.get(SensorID.tds, -1)) if data.get(SensorID.tds, -1) != "-9" else None,
            "turbidity": float(data.get(SensorID.turbidity, -1)) if data.get(SensorID.turbidity, -1) != "-9" else None
        }
        
        # Send to API if not in countdown mode
        api_success = False
        if refresh_countdown == 0:
            api_success = self.send_to_api(api_payload)

        # Print for debugging
        print()
        print(LogFormat.Foreground.DARK_GREY + "-----------------------------------")
        print(LogFormat.Foreground.LIGHT_GREY + "Time: " + LogFormat.Foreground.LIGHT_GREEN + str(cur_time) + LogFormat.Foreground.DARK_GREY)
        print(LogFormat.Foreground.LIGHT_GREY + "API: " + LogFormat.Foreground.LIGHT_BLUE + ("N/A" if refresh_countdown != 0 else ("✓ Sent" if api_success else "✗ Failed")) + LogFormat.RESET + LogFormat.Foreground.DARK_GREY)
        print()
        print(LogFormat.Foreground.DARK_GREY + json.dumps(data).replace("{", "{\n    ").replace("}", "\n}").replace(", ", ", \n    ").replace("\"-9\"", "Exception").replace("\"-1\"", "None").replace("\"-1,1\"", "None").replace("\"-1,-1,-1\"", "None"))
        print(LogFormat.Foreground.DARK_GREY + "-----------------------------------")


if __name__ in ["main", "__main__"]: # mpremote exec, startup
    Probe(ProbeID.main)

