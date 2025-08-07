import machine
import time
from rfm9x import RFM9x

# Setup LoRa with your pin configuration
lora_cs = machine.Pin(5, machine.Pin.OUT)
lora_rst = machine.Pin(14, machine.Pin.OUT)
lora_spi = machine.SPI(0, baudrate=5000000, polarity=0, phase=0, bits=8, firstbit=machine.SPI.MSB, sck=machine.Pin(6), mosi=machine.Pin(7), miso=machine.Pin(0))

# Initialize the radio
lora = RFM9x(lora_spi, lora_cs, lora_rst, frequency=915.0, tx_power=17)
print("LoRa radio initialized successfully!")

# Test loop
counter = 0
while True:
    counter += 1
    
    # Create a simple test payload
    message = f"Test message {counter}"
    
    try:
        # Send using the new simple API
        lora.send_text(message)
        print(f"✓ Sent: {message}")
    except TimeoutError:
        print(f"✗ Timeout sending: {message}")
    except Exception as e:
        print(f"✗ Error sending: {message} - {e}")
    
    time.sleep(2)

