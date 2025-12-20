# ThermalPi - Thermal Fusion HUD

A real-time thermal imaging fusion system for Raspberry Pi 4 that combines thermal camera data from a Seek Thermal Compact XR with a standard USB webcam, displaying the fused image on an ILI9341 SPI display.

## Current Status

**Operational in Webcam-Only Mode**

The system is fully functional with the webcam and display. The thermal camera integration code is implemented but requires a compiled C++ wrapper library to interface with the Seek Thermal `libseek.so` library (see Known Issues below).

## Hardware Requirements

- Raspberry Pi 4 (tested and working)
- ILI9341 320x240 SPI LCD Display
- USB Webcam (tested with Logitech HD Webcam C910)
- Seek Thermal Compact XR Camera (detected, integration pending)
- Female-to-female jumper wires for GPIO connections
- 5V/3A USB-C power supply

## Hardware Setup

**See [docs/HARDWARE_SETUP.md](docs/HARDWARE_SETUP.md) for detailed wiring instructions.**

### Quick Reference - ILI9341 Display Connections

| Display Pin | Raspberry Pi Pin | GPIO    |
| ----------- | ---------------- | ------- |
| VCC         | Pin 17           | 3.3V    |
| GND         | Pin 20           | GND     |
| CS          | Pin 24           | GPIO 8  |
| RESET       | Pin 22           | GPIO 25 |
| DC/RS       | Pin 18           | GPIO 24 |
| MOSI        | Pin 19           | GPIO 10 |
| SCK         | Pin 23           | GPIO 11 |
| LED         | Pin 17           | 3.3V    |

## Software Installation

### On Raspberry Pi

1. **Enable SPI interface:**

```bash
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
sudo reboot
```

2. **Clone or transfer project files:**

```bash
# Files should be in ~/ThermalPi/
cd ~/ThermalPi
```

3. **Create virtual environment and install dependencies:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Using Startup Script (Recommended)

```bash
cd ~/ThermalPi
./run_hud.sh
```

### Manual Start

```bash
cd ~/ThermalPi
source .venv/bin/activate
export LD_LIBRARY_PATH=~/ThermalPi/libraries:/usr/local/lib:$LD_LIBRARY_PATH
python3 thermal_fusion_hud.py
```

### Command-Line Options

Adjust the thermal overlay and blending parameters:

```bash
./run_hud.sh --alpha 0.7 --offset-x 5 --offset-y -3
```

Options:

- `--alpha FLOAT` - Alpha blend ratio (0.0=all visible, 1.0=all thermal), default: 0.6
- `--offset-x INT` - Thermal layer X offset in pixels for parallax correction, default: 0
- `--offset-y INT` - Thermal layer Y offset in pixels for parallax correction, default: 0

### Stopping the Application

Press `Ctrl+C` to gracefully shut down the application.

## Configuration

Edit `config.py` to adjust system parameters:

```python
# Thermal layer offset for parallax correction (pixels)
THERMAL_OFFSET_X = 0
THERMAL_OFFSET_Y = 0

# Display settings
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
SPI_BUS = 0
SPI_DEVICE = 0
DC_PIN = 24          # Data/Command pin
RST_PIN = 25         # Reset pin
SPI_SPEED = 32000000  # 32 MHz (reduce if display issues occur)

# Image processing parameters
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (8, 8)
CANNY_THRESHOLD_LOW = 50
CANNY_THRESHOLD_HIGH = 150
ALPHA_BLEND_RATIO = 0.6  # 0.0 = all visible, 1.0 = all thermal

# Thermal sensor settings
THERMAL_WIDTH = 206
THERMAL_HEIGHT = 156
THERMAL_FPS = 9

# Webcam settings
WEBCAM_WIDTH = 640
WEBCAM_HEIGHT = 480
WEBCAM_FPS = 60
WEBCAM_DEVICE_ID = 0  # Usually /dev/video0

# Threading settings
MAX_QUEUE_SIZE = 2  # Latest-frame policy: keep only 2 frames
```

You can also adjust offsets and alpha blend ratio at runtime using command-line arguments (see Usage section above).

## Project Structure

