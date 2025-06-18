from machine import Pin, SPI
from sdcard import SDCard
from logging import log
import uos
import json

class Helper:
    def __init__(self):
        # Minimal initialization
        self.setup_complete = False
        self.sd_available = False
        
    def setup(self, config_helper=None):
        """Heavy initialization - call this from main.py"""
        if self.setup_complete:
            return  # Already set up
            
        cs = Pin(1, Pin.OUT)
        spi = SPI(0, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
        try:
            sd = SDCard(spi, cs)
            log("SD initialized OK.", "success", "~sd")
        except OSError as e:
            log(f"SD init failed: {e}", "error", "~sd")
            self.setup_complete = True
            return

        # Ensure the mount point exists
        try:
            uos.mkdir("/sd")
        except OSError:
            pass

        # Unmount any previous mount
        try:
            uos.umount("/sd")
        except (OSError, AttributeError):
            pass

        vfs = uos.VfsFat(sd)
        try:
            uos.mount(vfs, "/sd")
            log("SD mounted at /sd.", "success", "~sd")
            self.sd_available = True
        except OSError as e:
            log(f"Mount failed: {e}", "error", "~sd")
            
        self.setup_complete = True
    
    def save_data(self, data: dict):
        if not self.setup_complete:
            log("SD helper not set up - call setup() first", "error", "~sd")
            return
            
        if not self.sd_available:
            log("SD card not available - cannot save data", "warning", "~sd")
            return
            
        try:
            with open("/sd/data.json", "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            log(f"Failed to save data to SD: {e}", "error", "~sd")

    def save_logs(self, log_entries: list):
        """Save error logs to SD card"""
        if not self.setup_complete:
            return  # Silently skip if not set up to avoid recursion
            
        if not self.sd_available:
            return  # Silently skip if SD not available
            
        try:
            with open("/sd/error_logs.txt", "a") as f:
                for log_entry in log_entries:
                    f.write(f"{log_entry}\n")
        except Exception as e:
            # Don't use log() here to avoid potential recursion
            print(f"Failed to save logs to SD: {e}")