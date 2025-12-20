# Flat Field Calibration (FFC)

## Overview

Flat field calibration, also known as Non-Uniformity Correction (NUC), eliminates fixed pattern noise from thermal images. This feature corrects pixel-to-pixel sensitivity variations in the thermal sensor, resulting in cleaner images on uniform temperature surfaces while preserving thermal detail.

## What Problem Does It Solve?

Thermal sensors have slight variations in sensitivity across different pixels. When viewing a uniform temperature surface (like a wall), you might see:
- Grainy or speckled patterns
- Vertical or horizontal stripes
- Hot or cold spots that aren't actually there
- Uneven coloring on what should be uniform

These artifacts are **fixed pattern noise** - they appear in the same locations on every frame because they're caused by the sensor hardware itself, not the scene being viewed.

## How It Works

The calibration process:

1. **Capture Reference**: Point the camera at a uniform temperature surface and capture multiple frames
2. **Average Frames**: Average 20 frames to reduce temporal noise
3. **Compute Correction**: Calculate correction factors for each pixel
4. **Apply Correction**: Every incoming frame is corrected before processing

The correction preserves thermal detail because it only removes the fixed sensor pattern, not actual temperature variations in the scene.

## Configuration

Edit `config.py` to configure flat field calibration:

```python
# Flat field calibration settings
FFC_ENABLED = True  # Enable/disable flat field correction
FFC_CALIBRATION_FILE = "calibration/thermal_ffc.npy"  # Calibration data path
FFC_METHOD = "offset"  # "gain" (multiplicative) or "offset" (additive) correction
```

### Correction Methods

**Offset Correction (Default - Recommended)**
- Additive correction: `corrected = raw - (calibration - mean)`
- Simple and fast
- Effective for most fixed pattern noise
- Best for thermal imaging where relative differences matter

**Gain Correction (Advanced)**
- Multiplicative correction: `corrected = raw * gain_map`
- Normalizes pixel sensitivities
- Better for severe non-uniformities
- May affect absolute temperature relationships

## Usage

### Initial Calibration

The first time you use the system, perform a calibration:

1. **Point camera at uniform surface**
   - Use a wall, ceiling, or large flat object
   - Ensure it fills the entire thermal field of view
   - Choose something at room temperature
   - Avoid surfaces with hot/cold spots

2. **Run calibration**:
   ```bash
   cd ~/ThermalPi
   ./run_hud.sh --calibrate
   ```

3. **Process**:
   - System waits 3 seconds (position camera)
   - Captures 20 frames
   - Averages them to reduce noise
   - Saves calibration to `calibration/thermal_ffc.npy`
   - Continues normal operation

### Automatic Loading

Once calibrated, the system automatically loads the calibration on startup. You'll see:

```
Initializing flat field calibration...
Calibration frame loaded from: calibration/thermal_ffc.npy
  Shape: (156, 207)
  Calibration date: Fri Dec 20 10:30:45 2025
  Mean value: 8234.5
```

### Recalibrate During Runtime

If the camera characteristics change (temperature drift, new environment), recalibrate without restarting:

```bash
# Find the process ID
ps aux | grep thermal_fusion_hud

# Send SIGUSR1 signal
kill -SIGUSR1 <pid>
```

The system will:
- Pause normal processing
- Perform calibration (point camera at uniform surface first!)
- Resume operation with new calibration

### Disable Calibration

To run without calibration, edit `config.py`:

```python
FFC_ENABLED = False
```

Or delete the calibration file:

```bash
rm calibration/thermal_ffc.npy
```

## When to Recalibrate

Recalibrate in these situations:

- **Camera warming up**: First 5-10 minutes after power on
- **Temperature changes**: Moving between environments
- **Noise reappears**: Fixed pattern becomes visible again
- **Periodic maintenance**: Daily or weekly for best results
- **After camera reset**: If the thermal camera was power cycled

## Testing

### Test with Thermal Camera

Run the comprehensive test suite:

```bash
cd ~/ThermalPi
source .venv/bin/activate
python3 tests/test_calibration.py
```

This tests:
- Camera initialization
- Frame capture
- Calibration capture and averaging
- Save/load functionality
- Live correction on 5 frames
- Noise reduction validation

### Test without Hardware (Simulation)

Test the calibration algorithms with simulated data:

```bash
python3 tests/test_calibration.py --no-camera
```

