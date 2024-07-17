import machine, onewire, ds18x20, time, sdcard, uos, ds1307, board, busio, adafruit_bno055, network, socket, _thread, bluetooth
from btlib.ble_simple_peripheral import BLESimplePeripheral
from machine import Pin, ADC, I2C, RTC

print("Main Pico")
try:
    
    main_iterations = 0
    
    # -- Initiates Water Level Monitoring Pin --#

    water = ADC(Pin(26))
        
    # -- Broadcast bluetooth signal -- #
    
    ble = bluetooth.BLE()
    ble_sp = BLESimplePeripheral(ble)
    
    def on_rx(v):
        print("Message from Bluetooth (RX):", v)

    ble_sp.on_write(on_rx)
            
    # -- Microphone + LED Stuff -- #

    sound_average = 0
    potential_wave = 0
    wave_detected = False
    microphone_disturbance_list = []
    analog_value = machine.ADC(28)
    conversion_factor = 3.3/(4096)
    led = Pin(15, Pin.OUT)
    led.value(1)
    time.sleep(1)
    led.value(0)
    SOUND_DIVISOR = 13 # TODO: update this value so that the 3.0 threshold makes sense to wake up the 9D sensors (higher = less sensitive)


    # -- SD Card Stuff -- #

    # Assign chip select (CS) pin (and start it high)
    cs = machine.Pin(1, machine.Pin.OUT)
    

    # Intialize SPI peripheral (start with 1 MHz)
    spi = machine.SPI(0, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=machine.SPI.MSB, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))


    # Initialize SD card
    sd = sdcard.SDCard(spi, cs)
    # Mount filesystem
    vfs = uos.VfsFat(sd)
    uos.mount(vfs, "/sd")



    # -- 9D Sensor Setup -- #
    
    i2c = busio.I2C(scl=board.GP19, sda=board.GP18)
    
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

    i = 0

    # -- RTC Stuff -- #

    """
    print("here")
    i3c=I2C(0, scl=Pin(17), sda=Pin(16))
    print(i3c.scan())
    r=machine.RTC()
    ds = ds1307.DS1307(i3c)
    print("here")
    ds.halt(False)    #Reads the RTC
    ds = ds.datetime()
    print("here")
    #print(ds)
    rtc = RTC()
    rtc.datetime((ds[0], ds[1], ds[2], ds[3]+1, ds[4], ds[5], ds[6], 0))
    #print(rtc.datetime())
    """

    # -- Detects Reboot and Writes it to SD Card -- #


    with open("/sd/sound.txt", "a") as file:
        file.write("Reboot detected" + "\n")
            
            

    # -- Connecting to Wi-Fi -- #
    
    
    """
    ssid = "GLAS Secure"
    password = "GeorgeHale"
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print("Waiting for connection...")
        time.sleep(1)
    if wlan.status() != 3:
        print("Network connection failed.")
    else:
        print("Connected!")
        status = wlan.ifconfig()
        pa'
        rint(f"IP: {status[0]}")
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print(f"Listening on {addr}!")
    """
            
    # -- Boot Up Light Show -- #
    
    
    iterations = 0
    blink_speed = 1
    while iterations >=0  and iterations <=30:
        iterations = iterations +1
        blink_speed = blink_speed/1.5
        led.value(1)
        time.sleep(blink_speed)
        led.value(0)
        time.sleep(blink_speed)
    

    # -- Main Operation Loop -- #

    old_rot = (0, 0, 0) # for 9D orientation visualization purposes


    while True:
        
        main_iterations += 1
        
        # -- Reads Water Level -- #
    
        water_detected = water.read_u16()
        if water_detected < 1000:
            water_level = "Dry"
        if water_detected >= 1000 and water_detected < 10000:
            water_level = "Damp"
        if water_detected > 10000:
            water_level = "Wet - Water Level Low"
        if water_detected > 20000:
            water_level = "Wet - Water Level High"
            # water_level determines how wet the interior of the buoy is

        
        # -- Updates and Sets Internal Clock -- #
        
        clock = time.localtime() # Prev: rtc.localtime()
        year = str(clock[0])
        month = str(clock[1])
        
        #Sets individual parts of time and ensures that every aspect of the time is a constant number of digits
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
        #Sets the date in a readable and compact format
        date = (year + "-" + month + "-" + day + ";" + hour + ":" + minute + ":" + second)
        
        
        # -- Reads Microphone -- #
        
        mic_readings = []
        for _ in range(50): # collect data for 50ms
            raw_value = analog_value.read_u16()
            print(raw_value)
            std_value = raw_value * conversion_factor
            mic_readings.append(std_value)
            time.sleep_ms(1)
        min_read = min(mic_readings)
        max_read = max(mic_readings)
        sound_reading = (max_read - min_read) / SOUND_DIVISOR
        mic_readings = []
        #print("Collected sound range:", sound_reading)
        
        """
        if sound_reading >= 2.7:
            led.value(1)
            time.sleep(0.1)
            led.value(0)
        """
        
        
        
        # -- Makes Sound Reading into a String -- #
        
        
        if len(str(sound_reading)) == 3:
            file_sound_reading = (str(sound_reading) + "0")    
        elif len(str(sound_reading)) > 3 :
            file_sound_reading = str(sound_reading)
        
        
        
        # -- Sets average sound reading for a 100 second window -- #
        
        
        sound_total = 0
        microphone_disturbance_list.append(sound_reading)
        if len(microphone_disturbance_list) >= 101:
            for i in range(0, len(microphone_disturbance_list)):
                sound_total = sound_total + microphone_disturbance_list[i]
                sound_average = sound_total/len(microphone_disturbance_list)
            del microphone_disturbance_list [0]
        
        
        
        # -- Detects waves via a disturbance in the previously set sound average -- #
        
        
        if sound_reading > sound_average + 0.01 and len(microphone_disturbance_list) >= 100:
            potential_wave = potential_wave + 1
            if potential_wave == 10:
                wave_detected = True
                potential_wave = 0
        if sound_reading <= sound_average + 0.01:
            potential_wave = 0
            wave_detected = False
            
        #print("Sound:", file_sound_reading, sound_reading, sound_average)
        
        
        #print(wave_detected, potential_wave, sound_reading, sound_average)
        #print(len(microphone_disturbance_list))
        
        
        # -- If no wave is detected it will write to the sound file -- #
        
        
        if sound_reading < 2.2 or wave_detected == False:
        
            with open("/sd/sound.txt", "a") as file:
                file.write(date + ";" + file_sound_reading + "\n")
           
           
        
        # -- Variables set for if a wave is detected -- #
           
        
        wave_timer = 0
        missed_scheduled_reboot = False
        

        # -- If the sound hits a certain level or if a wave was previously detected with a disturbance in the average -- #
        
        
        if sound_reading >= 3 or wave_detected == True:
            
            
            # -- Iterates every quater second through detecting the wave for 300 total seconds (five minutes) and repeats almost all code from main loop -- # 
            
            
            while wave_timer != 300:
            
                
                clock = time.localtime() # Prev: rtc.datetime()
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
                
                
                
                
                mic_readings = []
                for _ in range(50): # collect data for 50ms
                    raw_value = analog_value.read_u16()
                    print(raw_value)
                    std_value = raw_value * conversion_factor
                    mic_readings.append(std_value)
                    time.sleep_ms(1)
                min_read = min(mic_readings)
                max_read = max(mic_readings)
                sound_reading = (max_read - min_read) / SOUND_DIVISOR
                mic_readings = []
                if len(str(sound_reading)) == 3:
                    file_sound_reading = (str(sound_reading) + "0")    
                elif len(str(sound_reading)) > 3 :
                    file_sound_reading = str(sound_reading)
                    
                    
                    
                sound_total = 0
                microphone_disturbance_list.append(sound_reading)
                if len(microphone_disturbance_list) >= 101:
                    for i in range(0, len(microphone_disturbance_list)):
                        sound_total = sound_total + microphone_disturbance_list[i]
                        sound_average = sound_total/len(microphone_disturbance_list)
                    del microphone_disturbance_list [0]
                    
                # print(file_sound_reading, sound_average)
                    
                    
                
                # -- Reads 9-Axis Sensor -- #
                
                
                #print("Temperature: {} degrees C".format(sensor.temperature))
                #print("Accelerometer (m/s^2): {}".format(sensor.acceleration))
                #print("Magnetometer (microteslas): {}".format(sensor.magnetic))
                #print("Gyroscope (rad/sec): {}".format(sensor.gyro))
                #print("Euler angle: {}".format(sensor.euler))
                #print("Quaternion: {}".format(sensor.quaternion))
                #print("Linear acceleration (m/s^2): {}".format(sensor.linear_acceleration))
                #print("Gravity (m/s^2): {}".format(sensor.gravity))
                #print("Magnetometer (microteslas): {}".format(sensor.magnetic))
                #print()
                #global i
                #i += 1
                
                
                # -- Predicts if a wave is present -- #
                
                
                predict_wave = "true" if (abs(sensor.euler[1]) > 10) or (abs(sensor.euler[2]) > 15) else "false"
                data.append(f"{predict_wave},{water_detected},{sensor.euler[0]},{sensor.euler[1]},{sensor.euler[2]},{sensor.acceleration[0]},{sensor.acceleration[1]},{sensor.acceleration[2]};{sensor.gyro[0]},{sensor.gyro[1]},{sensor.gyro[2]},{sensor.quaternion[0]},{sensor.quaternion[1]},{sensor.quaternion[2]},{sensor.quaternion[3]},{sensor.linear_acceleration[0]},{sensor.linear_acceleration[1]},{sensor.linear_acceleration[2]}")
                
                rotational_change = min(abs(sensor.euler[0] - old_rot[0]) + abs(sensor.euler[1] - old_rot[1]) + abs(sensor.euler[2] - old_rot[2]), 40) # Sent over Bluetooth for visualization purposes; can be calculated later for actual analysis from raw sensor data
                old_rot = sensor.euler
                if ble_sp.is_connected():
                    ble_date = str(date).replace(";", "~")
                    ble_sound = min(sound_reading, 3)
                    ble_sp.send(f"WAKE;{main_iterations};{ble_date};{ble_sound};{water_detected};{sensor.euler[0]};{sensor.euler[1]};{sensor.euler[2]};{rotational_change}")
                #if i%5 == 0:
                
                
                # -- Writes wave data + sound to a wave file and continues to write sound to the sound file -- #
                
                
                with open("/sd/wave.txt", "a") as f:
                    f.write(date + ";" + file_sound_reading + ";" + f"{'\n'.join(data)}\n")
                    data = []
                    f.close()
                with open("/sd/sound.txt", "a") as file:
                    file.write(date + ";" + file_sound_reading + "\n")
                    
                time.sleep(0.25)
                wave_timer = wave_timer + 0.25
                if wave_timer == 300:
                    potential_wave = 0
                    wave_detected = False
                
                
                # -- Checks to see if a scheduled reboot was scheduled while a wave was present -- #
                
                
                if clock[3] == 23 and clock[4] == 55 and clock[5] >= 00 and clock[5] <= 10:
                    missed_scheduled_reboot = True

                
        # -- Send current stats over bluetooth -- #
    
        if ble_sp.is_connected():
            ble_date = str(date).replace(";", "~")
            ble_sound = min(sound_reading, 3)
            ble_sp.send(f"WAKE;{main_iterations};{ble_date};{ble_sound};{water_detected};0;0;0;0")
        
        # -- Reboots if it's time or if it missed its reboot while a wave was present -- #

            
        if clock[3] == 23 and clock[4] == 55 and clock[5] >= 00 and clock[5] <= 10 and voltage >= 4.00:
                with open("/sd/sound.txt", "a") as file:
                    file.write(date + ";" + "\n" + "Scheduled Reboot..." + "\n")
                machine.reset()

        if missed_scheduled_reboot == True and voltage >= 4.00:
            with open("/sd/sound.txt", "a") as file:
                    file.write(date + ";" + "\n" + "Scheduled Reboot..." + "\n")
            machine.reset()






except Exception as e:
    print(e)
    led = Pin(15, Pin.OUT)
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
            with open("/sd/sound.txt", "a") as file:
                file.write(date + "; An Error Occurred - Attempting Reboot..." + "\n")
        except:
            machine.reset()

        machine.reset()
