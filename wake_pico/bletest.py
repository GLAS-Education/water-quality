from machine import ADC, Pin
from btlib.ble_simple_peripheral import BLESimplePeripheral
import bluetooth
import machine
import time

ble = bluetooth.BLE()
ble_sp = BLESimplePeripheral(ble)

def on_rx(v):
    print("RX", v)

ble_sp.on_write(on_rx)

i = 0
while True:
    if ble_sp.is_connected():
        water = ADC(Pin(26))
        conversion_factor = 3.3/65535
        while True:
            water_detected = water.read_u16()
            ble_sp.send(f"{i};{water_detected}")
            i += 1
    time.sleep_ms(100)
