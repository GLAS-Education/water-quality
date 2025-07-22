import machine
import time

# Configuration - This will be modified by run.sh
CALIBRATION_POINT = "mid"
TARGET_PH = 7.00  # Will be set to 7.00, 4.00, or 10.00

class AtlasScientificpHCalibrator:
    def __init__(self):
        """Initialize UART communication with Atlas Scientific pH sensor"""
        # Same pins as used in the main pH sensor code
        self.uart = machine.UART(1, baudrate=9600, tx=machine.Pin(8), rx=machine.Pin(9))
        self.uart.init(bits=8, parity=None, stop=1)
        
        print("=== Atlas Scientific pH Sensor Calibration ===")
        print(f"Running {CALIBRATION_POINT.upper()} point calibration (pH {TARGET_PH})")
        print("")
        
    def send_command(self, command):
        """Send command to pH sensor and return response"""
        # Clear any existing data
        self.uart.read()
        
        # Send command with carriage return
        self.uart.write(command + "\r")
        
        # Wait for response
        time.sleep(1)
        
        response = ""
        if self.uart.any():
            data = self.uart.read()
            if data:
                response = data.decode('utf-8').strip()
        
        return response
    
    def get_reading(self):
        """Get a single pH reading"""
        response = self.send_command("R")
        
        # Debug: show raw response
        if response and response.strip():
            # Only show debug for non-empty responses
            if not response.strip().startswith("*OK"):
                print(f"\n[Debug] Raw response: {repr(response)}")
        
        try:
            # Parse the reading, removing any response codes
            # Split by both \n and \r to handle different response formats
            lines = response.replace('\r', '\n').split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('*'):
                    # Try to convert to float to verify it's a reading
                    float(line)
                    return line
        except:
            pass
        return None
    
    def wait_for_stable_reading(self):
        """Wait for pH reading to stabilize"""
        print(f"Waiting for reading to stabilize... (target: pH {TARGET_PH})")
        print("Make sure probe is in the correct calibration solution!")
        print("Current reading: ", end="")
        
        readings = []
        stable_count = 0
        no_reading_count = 0
        
        while stable_count < 20:  # Need 20 consecutive stable readings
            reading = self.get_reading()
            if reading:
                print(f"{reading} ", end="")
                no_reading_count = 0  # Reset counter
                try:
                    reading_float = float(reading)
                    readings.append(reading_float)
                    
                    if len(readings) >= 3:
                        # Check if last 3 readings are within 0.03 pH units
                        recent = readings[-3:]
                        if max(recent) - min(recent) <= 0.03:
                            stable_count += 1
                        else:
                            stable_count = 0
                    
                    # Keep only last 5 readings
                    if len(readings) > 5:
                        readings.pop(0)
                        
                except ValueError:
                    stable_count = 0
            else:
                # No reading received
                no_reading_count += 1
                print(".", end="")  # Show progress even without readings
                
                # If no readings for too long, show error
                if no_reading_count >= 10:
                    print("\n\nERROR: No readings from pH sensor!")
                    print("Possible issues:")
                    print("- pH probe not connected")
                    print("- Probe not in solution") 
                    print("- Sensor communication issue")
                    print("- Probe needs time to stabilize")
                    return None
            
            time.sleep(2)
        
        print("\nReading stabilized!")
        return readings[-1] if readings else None
    
    def check_device_info(self):
        """Check if device is responding"""
        print("Checking device connection...")
        response = self.send_command("i")
        print(f"Device info: {response}")
        
        if "pH" in response:
            return True
        else:
            print("WARNING: Device may not be responding correctly")
            return False
    
    def run_calibration_point(self):
        """Run calibration for the specified point"""
        print("Starting pH sensor calibration...\n")
        
        # Check device connection
        if not self.check_device_info():
            print("Unable to communicate with pH sensor. Check connections.")
            return False
        
        # Disable continuous readings if enabled
        self.send_command("c,0")
        time.sleep(0.5)
        
        # Show instructions
        print(f"\n--- {CALIBRATION_POINT.upper()} POINT CALIBRATION (pH {TARGET_PH}) ---")
        
        if CALIBRATION_POINT == "mid":
            print("INSTRUCTIONS:")
            print("1. Rinse the pH probe with distilled water")
            print("2. Place the probe in pH 7.00 calibration solution")
            print("3. Ensure the probe tip is completely submerged")
            print("4. Gently shake to remove air bubbles")
            print("")
            print("NOTE: This mid point calibration will automatically")
            print("      clear any existing calibration data.")
        elif CALIBRATION_POINT == "low":
            print("INSTRUCTIONS:")
            print("1. Rinse the pH probe with distilled water") 
            print("2. Place the probe in pH 4.00 calibration solution")
            print("3. Ensure the probe tip is completely submerged")
            print("4. Gently shake to remove air bubbles")
            print("")
            print("NOTE: Make sure you have already completed MID point calibration!")
        elif CALIBRATION_POINT == "high":
            print("INSTRUCTIONS:")
            print("1. Rinse the pH probe with distilled water")
            print("2. Place the probe in pH 10.00 calibration solution")
            print("3. Ensure the probe tip is completely submerged")
            print("4. Gently shake to remove air bubbles")
            print("")
            print("NOTE: Make sure you have already completed MID and LOW point calibration!")
        
        print("The calibration will start automatically in 10 seconds...")
        for i in range(10, 0, -1):
            print(f"Starting in {i}...", end="\r")
            time.sleep(1)
        print("")
        
        # Wait for reading to stabilize
        stable_reading = self.wait_for_stable_reading()
        
        if stable_reading is None:
            print("ERROR: Could not get stable reading!")
            return False
        
        # Send calibration command
        cal_command = f"cal,{CALIBRATION_POINT},{int(TARGET_PH)}"
        print(f"\nSending calibration command: {cal_command}")
        
        response = self.send_command(cal_command)
        print(f"Response: {response}")
        
        if "*OK" in response or "OK" in response:
            print(f"✓ {CALIBRATION_POINT.upper()} point calibration successful!")
            print(f"  Target pH: {TARGET_PH}")
            print(f"  Actual reading: {stable_reading:.3f}")
            
            # Verify calibration by taking a few more readings
            print("\nVerifying calibration...")
            time.sleep(2)
            
            verification_readings = []
            for i in range(5):
                reading = self.get_reading()
                if reading:
                    try:
                        ph_value = float(reading)
                        verification_readings.append(ph_value)
                        print(f"  Verification reading {i+1}: {ph_value:.3f}")
                    except ValueError:
                        pass
                time.sleep(1)
            
            if verification_readings:
                avg_reading = sum(verification_readings) / len(verification_readings)
                error = abs(avg_reading - TARGET_PH)
                print(f"\n  Average verified reading: {avg_reading:.3f}")
                print(f"  Error from target: {error:.3f} pH units")
                
                if error < 0.1:  # Within 0.1 pH units
                    print("  ✓ Calibration verified - Excellent accuracy!")
                elif error < 0.3:  # Within 0.3 pH units
                    print("  ✓ Calibration verified - Good accuracy")
                else:
                    print("  ⚠ Calibration may need to be repeated")
                    print("    Ensure probe is clean and solution is fresh")
            
            # Check slope if this was a multi-point calibration
            if CALIBRATION_POINT == "high":
                print("\nChecking calibration slope...")
                response = self.send_command("slope,?")
                print(f"Slope response: {response}")
                
                # Also check calibration status
                print("\nChecking calibration status...")
                cal_response = self.send_command("cal,?")
                print(f"Calibration status: {cal_response}")
                # Should show ?cal,3 for 3-point calibration
            
            print(f"\n{CALIBRATION_POINT.upper()} point calibration is complete!")
            print("The calibration is stored in the sensor's memory.")
            
            return True
        else:
            print(f"✗ {CALIBRATION_POINT.upper()} point calibration failed!")
            print("Check your calibration solution and probe connection.")
            return False

def main():
    """Main calibration routine"""
    calibrator = AtlasScientificpHCalibrator()
    
    try:
        success = calibrator.run_calibration_point()
        
        if success:
            print(f"\n{CALIBRATION_POINT.upper()} point calibration complete!")
            if CALIBRATION_POINT == "mid":
                print("Next step: Run './run.sh low' to calibrate the low point.")
            elif CALIBRATION_POINT == "low":
                print("Next step: Run './run.sh high' to calibrate the high point.")
            elif CALIBRATION_POINT == "high":
                print("All calibration points complete! Your sensor is ready to use.")
        else:
            print(f"\n{CALIBRATION_POINT.upper()} point calibration failed.")
            print("Please check your setup and try again.")
            
    except Exception as e:
        print(f"\nError during calibration: {e}")
        print("Please check your connections and try again.")

if __name__ in ["script", "__main__"]: # mpremote exec, startup
    main() 