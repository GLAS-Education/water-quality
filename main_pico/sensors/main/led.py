import machine, time
from structs import Sensor, SensorID, IntentionalUndefined


class StatusLED(Sensor):
    def __init__(self):
        super().__init__(SensorID.status_led)
        self.pin = machine.Pin(18, machine.Pin.OUT)

    def init(self):
        try:
            self.pin.value(1)
            time.sleep(1)
            self.pin.value(0)
            return True
        except Exception as err:
            return err
    
    def read(self):
        return IntentionalUndefined

