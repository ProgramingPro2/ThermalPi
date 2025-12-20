# Power Supply Issues and Solutions

## Problem: System Crashes/Freezes

The Raspberry Pi is experiencing **undervoltage** which causes system crashes when running the thermal fusion HUD.

### Symptoms
- System freezes/crashes when thermal processing is active
- SSH connections freeze
- Logs show: `hwmon hwmon1: Undervoltage detected!`
- `vcgencmd get_throttled` shows `0x50000` (undervoltage flag set)

### Root Cause
Running multiple high-power components simultaneously:
- Thermal camera (USB powered, ~150-200mA)
- USB webcam (~100-200mA)
- ILI9341 display (~100-150mA with backlight)
- Raspberry Pi 4 CPU under load (~800mA-1.2A)
- **Total: ~1.5-2.5A typical, up to 3A peak**

Most USB power supplies can't deliver consistent 3A, especially under load.

### Solutions Implemented

1. **Reduced SPI Display Speed**
   - Changed from 32 MHz to 16 MHz
   - Reduces power draw from display communication
   - Location: `config.py` → `SPI_SPEED = 16000000`

2. **Reduced Webcam Frame Rate**
   - Changed from 60 FPS to 30 FPS
   - Reduces CPU load and USB bus traffic
   - Location: `config.py` → `WEBCAM_FPS = 30`

3. **Reduced Queue Size**
   - Changed from 2 frames to 1 frame
   - Reduces memory usage and processing overhead
   - Location: `config.py` → `MAX_QUEUE_SIZE = 1`

### Recommended Hardware Solutions

**IMMEDIATE:**
1. Use a **high-quality 5V/3A (or higher) USB-C power supply**
   - Official Raspberry Pi power supply recommended
   - Avoid cheap USB chargers or phone chargers
   - Use a short, thick USB-C cable (minimum 18AWG)

2. **Add a USB-C power supply with LED indicator**
   - Shows when power is adequate
   - Green = good, red = undervoltage

**ADVANCED:**
1. **Use a powered USB hub** for cameras
   - Reduces load on Pi's USB ports
   - Provides dedicated power for cameras

2. **Disable unnecessary services**
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl disable wifi  # if using Ethernet
   ```

3. **Reduce GPU memory split**
   ```bash
   sudo raspi-config
   # Advanced Options → Memory Split → 64 (minimum)
   ```

4. **Use USB power monitor**
   - Hardware device that shows actual voltage/current
   - Helps diagnose power supply issues

### Checking Power Status

```bash
# Check throttling status
vcgencmd get_throttled
# 0x0 = OK
# 0x50000 = Under-voltage has occurred

# Check temperature
vcgencmd measure_temp

# Monitor in real-time
watch -n 1 vcgencmd get_throttled
```

### Warning Signs

- Lightning bolt icon appears on screen
- System becomes sluggish
- USB devices disconnect randomly
- System crashes/freezes under load
- Logs show undervoltage warnings

### If Still Having Issues

1. Try running with only one camera (thermal OR webcam)
2. Disable display backlight (if possible)
3. Reduce image processing (disable CLAHE, edge detection)
4. Use a powered USB hub for all USB devices
5. Consider using a 5V/4A or 5V/5A power supply

### Notes

- The Pi 4 requires a minimum of 3A for stable operation under load
- Peak current can exceed 3A during intensive processing
- Voltage drops on USB-C connector can cause issues even with good supply
- Always use official or certified high-quality power supplies

