# Atlas Scientific pH Sensor Calibration

This directory contains the pH calibration system for the Atlas Scientific pH sensor used in the water quality monitoring probe.

## Overview

The Atlas Scientific pH sensor requires periodic calibration to maintain accuracy. This system provides an automated 3-point calibration process that communicates directly with the sensor via UART.

## Required Materials

Before starting calibration, ensure you have:

- **pH 4.00 calibration solution** (low point)
- **pH 7.00 calibration solution** (mid point)  
- **pH 10.00 calibration solution** (high point)
- **Distilled water** for rinsing the probe
- **Clean towels** for drying

⚠️ **Important**: Calibration solutions expire and can become contaminated. Use fresh solutions and dispose of them after use (within 20 minutes of opening pouches).

## Calibration Process

The calibration **MUST** be performed in this exact order:

### Step 1: Mid Point Calibration (pH 7.00)
```bash
./run.sh mid
```

This is the most critical calibration point and must be done first. It will clear any existing calibration data.

### Step 2: Low Point Calibration (pH 4.00)
```bash
./run.sh low
```

This adds the acidic calibration point. Only run this after successfully completing the mid point calibration.

### Step 3: High Point Calibration (pH 10.00)
```bash
./run.sh high
```

This completes the 3-point calibration by adding the basic calibration point.

## Usage Instructions

1. **Connect your MicroPython device** with the pH sensor attached
2. **Navigate to the calibration directory**:
   ```bash
   cd main_pico/ph_calibration
   ```
3. **Run the calibration commands in order** (mid → low → high)

### For each calibration point:

1. **Prepare the solution**: Open the appropriate calibration solution pouch
2. **Run the calibration command**: e.g., `./run.sh mid`
3. **Follow the on-screen instructions**:
   - Rinse the pH probe with distilled water
   - Place the probe in the calibration solution
   - Ensure the probe tip is completely submerged
   - Gently shake to remove air bubbles
4. **Wait for automatic calibration**: The script will wait for readings to stabilize and then perform the calibration
5. **Check the results**: The script will show if calibration was successful

## Technical Details

### Communication Protocol
- **Interface**: UART (9600 baud, 8N1)
- **Pins**: TX=GPIO8, RX=GPIO9 (same as main sensor code)
- **Commands**: Uses Atlas Scientific EZO-pH command set

### Calibration Commands Used
- `Cal,mid,7.00` - Mid point calibration
- `Cal,low,4.00` - Low point calibration  
- `Cal,high,10.00` - High point calibration
- `Cal,clear` - Clear existing calibration (done automatically for mid point)

### Stability Requirements
- Readings must be stable within ±0.03 pH units
- 8 consecutive stable readings required before calibration
- 2-second intervals between readings

## Troubleshooting

### Calibration Fails
- **Check connections**: Ensure UART pins are properly connected
- **Check solutions**: Use fresh, uncontaminated calibration solutions
- **Check probe condition**: Clean probe tip, ensure no air bubbles
- **Check sequence**: Always start with mid point calibration first

### Device Not Responding
- Verify MicroPython device is connected and responsive
- Check that `mpremote` command works
- Ensure no other processes are using the serial port

### Readings Won't Stabilize
- Allow more time for probe to equilibrate
- Gently stir the solution
- Check probe is fully submerged
- Verify calibration solution hasn't expired

## Calibration Frequency

- **New probe**: Calibrate before first use
- **Regular use**: Recalibrate every 1-2 months
- **Heavy use**: Recalibrate monthly  
- **After storage**: Recalibrate before use
- **If readings seem inaccurate**: Recalibrate immediately

## Files

- `run.sh` - Main calibration script (accepts mid/low/high arguments)
- `script.py` - MicroPython calibration code (automatically configured by run.sh)
- `README.md` - This documentation

## Notes

- Calibration data is stored in the sensor's non-volatile memory
- Calibration persists through power cycles
- The system uses the same UART pins as the main sensor code
- Temperature compensation is set to 25°C by default (can be adjusted if needed)

For questions about the Atlas Scientific pH sensor commands, refer to the [official EZO-pH datasheet](https://www.atlas-scientific.com/files/pH_EZO_Datasheet.pdf). 