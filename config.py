"""
Configuration file for Thermal Fusion HUD system.
Adjust parameters here for parallax correction and image processing.
"""

# Thermal layer offset for parallax correction (pixels)
THERMAL_OFFSET_X = 0
THERMAL_OFFSET_Y = 0

# Display settings
DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
SPI_BUS = 0
SPI_DEVICE = 0
DC_PIN = 24  # Data/Command pin
RST_PIN = 25  # Reset pin
SPI_SPEED = 16000000  # 16 MHz (reduced to save power, prevent undervoltage)

# Image processing parameters
CLAHE_CLIP_LIMIT = 8.0  # Very strong contrast enhancement
CLAHE_TILE_GRID_SIZE = (8, 8)
CANNY_THRESHOLD_LOW = 50
CANNY_THRESHOLD_HIGH = 150
ALPHA_BLEND_RATIO = 0.5  # 0.0 = all visible, 1.0 = all thermal

# Thermal sensor settings
THERMAL_WIDTH = 207  # Actual Seek Thermal Compact/CompactXR resolution
THERMAL_HEIGHT = 156
THERMAL_FPS = 9

# Webcam settings
WEBCAM_WIDTH = 640
WEBCAM_HEIGHT = 480
WEBCAM_FPS = 30  # Reduced from 60 to save power and CPU
WEBCAM_DEVICE_ID = 0  # Usually /dev/video0
WEBCAM_ZOOM = 1.0  # Zoom factor (1.0 = no zoom, >1.0 = zoom in, <1.0 = zoom out)

# Threading settings
WEBCAM_THREAD_PRIORITY = 1
THERMAL_THREAD_PRIORITY = 1
MAX_QUEUE_SIZE = 1  # Reduced to save memory/power - only keep latest frame

