"""
Seek Thermal Compact XR interface using the C wrapper (libseekwrapper.so)
Handles thermal frame capture at 9Hz via C++ library bridge.
"""

import ctypes
import os
import threading
import time
import numpy as np
from pathlib import Path

import config


class SeekThermalWrapper:
    """Interface to Seek Thermal Compact XR camera via libseekwrapper.so"""
    
    def __init__(self):
        self.lib = None
        self.camera_handle = None
        self.lock = threading.Lock()
        self.is_initialized = False
        self._load_library()
    
    def _load_library(self):
        """Load libseekwrapper.so using ctypes"""
        lib_path = Path(__file__).parent / "libraries" / "libseekwrapper.so"
        
        if not lib_path.exists():
            raise FileNotFoundError(f"libseekwrapper.so not found at {lib_path}")
        
        try:
            # Set LD_LIBRARY_PATH for dependent libraries
            library_dir = str(lib_path.parent)
            if 'LD_LIBRARY_PATH' in os.environ:
                os.environ['LD_LIBRARY_PATH'] = f"{library_dir}:{os.environ['LD_LIBRARY_PATH']}"
            else:
                os.environ['LD_LIBRARY_PATH'] = library_dir
            
            # Load the wrapper library
            self.lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            # SeekThermalHandle seek_thermal_create()
            self.lib.seek_thermal_create.argtypes = []
            self.lib.seek_thermal_create.restype = ctypes.c_void_p
            
            # int seek_thermal_open(SeekThermalHandle handle)
            self.lib.seek_thermal_open.argtypes = [ctypes.c_void_p]
            self.lib.seek_thermal_open.restype = ctypes.c_int
            
            # int seek_thermal_is_opened(SeekThermalHandle handle)
            self.lib.seek_thermal_is_opened.argtypes = [ctypes.c_void_p]
            self.lib.seek_thermal_is_opened.restype = ctypes.c_int
            
            # int seek_thermal_read_frame(handle, buffer, width, height)
            self.lib.seek_thermal_read_frame.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint16),
                ctypes.c_int,
                ctypes.c_int
            ]
            self.lib.seek_thermal_read_frame.restype = ctypes.c_int
            
            # void seek_thermal_get_dimensions(handle, width*, height*)
            self.lib.seek_thermal_get_dimensions.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int)
            ]
            self.lib.seek_thermal_get_dimensions.restype = None
            
            # void seek_thermal_close(SeekThermalHandle handle)
            self.lib.seek_thermal_close.argtypes = [ctypes.c_void_p]
            self.lib.seek_thermal_close.restype = None
            
            # void seek_thermal_destroy(SeekThermalHandle handle)
            self.lib.seek_thermal_destroy.argtypes = [ctypes.c_void_p]
            self.lib.seek_thermal_destroy.restype = None
            
        except OSError as e:
            raise RuntimeError(f"Failed to load libseekwrapper.so: {e}")
    
    def initialize(self):
        """Initialize the Seek Thermal device"""
        with self.lock:
            if self.is_initialized:
                return True
            
            try:
                # Create camera instance
                self.camera_handle = self.lib.seek_thermal_create()
                if self.camera_handle is None or self.camera_handle == 0:
                    raise RuntimeError("Failed to create Seek Thermal instance")
                
                # Open the camera
                result = self.lib.seek_thermal_open(self.camera_handle)
                if result == 0:
                    self.lib.seek_thermal_destroy(self.camera_handle)
                    self.camera_handle = None
                    raise RuntimeError("Failed to open Seek Thermal device")
                
                # Get actual dimensions
                width = ctypes.c_int()
                height = ctypes.c_int()
                self.lib.seek_thermal_get_dimensions(
                    self.camera_handle,
                    ctypes.byref(width),
                    ctypes.byref(height)
                )
                
                actual_width = width.value
                actual_height = height.value
                
                print(f"Seek Thermal opened: {actual_width}x{actual_height}")
                
                if actual_width != config.THERMAL_WIDTH or actual_height != config.THERMAL_HEIGHT:
                    print(f"Warning: Expected {config.THERMAL_WIDTH}x{config.THERMAL_HEIGHT}, "
                          f"got {actual_width}x{actual_height}")
                
                self.is_initialized = True
                return True
                
            except Exception as e:
                print(f"Error initializing Seek Thermal: {e}")
                if self.camera_handle:
                    try:
                        self.lib.seek_thermal_destroy(self.camera_handle)
                    except:
                        pass
                    self.camera_handle = None
                self.is_initialized = False
                return False
    
    def capture_frame(self):
        """
        Capture a single thermal frame.
        Returns numpy array of shape (height, width) with uint16 thermal data,
        or None if capture fails.
        """
        with self.lock:
            if not self.is_initialized or self.camera_handle is None:
                return None
            
            try:
                # Check if camera is still opened
                if self.lib.seek_thermal_is_opened(self.camera_handle) == 0:
                    return None
                
                # Allocate buffer for frame data
                buffer_size = config.THERMAL_WIDTH * config.THERMAL_HEIGHT
                buffer = (ctypes.c_uint16 * buffer_size)()
                
                # Read frame
                result = self.lib.seek_thermal_read_frame(
                    self.camera_handle,
                    buffer,
                    config.THERMAL_WIDTH,
                    config.THERMAL_HEIGHT
                )
                
                if result == 0:
                    return None
                
                # Convert ctypes array to numpy array
                frame = np.ctypeslib.as_array(buffer)
                frame = frame.reshape((config.THERMAL_HEIGHT, config.THERMAL_WIDTH))
                
                return frame.copy()
                
            except Exception as e:
                print(f"Error capturing thermal frame: {e}")
                return None
    
    def close(self):
        """Close the Seek Thermal device"""
        with self.lock:
            if self.camera_handle is not None:
                try:
                    self.lib.seek_thermal_close(self.camera_handle)
                    self.lib.seek_thermal_destroy(self.camera_handle)
                except Exception as e:
                    print(f"Error closing thermal device: {e}")
                finally:
                    self.camera_handle = None
                    self.is_initialized = False
    
    def is_ready(self):
        """Check if device is initialized and ready"""
        with self.lock:
            if not self.is_initialized or self.camera_handle is None:
                return False
            try:
                return self.lib.seek_thermal_is_opened(self.camera_handle) == 1
            except:
                return False


