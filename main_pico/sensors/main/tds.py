from machine import ADC, Pin
from structs import Sensor, SensorID


class TDS(Sensor):
    def __init__(self):
        super().__init__(SensorID.tds)
        self.pin = 27
        self.VREF = 3.3
        self.temperature = 25.0

    def init(self):
        try:
            self.adc = ADC(Pin(self.pin))
            self.read()
            return True
        except Exception as err:
            return err

    def _read_raw_10bit(self) -> int:
        return self.adc.read_u16() >> 6

    def _convert_to_tds(self, raw: int) -> float:
        voltage = raw * self.VREF / 1024.0
        comp_coeff = 1.0 + 0.02 * (self.temperature - 25.0)
        comp_voltage = voltage / comp_coeff
        tds = (
            133.42 * comp_voltage**3
            - 255.86 * comp_voltage**2
            + 857.39 * comp_voltage
        ) * 0.5
        calibrated = -7.23456 + (1.20576 * round(tds, 0))
        return calibrated

    def read(self):
        try:
            raw = self._read_raw_10bit()
            ppm = self._convert_to_tds(raw)
            return float(f"{ppm:.2f}")
        except Exception as err:
            return err


if __name__ == "__main__":
    tds = TDS()
    if tds.init() is True:
        print(f"TDS value: {tds.read()} ppm")
    else:
        print("TDS initialisation failed:", tds.init())
