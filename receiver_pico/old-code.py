# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import busio
import adafruit_bno055

i2c = busio.I2C(scl=board.GP17, sda=board.GP16)

sensor = adafruit_bno055.BNO055_I2C(i2c)
last_val = 0xFFFF

def temperature():
    global last_val  # pylint: disable=global-statement
    result = sensor.temperature
    if abs(result - last_val) == 128:
        result = sensor.temperature
        if abs(result - last_val) == 128:
            return 0b00111111 & result
    last_val = result
    return result

data = []
# i = 0

while True:
    """print("Temperature: {} degrees C".format(sensor.temperature))
    print("Accelerometer (m/s^2): {}".format(sensor.acceleration))
    print("Magnetometer (microteslas): {}".format(sensor.magnetic))
    print("Gyroscope (rad/sec): {}".format(sensor.gyro))
    print("Euler angle: {}".format(sensor.euler))
    print("Quaternion: {}".format(sensor.quaternion))
    print("Linear acceleration (m/s^2): {}".format(sensor.linear_acceleration))
    print("Gravity (m/s^2): {}".format(sensor.gravity))"""
    print("Magnetometer (microteslas): {}".format(sensor.magnetic))
    print()
    time.sleep(0.25)

"""while True:
    predict_wave = "🟢" if (abs(sensor.euler[1]) > 10) or (abs(sensor.euler[2]) > 15) else "🔴"
    print(f"{predict_wave}  {sensor.euler[0]}  /  {sensor.euler[1]}  /  {sensor.euler[2]}")
    time.sleep(0.2)
    ---------
    i += 1
    predict_wave = "true" if (abs(sensor.euler[1]) > 10) or (abs(sensor.euler[2]) > 15) else "false"
    data.append(f"{predict_wave},{sensor.euler[0]},{sensor.euler[1]},{sensor.euler[2]}")
    if i%25 == 0:
        with open("/sd/data.csv", "r") as rf:
            existing_data = rf.read()
            for line in data:
                existing_data += f"\n{line}"
            with open("/sd/data.csv", "w") as wf:
                f.write(existing_data)
                f.close()
    time.sleep(0.2)"""