# Update the main import to use the new wrapper
SeekThermal = SeekThermalWrapper


# Keep the OpenCV fallback for compatibility
class SeekThermalOpenCV:
    """Alternative Seek Thermal interface using OpenCV (if device appears as USB video)"""
    
    def __init__(self):
        self.cap = None
        self.lock = threading.Lock()
        self.is_initialized = False
    
    def initialize(self, device_index=0):
        """Initialize using OpenCV VideoCapture"""
        import cv2
        
        with self.lock:
            try:
                self.cap = cv2.VideoCapture(device_index)
                if not self.cap.isOpened():
                    return False
                
                # Set resolution if possible
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.THERMAL_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.THERMAL_HEIGHT)
                
                self.is_initialized = True
                return True
            except Exception as e:
                print(f"Error initializing Seek Thermal via OpenCV: {e}")
                return False
    
    def capture_frame(self):
        """Capture frame using OpenCV"""
        import cv2
        
        with self.lock:
            if not self.is_initialized or self.cap is None:
                return None
            
            try:
                ret, frame = self.cap.read()
                if not ret:
                    return None
                
                # Convert to grayscale if needed and extract thermal data
                if len(frame.shape) == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Resize if needed
                if frame.shape != (config.THERMAL_HEIGHT, config.THERMAL_WIDTH):
                    frame = cv2.resize(frame, (config.THERMAL_WIDTH, config.THERMAL_HEIGHT))
                
                return frame.astype(np.uint16)
                
            except Exception as e:
                print(f"Error capturing thermal frame via OpenCV: {e}")
                return None
    
    def close(self):
        """Close the device"""
        with self.lock:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
                self.is_initialized = False
    
    def is_ready(self):
        """Check if device is ready"""
        return self.is_initialized and self.cap is not None

