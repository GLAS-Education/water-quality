"""
MicroPython-compatible RFM9x driver based on Adafruit CircuitPython library
Adapted for use on Raspberry Pi Pico and similar boards
"""

from machine import Pin, SPI
import time
import struct
import random

# Constants (partial; can expand as needed)
_REG_FIFO = 0x00
_REG_OP_MODE = 0x01
_MODE_SLEEP = 0x00
_MODE_STDBY = 0x01
_MODE_TX = 0x03
_MODE_RXCONTINUOUS = 0x05
_LONG_RANGE_MODE = 0x80
_PA_BOOST = 0x80

class RFM9x:
    def __init__(self, spi: SPI, cs: Pin, reset: Pin, frequency: float = 915.0):
        self.spi = spi
        self.cs = cs
        self.reset = reset
        self.cs.init(Pin.OUT, value=1)
        self.reset.init(Pin.OUT, value=1)

        self._reset()

        # Enter LoRa mode
        self._write_u8(_REG_OP_MODE, _MODE_SLEEP | _LONG_RANGE_MODE)
        time.sleep(0.01)
        self._write_u8(_REG_OP_MODE, _MODE_STDBY | _LONG_RANGE_MODE)

        # Set frequency
        frf = int((frequency * 1000000.0) / 61.03515625)
        self._write_u8(0x06, (frf >> 16) & 0xFF)
        self._write_u8(0x07, (frf >> 8) & 0xFF)
        self._write_u8(0x08, frf & 0xFF)

    def _reset(self):
        self.reset.value(0)
        time.sleep(0.01)
        self.reset.value(1)
        time.sleep(0.01)

    def _write_u8(self, address, value):
        self._write(address, bytes([value]))

    def _read_u8(self, address):
        return self._read(address, 1)[0]

    def _write(self, address, buffer):
        self.cs.value(0)
        self.spi.write(bytes([address | 0x80]))
        self.spi.write(buffer)
        self.cs.value(1)

    def _read(self, address, length):
        self.cs.value(0)
        self.spi.write(bytes([address & 0x7F]))
        result = self.spi.read(length)
        self.cs.value(1)
        return result

    def send(self, data: bytes):
        # Go to standby
        self._write_u8(_REG_OP_MODE, _MODE_STDBY | _LONG_RANGE_MODE)
        # Write payload to FIFO
        self._write_u8(0x0D, 0x00)  # FIFO addr ptr = 0
        self._write(0x00, data)     # Write to FIFO
        self._write_u8(0x22, len(data))
        # Send
        self._write_u8(_REG_OP_MODE, _MODE_TX | _LONG_RANGE_MODE)
        # Wait for TX done
        while (self._read_u8(0x12) & 0x08) == 0:
            time.sleep(0.01)
        # Clear IRQ
        self._write_u8(0x12, 0xFF)
        self._write_u8(_REG_OP_MODE, _MODE_STDBY | _LONG_RANGE_MODE)

    def receive(self, timeout=5):
        self._write_u8(_REG_OP_MODE, _MODE_RXCONTINUOUS | _LONG_RANGE_MODE)
        t_start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t_start) < timeout * 1000:
            irq_flags = self._read_u8(0x12)
            if irq_flags & 0x40:  # RX done
                self._write_u8(0x12, 0xFF)
                fifo_addr = self._read_u8(0x10)
                length = self._read_u8(0x13)
                self._write_u8(0x0D, fifo_addr)
                payload = self._read(_REG_FIFO, length)
                return payload
            time.sleep(0.01)
        return None