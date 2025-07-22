# sensors/wake/absrot.py
#
# Drop-in replacement for the BNO055 wrapper, now talking to a BNO085/BNO08x
# via Dobodu’s MicroPython I²C driver (https://github.com/dobodu/BOSCH-BNO085-I2C-micropython-library).
#
# Copy bno08x.py (and its folder, if present) into /lib on your board,
# then place this file alongside structs.py.

import machine
from structs import Sensor, SensorID
import bno08x  # Dobodu MicroPython library

class AbsoluteOrientation(Sensor):
    def __init__(self):
        super().__init__(SensorID.absrot)
        self.forced_error_value = "-1,-1,-1"

    # ─────────────────────────── init ───────────────────────────────────────
    def init(self):
        try:
            # Pico’s I²C-1 on GP18 (SDA) / GP19 (SCL)
            self.i2c = machine.I2C(1, scl=machine.Pin(19),
                                      sda=machine.Pin(18),
                                      freq=400_000)
            # Create the sensor object
            self.sensor = bno08x.BNO08X(self.i2c)

            # Enable the four data streams we’ll read
            for rpt in (
                bno08x.BNO_REPORT_ACCELEROMETER,
                bno08x.BNO_REPORT_GYROSCOPE,
                bno08x.BNO_REPORT_LINEAR_ACCELERATION,
                bno08x.BNO_REPORT_ROTATION_VECTOR,
                bno08x.BNO_REPORT_GAME_ROTATION_VECTOR,
            ):
                self.sensor.enable_feature(rpt)

            return True
        except Exception as err:
            return err

    # ─────────────────────────── read ───────────────────────────────────────
    def read(self):
        """
        Returns a 16-value CSV string:

            yaw,pitch,roll,
            ax,ay,az,
            gx,gy,gz,
            qx,qy,qz,qw,
            lax,lay,laz
        """
        try:
            s = self.sensor

            euler = s.euler              # (Roll, Tilt, Pan) in ° – same tuple-length
            accel = s.acc               # m s⁻²
            gyro  = s.gyro              # rad s⁻¹
            quat  = s.quaternion        # (x, y, z, w)
            lin   = s.acc_linear        # m s⁻² (gravity removed)

            return (
                f"{euler[0]},{euler[1]},{euler[2]},"
                f"{accel[0]},{accel[1]},{accel[2]},"
                f"{gyro[0]},{gyro[1]},{gyro[2]},"
                f"{quat[0]},{quat[1]},{quat[2]},{quat[3]},"
                f"{lin[0]},{lin[1]},{lin[2]}"
            )
        except Exception as err:
            return err