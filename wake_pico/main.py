# This file must be compatible with MicroPython.

from logging import log, LogFormat
import time
import os
import sys
import machine

def load_components(directory: str, get_instance=None, with_setup=False):
    """
    Unified loader for both modules and helpers
    
    Args:
        directory: Directory to load from ("modules" or "helpers")
        get_instance: Function to create instance (for modules) or None (for helpers)
        with_setup: Whether to run two-phase setup with dependencies (for helpers)
    """
    components = {}
    
    # Phase 1: Load and import all components
    for file in os.listdir(directory):
        if file.endswith(".py"):
            name = file.replace(".py", '')
            module_path = f"{directory}.{name}"
            
            try:
                exec(f"import {module_path}", {})
                
                if get_instance:
                    # For modules: use provided instance creator
                    components[name] = get_instance(sys.modules[module_path])
                else:
                    # For helpers: use standard Helper() constructor
                    components[name] = sys.modules[module_path].Helper()
                    
                log(f"Successfully loaded {directory[:-1]} '{name}'", "success", f"~{directory[:-1]}")
                
            except Exception as e:
                error_msg = f"Failed to load {directory[:-1]} '{name}': {str(e)}"
                log(error_msg, "error", f"~{directory[:-1]}")
                # For modules, we'll track this as a failed module from the start
                # For helpers, we skip them entirely if they fail to load
                if get_instance:
                    components[name] = None  # Mark as failed but keep in components list
    
    # Phase 2: Setup with dependencies (only for helpers)
    if with_setup:
        # Setup config first
        config_helper = None
        if "config" in components and components["config"] is not None:
            try:
                components["config"].setup()
                config_helper = components["config"]
            except Exception as e:
                log(f"Failed to setup config helper: {str(e)}", "error", "~config")
                components["config"] = None
        
        # Setup other helpers, passing config to those that need it
        for name, helper in components.items():
            if name == "config" or helper is None:
                continue  # Already set up or failed to load
            try:
                if name == "wifi":
                    # WiFi needs config for credentials and API key
                    helper.setup(config_helper)
                else:
                    # Other helpers don't need config (yet)
                    helper.setup()
            except Exception as e:
                log(f"Failed to setup {name} helper: {str(e)}", "error", f"~{name}")
                components[name] = None
    
    return components

def reinitialize_module(name: str, module_path: str, get_module):
    """Attempt to reinitialize a failed module"""
    try:
        # Force reload the module
        if module_path in sys.modules:
            del sys.modules[module_path]
        exec(f"import {module_path}", {})
        new_module = get_module(sys.modules[module_path])
        log(f"Requested reinitialization of module '{name}'", "success", "~error")
        return new_module
    except Exception as e:
        log(f"Failed to reinitialize module '{name}': {str(e)}", "error", "~error")
        return None

modules = load_components("modules", get_instance=lambda m: m.Module())
helpers = load_components("helpers", with_setup=True)

def handle_status_led(failed_components, total_components):
    """Handle status LED indication based on module and helper initialization results"""
    try:
        # Get status_led pin from config
        if "config" not in helpers or helpers["config"] is None:
            return  # No config available, skip LED
        
        status_led_pin = helpers["config"].get("status_led", "")
        if not status_led_pin or status_led_pin.strip() == "":
            return  # No LED configured, skip
        
        # Initialize LED pin
        led_pin = machine.Pin(int(status_led_pin), machine.Pin.OUT)
        
        if failed_components > 0:
            # Flash LED for several seconds if there are failures
            log(f"Status LED: Flashing for {failed_components}/{total_components} failed components", "info", "~led")
            for _ in range(10):  # Flash for ~5 seconds (10 cycles of 0.5s each)
                led_pin.value(1)
                time.sleep(0.25)
                led_pin.value(0)
                time.sleep(0.25)
        else:
            # Keep LED on constantly for several seconds if all components loaded successfully
            log("Status LED: Solid on - all components loaded successfully", "success", "~led")
            led_pin.value(1)
            time.sleep(3)  # Stay on for 3 seconds
            led_pin.value(0)
            
    except Exception as e:
        # Don't let LED errors halt the program
        log(f"Status LED error (continuing anyway): {str(e)}", "warning", "~led")

# Error tracking for modules
module_failures = {}  # {module_name: {'count': int, 'last_attempt': float, 'backoff': int}}

# Initialize failure tracking for modules that failed during initial loading
for name, module in modules.items():
    if module is None:
        module_failures[name] = {'count': 1, 'last_attempt': 0, 'backoff': 1}
        log(f"Module '{name}' marked as failed from initial loading", "warning", f"~{name}")

loop_count = 0
led_status_shown = False  # Track if we've shown LED status after first initialization

