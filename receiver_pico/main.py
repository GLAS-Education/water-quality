import machine
import network
import time
import json
import urequests
from machine import Pin, SPI, PWM, RTC
import framebuf
import gc

# Configuration
WIFI_SSID = "GLAS Secure"  # Change this
WIFI_PASSWORD = "GeorgeHale"  # Change this
SERVER_URL = "http://mac.tlampert.net"  # Change this
API_KEY = "1234"  # Change this
EXPERIMENT_ID = "inoffice0.1"  # Change this

# LCD Pins
BL = 13
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

# LoRa Pins
LORA_CS = 5
LORA_RST = 0
LORA_SCK = 6
LORA_MOSI = 7
LORA_MISO = 4

# RFM9x Registers
from micropython import const
_REG_FIFO = const(0x00)
_REG_OP_MODE = const(0x01)
_REG_FRF_MSB = const(0x06)
_REG_FRF_MID = const(0x07)
_REG_FRF_LSB = const(0x08)
_REG_FIFO_ADDR_PTR = const(0x0D)
_REG_FIFO_RX_BASE = const(0x0F)
_REG_FIFO_RX_CURRENT = const(0x10)
_REG_IRQ_FLAGS = const(0x12)
_REG_RX_NB_BYTES = const(0x13)

_LONG_RANGE_MODE = const(0x80)
_OPMODE_STDBY = const(0x01)
_OPMODE_RXCONT = const(0x05)
_IRQ_RX_DONE = const(0x40)
_IRQ_PAYLOAD_CRC_ERROR = const(0x20)

class LCD_1inch14(framebuf.FrameBuffer):
    """LCD Display driver"""
    def __init__(self):
        self.width = 240
        self.height = 135
        
        self.cs = Pin(CS, Pin.OUT)
        self.rst = Pin(RST, Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1, 10000_000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI), miso=None)
        self.dc = Pin(DC, Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()
        
        # Colors (RGB565)
        self.red = 0xF800
        self.green = 0x07E0
        self.blue = 0x001F
        self.white = 0xFFFF
        self.black = 0x0000
        self.yellow = 0xFFE0
        self.gray = 0x8410
    
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)
    
    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)
    
    def init_display(self):
        """Initialize display"""
        self.rst(1)
        self.rst(0)
        self.rst(1)
        
        # ST7789 initialization sequence
        self.write_cmd(0x36)
        self.write_data(0x70)
        self.write_cmd(0x3A)
        self.write_data(0x05)
        self.write_cmd(0xB2)
        self.write_data(0x0C)
        self.write_data(0x0C)
        self.write_data(0x00)
        self.write_data(0x33)
        self.write_data(0x33)
        self.write_cmd(0xB7)
        self.write_data(0x35)
        self.write_cmd(0xBB)
        self.write_data(0x19)
        self.write_cmd(0xC0)
        self.write_data(0x2C)
        self.write_cmd(0xC2)
        self.write_data(0x01)
        self.write_cmd(0xC3)
        self.write_data(0x12)
        self.write_cmd(0xC4)
        self.write_data(0x20)
        self.write_cmd(0xC6)
        self.write_data(0x0F)
        self.write_cmd(0xD0)
        self.write_data(0xA4)
        self.write_data(0xA1)
        self.write_cmd(0x21)
        self.write_cmd(0x11)
        self.write_cmd(0x29)
    
    def show(self):
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(0x28)
        self.write_data(0x01)
        self.write_data(0x17)
        
        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(0x35)
        self.write_data(0x00)
        self.write_data(0xBB)
        
        self.write_cmd(0x2C)
        
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

