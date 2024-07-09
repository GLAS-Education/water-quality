import machine, onewire, ds18x20, time, sdcard, uos, ds1307, bluetooth, _thread
from btlib.ble_simple_peripheral import BLESimplePeripheral
from machine import Pin, ADC, I2C, RTC, UART
    
#import libraries for SD card, temp. sensors, voltimeter, and RTC
#If anything fails, goes to error loop
try:
    
    # Setup bluetooth & open for connections
    
    ble = bluetooth.BLE()
    ble_sp = BLESimplePeripheral(ble)
    
    # Assign chip select (CS) pin (and start it high)
    cs = machine.Pin(1, machine.Pin.OUT)
    
    # Intialize SPI peripheral (start with 1 MHz)
    spi = machine.SPI(0,
                      baudrate=1000000,
                      polarity=0,
                      phase=0,
                      bits=8,
                      firstbit=machine.SPI.MSB,
                      sck=machine.Pin(2),
                      mosi=machine.Pin(3),
                      miso=machine.Pin(0))

    # Initialize SD card
    sd = sdcard.SDCard(spi, cs)
    # Mount filesystem
    vfs = uos.VfsFat(sd)
    uos.mount(vfs, "/sd")
    voltage_value = machine.ADC(28)
    
    ds_pin = machine.Pin(13)
    
    ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
    
    led = Pin(27, Pin.OUT)
    led.value(1) 
    
    roms = ds_sensor.scan()
    #Sets up pins for everything


    i2c=I2C(0, scl=Pin(17), sda=Pin(16))
    r=machine.RTC()


    #print(i2c.scan())


    
    
    ds = ds1307.DS1307(i2c)


    ds.halt(False) #Not working with LiPo battery at low charge, but works fine with other power sources

    #Reads the RTC

    print('Found DS devices: ', roms)

    #with open("/sd/temp.txt", "w") as file:
    #            file.write("")
    #Clears text file
    time.sleep(1)

    with open("/sd/test7.txt", "a") as file:
                file.write("Reboot detected" + "\n")
    
    # Setup pH sensor

    uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))
    uart.init(bits=8, parity=None, stop=1)
    uart.write(b'*IDN?\n')
    time.sleep(1)
    rcv_val = 0
    
    # Setup turbidity sensor
    
    triggerPin1 = Pin(22, Pin.IN, Pin.PULL_UP)
    triggerPin2 = Pin(21, Pin.IN, Pin.PULL_UP)
    pulses_list = []
    total_list = []
    pulses_average = 0
    total = 0
    count = 0
    darks = False
    lights = False

    def TriggerCount(self):
        global count
        count += 1
    def TriggerCount2(self):
        global count2
        count2 += 1

    triggerPin1.irq(trigger=Pin.IRQ_RISING, handler=TriggerCount)
    triggerPin2.irq(trigger=Pin.IRQ_RISING, handler=TriggerCount)
    
    # Detects reboot
    
    iterations = 0
    blink_speed = 2
    ds = ds.datetime()
    #print(ds)
    rtc = RTC()
    rtc.datetime((ds[0], ds[1], ds[2], ds[3]+1, ds[4], ds[5], ds[6], 0))
    #print(rtc.datetime())
    def update_bluetooth():
        ble_date = date.replace(";", "~")
        ble_sp.send(f"MAIN;{i};{ble_date};{voltage_dec};{s1};{s2};{rcv_val};{turbidity_avg}")
    i = 0
    while True:
        clock = rtc.datetime()
        year = str(clock[0])
        month = str(clock[1])
        #Ensures that every aspect of the time is a constant number of digits
        if len(month) == 1:
            month = "0"+month
        day = str(clock[2])
        if len(day) == 1:
            day = "0"+day
        hour = str(clock[4])
        if len(hour) == 1:
            hour = "0"+hour
        minute = str(clock[5])
        if len(minute) == 1:
            minute = "0"+minute
        second = str(clock[6])
        if len(second) == 1:
            second = "0"+second
        
        date = (year + "-" + month + "-" + day + ";" + hour + ":" + minute + ":" + second)    
                
        raw = voltage_value.read_u16()
        #print(raw)
        voltage_dec = raw*(6.6 / 65535)
        voltage = round(voltage_dec, 2)
        #print(voltage)

        ds_sensor.convert_temp()
        
        for rom in roms:
     
            if rom == bytearray(b'(\x99\xb2\x96\xf0\x01<I'):
                s1 = round(ds_sensor.read_temp(rom), 2)
            elif rom == bytearray(b'(/\xbcI\xf6\xcf<|'):
                s2 = round(ds_sensor.read_temp(rom), 2)
        #print(sensor)
        #print(reading)
        
        # Reading pH
        
        if uart.any():
            read_val = uart.read()
            try:            
                rcv_val = float(read_val)
            except ValueError as e:
                print(read_val)
                
        # Reading turbidity
        
        count = 0
        iterations = 0
        darks_total = 0
        lights_total = 0
        darks_list = []
        lights_list = []


        counted = count
        #print("{} pulses".format(count))

        
        
        #Darks
        while darks == False:
            count = 0
            time.sleep(.1)
            led.value(0)
            darks_list.append(count)
            iterations += 1
            if iterations == 5:
                darks = True
                for i in range(0, len(darks_list)):
                    darks_total += darks_list[i]
                darks_average = round(darks_total/len(darks_list))

                
        while lights == False:
            count = 0
            time.sleep(.1)
            led.value(1)
            lights_list.append(count)
            iterations += 1
            if iterations == 10:
                lights = True
                for i in range(0, len(lights_list)):
                    lights_total += lights_list[i]
                lights_average = round(lights_total/len(lights_list))
        turbidity_range = lights_average - darks_average
        turbidity_avg = (lights_average + darks_average) / 2
        
        lights = False
        darks = False
                
        
        iterations += 1
        #Boot sequence
        while iterations >= 2 and iterations <=20:
            iterations += 1
            with open("/sd/bootfile.txt", "a") as file:
                file.write(date + ";" + str(s1) + ";" + str(s2) + ";" + str(voltage) + "\n")
            blink_speed = blink_speed/1.5
            led.value(1)
            time.sleep(blink_speed)
            led.value(0)
            time.sleep(blink_speed)
            if ble_sp.is_connected():
                update_bluetooth()
        with open("/sd/main2024.txt", "a") as file:
            file.write(date + ";" + str(s1) + ";" + str(s2) + ";" + str(voltage) + ";" + str(rcv_val) + ";" + str(turbidity_avg) + "\n")
        """
        with open("/sd/test5.txt", "r") as file:
            data = file.read()
            #print(data)
        """
        
        #Waits to record data again and if the time criteria is met it will reboot
        if iterations < 20:
            time.sleep(1)
        if iterations >=20:
            if voltage >= 4.10:
                if clock[4] == 12:
                    if clock[5] >= 00 and clock[5] <= 01:
                        time.sleep(60)
                        with open("/sd/test7.txt", "a") as file:
                            file.write(date + ";" + "\n" + "Scheduled Reboot..." + "\n")
                        machine.reset()
                print("Sleeping for 60 seconds...")
                for _ in range(60):
                    if ble_sp.is_connected():
                        update_bluetooth()
                    time.sleep(1)
            if voltage < 4.10 and voltage > 4.00:
                if hour == 12:
                    if clock[5] >= 00 and clock[5] <= 02:
                        time.sleep(90)
                        with open("/sd/test7.txt", "a") as file:
                            file.write(date + ";" + "\n" + "Scheduled Reboot..." + "\n")
                        machine.reset()
                print("Sleeping for 90 seconds...")
                for _ in range(90):
                    if ble_sp.is_connected():
                        update_bluetooth()
                    time.sleep(1)
            if voltage <= 4.00:
                print("Sleeping for 150 seconds...")
                for _ in range(150):
                    if ble_sp.is_connected():
                        update_bluetooth()
                    time.sleep(1)
        if ble_sp.is_connected():
            update_bluetooth()
        i += 1
        time.sleep(1) # Minimum sleep to prevent super fast iterations

#Error Loop
except Exception as e:
    print(e)
    led = Pin(27, Pin.OUT)
    while True:
        led.value(1)
        time.sleep(0.1)
        led.value(0)
        time.sleep(0.1)
        led.value(1)
        time.sleep(0.1)
        led.value(0)
        time.sleep(2)
        
        try:
            with open("/sd/test7.txt", "a") as file:
                file.write(date + "; An Error Occured - Attempting Reboot..." + "\n")
        except:
            machine.reset()

        machine.reset()
        

