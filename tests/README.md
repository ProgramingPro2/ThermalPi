# ThermalPi Test Scripts

## test_calibration.py

Comprehensive test for flat field calibration system.

**Usage (with thermal camera):**
```bash
cd ~/ThermalPi
source .venv/bin/activate
python3 tests/test_calibration.py
```

**Usage (simulation without hardware):**
```bash
python3 tests/test_calibration.py --no-camera
```

**Purpose:** 
- Validates calibration capture, save, load, and correction
- Tests that calibration reduces fixed pattern noise
- Can run with or without thermal camera hardware
- Point camera at uniform surface (wall, ceiling, etc.) when prompted

**What it tests:**
1. Thermal camera initialization
2. Raw frame capture
3. Calibration frame capture (averaging 20 frames)
4. Calibration save/load functionality
5. Flat field correction on live frames
6. Noise reduction validation

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