class RFM9xReceiver:
    """RFM9x driver for receiving LoRa packets"""
    
    def __init__(self, spi, cs, rst, frequency=915.0):
        self.spi = spi
        self.cs = cs
        self.rst = rst
        
        # Initialize pins
        self.cs.init(Pin.OUT, value=1)
        self.rst.init(Pin.OUT, value=1)
        
        # Hardware reset
        self.rst.value(0)
        time.sleep_us(100)
        self.rst.value(1)
        time.sleep_ms(5)
        
        # Ensure LoRa mode is actually engaged
        if not self._ensure_lora_mode():
            raise Exception("Failed to enter LoRa mode")
        
        # Set frequency
        self.set_frequency(frequency)
        
        # Configure modem (125kHz BW, CR 4/5, SF 7)
        self._write_reg(0x1D, 0x72)  # RegModemConfig1
        self._write_reg(0x1E, 0x74)  # RegModemConfig2
        self._write_reg(0x26, 0x04)  # RegModemConfig3 (AGC on)
        
        # Improve RX sensitivity and compatibility
        self._write_reg(0x0C, 0x23)  # RegLna: LNA boost on, highest gain
        self._write_reg(0x39, 0x12)  # RegSyncWord: default 0x12
        self._write_reg(0x22, 0xFF)  # RegPayloadLength: allow up to 255
        self._write_reg(0x23, 0xFF)  # RegMaxPayloadLength
        
        # Set FIFO base address and pointer
        self._write_reg(_REG_FIFO_RX_BASE, 0x00)
        self._write_reg(_REG_FIFO_ADDR_PTR, 0x00)
        
        # Clear IRQ flags
        self._write_reg(_REG_IRQ_FLAGS, 0xFF)
    
    def set_frequency(self, freq_mhz):
        frf = int(freq_mhz * 1_000_000 / (32_000_000 / (1 << 19)))
        self._write_reg(_REG_FRF_MSB, (frf >> 16) & 0xFF)
        self._write_reg(_REG_FRF_MID, (frf >> 8) & 0xFF)
        self._write_reg(_REG_FRF_LSB, frf & 0xFF)
    
    def start_receive(self):
        """Put radio in continuous receive mode"""
        # Ensure we are in LoRa before switching to RXCONT
        self._ensure_lora_mode()
        time.sleep_ms(2)
        # Reset FIFO pointer to RX base before RX
        self._write_reg(_REG_FIFO_ADDR_PTR, self._read_reg(_REG_FIFO_RX_BASE))
        # Clear IRQs and enter RX continuous
        self._write_reg(_REG_IRQ_FLAGS, 0xFF)
        self._write_reg(_REG_OP_MODE, _LONG_RANGE_MODE | _OPMODE_RXCONT)

    def _ensure_lora_mode(self):
        """Try hard to switch the radio into LoRa mode; return True on success."""
        for _ in range(5):
            # Go to Sleep (FSK)
            self._write_reg(_REG_OP_MODE, 0x00)
            time.sleep_ms(2)
            # Sleep (LoRa)
            self._write_reg(_REG_OP_MODE, _LONG_RANGE_MODE | 0x00)
            time.sleep_ms(5)
            op = self._read_reg(_REG_OP_MODE)
            if (op & _LONG_RANGE_MODE):
                # Standby (LoRa)
                self._write_reg(_REG_OP_MODE, _LONG_RANGE_MODE | _OPMODE_STDBY)
                time.sleep_ms(2)
                op2 = self._read_reg(_REG_OP_MODE)
                if (op2 & _LONG_RANGE_MODE) and ((op2 & 0x07) == _OPMODE_STDBY):
                    return True
        return False
    
    def check_receive(self):
        """Check if packet received and return it"""
        irq_flags = self._read_reg(_REG_IRQ_FLAGS)
        
        if irq_flags & _IRQ_RX_DONE:
            # Check CRC error
            if irq_flags & _IRQ_PAYLOAD_CRC_ERROR:
                self._write_reg(_REG_IRQ_FLAGS, 0xFF)
                return None
            
            # Read packet
            current_addr = self._read_reg(_REG_FIFO_RX_CURRENT)
            received_bytes = self._read_reg(_REG_RX_NB_BYTES)
            
            self._write_reg(_REG_FIFO_ADDR_PTR, current_addr)
            
            # Read from FIFO
            self.cs.value(0)
            self.spi.write(bytearray([_REG_FIFO & 0x7F]))
            data = self.spi.read(received_bytes, 0x00)
            self.cs.value(1)
            
            # Clear IRQ flags
            self._write_reg(_REG_IRQ_FLAGS, 0xFF)
            
            try:
                return data.decode('utf-8')
            except:
                return None
        
        return None
    
    def _write_reg(self, addr, value):
        self.cs.value(0)
        self.spi.write(bytearray([addr | 0x80, value & 0xFF]))
        self.cs.value(1)
    
    def _read_reg(self, addr):
        self.cs.value(0)
        self.spi.write(bytearray([addr & 0x7F]))
        result = self.spi.read(1, 0x00)
        self.cs.value(1)
        return result[0]

