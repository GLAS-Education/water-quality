from logging import log
import ujson as json
import os

class Helper:
    def __init__(self):
        # Minimal initialization
        self.config_file = "./config.json"
        self.config = {}
        self.setup_complete = False
        
    def setup(self, config_helper=None):
        """Load configuration from file"""
        if self.setup_complete:
            return  # Already set up
            
        self._load_config()
        self.setup_complete = True

    def _load_config(self):
        """Load configuration from config.json file"""
        try:
            # Check if file exists by trying to open it
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            log(f"Configuration loaded from {self.config_file}", "success", "~config")
        except OSError:
            log(f"Config file {self.config_file} not found - using defaults", "warning", "~config")
            self.config = {}
        except Exception as e:
            log(f"Failed to load config file: {str(e)}", "error", "~config")
            self.config = {}

    def get(self, key, default=None):
        """Get a configuration value by key"""
        return self.config.get(key, default)

    def get_api_key(self):
        """Get the API key from configuration"""
        return self.config.get("api_key", None)

    def get_device(self):
        """Get the device name from configuration"""
        return self.config.get("device", "unknown")

    def get_experiment_id(self):
        """Get the experiment ID from configuration"""
        return self.config.get("experiment_id", "default")

    def get_wifi_ssid(self):
        """Get WiFi SSID from configuration"""
        return self.config.get("wifi_ssid", "GLAS Secure")

    def get_wifi_password(self):
        """Get WiFi password from configuration"""
        return self.config.get("wifi_password", "GeorgeHale")

    def get_server_url(self):
        """Get server URL from configuration"""
        return self.config.get("server_url", "http://mac.tlampert.net")

    def has_key(self, key):
        """Check if a configuration key exists"""
        return key in self.config

    def reload(self):
        """Reload configuration from file"""
        log("Reloading configuration", "info", "~config")
        self._load_config()

    def get_all(self):
        """Get all configuration values"""
        return dict(self.config)

    def get_sleep_times(self):
        """Get battery-based sleep configuration"""
        return {
            "high": self.config.get("sleep_high_battery", 60),      # >= 4.1V
            "medium": self.config.get("sleep_medium_battery", 90),  # > 4.0V
            "low": self.config.get("sleep_low_battery", 150)        # <= 4.0V
        } 