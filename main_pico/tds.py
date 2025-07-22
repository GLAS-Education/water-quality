from machine import ADC, Pin
import time

TdsSensorPin = 28
VREF = 3.3            # analog reference voltage
SCOUNT = 30           # number of samples
temperature = 25.0    # assumed temperature

analog_buffer = [0] * SCOUNT
analog_buffer_index = 0

adc = ADC(Pin(TdsSensorPin))

def get_median_num(b_array):
    sorted_array = sorted(b_array)
    mid = len(sorted_array) // 2
    if len(sorted_array) % 2 == 0:
        return (sorted_array[mid - 1] + sorted_array[mid]) // 2
    else:
        return sorted_array[mid]

def read_tds():
    global analog_buffer_index

    analog_buffer[analog_buffer_index] = adc.read_u16() >> 6  # Convert 16-bit to 10-bit equivalent
    analog_buffer_index = (analog_buffer_index + 1) % SCOUNT

def calculate_tds():
    average_raw = get_median_num(analog_buffer)
    average_voltage = average_raw * VREF / 1024.0

    compensation_coefficient = 1.0 + 0.02 * (temperature - 25.0)
    compensation_voltage = average_voltage / compensation_coefficient

    tds_value = (
        133.42 * compensation_voltage**3
        - 255.86 * compensation_voltage**2
        + 857.39 * compensation_voltage
    ) * 0.5

    return tds_value

last_sample_time = time.ticks_ms()
last_print_time = time.ticks_ms()

while True:
    if time.ticks_diff(time.ticks_ms(), last_sample_time) > 40:
        last_sample_time = time.ticks_ms()
        read_tds()

    if time.ticks_diff(time.ticks_ms(), last_print_time) > 800:
        last_print_time = time.ticks_ms()
        tds = calculate_tds()
        print("TDS Value: {:.0f} ppm".format(tds))

