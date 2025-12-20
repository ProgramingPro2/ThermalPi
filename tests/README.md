# ThermalPi Test Scripts

## thermal_simple_test.py

Minimal thermal camera test - simplest possible processing to isolate issues.

**Usage:**
```bash
cd ~/ThermalPi
export LD_LIBRARY_PATH=~/ThermalPi/libraries:/usr/local/lib:$LD_LIBRARY_PATH
source .venv/bin/activate
python3 tests/thermal_simple_test.py
```

**Purpose:** Test thermal camera with minimal processing (simple normalization only). Use this to isolate crashes or issues.

## thermal_only_display.py

Full thermal-only display (no webcam fusion). Includes CLAHE processing.

**Usage:**
```bash
cd ~/ThermalPi
export LD_LIBRARY_PATH=~/ThermalPi/libraries:/usr/local/lib:$LD_LIBRARY_PATH
source .venv/bin/activate
python3 tests/thermal_only_display.py
```

**Purpose:** Test thermal camera with full processing pipeline but without webcam fusion. Useful for testing thermal processing stability.

