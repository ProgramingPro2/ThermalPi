# Thermal Camera Calibration Data

This directory stores flat field calibration (FFC) data for the Seek Thermal camera.

## About Flat Field Calibration

Flat field calibration, also known as Non-Uniformity Correction (NUC), eliminates fixed pattern noise from thermal images. It works by:

1. Capturing a reference frame of a uniform temperature surface
2. Computing correction factors for each pixel
3. Applying the correction to subsequent frames

This removes pixel-to-pixel sensitivity differences while preserving thermal detail.

## Files

- `thermal_ffc.npy` - Calibration frame data (NumPy binary format)
- `thermal_ffc_metadata.json` - Calibration metadata (timestamp, statistics, etc.)

## Calibration Instructions

### Initial Calibration

1. Point the thermal camera at a uniform temperature surface (e.g., a wall, ceiling, or large flat object)
2. Ensure the surface fills the entire thermal camera field of view
3. Run the HUD with calibration flag:

```bash
./run_hud.sh --calibrate
```

The system will:
- Wait 3 seconds to allow you to position the camera
- Capture 20 frames
- Average them to reduce noise
- Save the calibration data
- Continue normal operation

### Recalibrate During Runtime

If the thermal camera characteristics change (temperature drift, environment change), you can recalibrate without restarting:

```bash
# Find the HUD process ID
ps aux | grep thermal_fusion_hud

# Send SIGUSR1 signal to trigger calibration
kill -SIGUSR1 <pid>
```

Position the camera at a uniform surface before sending the signal.

### When to Recalibrate

- After significant temperature changes (camera warming up)
- When fixed pattern noise reappears
- After moving to a different environment
- Periodically (e.g., daily for best results)

### Disable Calibration

Edit `config.py`:

```python
FFC_ENABLED = False
```

## Correction Methods

The system supports two correction methods (configured in `config.py`):

### Offset Correction (Default)
- Simple additive correction
- Fast and effective for most cases
- Removes fixed pattern while preserving relative differences

### Gain Correction
- Multiplicative correction
- Better for severe non-uniformities
- Normalizes pixel sensitivities

## Technical Notes

- Calibration frames are stored as 16-bit unsigned integers
- The correction is applied before normalization in the image processing pipeline
- Performance impact is negligible (simple arithmetic operation)
- Calibration data is specific to each camera unit and should not be shared between devices

