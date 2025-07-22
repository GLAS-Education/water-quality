# compat_cp.py ── tiny shim so CircuitPython drivers import under MicroPython
import sys, machine, utime, time

# ── busio.I2C ---------------------------------------------------------------
class _BusIOModule:
    pass

busio = _BusIOModule()

class I2C(machine.I2C):
    def __init__(self, *, scl, sda, frequency=400_000):
        # RP2040: use I²C-1 so GP18 (SDA) / GP19 (SCL) match CircuitPython examples
        super().__init__(1, scl=scl, sda=sda, freq=frequency)

busio.I2C = I2C
sys.modules["busio"] = busio

# ── board.GPxx --------------------------------------------------------------
class _BoardModule:
    pass

board = _BoardModule()
# Expose every GPIO as board.GP##
for pin_num in (
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
    10, 11, 12, 13, 14, 15, 16, 17,
    18, 19, 20, 21, 22, 26, 27, 28
):
    setattr(board, f"GP{pin_num}", machine.Pin(pin_num))
sys.modules["board"] = board

# ── time.monotonic ----------------------------------------------------------
if not hasattr(time, "monotonic"):
    time.monotonic = lambda: utime.ticks_ms() / 1000