```
ThermalPi/
├── thermal_fusion_hud.py    # Main application
├── seek_thermal.py          # Seek Thermal camera interface (ctypes wrapper)
├── display_controller.py    # ILI9341 display driver
├── image_processor.py       # Image fusion and processing
├── config.py                # Configuration parameters
├── run_hud.sh               # Startup script
├── requirements.txt         # Python dependencies
├── Makefile                 # C++ wrapper compilation
├── seek_wrapper.cpp         # C++ wrapper source (needs compilation)
├── libraries/               # Seek Thermal libraries
│   ├── libseek.so           # Original Seek Thermal library (C++ API)
│   └── libseekshim.so       # Seek Thermal shim library
└── docs/                    # Documentation
    └── HARDWARE_SETUP.md    # Detailed wiring guide
```

## Performance

Tested performance on Raspberry Pi 4:

- Webcam capture: 23-25 FPS
- Display output: 7-12 FPS
- Processing latency: ~50-110ms per frame

## Known Issues

### Seek Thermal Camera Integration

**Status**: Camera detected via USB but not accessible via software

**Issue**: The `libseek.so` library uses C++ mangled symbols, which cannot be directly accessed via Python ctypes. The current `seek_thermal.py` implementation attempts to use ctypes but will fail with errors like `undefined symbol: seek_open`.

**Workaround**: System currently runs in webcam-only mode (fully functional). When thermal camera fails to initialize, the system gracefully degrades to webcam-only operation.

**Solution Available**: A C++ wrapper (`seek_wrapper.cpp`) exists to bridge the C++ API to a C-compatible interface. To enable thermal camera support:

1. Compile the C++ wrapper:

   ```bash
   cd ~/ThermalPi
   make
   make install
   ```

2. Update `seek_thermal.py` to use the compiled `libseekwrapper.so` instead of directly accessing `libseek.so`

**Alternative Solutions**:

1. Use the existing `SeekThermalOpenCV` fallback class if the camera appears as a V4L2 device
2. Obtain official Seek Thermal SDK with C bindings
3. Use alternative library (libseek-thermal open source project)
4. Reverse-engineer USB protocol

## Features

### Currently Working

- Real-time webcam capture and display
- ILI9341 SPI display output (320x240)
- Grayscale image processing
- CLAHE contrast enhancement
- Canny edge detection overlay
- Multi-threaded capture and rendering (webcam @ 60fps, thermal @ 9Hz target)
- Graceful shutdown handling
- Performance monitoring (FPS display)
- Automatic device reconnection
- Latest-frame policy to prevent queue buildup

### Code Implemented (Requires Compiled Wrapper)

All thermal processing code is implemented and ready:

- Thermal/visible image fusion pipeline
- White-hot thermal colormap mapping
- Thermal data normalization (Min-Max)
- CLAHE enhancement for thermal data
- Parallax correction (adjustable X/Y offsets)
- Alpha-blending between thermal and visible layers
- **Requires**: Compiled C++ wrapper (`libseekwrapper.so`) to interface with `libseek.so`

## Dependencies

- Python 3.11+
- OpenCV (opencv-python)
- NumPy
- Pillow (PIL)
- luma.lcd (ILI9341 driver)
- RPi.GPIO
- spidev

See `requirements.txt` for specific versions.

## Troubleshooting

### Display Issues

- **Blank screen**: Check wiring, verify SPI is enabled (`ls /dev/spidev*`)
- **Garbled output**: Reduce SPI speed in `config.py` from 32MHz to 16MHz
- **GPIO warnings**: Normal on subsequent runs, can be ignored

### Camera Issues

- **Webcam not found**: Check device ID with `v4l2-ctl --list-devices`
- **Permission denied**: Ensure user is in `video` group: `groups`
- **Low framerate**: Some webcams don't support 60fps, will use maximum available

### Power Issues

- **Random reboots**: Use quality 5V/3A power supply
- **USB disconnections**: Insufficient power, upgrade power supply
- **Under-voltage warning**: Lightning bolt icon on boot, replace power supply

## Remote Testing

To test on the Raspberry Pi from another computer:

```bash
# Transfer files (from local machine)
rsync -avz --progress ThermalPi/ jpearce@192.168.30.130:~/ThermalPi/

# Connect and run
ssh jpearce@192.168.30.130
cd ~/ThermalPi
./run_hud.sh
```

Note: The startup script (`run_hud.sh`) automatically handles virtual environment activation and library path setup.

## License

This project is for personal/educational use. Respect licenses of dependencies and hardware SDKs.

## Contributing

This is a personal project, but suggestions for Seek Thermal integration are welcome!

## Acknowledgments

- luma.lcd for excellent Python display drivers
- OpenCV for image processing capabilities
- Seek Thermal for innovative thermal imaging hardware
