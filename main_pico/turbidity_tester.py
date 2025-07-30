import machine, time
from rp2 import PIO, StateMachine, asm_pio

# Pin assignments
LED_PIN = 0
TSL1_PIN = 1
TSL2_PIN = 2

# Initialize sensor and LED pins
sensor1 = machine.Pin(TSL1_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
sensor2 = machine.Pin(TSL2_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
led = machine.Pin(LED_PIN, machine.Pin.OUT, machine.Pin.PULL_DOWN)

# PIO program to count rising edges
@asm_pio(autopush=True, push_thresh=32)
def edge_counter():
    wait(0, pin, 0)    # Wait for low
    wait(1, pin, 0)    # Wait for high (rising edge)
    in_(null, 2)       # Count as 2 edges (since we skip falling)

# Measure counts per second for a given pin using an available state machine ID
def report_value(sensor_pin, sm_id=0, duration_seconds=1):
    sm = StateMachine(
        sm_id,
        edge_counter,
        freq=125_000_000,
        in_base=sensor_pin
    )
    
    # Clear stale FIFO data
    while sm.rx_fifo():
        sm.get()
    
    sm.active(1)
    edge_count = 0
    start_time = time.ticks_ms()
    duration_ms = duration_seconds * 1000

    while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
        if sm.rx_fifo():
            edge_count += 32
            sm.get()
    
    sm.active(0)
    return edge_count / duration_seconds

# Calculate net light (LED ON - LED OFF)
def read_light_difference(sensor_pin, led, sm_id):
    led.off()
    time.sleep(0.05)  # Let sensor settle
    dark = report_value(sensor_pin, sm_id)

    led.on()
    time.sleep(0.05)
    light = report_value(sensor_pin, sm_id)

    led.off()
    return light - dark

# Main loop
while True:
    net1 = read_light_difference(sensor1, led, sm_id=0)
    net2 = read_light_difference(sensor2, led, sm_id=1)
    average_net = (net1 + net2) / 2

    print(f'\nSensor 1 net: {net1:.1f} cps | Sensor 2 net: {net2:.1f} cps | Average: {average_net:.1f} cps')

    time.sleep(0.5)
