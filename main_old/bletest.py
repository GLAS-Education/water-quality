import machine, bluetooth, time
from btlib.ble_simple_peripheral import BLESimplePeripheral
from machine import Pin, ADC, I2C, RTC

ble = bluetooth.BLE()
ble_sp = BLESimplePeripheral(ble)

def on_rx(v):
    print("RX", v)

ble_sp.on_write(on_rx)

i = 0
while True:
    if ble_sp.is_connected():
        ble_sp.send(f"MAIN;{i}")
        i += 1
    time.sleep_ms(1)
