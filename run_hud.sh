#!/bin/bash
# ThermalPi HUD Startup Script
# This script activates the virtual environment and runs the thermal fusion HUD

# Navigate to ThermalPi directory
cd ~/ThermalPi

# Set library path for Seek Thermal libraries (both local and system-wide)
export LD_LIBRARY_PATH=~/ThermalPi/libraries:/usr/local/lib:$LD_LIBRARY_PATH

# Activate virtual environment
source .venv/bin/activate

# Run the application with any passed arguments
python3 thermal_fusion_hud.py "$@"

