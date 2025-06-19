from logging import log
import network
import time
import urequests as requests
import ujson as json

class Helper:
    def __init__(self):
        # Minimal initialization - no heavy operations
        self.wlan = network.WLAN(network.STA_IF)
        self.connected = False
        self.api_key_warning_shown = False
        self.setup_complete = False
        self.config_helper = None  # Store reference to config helper
        
    def setup(self, config_helper=None):
        """Heavy initialization - call this from main.py"""
        if self.setup_complete:
            return  # Already set up
            
        # Store reference to config helper for later use
        self.config_helper = config_helper
            
        # Use provided config helper or fallback to defaults
        if config_helper:
            self.ssid = config_helper.get_wifi_ssid()
            self.password = config_helper.get_wifi_password()
            self.base_url = config_helper.get_server_url()
            self.api_key = config_helper.get_api_key()
        else:
            # Fallback to defaults if no config provided
            self.ssid = "GLAS Secure"
            self.password = "GeorgeHale"
            self.base_url = "http://mac.tlampert.net"
            self.api_key = None
        
        # Check API key and warn if missing
        if self.api_key:
            log("API key found - requests will be authenticated", "success", "~wifi")
        else:
            log("API key not found in config - requests will be unauthenticated", "warning", "~wifi")
            self.api_key_warning_shown = True
        
        self._connect_wifi()
        self.setup_complete = True

    def _connect_wifi(self):
        """Attempt to connect to WiFi with timeout"""
        if not self.wlan.active():
            self.wlan.active(True)
            
        if self.wlan.isconnected():
            self.connected = True
            log(f"Detected existing WiFi connection: {self.wlan.ifconfig()[0]}", "success", "~wifi")
            return
            
        log(f"Connecting to WiFi: {self.ssid}", "info", "~wifi")
        self.wlan.connect(self.ssid, self.password)
        
        # Wait up to 10 seconds for connection
        timeout = 10
        start_time = time.time()
        
        while not self.wlan.isconnected() and (time.time() - start_time) < timeout:
            time.sleep(0.5)
            
        if self.wlan.isconnected():
            self.connected = True
            ip = self.wlan.ifconfig()[0]
            log(f"WiFi connected successfully: {ip}", "success", "~wifi")
        else:
            self.connected = False
            log(f"WiFi connection failed after {timeout}s - continuing without network", "warning", "~wifi")
            self.wlan.active(False)  # Save power

    def is_connected(self):
        """Check if WiFi is currently connected"""
        if not self.connected:
            return False
        return self.wlan.isconnected()

    def reconnect(self):
        """Attempt to reconnect to WiFi"""
        if self.is_connected():
            return True
            
        log("Attempting WiFi reconnection", "info", "~wifi")
        self._connect_wifi()
        return self.connected

    def get_ip(self):
        """Get current IP address or None if not connected"""
        if self.is_connected():
            return self.wlan.ifconfig()[0]
        return None

    def _get_headers(self, additional_headers=None):
        """Get headers with API key if available"""
        headers = {'Content-Type': 'application/json'}
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        elif not self.api_key_warning_shown:
            log("Sending unauthenticated request - API_KEY not available", "warning", "~wifi")
            self.api_key_warning_shown = True
            
        if additional_headers:
            headers.update(additional_headers)
            
        return headers

    def post_data(self, endpoint, data, timeout=10):
        """
        POST data to mac.tlampert.net endpoint
        
        Args:
            endpoint (str): API endpoint (e.g., '/api/water-quality')
            data (dict): Data to send as JSON
            timeout (int): Request timeout in seconds
            
        Returns:
            dict: Response data or None if failed
        """
        if not self.is_connected():
            log("Cannot POST data - WiFi not connected", "warning", "~wifi")
            return None
            
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            auth_status = "authenticated" if self.api_key else "unauthenticated"
            log(f"POSTing data to {endpoint} ({auth_status})", "info", "~wifi")
            response = requests.post(
                url, 
                data=json.dumps(data), 
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                log(f"Data posted successfully to {endpoint}", "success", "~wifi")
                result = response.json()
                response.close()
                return result
            else:
                log(f"POST failed with status {response.status_code}", "error", "~wifi")
                response.close()
                return None
                
        except Exception as e:
            log(f"POST request failed: {str(e)}", "error", "~wifi")
            return None

    def get_data(self, endpoint, timeout=10):
        """
        GET data from mac.tlampert.net endpoint
        
        Args:
            endpoint (str): API endpoint
            timeout (int): Request timeout in seconds
            
        Returns:
            dict: Response data or None if failed
        """
        if not self.is_connected():
            log("Cannot GET data - WiFi not connected", "warning", "~wifi")
            return None
            
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers({'Content-Type': 'application/json'})
        
        try:
            auth_status = "authenticated" if self.api_key else "unauthenticated"
            log(f"GETting data from {endpoint} ({auth_status})", "info", "~wifi")
            response = requests.get(url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                log(f"Data retrieved successfully from {endpoint}", "success", "~wifi")
                result = response.json()
                response.close()
                return result
            else:
                log(f"GET failed with status {response.status_code}", "error", "~wifi")
                response.close()
                return None
                
        except Exception as e:
            log(f"GET request failed: {str(e)}", "error", "~wifi")
            return None

    def upload_batch(self, batch_data):
        """
        Upload water quality batch data to the server
        
        Args:
            batch_data (dict): The batch data from main.py
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Skip upload if no API key is configured
        if not self.api_key:
            log("Skipping batch upload - no API key configured", "info", "~wifi")
            return False
        
        # Get device and experiment info from config
        try:
            if self.config_helper:
                device = self.config_helper.get_device()
                experiment_id = self.config_helper.get_experiment_id()
            else:
                # Fallback to defaults if no config helper available
                device = "unknown"
                experiment_id = "default"
        except:
            # Fallback to defaults if config fails
            device = "unknown"
            experiment_id = "default"
        
        # Convert time tuple to ISO format if needed
        processed_data = dict(batch_data)
        if 'time' in processed_data:
            time_tuple = processed_data['time']
            if isinstance(time_tuple, tuple):
                # Convert (year, month, day, weekday, hour, minute, second, subsecond) to ISO
                processed_data['timestamp'] = f"{time_tuple[0]:04d}-{time_tuple[1]:02d}-{time_tuple[2]:02d}T{time_tuple[4]:02d}:{time_tuple[5]:02d}:{time_tuple[6]:02d}"
                processed_data['time'] = processed_data['timestamp']  # Keep both for compatibility
        
        # Construct endpoint: /sync/{device}?expid={experiment_id}
        endpoint = f"/sync/{device}?expid={experiment_id}"
        result = self.post_data(endpoint, processed_data)
        return result is not None

    def get_status(self):
        """Get WiFi connection status information"""
        status = {
            'connected': self.is_connected(),
            'ssid': self.ssid,
            'ip': self.get_ip(),
            'signal_strength': None
        }
        
        if self.is_connected():
            try:
                # Get signal strength (RSSI)
                status['signal_strength'] = self.wlan.status('rssi')
            except:
                pass
                
        return status 