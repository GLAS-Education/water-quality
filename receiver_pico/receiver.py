# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries 
# SPDX-License-Identifier: MIT

# MicroPython version of RFM9x communication example.
# Adapted by ChatGPT for Raspberry Pi Pico with MicroPython.

from machine import Pin, SPI
import time
from adafruit_rfm9x import RFM9x

# Define radio parameters.
RADIO_FREQ_MHZ = 915.0  # Frequency of the radio in MHz

# Define pins connected to the chip
CS = Pin(5, Pin.OUT)
RESET = Pin(0, Pin.OUT)
LED = Pin(15, Pin.OUT)
LED2 = Pin(16, Pin.OUT)

# Initialize SPI bus
spi = SPI(0, baudrate=5000000, polarity=0, phase=0, sck=Pin(6), mosi=Pin(7), miso=Pin(4))

# Initialize RFM radio
rfm9x = RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
rfm9x.tx_power = 23

print("Waiting for packets...")

while True:
    time.sleep(0.1)
    packet = rfm9x.receive()
    if packet is None:
        LED.value(0)
        LED2.value(1)
        print("Received nothing! Listening again...")
    else:
        LED.value(1)
        LED2.value(0)
        print(f"Received (raw bytes): {packet}")
        try:
            packet_text = packet[4:].decode('utf-8')

            print(f"Received (ASCII): {packet_text}")
        except:
            print("Could not decode packet")
        #print("Received signal strength: N/A (RSSI not yet implemented)")
