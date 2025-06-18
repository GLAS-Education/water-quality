from logging import log
from machine import Pin, I2C, RTC
import ds1307
import time
import os

class Helper:
    def __init__(self):
        # Minimal initialization
        self.rtc = None
        self.setup_complete = False
        
    def setup(self, config_helper=None):
        """Heavy initialization - call this from main.py"""
        if self.setup_complete:
            return  # Already set up
            
        i2c = I2C(0, scl=Pin(17), sda=Pin(16))
        ds = ds1307.DS1307(i2c)
        ds = ds.datetime()
        self.rtc = RTC()
        self.rtc.datetime((ds[0], ds[1], ds[2], ds[3]+1, ds[4], ds[5], ds[6], 0))

        log("RTC setup complete.", "success", "~time")
        self.setup_complete = True

    def get_time(self):
        if not self.setup_complete:
            log("Time helper not set up - call setup() first", "error", "~time")
            return None
        return self.rtc.datetime()