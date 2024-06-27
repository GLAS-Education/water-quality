import machine, onewire, ds18x20, time, sdcard, uos, ds1307, board, busio, adafruit_bno055, network, socket, _thread, bluetooth
from btlib.ble_simple_peripheral import BLESimplePeripheral
from machine import Pin, ADC, I2C, RTC

ble = bluetooth.BLE()
ble_sp = BLESimplePeripheral(ble)

def on_rx(v):
    print("RX", v)

ble_sp.on_write(on_rx)

water = ADC(Pin(26))
i2c = busio.I2C(scl=board.GP19, sda=board.GP18)
bno055_sensor = adafruit_bno055.BNO055_I2C(i2c)
conversion_factor = 3.3/65535
sound_average = 0
potential_wave = 0
wave_detected = False
microphone_disturbance_list = []
analog_value = machine.ADC(28)
conversion_factor = 3.3/(65535)
i3c=I2C(0, scl=Pin(17), sda=Pin(16))
r=machine.RTC()
ds = ds1307.DS1307(i3c)
ds.halt(False)    #Reads the RTC
ds = ds.datetime()
#print(ds)
rtc = RTC()
rtc.datetime((ds[0], ds[1], ds[2], ds[3]+1, ds[4], ds[5], ds[6], 0))

i = 0
old_rot = (0, 0, 0)
while True:
    if ble_sp.is_connected():
        clock = rtc.datetime()
        year = str(clock[0])
        month = str(clock[1])
        #Sets individual parts of time and ensures that every aspect of the time is a constant number of digits
        if len(month) == 1:
            month = "0"+month
        day = str(clock[2])
        if len(day) == 1:
            day = "0"+day
        hour = str(clock[4])
        if len(hour) == 1:
            hour = "0"+hour
        minute = str(clock[5])
        if len(minute) == 1:
            minute = "0"+minute
        second = str(clock[6])
        if len(second) == 1:
            second = "0"+second
        #Sets the date in a readable and compact format
        date = (year + "-" + month + "-" + day + ";" + hour + ":" + minute + ":" + second)
        rotation_change = abs(bno055_sensor.euler[0] - old_rot[0]) + abs(bno055_sensor.euler[1] - old_rot[1]) + abs(bno055_sensor.euler[2] - old_rot[2])
        old_rot = bno055_sensor.euler
        water_detected = water.read_u16()
        sound_reading = round(analog_value.read_u16() * conversion_factor, 2)
        print(sound_reading, analog_value.read_u16())
        ble_date = date.replace(";", "~")
        ble_sp.send(f"WAKE;{i};{ble_date};{sound_reading};{water_detected};{bno055_sensor.euler[0]};{bno055_sensor.euler[1]};{bno055_sensor.euler[2]};{rotation_change}")
        i += 1
    time.sleep_ms(1)
