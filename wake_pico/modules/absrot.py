import machine, board, time, busio
import struct
from base import BaseModule
from logging import log

class Module(BaseModule):
    def __init__(self):
        super().__init__("absrot")
        self.i2c = None
        self.addr = 0x28
        self.initialized = False
        
    def _init_sensor(self):
        """Initialize the BNO055 absolute orientation sensor"""
        if not self.initialized:
            # Create I2C bus
            self.i2c = busio.I2C(scl=board.GP19, sda=board.GP18)
            
            # Verify sensor is present and get chip ID
            while not self.i2c.try_lock():
                time.sleep(0.01)
            try:
                devices = self.i2c.scan()
                if self.addr not in devices:
                    raise Exception(f"BNO055 not found at address 0x{self.addr:02x}")
                
                # Read and verify chip ID
                chip_id = self._read_register(0x00)
                if chip_id != 0xA0:
                    raise Exception(f"Invalid chip ID: 0x{chip_id:02x} (expected 0xA0)")
                
                log(f"BNO055 chip ID verified: 0x{chip_id:02x}", "success", self.id)
            finally:
                self.i2c.unlock()
            
            # Initialize sensor
            self._reset_sensor()
            self._configure_sensor()
            self._wait_for_sensor_ready()
            
            self.initialized = True
            log("Setup complete!", "success", self.id)
    
    def _read_register(self, reg):
        """Read a single byte from a register"""
        result = bytearray(1)
        self.i2c.writeto(self.addr, bytearray([reg]))
        self.i2c.readfrom_into(self.addr, result)
        return result[0]
    
    def _write_register(self, reg, value):
        """Write a single byte to a register"""
        self.i2c.writeto(self.addr, bytearray([reg, value]))
    
    def _read_registers(self, reg, count):
        """Read multiple bytes from consecutive registers"""
        result = bytearray(count)
        self.i2c.writeto(self.addr, bytearray([reg]))
        self.i2c.readfrom_into(self.addr, result)
        return result
    
    def _reset_sensor(self):
        """Reset the BNO055 sensor"""
        while not self.i2c.try_lock():
            time.sleep(0.01)
        try:
            # Set to config mode
            self._write_register(0x3D, 0x00)  # OPR_MODE register
            time.sleep(0.02)
            
            # Trigger reset
            try:
                self._write_register(0x3F, 0x20)  # SYS_TRIGGER register
            except:
                pass  # Reset may cause I2C error
            
            # Wait for reset to complete
            time.sleep(0.7)
        finally:
            self.i2c.unlock()
    
    def _configure_sensor(self):
        """Configure the BNO055 sensor"""
        while not self.i2c.try_lock():
            time.sleep(0.01)
        try:
            # Set to config mode
            self._write_register(0x3D, 0x00)  # CONFIG_MODE
            time.sleep(0.02)
            
            # Set normal power mode
            self._write_register(0x3E, 0x00)  # PWR_MODE register
            
            # Set page 0
            self._write_register(0x07, 0x00)  # PAGE_ID register
            
            # Reset trigger register
            self._write_register(0x3F, 0x00)  # SYS_TRIGGER register
            
            # Configure accelerometer (4G range)
            self._write_register(0x08, 0x0D)  # ACC_CONFIG register
            
            # Configure gyroscope (2000 dps)
            self._write_register(0x0A, 0x00)  # GYR_CONFIG_0 register
            self._write_register(0x0B, 0x00)  # GYR_CONFIG_1 register
            
            # Configure magnetometer (20Hz)
            self._write_register(0x09, 0x1F)  # MAG_CONFIG register
            
            time.sleep(0.01)
            
            # Set to NDOF mode (9DOF fusion)
            self._write_register(0x3D, 0x0C)  # NDOF_MODE
            time.sleep(0.01)
            
        finally:
            self.i2c.unlock()
    
    def _wait_for_sensor_ready(self):
        """Wait for sensor fusion to be ready and providing valid data"""
        log("Waiting for sensor fusion to stabilize...", "info", self.id)
        
        max_attempts = 50  # 5 seconds max wait
        for attempt in range(max_attempts):
            while not self.i2c.try_lock():
                time.sleep(0.01)
            try:
                # Check system status
                sys_status = self._read_register(0x39)  # SYS_STAT register
                
                # System status: 5 = fusion algorithm running
                if sys_status == 5:
                    # Also check if we're getting non-zero Euler angles
                    euler_data = self._read_registers(0x1A, 6)
                    euler = struct.unpack('<hhh', euler_data)
                    
                    # If any Euler angle is non-zero, fusion is working
                    if any(x != 0 for x in euler):
                        log(f"Sensor fusion ready after {attempt * 0.1:.1f}s", "success", self.id)
                        return
                
                # If still not ready, wait a bit more
                time.sleep(0.1)
                
            finally:
                self.i2c.unlock()
        
        # If we get here, sensor might still work but took longer to stabilize
        log("Sensor fusion taking longer than expected, continuing anyway", "warning", self.id)

    def read(self) -> dict:
        self._init_sensor()
        
        while not self.i2c.try_lock():
            time.sleep(0.01)
        
        try:
            # Read all sensor data
            # Euler angles (3 * 2 bytes) at 0x1A
            euler_data = self._read_registers(0x1A, 6)
            euler = struct.unpack('<hhh', euler_data)
            euler = tuple(x / 16.0 for x in euler)  # Scale factor 1/16
            
            # Acceleration (3 * 2 bytes) at 0x08  
            accel_data = self._read_registers(0x08, 6)
            acceleration = struct.unpack('<hhh', accel_data)
            acceleration = tuple(x / 100.0 for x in acceleration)  # Scale factor 1/100 (m/s²)
            
            # Gyroscope (3 * 2 bytes) at 0x14
            gyro_data = self._read_registers(0x14, 6)
            gyro = struct.unpack('<hhh', gyro_data) 
            gyro = tuple(x * 0.001090830782496456 for x in gyro)  # Scale to rad/s
            
            # Quaternion (4 * 2 bytes) at 0x20
            quat_data = self._read_registers(0x20, 8)
            quaternion = struct.unpack('<hhhh', quat_data)
            quaternion = tuple(x / (1 << 14) for x in quaternion)  # Scale factor 1/16384
            
            # Linear acceleration (3 * 2 bytes) at 0x28
            lin_accel_data = self._read_registers(0x28, 6)
            linear_acceleration = struct.unpack('<hhh', lin_accel_data)
            linear_acceleration = tuple(x / 100.0 for x in linear_acceleration)  # Scale factor 1/100
            
            # Format as comma-separated string to match original format
            sensor_data = f"{euler[0]},{euler[1]},{euler[2]},{acceleration[0]},{acceleration[1]},{acceleration[2]},{gyro[0]},{gyro[1]},{gyro[2]},{quaternion[0]},{quaternion[1]},{quaternion[2]},{quaternion[3]},{linear_acceleration[0]},{linear_acceleration[1]},{linear_acceleration[2]}"
            
        finally:
            self.i2c.unlock()
        
        return {
            "value": sensor_data
        }

    def pretty_print(self, data: dict) -> str:
        sensor_data = data.get("value")
        
        if sensor_data is not None:
            # Parse the data for prettier display
            try:
                values = [float(x) for x in sensor_data.split(',')]
                if len(values) >= 16:
                    return f"Euler = ({values[0]:.1f}°,{values[1]:.1f}°,{values[2]:.1f}°)\nAccel = ({values[3]:.2f},{values[4]:.2f},{values[5]:.2f})m/s²"
            except:
                pass
            return f"{sensor_data}"
        else:
            return f"No reading"
