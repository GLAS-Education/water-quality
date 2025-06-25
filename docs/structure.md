# Structure

There are two Picos which split up the work of monitoring different sensors.

### Main Pico

Infrequently (every 2-10 minutes), monitor & record:

- Real-time clock (RTC)
    - Synchrozing logs for later analysis
- Temperature sensors (x2)
    - Record at two depths
- Battery voltage sensor
    - Dynamic interval adjustment
    - Later debugging & analysis
- SD card module
    - Safely archive data in a physical location
- Turbidity sensor
    - Measure clearness of water
- pH sensor
    - Measure acidity of water

### Secondary Pico (frequent)

Frequently (every 1 second), monitor & record:

- 9D absolute rotation sensor
    - Detect waves using magnitude of all 3 axes' acceleration
- Water level sensor
    - Check for water damage (to aid later interpretation of data)
- Microphone
    - Measure sound levels in water to get a sense for human activity
- SD card module
    - Safely archive data in a physical location