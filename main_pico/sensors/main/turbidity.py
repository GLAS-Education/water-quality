import machine, time
from structs import Sensor, SensorID

# failsafe
import micropython
micropython.alloc_emergency_exception_buf(100)


class Turbidity(Sensor):
    def __init__(self):
        super().__init__(SensorID.turbidity)
        self.trigger_pin1 = machine.Pin(22, machine.Pin.IN, machine.Pin.PULL_UP)
        self.trigger_pin2 = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_UP)
        self.led = machine.Pin(15, machine.Pin.OUT)
        self.pulses_list = []
        self.total_list = []
        self.pulses_average = 0
        self.total = 0
        self.count = 0
        self.darks = False
        self.lights = False
    
    def TriggerCount(self, pin):
        try:
            self.count += 1
        except Exception as err:
            print(err)

    def init(self):
        try:
            self.trigger_pin1.irq(trigger=machine.Pin.IRQ_RISING, handler=self.TriggerCount)
            self.trigger_pin2.irq(trigger=machine.Pin.IRQ_RISING, handler=self.TriggerCount)
            return True
        except Exception as err:
            return err
    
    def read(self):
        try:
            self.count = 0
            iterations = 0
            darks_total = 0
            lights_total = 0
            darks_list = []
            lights_list = []
            
            while self.darks == False:
                print("while 1")
                self.count = 0
                time.sleep(.1)
                self.led.value(0)
                darks_list.append(self.count)
                iterations += 1
                if iterations == 5:
                    self.darks = True
                    for i in range(0, len(darks_list)):
                        print("while 1.1")
                        darks_total += darks_list[i]
                    darks_average = round(darks_total/len(darks_list))

                
            while self.lights == False:
                print("while 2")
                self.count = 0
                time.sleep(.1)
                self.led.value(1)
                lights_list.append(self.count)
                iterations += 1
                if iterations == 10:
                    self.lights = True
                    for i in range(0, len(lights_list)):
                        print("while 2.1")
                        lights_total += lights_list[i]
                    lights_average = round(lights_total/len(lights_list))
                        
            turbidity_range = lights_average - darks_average
            turbidity_avg = (lights_average + darks_average) / 2
            
            self.lights = False
            self.darks = False
            
            return turbidity_avg
        except Exception as err:
            return err