while True:
    batch = {}
    start_time = time.time()
    loop_count += 1
    
    # Collect error logs for this loop iteration
    loop_error_logs = []

    real_time = helpers["time"].get_time()
    batch["time"] = real_time

    for name, module in modules.items():
        # Skip modules that failed during initial loading and aren't ready for retry yet
        if module is None:
            # Check if it's time to attempt reinitializing this initially failed module
            if name in module_failures:
                current_time = time.time()
                if (loop_count - module_failures[name]['last_attempt']) >= module_failures[name]['backoff']:
                    reinit_msg = f"Attempting to initialize (attempt {module_failures[name]['count']})"
                    log(reinit_msg, "info", name)
                    loop_error_logs.append(f"{helpers['time'].get_time()} - INFO: {reinit_msg}")
                    
                    module_path = f"modules.{name}"
                    new_module = reinitialize_module(name, module_path, lambda m: m.Module())
                    
                    if new_module:
                        modules[name] = new_module
                        module = new_module  # Continue with reading this module
                    else:
                        module_failures[name]['last_attempt'] = loop_count
                        module_failures[name]['backoff'] = min(module_failures[name]['backoff'] * 2, 10)
                        batch[name] = None
                        continue
                else:
                    batch[name] = None
                    continue
            else:
                batch[name] = None
                continue
        
        try:
            data = module.read()
            batch[name] = data
            
            # Reset failure tracking on successful read
            if name in module_failures:
                recovery_msg = f"Module recovered after {module_failures[name]['count']} failures"
                log(recovery_msg, "success", name)
                loop_error_logs.append(f"{helpers['time'].get_time()} - SUCCESS: {recovery_msg}")
                del module_failures[name]
                
        except Exception as e:
            error_msg = f"Module failed: {str(e)}"
            log(error_msg, "error", name)
            loop_error_logs.append(f"{helpers['time'].get_time()} - ERROR: {error_msg}")
            
            # Initialize or update failure tracking
            if name not in module_failures:
                module_failures[name] = {'count': 0, 'last_attempt': 0, 'backoff': 1}
            
            module_failures[name]['count'] += 1
            current_time = time.time()
            
            # Try to reinitialize with exponential backoff
            # Only attempt reinitialize every backoff loops, not every failure
            if (loop_count - module_failures[name]['last_attempt']) >= module_failures[name]['backoff']:
                reinit_msg = f"Attempting to reinitialize (attempt {module_failures[name]['count']})"
                log(reinit_msg, "info", name)
                loop_error_logs.append(f"{helpers['time'].get_time()} - INFO: {reinit_msg}")
                
                module_path = f"modules.{name}"
                new_module = reinitialize_module(name, module_path, lambda m: m.Module())
                
                if new_module:
                    modules[name] = new_module
                    # Try reading again immediately after successful reinit
                    try:
                        data = new_module.read()
                        batch[name] = data
                        success_msg = f"Recovered and read successfully"
                        log(success_msg, "success", name)
                        loop_error_logs.append(f"{helpers['time'].get_time()} - SUCCESS: {success_msg}")
                        del module_failures[name]
                    except Exception as retry_e:
                        retry_msg = f"Failed again after reinit: {str(retry_e)}"
                        log(retry_msg, "error", name)
                        loop_error_logs.append(f"{helpers['time'].get_time()} - WARNING: {retry_msg}")
                        module_failures[name]['last_attempt'] = loop_count
                        module_failures[name]['backoff'] = min(module_failures[name]['backoff'] * 2, 10)  # Cap at 10 loops
                else:
                    module_failures[name]['last_attempt'] = loop_count
                    module_failures[name]['backoff'] = min(module_failures[name]['backoff'] * 2, 10)  # Cap at 10 loops
            
            # Use default/safe value for failed modules
            batch[name] = None

    # Handle LED status indication after first initialization attempt
    if not led_status_shown:
        # Count actual initialization failures (modules that are None or couldn't read)
        failed_modules = sum(1 for name, value in batch.items() 
                           if name != "time" and value is None)
        total_modules = len([name for name in batch.keys() if name != "time"])
        
        # Also count helper failures (helpers that are None)
        failed_helpers = sum(1 for helper in helpers.values() if helper is None)
        total_helpers = len(helpers)
        
        total_failed = failed_modules + failed_helpers
        total_components = total_modules + total_helpers
        
        if total_failed > 0:
            log(f"Component failures detected: {failed_modules}/{total_modules} modules, {failed_helpers}/{total_helpers} helpers", "warning", "~led")
        
        handle_status_led(total_failed, total_components)
        led_status_shown = True

    print()
    log(f"Data retrieved in {time.time() - start_time:.2f}s!", "success")
    
    # Display successful reads and failure summary
    successful_modules = 0
    for key, value in batch.items():
        if key == "time":
            continue
            
        if value is not None:
            pretty_value = modules[key].pretty_print(value)
            # Find longest key length for alignment
            max_key_length = max(len(k) for k in batch.keys() if k != "time")
            padding = " " * (max_key_length - len(key) + 2)
            # Add extra padding for multi-line values
            lines = pretty_value.split("\n")
            formatted_lines = []
            for i, line in enumerate(lines):
                if i == 0:
                    formatted_lines.append(line)
                else:
                    formatted_lines.append(" " * (max_key_length + 9) + line)
            aligned_value = "\n".join(formatted_lines)
            
            print(
                "    " + LogFormat.Foreground.LIGHT_GREY + ">" + LogFormat.RESET + " " +
                key + ":" + padding + LogFormat.Foreground.DARK_GREY + aligned_value + LogFormat.RESET
            )
            successful_modules += 1
        else:
            # Use same padding calculation for failed messages
            max_key_length = max(len(k) for k in batch.keys() if k != "time")
            padding = " " * (max_key_length - len(key) + 2)
            print(
                "    " + LogFormat.Foreground.LIGHT_GREY + ">" + LogFormat.RESET + " " +
                key + ":" + padding + LogFormat.Foreground.RED + "FAILED" + LogFormat.RESET
            )
    
    # Show failure summary
    if module_failures:
        failed_count = len(module_failures)
        total_modules = len(modules)
        print(
            "    " + LogFormat.Foreground.YELLOW + f"⚠ {failed_count}/{total_modules} modules failing" + LogFormat.RESET
        )
    
    print()

    # Always save data - failures are valuable information for analysis
    try:
        helpers["sd"].save_data(batch)
        if successful_modules == 0:
            log("Saved batch with all failed readings for analysis", "info", "~save")
    except Exception as e:
        sd_error_msg = f"Failed to save data to SD card: {str(e)}"
        log(sd_error_msg, "error", "~save")
        loop_error_logs.append(f"{helpers['time'].get_time()} - ERROR: {sd_error_msg}")

    # Save error logs to SD card (separate from data)
    if loop_error_logs and "sd" in helpers:
        try:
            helpers["sd"].save_logs(loop_error_logs)
        except Exception as e:
            # Don't log this failure to avoid recursion, just print
            print(f"Failed to save error logs: {str(e)}")

    # Upload to server if WiFi is connected
    if "wifi" in helpers and helpers["wifi"].is_connected():
        try:
            success = helpers["wifi"].upload_batch(batch)
            if success:
                log("Batch uploaded to server successfully", "success", "~upload")
            # Note: upload_batch returns False and logs its own message when no API key is configured
            # so we don't need to log an error in that case
        except Exception as e:
            wifi_error_msg = f"WiFi upload failed: {str(e)}"
            log(wifi_error_msg, "error", "~upload")
            loop_error_logs.append(f"{helpers['time'].get_time()} - ERROR: {wifi_error_msg}")
    else:
        log("WiFi not connected - skipping server upload", "info", "~upload")

    # Battery management - handle potential battery module failure
    try:
        voltage = batch["battery"]["voltage"] if batch.get("battery") else 3.7  # Default safe voltage
        
        # Get sleep times from config
        sleep_times = helpers["config"].get_sleep_times() if "config" in helpers else {
            "high": 60, "medium": 90, "low": 150
        }
        
        if voltage >= 4.1:
            sleep_time = sleep_times["high"]
            log(f"Battery at {voltage}V - sleeping for {sleep_time}s", "info")
            time.sleep(sleep_time)
        elif voltage > 4.0:
            sleep_time = sleep_times["medium"]
            log(f"Battery at {voltage}V - sleeping for {sleep_time}s", "info")
            time.sleep(sleep_time)
        else:
            sleep_time = sleep_times["low"]
            log(f"Battery at {voltage}V - sleeping for {sleep_time}s", "info")
            time.sleep(sleep_time)
    except Exception as e:
        battery_error_msg = f"Battery check failed: {str(e)} - using default sleep"
        log(battery_error_msg, "error", "Battery")
        loop_error_logs.append(f"{helpers['time'].get_time()} - ERROR: {battery_error_msg}")
        default_sleep = helpers["config"].get_sleep_times()["medium"] if "config" in helpers else 90
        time.sleep(default_sleep)
    
    # Final attempt to save any remaining error logs from this iteration
    if loop_error_logs and "sd" in helpers:
        try:
            helpers["sd"].save_logs(loop_error_logs)
        except Exception as e:
            print(f"Failed to save final error logs: {str(e)}")