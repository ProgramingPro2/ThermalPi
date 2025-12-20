# ThermalPi Hardware Setup Guide

## Overview

The ThermalPi project combines three hardware components to create a thermal fusion HUD display:

1. **Seek Thermal Compact XR Camera** - USB thermal imaging camera (206x156 @ 9Hz)
2. **USB Webcam** - Standard USB webcam for visible light imaging (640x480 @ 60fps)
3. **ILI9341 SPI Display** - 320x240 LCD display for output

## Required Components

### Main Components

- Raspberry Pi 4 (recommended for performance)
- Seek Thermal Compact XR camera with USB cable
- USB webcam (any standard UVC-compatible webcam)
- ILI9341 2.8" or 3.2" SPI LCD display module (320x240)
- MicroSD card (16GB+ recommended)
- 5V/3A power supply for Raspberry Pi

### Cables and Connectors

- Female-to-female jumper wires (at least 8 wires)
- USB cables for cameras
- Ethernet cable or WiFi for network access (optional, for testing)

## Raspberry Pi GPIO Pinout Reference

```
         3V3  (1) (2)  5V
   GPIO2 (SDA) (3) (4)  5V
   GPIO3 (SCL) (5) (6)  GND
       GPIO4  (7) (8)  GPIO14 (TXD)
         GND  (9) (10) GPIO15 (RXD)
      GPIO17 (11) (12) GPIO18 (PCM_CLK)
      GPIO27 (13) (14) GND
      GPIO22 (15) (16) GPIO23
         3V3 (17) (18) GPIO24 ◄── DC
      GPIO10 (19) (20) GND         ◄── MOSI
       GPIO9 (21) (22) GPIO25      ◄── RST
      GPIO11 (23) (24) GPIO8       ◄── SCLK, CS
         GND (25) (26) GPIO7
```

## ILI9341 SPI Display Connection

### Pin Connections

Connect the ILI9341 display to the Raspberry Pi GPIO header as follows:

| ILI9341 Pin | Function     | Raspberry Pi Pin            | GPIO/Description                                |
| ----------- | ------------ | --------------------------- | ----------------------------------------------- |
| VCC         | Power        | Pin 1 or 17                 | 3.3V (or Pin 2/4 for 5V if display supports it) |
| GND         | Ground       | Pin 6, 9, 14, 20, 25, or 39 | Any GND pin                                     |
| CS          | Chip Select  | Pin 24                      | GPIO 8 (CE0/SPI0_CS0)                           |
| RESET       | Reset        | Pin 22                      | GPIO 25                                         |
| DC/RS       | Data/Command | Pin 18                      | GPIO 24                                         |
| MOSI        | SPI Data     | Pin 19                      | GPIO 10 (SPI0_MOSI)                             |
| SCK/SCLK    | SPI Clock    | Pin 23                      | GPIO 11 (SPI0_SCLK)                             |
| LED         | Backlight    | Pin 1 or 17                 | 3.3V (or connect via resistor)                  |
| MISO        | SPI Data Out | Not connected               | Not used for this display                       |

### Visual Connection Guide

```
ILI9341 Display          Raspberry Pi 4
┌─────────────┐          ┌─────────────┐
│             │          │             │
│  VCC    ────┼──────────┤ Pin 17 (3.3V)
│  GND    ────┼──────────┤ Pin 20 (GND)│
│  CS     ────┼──────────┤ Pin 24 (GPIO8)
│  RESET  ────┼──────────┤ Pin 22 (GPIO25)
│  DC/RS  ────┼──────────┤ Pin 18 (GPIO24)
│  MOSI   ────┼──────────┤ Pin 19 (GPIO10)
│  SCK    ────┼──────────┤ Pin 23 (GPIO11)
│  LED    ────┼──────────┤ Pin 17 (3.3V)
│  MISO   ────┼────────── Not connected
│             │          │             │
└─────────────┘          └─────────────┘
```

### Important Notes

1. **Voltage Level**: Most ILI9341 modules are 3.3V compatible, but some have built-in regulators and work with 5V. Check your module's specifications.

2. **SPI Configuration**: This project uses SPI0 (the hardware SPI interface):

   - Bus: 0
   - Device: 0
   - Speed: 32 MHz

3. **Backlight (LED)**:
   - For simple setup, connect LED to 3.3V for always-on backlight
   - For PWM brightness control (optional), connect to a PWM-capable GPIO pin with appropriate resistor

## USB Camera Connections

### Seek Thermal Compact XR

- Connect to any available USB port on the Raspberry Pi
- The camera will appear as a USB device
- Driver uses libseek.so library (included in `/libraries` folder)
- No additional power needed (USB powered)

### USB Webcam

- Connect to any available USB port on the Raspberry Pi
- Should appear as `/dev/video0` (or `/dev/video1` if thermal camera is video0)
- Supports UVC (USB Video Class) standard
- Verify device ID in `config.py` if using multiple cameras

## Power Requirements

### Raspberry Pi Power

