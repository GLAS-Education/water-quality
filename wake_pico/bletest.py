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

i = 0
old_rot = (0, 0, 0)
while True:
    if ble_sp.is_connected():
        rotation_change = abs(bno055_sensor.euler[0] - old_rot[0]) + abs(bno055_sensor.euler[1] - old_rot[1]) + abs(bno055_sensor.euler[2] - old_rot[2])
        old_rot = bno055_sensor.euler
        water_detected = water.read_u16()
        sound_reading = round(analog_value.read_u16() * conversion_factor, 2)
        print(sound_reading, analog_value.read_u16())
        ble_sp.send(f"WAKE;{i};{sound_reading};{water_detected};{bno055_sensor.euler[0]};{bno055_sensor.euler[1]};{bno055_sensor.euler[2]};{rotation_change}")
        i += 1
    time.sleep_ms(1)