This validates the correction math without requiring hardware.

## Files Created

### Code Files

- `thermal_calibration.py` - Calibration module with capture, save, load, and correction functions
- `config.py` - Added FFC configuration parameters
- `image_processor.py` - Integrated correction into normalize_thermal()
- `thermal_fusion_hud.py` - Added --calibrate argument and SIGUSR1 signal handler
- `tests/test_calibration.py` - Comprehensive test suite

### Data Files (Created at Runtime)

- `calibration/thermal_ffc.npy` - Calibration frame data (NumPy binary)
- `calibration/thermal_ffc_metadata.json` - Metadata (timestamp, statistics)
- `calibration/README.md` - Documentation
- `calibration/.gitignore` - Prevents committing calibration data

## Technical Details

### Processing Pipeline Integration

The flat field correction is applied **early** in the processing pipeline:

```
Raw Frame (uint16)
    ↓
[Flat Field Correction] ← Applied here (if enabled)
    ↓
Percentile Normalization
    ↓
Human Detection Threshold
    ↓
CLAHE Enhancement
    ↓
Colormap Application
    ↓
Display
```

Applying correction before normalization prevents the aggressive CLAHE from amplifying fixed pattern noise.

### Performance Impact

- **Computation**: Simple element-wise arithmetic (addition or multiplication)
- **Memory**: ~64KB per calibration (207×156×2 bytes)
- **Speed**: Negligible impact (<0.1ms per frame)
- **Storage**: Calibration files are small (<100KB with metadata)

### Calibration Quality

Good calibration characteristics:
- Low standard deviation in corrected frames (uniform surfaces should be uniform)
- No visible patterns on flat surfaces
- Thermal detail preserved (hot/cold objects still clearly visible)

Poor calibration characteristics:
- High standard deviation (surface wasn't uniform during calibration)
- New patterns appear (incorrect calibration method)
- Loss of detail (shouldn't happen with proper calibration)

## Troubleshooting

### "No existing calibration found"

**Normal on first run.** Run with `--calibrate` flag to create initial calibration.

### "Frame shape mismatch"

Calibration was created with different camera resolution. Recalibrate or check thermal sensor configuration.

### "Calibration failed: Could not capture frames"

- Check thermal camera is connected and powered
- Verify `libseek.so` and wrapper are properly installed
- Test with `tests/thermal_simple_test.py` first

### Noise reduction not effective

- Surface wasn't uniform during calibration (use a plain wall)
- Camera moved during calibration capture
- Wrong correction method (try switching between "offset" and "gain")
- Recalibrate with camera at operating temperature

### Calibration file not loading

- Check file exists: `ls -la calibration/thermal_ffc.npy`
- Verify permissions: `chmod 644 calibration/thermal_ffc.npy`
- Check config: `FFC_ENABLED = True` and correct path

## Example Results

### Before Calibration
```
Raw frame on uniform wall:
  Mean: 8234.5
  Std Dev: 142.8  ← High variation on uniform surface
```

### After Calibration
```
Corrected frame on uniform wall:
  Mean: 8234.5
  Std Dev: 38.2   ← Much lower variation, cleaner image
  Noise reduced by 73.2%
```

## Command Reference

```bash
# Initial calibration
./run_hud.sh --calibrate

# Normal operation (auto-loads calibration)
./run_hud.sh

# Recalibrate during runtime
kill -SIGUSR1 $(pgrep -f thermal_fusion_hud)

# Test calibration
python3 tests/test_calibration.py

# Test without hardware
python3 tests/test_calibration.py --no-camera

# Disable calibration
# Edit config.py: FFC_ENABLED = False

# Delete calibration
rm calibration/thermal_ffc.npy
```

## Benefits

✓ Eliminates fixed pattern noise on flat surfaces  
✓ Preserves thermal detail (no spatial blurring)  
✓ One-time calibration (recalibrate only when needed)  
✓ Negligible performance impact  
✓ Works before enhancement, preventing noise amplification  
✓ Runtime recalibration without restart (SIGUSR1)  
✓ Comprehensive testing and validation tools  

## References

- [Non-uniformity correction - Wikipedia](https://en.wikipedia.org/wiki/Non-uniformity_correction)
- Thermal imaging best practices recommend regular flat field calibration
- Similar to "dark frame subtraction" in astronomy imaging

