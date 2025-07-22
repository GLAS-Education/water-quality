#!/bin/bash

# pH Calibration Script for Atlas Scientific pH Sensor
# Usage: ./run.sh [mid|low|high]
# 
# This script will:
# 1. Configure script.py for the specified calibration point
# 2. Upload the script to the MicroPython device 
# 3. Run the calibration automatically
#
# Calibration must be done in order: mid -> low -> high

CALIBRATION_POINT=$1

# Check if argument is provided
if [ -z "$CALIBRATION_POINT" ]; then
    echo "Usage: $0 [mid|low|high]"
    echo ""
    echo "pH Calibration Instructions:"
    echo "  1. First run: ./run.sh mid    (pH 7.00 calibration)"
    echo "  2. Then run:  ./run.sh low    (pH 4.00 calibration)"  
    echo "  3. Finally:   ./run.sh high   (pH 10.00 calibration)"
    echo ""
    echo "Make sure you have the corresponding calibration solutions ready!"
    exit 1
fi

# Validate argument
case $CALIBRATION_POINT in
    mid)
        TARGET_PH="7.00"
        echo "Configuring for MID point calibration (pH 7.00)"
        ;;
    low)
        TARGET_PH="4.00"
        echo "Configuring for LOW point calibration (pH 4.00)"
        ;;
    high)
        TARGET_PH="10.00"
        echo "Configuring for HIGH point calibration (pH 10.00)"
        ;;
    *)
        echo "Error: Invalid calibration point '$CALIBRATION_POINT'"
        echo "Valid options are: mid, low, high"
        exit 1
        ;;
esac

# Create a backup of the original script
cp script.py script.py.backup

# Update the calibration point and target pH in script.py
sed -i '' "s/CALIBRATION_POINT = \".*\"/CALIBRATION_POINT = \"$CALIBRATION_POINT\"/" script.py
sed -i '' "s/TARGET_PH = [0-9.]*/TARGET_PH = $TARGET_PH/" script.py

echo "Updated script.py for $CALIBRATION_POINT point calibration"

# Clean up any existing files on the device and upload everything
echo "Uploading to MicroPython device..."
mpremote exec "import os; exec('def rm(p):\\n try:\\n  for i in os.listdir(p): rm(p+\"/\"+i)\\n  os.rmdir(p)\\n except: os.remove(p)\\nfor i in os.listdir():\\n if i not in [\"lib\",\"archive\"]: rm(i)')" && mpremote cp -r . : && mpremote exec "import script"

# Restore the original script
mv script.py.backup script.py

echo "Calibration complete!" 