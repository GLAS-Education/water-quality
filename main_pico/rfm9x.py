# SPDX-FileCopyrightText: 2025
# SPDX-License-Identifier: MIT
"""
Minimal MicroPython LoRa driver (SX1276/78 RFM9x) – **Transmit Only**
====================================================================
This extremely small driver does just one job: send a text packet over LoRa.
All receive/path/ACK/CRC features are stripped for simplicity & reliability on
resource-constrained boards.

Example (Raspberry Pi Pico):
    from machine import SPI, Pin
    import rfm9x

    spi  = SPI(0, baudrate=5_000_000, polarity=0, phase=0)
    cs   = Pin(17, Pin.OUT)   # Chip-select pin
    rst  = Pin(16, Pin.OUT)   # Reset pin

    radio = rfm9x.RFM9x(spi, cs, rst, frequency=915.0, tx_power=17)
    radio.send_text("Hello LoRa!")
"""

from micropython import const
from machine import Pin, SPI
import time
from typing import Union

# ---------------------------------------------------------------------------
# Register map (subset)
# ---------------------------------------------------------------------------
_REG_FIFO            = const(0x00)
_REG_OP_MODE         = const(0x01)
_REG_FRF_MSB         = const(0x06)
_REG_FRF_MID         = const(0x07)
_REG_FRF_LSB         = const(0x08)
_REG_PA_CONFIG       = const(0x09)
_REG_FIFO_ADDR_PTR   = const(0x0D)
_REG_FIFO_TX_BASE    = const(0x0E)
_REG_PAYLOAD_LENGTH  = const(0x22)
_REG_IRQ_FLAGS       = const(0x12)

# ---------------------------------------------------------------------------
# Bit masks / helper constants
# ---------------------------------------------------------------------------
_LONG_RANGE_MODE = const(0x80)  # Enables LoRa mode when set in _REG_OP_MODE
_OPMODE_SLEEP    = const(0x00)
_OPMODE_STDBY    = const(0x01)
_OPMODE_TX       = const(0x03)

_IRQ_TX_DONE = const(0x08)      # Bit 3 of _REG_IRQ_FLAGS

# Frequency helper constants
_FXOSC  = 32_000_000            # Crystal oscillator frequency (Hz)
_FSTEP  = _FXOSC / (1 << 19)    # Register step = FXOSC / 2^19

class RFM9x:
    """Tiny transmit-only SX1276 driver."""

    def __init__(
        self,
        spi: SPI,
        cs: Pin,
        reset: Pin,
        *,
        frequency: float = 915.0,
        tx_power: int = 17,
        timeout_ms: int = 2000,
    ) -> None:
        self.spi = spi
        self.cs  = cs
        self.rst = reset
        self.timeout_ms = timeout_ms

        # Ensure correct pin states & directions.
        self.cs.init(Pin.OUT, value=1)
        self.rst.init(Pin.OUT, value=1)

        # Hardware reset – 100 µs low pulse.
        self.rst.value(0)
        time.sleep_us(100)
        self.rst.value(1)
        time.sleep_ms(5)

        # LoRa sleep then standby.
        self._write_reg(_REG_OP_MODE, _LONG_RANGE_MODE | _OPMODE_SLEEP)
        self._write_reg(_REG_OP_MODE, _LONG_RANGE_MODE | _OPMODE_STDBY)

        # Set FIFO base pointer to 0 for TX.
        self._write_reg(_REG_FIFO_TX_BASE, 0x00)
        self._write_reg(_REG_FIFO_ADDR_PTR, 0x00)

        # Configure frequency and power.
        self.set_frequency(frequency)
        self.set_tx_power(tx_power)

        # Minimal modem config: 125 kHz BW, CR 4/5, SF 7  (RadioHead default)
        self._write_reg(0x1D, 0x72)   # RegModemConfig1
        self._write_reg(0x1E, 0x74)   # RegModemConfig2
        self._write_reg(0x26, 0x04)   # RegModemConfig3 (AGC auto on)

        # Clear pending IRQs.
        self._write_reg(_REG_IRQ_FLAGS, 0xFF)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def send_text(self, text: Union[str, bytes]) -> None:
        """Send *text* (str / bytes) over LoRa. Blocks until TX done."""
        if isinstance(text, str):
            data = text.encode()
        else:
            data = bytes(text)
        if not (1 <= len(data) <= 255):
            raise ValueError("Packet length must be 1–255 bytes")

        # Standby, point FIFO pointer to TX base.
        self._write_reg(_REG_OP_MODE, _LONG_RANGE_MODE | _OPMODE_STDBY)
        self._write_reg(_REG_FIFO_ADDR_PTR, 0x00)

        # Burst-write payload to FIFO.
        self.cs.value(0)
        self.spi.write(bytearray([_REG_FIFO | 0x80]))  # Write burst header
        self.spi.write(data)
        self.cs.value(1)

        # Payload length register.
        self._write_reg(_REG_PAYLOAD_LENGTH, len(data))

        # Start transmission.
        self._write_reg(_REG_OP_MODE, _LONG_RANGE_MODE | _OPMODE_TX)

        # Wait for TxDone or timeout.
        start = time.ticks_ms()
        while (self._read_reg(_REG_IRQ_FLAGS) & _IRQ_TX_DONE) == 0:
            if time.ticks_diff(time.ticks_ms(), start) > self.timeout_ms:
                raise TimeoutError("LoRa transmit timeout")
        # Clear all IRQ flags.
        self._write_reg(_REG_IRQ_FLAGS, 0xFF)

    # ------------------------------------------------------------------
    # Helpers – frequency & power
    # ------------------------------------------------------------------
    def set_frequency(self, freq_mhz: float) -> None:
        frf = int(freq_mhz * 1_000_000 / _FSTEP)
        self._write_reg(_REG_FRF_MSB, (frf >> 16) & 0xFF)
        self._write_reg(_REG_FRF_MID, (frf >> 8)  & 0xFF)
        self._write_reg(_REG_FRF_LSB, frf & 0xFF)

    def set_tx_power(self, level: int = 17) -> None:
        level = max(2, min(level, 17))
        # PA_BOOST (bit 7) + OutputPower bits (0–15, level-2 gives 2–17 dBm)
        self._write_reg(_REG_PA_CONFIG, 0x80 | (level - 2))

    # ------------------------------------------------------------------
    # Low-level SPI register access
    # ------------------------------------------------------------------
    def _write_reg(self, addr: int, value: int) -> None:
        self.cs.value(0)
        self.spi.write(bytearray([addr | 0x80, value & 0xFF]))
        self.cs.value(1)

    def _read_reg(self, addr: int) -> int:
        self.cs.value(0)
        self.spi.write(bytearray([addr & 0x7F]))
        result = self.spi.read(1, 0x00)
        self.cs.value(1)
        return result[0]

