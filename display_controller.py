"""
ILI9341 SPI display controller using luma.lcd library.
Handles frame buffer management and display updates.
"""

from luma.lcd.device import ili9341
from luma.core.interface.serial import spi
from luma.core.render import canvas
from PIL import Image
import numpy as np
import config


class DisplayController:
    """Controller for ILI9341 SPI display (320x240)"""
    
    def __init__(self):
        self.device = None
        self.is_initialized = False
        self._initialize_display()
    
    def _initialize_display(self):
        """Initialize the ILI9341 display via SPI"""
        try:
            # Create SPI interface
            serial_interface = spi(
                port=config.SPI_BUS,
                device=config.SPI_DEVICE,
                gpio_DC=config.DC_PIN,
                gpio_RST=config.RST_PIN,
                bus_speed_hz=config.SPI_SPEED
            )
            
            # Create ILI9341 device
            self.device = ili9341(
                serial_interface,
                width=config.DISPLAY_WIDTH,
                height=config.DISPLAY_HEIGHT,
                rotate=0  # No rotation
            )
            
            self.is_initialized = True
            print(f"ILI9341 display initialized: {config.DISPLAY_WIDTH}x{config.DISPLAY_HEIGHT}")
            
        except Exception as e:
            print(f"Error initializing display: {e}")
            self.is_initialized = False
            raise
    
    def update_frame(self, frame):
        """
        Update display with new frame.
        
        Args:
            frame: numpy array of shape (height, width) with values in range [0, 1]
                  or PIL Image
        """
        if not self.is_initialized or self.device is None:
            return False
        
        try:
            # Convert numpy array to PIL Image if needed
            if isinstance(frame, np.ndarray):
                # Ensure frame is in correct format
                if frame.dtype != np.uint8:
                    # Convert from [0, 1] float to [0, 255] uint8
                    frame_uint8 = (np.clip(frame, 0.0, 1.0) * 255).astype(np.uint8)
                else:
                    frame_uint8 = frame
                
                # Ensure correct shape
                if len(frame_uint8.shape) == 2:
                    # Grayscale: convert to RGB
                    frame_rgb = np.stack([frame_uint8] * 3, axis=2)
                elif frame_uint8.shape[2] == 1:
                    # Single channel: convert to RGB
                    frame_rgb = np.repeat(frame_uint8, 3, axis=2)
                else:
                    frame_rgb = frame_uint8
                
                # Resize if needed
                if frame_rgb.shape[:2] != (config.DISPLAY_HEIGHT, config.DISPLAY_WIDTH):
                    pil_img = Image.fromarray(frame_rgb)
                    pil_img = pil_img.resize(
                        (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
                        Image.Resampling.LANCZOS
                    )
                    frame_rgb = np.array(pil_img)
                
                # Convert to PIL Image
                pil_image = Image.fromarray(frame_rgb, mode='RGB')
            elif isinstance(frame, Image.Image):
                pil_image = frame
                # Resize if needed
                if pil_image.size != (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT):
                    pil_image = pil_image.resize(
                        (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
                        Image.Resampling.LANCZOS
                    )
            else:
                raise ValueError(f"Unsupported frame type: {type(frame)}")
            
            # Display the image
            self.device.display(pil_image)
            return True
            
        except Exception as e:
            print(f"Error updating display: {e}")
            return False
    
    def clear(self):
        """Clear the display (fill with black)"""
        if not self.is_initialized or self.device is None:
            return
        
        try:
            black_image = Image.new('RGB', (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT), (0, 0, 0))
            self.device.display(black_image)
        except Exception as e:
            print(f"Error clearing display: {e}")
    
    def close(self):
        """Close the display connection"""
        # luma.lcd devices don't typically need explicit closing
        # but we can mark as uninitialized
        self.is_initialized = False
        self.device = None
    
    def is_ready(self):
        """Check if display is initialized and ready"""
        return self.is_initialized and self.device is not None