class LoRaGateway:
    def __init__(self):
        # Initialize LCD
        pwm = PWM(Pin(BL))
        pwm.freq(1000)
        pwm.duty_u16(32768)
        self.lcd = LCD_1inch14()
        
        # Display startup message
        self.lcd.fill(self.lcd.black)
        self.lcd.text("Gateway Starting...", 20, 60, self.lcd.white)
        self.lcd.show()
        
        # Initialize WiFi
        self.wifi_connected = False
        self.connect_wifi()
        
        # Initialize LoRa
        try:
            lora_spi = SPI(0, baudrate=5000000, polarity=0, phase=0, 
                          sck=Pin(LORA_SCK), mosi=Pin(LORA_MOSI), miso=Pin(LORA_MISO))
            lora_cs = Pin(LORA_CS, Pin.OUT)
            lora_rst = Pin(LORA_RST, Pin.OUT)
            
            self.radio = RFM9xReceiver(lora_spi, lora_cs, lora_rst, frequency=915.0)
            self.radio.start_receive()
            # Immediately read op mode to verify we're in LoRa RX (0x85 expected)
            try:
                op_mode = self.radio._read_reg(_REG_OP_MODE)
                print("Post-start OPMODE=0x%02X" % op_mode)
            except Exception as _:
                pass
            # Basic SX127x presence/version check for diagnostics
            try:
                version = self.radio._read_reg(0x42)
                print("LoRa RegVersion: 0x%02X" % version)
                if version not in (0x11, 0x12):
                    print("Warning: Unexpected SX127x version. Check wiring (MISO/MOSI/SCK/CS/RST) and pins.")
            except Exception as ve:
                print("LoRa version read failed: %s" % ve)
            self.lora_working = True
        except Exception as e:
            print(f"LoRa init failed: {e}")
            self.radio = None
            self.lora_working = False
        
        # Statistics and data
        self.packets_received = 0
        self.packets_forwarded = 0
        # None until a packet is actually received. We use monotonic ticks (ms)
        # and time.ticks_diff for wrap-around safe comparisons.
        self.last_packet_time_ms = None
        self.last_data = {
            'temperature_1': 0.0,
            'temperature_2': 0.0,
            'temperature_3': 0.0,
            'temperature_4': 0.0,
            'ph': 0.0,
            'battery': 0.0,
            'water_detected': False
        }
        # UI water indicator that persists across No Signal until next Alive update
        self.water_display_flag = False
    
    def connect_wifi(self):
        """Connect to WiFi network"""
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        if not wlan.isconnected():
            print(f"Connecting to WiFi: {WIFI_SSID}")
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            timeout = 10
            while not wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
        
        if wlan.isconnected():
            self.wifi_connected = True
            self.ip = wlan.ifconfig()[0]
            print(f"WiFi connected! IP: {self.ip}")
        else:
            print("WiFi connection failed!")
            self.wifi_connected = False
    
    def parse_lora_payload(self, payload):
        """Parse the LoRa payload: MAIN;1;2025/8/7/3/11/46/36/0;84.91;24.38;-1.0;-1.0;-1.0;-1;223.07;-5;3;0"""
        try:
            parts = payload.strip().split(";")
            print(f"Parsing {len(parts)} parts: {parts}")
            
            if len(parts) < 13:
                print(f"Not enough parts: {len(parts)}")
                return None
            
            # Parse based on the actual format received
            data = {
                "probe_id": parts[0],                    # MAIN
                "iterations": int(parts[1]),             # 1
                "timestamp": parts[2],                   # 2025/8/7/3/11/46/36/0
                "battery": float(parts[3]),              # 84.91
                "temperature_1": float(parts[4]),        # 24.38
                "temperature_2": float(parts[5]),        # -1.0
                "temperature_3": float(parts[6]),        # -1.0
                "temperature_4": float(parts[7]),        # -1.0
                "ph": float(parts[8]),                   # -1
                "tds": float(parts[9]),                  # 223.07
                "turbidity": float(parts[10]),           # -5
                "refresh_countdown": int(parts[11]),     # 3
                "water_detected": bool(int(parts[12]))   # 0
            }
            
            print(f"Parsed successfully: {data}")
            return data
            
        except Exception as e:
            print(f"Error parsing payload: {e}")
            print(f"Payload was: {payload}")
            return None
    
    def get_average_temperature(self):
        """Calculate average temperature from valid readings"""
        temps = [
            self.last_data['temperature_1'],
            self.last_data['temperature_2'],
            self.last_data['temperature_3'],
            self.last_data['temperature_4']
        ]
        
        # Filter out invalid readings (-1.0)
        valid_temps = [t for t in temps if t != -1.0]
        
        if valid_temps:
            return sum(valid_temps) / len(valid_temps)
        else:
            return 0.0
    
    def send_to_server(self, data):
        """Send data to Flask server"""
        if not self.wifi_connected:
            return False
        
        try:
            payload = {
                "experiment_id": EXPERIMENT_ID,
                "temperature_1": data["temperature_1"] if data["temperature_1"] != -1.0 else 0,
                "temperature_2": data["temperature_2"] if data["temperature_2"] != -1.0 else 0,
                "temperature_3": data["temperature_3"] if data["temperature_3"] != -1.0 else 0,
                "temperature_4": data["temperature_4"] if data["temperature_4"] != -1.0 else 0,
                "ph": data["ph"] if data["ph"] != -1.0 else 0,
                "battery_level": data["battery"],
                "tds": data["tds"] if data["tds"] != -1.0 else 0,
                "turbidity": data["turbidity"] if data["turbidity"] != -1.0 else 0,
                "water_detected": data["water_detected"] if data["water_detected"] else False
            }
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            url = SERVER_URL + "/api/main"
            response = urequests.post(url, json=payload, headers=headers)
            
            success = response.status_code == 200
            response.close()
            
            if success:
                self.packets_forwarded += 1
            
            return success
            
        except Exception as e:
            err_text = str(e)
            print(f"Error sending to server: {err_text}")
            # Fallback: if TLS fails (common on MicroPython), retry over HTTP if using HTTPS
            if SERVER_URL.startswith("https://") and ("MBEDTLS_ERR_SSL" in err_text or "SSL" in err_text or "EOF" in err_text):
                try:
                    fallback_base = SERVER_URL.replace("https://", "http://", 1)
                    fallback_url = fallback_base + "/api/main"
                    print("Retrying over HTTP:", fallback_url)
                    response = urequests.post(fallback_url, json=payload, headers=headers)
                    success = response.status_code == 200
                    response.close()
                    if success:
                        self.packets_forwarded += 1
                    return success
                except Exception as e2:
                    print(f"HTTP fallback failed: {e2}")
                    return False
            return False
    
    def update_display(self):
        """Update LCD display with centered title and right-aligned values"""
        self.lcd.fill(self.lcd.black)
        
        # Centered title - "Water Quality" is 13 chars, at ~8px per char = 104px
        # Screen is 240px wide, so center at (240-104)/2 = 68px
        self.lcd.text("Water Quality", 68, 5, self.lcd.white)
        
        y_pos = 25
        label_x = 10        # X position for labels (left side)
        right_margin = 230  # Right edge for values
        
        # Status indicators
        now_ms = time.ticks_ms()
        # Only show Alive for 5 minutes AFTER a real packet is received
        lora_alive = (
            self.lora_working and
            (self.last_packet_time_ms is not None) and
            (time.ticks_diff(now_ms, self.last_packet_time_ms) < 300_000)
        )
        
        # WiFi status
        self.lcd.text("WiFi:", label_x, y_pos, self.lcd.white)
        wifi_color = self.lcd.white
        wifi_text = "Connected" if self.wifi_connected else "Disconnected"
        wifi_text_width = len(wifi_text) * 8  # Approximate 8 pixels per character
        self.lcd.text(wifi_text, right_margin - wifi_text_width, y_pos, wifi_color)
        y_pos += 18
        
        # LoRa status
        self.lcd.text("LoRa:", label_x, y_pos, self.lcd.white)
        lora_color = self.lcd.white
        lora_text = "Alive" if lora_alive else "No Signal"
        if self.water_display_flag:
            lora_text += " (Water)"
        lora_text_width = len(lora_text) * 8
        self.lcd.text(lora_text, right_margin - lora_text_width, y_pos, lora_color)
        y_pos += 22
        
        # Average temperature
        avg_temp = self.get_average_temperature()
        self.lcd.text("Temp:", label_x, y_pos, self.lcd.white)
        temp_text = f"{avg_temp:4.1f}C"
        temp_text_width = len(temp_text) * 8
        self.lcd.text(temp_text, right_margin - temp_text_width, y_pos, self.lcd.white)
        y_pos += 18
        
        # pH reading
        ph_value = self.last_data['ph'] if self.last_data['ph'] != -1.0 else 0.0
        self.lcd.text("pH:", label_x, y_pos, self.lcd.white)
        ph_text = f"{ph_value:6.2f}"
        ph_text_width = len(ph_text) * 8
        self.lcd.text(ph_text, right_margin - ph_text_width, y_pos, self.lcd.white)
        y_pos += 18
        
        # Battery percentage
        battery = self.last_data['battery']
        self.lcd.text("Battery:", label_x, y_pos, self.lcd.white)
        battery_text = f"{battery:4.1f}%"
        battery_text_width = len(battery_text) * 8
        self.lcd.text(battery_text, right_margin - battery_text_width, y_pos, self.lcd.white)
        
        self.lcd.show()
    
    def run(self):
        """Main loop"""
        print("LoRa Gateway started! Listening for packets...")
        
        last_display_update = time.ticks_ms()
        last_status_log = time.ticks_ms()
        
        while True:
            # Check for received packets
            if self.radio:
                packet = self.radio.check_receive()
                
                if packet:
                    print(f"Received: {packet}")
                    self.packets_received += 1
                    self.last_packet_time_ms = time.ticks_ms()
                    
                    # Parse packet
                    data = self.parse_lora_payload(packet)
                    if data:
                        # Update display data
                        self.last_data['temperature_1'] = data['temperature_1']
                        self.last_data['temperature_2'] = data['temperature_2']
                        self.last_data['temperature_3'] = data['temperature_3']
                        self.last_data['temperature_4'] = data['temperature_4']
                        self.last_data['ph'] = data['ph']
                        self.last_data['battery'] = data['battery']
                        self.last_data['water_detected'] = data['water_detected']
                        # Update the UI water flag immediately on each packet
                        # so removal/addition occurs right away when Alive,
                        # and persists across No Signal until next Alive.
                        self.water_display_flag = bool(data['water_detected'])
                        # Refresh display immediately to reflect change
                        self.update_display()
                        
                        # Send to server
                        if self.send_to_server(data):
                            print("Data forwarded to server successfully")
                        else:
                            print("Failed to forward data to server")
            
            now_ms = time.ticks_ms()

            # Periodic radio status diagnostics
            if time.ticks_diff(now_ms, last_status_log) > 5000:
                if self.radio:
                    try:
                        irq_flags = self.radio._read_reg(_REG_IRQ_FLAGS)
                        op_mode = self.radio._read_reg(_REG_OP_MODE)
                        print("Radio status: IRQ=0x%02X OPMODE=0x%02X" % (irq_flags, op_mode))
                    except Exception as e:
                        print("Radio status read error: %s" % e)
                last_status_log = now_ms

            # Update display every 1 second
            if time.ticks_diff(now_ms, last_display_update) > 1000:
                self.update_display()
                last_display_update = now_ms
                gc.collect()
            
            time.sleep_ms(50)

# Main execution
if __name__ == "__main__":
    gateway = LoRaGateway()
    gateway.run()