- Use a quality 5V/3A USB-C power supply
- Important: Running both cameras and display requires adequate power
- Poor power supply can cause:
  - Random reboots
  - Camera disconnections
  - Display artifacts
  - Throttling

### Power Consumption Estimate

- Raspberry Pi 4: ~600-800mA idle, up to 1.2A under load
- ILI9341 Display: ~100-150mA (with backlight)
- Seek Thermal Camera: ~150-200mA
- USB Webcam: ~100-200mA
- **Total: ~1.5-2.5A typical**

## Assembly Steps

### Step 1: Prepare Raspberry Pi

1. Flash Raspberry Pi OS (64-bit recommended) to microSD card
2. Enable SPI interface:
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options → SPI → Enable
   ```
3. Reboot after enabling SPI

### Step 2: Connect ILI9341 Display

1. Power OFF the Raspberry Pi completely
2. Using female-to-female jumper wires, connect the display following the pin table above
3. Double-check all connections (wrong connections can damage components)
4. Ensure jumper wires are firmly seated on GPIO pins

### Step 3: Connect Cameras

1. Plug Seek Thermal Compact XR into USB port (use USB 3.0 port for best performance)
2. Plug USB webcam into another USB port
3. Note: Order doesn't matter, but track which is `/dev/video0` and `/dev/video1`

### Step 4: Power On

1. Connect power supply to Raspberry Pi
2. Boot should proceed normally
3. Display will remain blank until software is running

## Testing Hardware

### Test SPI Interface

```bash
# Check if SPI is enabled
ls -l /dev/spidev*
# Should show: /dev/spidev0.0 and /dev/spidev0.1
```

### Test GPIO Access

```bash
# Install GPIO utilities if needed
sudo apt-get install python3-rpi.gpio

# Check GPIO status
gpio readall
```

### Test USB Cameras

```bash
# List USB devices
lsusb
# Should show Seek Thermal device and webcam

# List video devices
ls -l /dev/video*
# Should show /dev/video0 and possibly /dev/video1

# Test webcam with v4l2
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats
```

## Troubleshooting

### Display Not Working

- **Blank screen**: Check all wire connections, verify SPI is enabled
- **Garbled output**: Check SPI speed (try reducing from 32MHz to 16MHz in config.py)
- **No display device**: Run `ls /dev/spidev*` to verify SPI interface exists

### Seek Thermal Camera Issues

- **Device not found**: Run `lsusb` to verify USB connection
- **Permission denied**: User must be in `video` group: `sudo usermod -a -G video $USER`
- **Library error**: Verify `libseek.so` exists in `/libraries` folder

### Webcam Issues

- **Wrong device ID**: Check `/dev/video*` and update `WEBCAM_DEVICE_ID` in `config.py`
- **Low framerate**: Some webcams don't support 60fps, will use maximum available
- **No image**: Test with `fswebcam` or `v4l2-ctl`

### Power Issues

- **Random reboots**: Insufficient power supply
- **USB devices disconnecting**: Power supply can't provide enough current
- **Under-voltage warning**: Replace with higher quality/amperage power supply
- Check for lightning bolt icon on screen (indicates under-voltage)

## Configuration

After hardware is connected, you can adjust settings in `/config.py`:

```python
# Display settings
SPI_BUS = 0          # SPI bus number
SPI_DEVICE = 0       # SPI device number
DC_PIN = 24          # Data/Command GPIO pin
RST_PIN = 25         # Reset GPIO pin
SPI_SPEED = 32000000 # 32 MHz (reduce if display issues occur)

# Webcam settings
WEBCAM_DEVICE_ID = 0 # Usually /dev/video0 (change if needed)

# Thermal overlay adjustment
THERMAL_OFFSET_X = 0 # Adjust if thermal/visible don't align
THERMAL_OFFSET_Y = 0 # Adjust if thermal/visible don't align
ALPHA_BLEND_RATIO = 0.6 # 0.0=all visible, 1.0=all thermal
```

## Safety Notes

1. **Static Electricity**: Touch a grounded metal object before handling components
2. **Power Off First**: Always power off before connecting/disconnecting GPIO wires
3. **GPIO Voltage**: Raspberry Pi GPIO pins are 3.3V only, not 5V tolerant
4. **Current Limits**: GPIO pins limited to ~16mA each, do not power devices directly from GPIO
5. **Proper Shutdown**: Always shutdown properly (`sudo shutdown -h now`) before unplugging power

## Next Steps

Once hardware is connected and tested:

1. Install software dependencies (see main README.md)
2. Run `python3 thermal_fusion_hud.py` to start the HUD
3. Use command-line arguments to adjust parallax correction if needed

## Reference Documentation

- [Raspberry Pi GPIO Pinout](https://pinout.xyz/)
- [ILI9341 Datasheet](https://cdn-shop.adafruit.com/datasheets/ILI9341.pdf)
- [Seek Thermal Compact XR Specifications](https://www.thermal.com/compact-series.html)
- [luma.lcd Documentation](https://luma-lcd.readthedocs.io/)
