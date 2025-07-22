from machine import ADC, Pin
from structs import Sensor, SensorID
import time


class TDS(Sensor):
    def __init__(self):
        super().__init__(SensorID.tds)
        self.TdsSensorPin = 27
        self.VREF = 3.3            # analog reference voltage
        self.SCOUNT = 30           # number of samples
        self.temperature = 25      # assumed temperature
        
        self.analog_buffer = [0] * self.SCOUNT
        self.analog_buffer_index = 0
        
        self.last_sample_time = 0
        self.last_print_time = 0

    def init(self):
        try:
            self.adc = ADC(Pin(self.TdsSensorPin))
            self.last_sample_time = time.ticks_ms()
            self.last_print_time = time.ticks_ms()
            return True
        except Exception as err:
            return err

    def get_median_num(self, b_array):
        sorted_array = sorted(b_array)
        mid = len(sorted_array) // 2
        if len(sorted_array) % 2 == 0:
            return (sorted_array[mid - 1] + sorted_array[mid]) // 2
        else:
            return sorted_array[mid]

    def read_tds_sample(self):
        self.analog_buffer[self.analog_buffer_index] = self.adc.read_u16() >> 6  # Convert 16-bit to 10-bit equivalent
        self.analog_buffer_index = (self.analog_buffer_index + 1) % self.SCOUNT

    def calculate_tds(self):
        average_raw = self.get_median_num(self.analog_buffer)
        average_voltage = average_raw * self.VREF / 1024.0

        compensation_coefficient = 1.0 + 0.02 * (self.temperature - 25.0)
        compensation_voltage = average_voltage / compensation_coefficient

        tds_value = (
            133.42 * compensation_voltage**3
            - 255.86 * compensation_voltage**2
            + 857.39 * compensation_voltage
        ) * 0.5

        return tds_value

    def read(self):
        try:
            current_time = time.ticks_ms()
            
            # Sample every 40ms
            if time.ticks_diff(current_time, self.last_sample_time) > 40:
                self.last_sample_time = current_time
                self.read_tds_sample()

            # Calculate and return value every 800ms
            if time.ticks_diff(current_time, self.last_print_time) > 800:
                self.last_print_time = current_time
                tds = self.calculate_tds()
                calibrated = -7.23456 + (1.20576 * round(tds, 0))
                return f"{calibrated:.2f}"
            
            return None  # Return None if not time to calculate yet
        except Exception as err:
            return err