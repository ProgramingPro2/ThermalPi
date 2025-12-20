"""
Flat Field Calibration (Non-Uniformity Correction) for Seek Thermal Camera.
Eliminates fixed pattern noise by capturing and applying reference calibration frames.
"""

import numpy as np
import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Tuple

import config


class ThermalCalibration:
    """Handles flat field calibration for thermal camera"""
    
    def __init__(self):
        self.calibration_frame = None
        self.gain_map = None
        self.dark_reference = None
        self.metadata = {}
        self.is_loaded = False
        
    def capture_calibration_frame(self, thermal_camera, num_frames: int = 20) -> Optional[np.ndarray]:
        """
        Capture calibration frame by averaging multiple frames from uniform surface.
        
        Args:
            thermal_camera: Initialized SeekThermal camera instance
            num_frames: Number of frames to average for noise reduction
            
        Returns:
            Averaged calibration frame (uint16), or None on error
        """
        if thermal_camera is None or not thermal_camera.is_ready():
            print("Error: Thermal camera not ready for calibration")
            return None
        
        print(f"Capturing calibration data ({num_frames} frames)...")
        frames = []
        
        for i in range(num_frames):
            try:
                frame = thermal_camera.capture_frame()
                if frame is not None and frame.size > 0:
                    frames.append(frame.astype(np.float32))
                    print(f"  Frame {i+1}/{num_frames} captured")
                else:
                    print(f"  Warning: Frame {i+1} capture failed, skipping")
            except Exception as e:
                print(f"  Error capturing frame {i+1}: {e}")
                continue
            
            # Small delay between captures
            time.sleep(0.05)
        
        if len(frames) == 0:
            print("Error: No frames captured for calibration")
            return None
        
        print(f"Averaging {len(frames)} frames...")
        # Average all frames to reduce temporal noise
        calibration_frame = np.mean(frames, axis=0).astype(np.uint16)
        
        # Store statistics
        self.metadata = {
            'timestamp': time.time(),
            'num_frames_averaged': len(frames),
            'shape': calibration_frame.shape,
            'mean_value': float(np.mean(calibration_frame)),
            'std_value': float(np.std(calibration_frame)),
            'min_value': int(np.min(calibration_frame)),
            'max_value': int(np.max(calibration_frame))
        }
        
        print(f"Calibration frame captured:")
        print(f"  Shape: {self.metadata['shape']}")
        print(f"  Mean: {self.metadata['mean_value']:.1f}")
        print(f"  Std Dev: {self.metadata['std_value']:.1f}")
        print(f"  Range: [{self.metadata['min_value']}, {self.metadata['max_value']}]")
        
        return calibration_frame
    
    def compute_gain_map(self, calibration_frame: np.ndarray) -> np.ndarray:
        """
        Compute gain map from calibration frame for multiplicative correction.
        
        Args:
            calibration_frame: Reference frame from uniform temperature surface
            
        Returns:
            Gain map (float32) to normalize pixel sensitivities
        """
        # Convert to float for computation
        cal_float = calibration_frame.astype(np.float32)
        
        # Compute mean value as reference
        cal_mean = np.mean(cal_float)
        
        # Avoid division by zero: set minimum threshold
        cal_float_safe = np.maximum(cal_float, cal_mean * 0.1)
        
        # Gain map: how much to multiply each pixel to match mean
        gain_map = cal_mean / cal_float_safe
        
        # Clamp extreme values to prevent overcorrection
        gain_map = np.clip(gain_map, 0.5, 2.0)
        
        return gain_map
    
    def save_calibration(self, calibration_frame: np.ndarray, filepath: str = None) -> bool:
        """
        Save calibration data to disk.
        
        Args:
            calibration_frame: Calibration frame to save
            filepath: Path to save calibration (default from config)
            
        Returns:
            True if successful, False otherwise
        """
        if filepath is None:
            filepath = config.FFC_CALIBRATION_FILE
        
        # Ensure directory exists
        dirpath = os.path.dirname(filepath)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
            print(f"Created calibration directory: {dirpath}")
        
        try:
            # Save calibration frame as numpy array
            np.save(filepath, calibration_frame)
            print(f"Calibration frame saved to: {filepath}")
            
            # Save metadata as JSON
            metadata_path = filepath.replace('.npy', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            print(f"Calibration metadata saved to: {metadata_path}")
            
            return True
            
        except Exception as e:
            print(f"Error saving calibration: {e}")
            return False
    
    def load_calibration(self, filepath: str = None) -> bool:
        """
        Load calibration data from disk.
        
        Args:
            filepath: Path to load calibration from (default from config)
            
        Returns:
            True if successful, False otherwise
        """
        if filepath is None:
            filepath = config.FFC_CALIBRATION_FILE
        
        if not os.path.exists(filepath):
            print(f"No calibration file found at: {filepath}")
            return False
        
        try:
            # Load calibration frame
            self.calibration_frame = np.load(filepath)
            print(f"Calibration frame loaded from: {filepath}")
            print(f"  Shape: {self.calibration_frame.shape}")
            
            # Load metadata if available
            metadata_path = filepath.replace('.npy', '_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                print(f"  Calibration date: {time.ctime(self.metadata.get('timestamp', 0))}")
                print(f"  Mean value: {self.metadata.get('mean_value', 'N/A')}")
            
            # Compute gain map for gain correction method
            if config.FFC_METHOD == "gain":
                self.gain_map = self.compute_gain_map(self.calibration_frame)
                print(f"  Gain map computed (method: {config.FFC_METHOD})")
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            print(f"Error loading calibration: {e}")
            self.calibration_frame = None
            self.gain_map = None
            self.is_loaded = False
            return False
    
    def apply_flat_field_correction(self, raw_frame: np.ndarray) -> np.ndarray:
        """
        Apply flat field correction to incoming thermal frame.
        
        Args:
            raw_frame: Raw thermal frame (uint16)
            
        Returns:
            Corrected thermal frame (uint16)
        """
        if not self.is_loaded or self.calibration_frame is None:
            # No calibration loaded, return original frame
            return raw_frame
        
        if raw_frame.shape != self.calibration_frame.shape:
            print(f"Warning: Frame shape mismatch. Expected {self.calibration_frame.shape}, "
                  f"got {raw_frame.shape}. Skipping correction.")
            return raw_frame
        
        try:
            # Convert to float for computation
            frame_float = raw_frame.astype(np.float32)
            
            if config.FFC_METHOD == "gain":
                # Gain correction: multiplicative
                if self.gain_map is not None:
                    corrected = frame_float * self.gain_map
                else:
                    # Compute gain map on the fly if not cached
                    self.gain_map = self.compute_gain_map(self.calibration_frame)
                    corrected = frame_float * self.gain_map
                    
            elif config.FFC_METHOD == "offset":
                # Offset correction: subtractive
                cal_float = self.calibration_frame.astype(np.float32)
                cal_mean = np.mean(cal_float)
                
                # Remove fixed pattern: subtract (calibration - mean)
                offset = cal_float - cal_mean
                corrected = frame_float - offset
                
            else:
                print(f"Warning: Unknown FFC method '{config.FFC_METHOD}', using offset")
                cal_float = self.calibration_frame.astype(np.float32)
                cal_mean = np.mean(cal_float)
                offset = cal_float - cal_mean
                corrected = frame_float - offset
            
            # Clip to valid uint16 range
            corrected = np.clip(corrected, 0, 65535)
            
            return corrected.astype(np.uint16)
            
        except Exception as e:
            print(f"Error applying flat field correction: {e}")
            return raw_frame
    
    def perform_calibration(self, thermal_camera, save: bool = True) -> bool:
        """
        Complete calibration workflow: capture, compute, and optionally save.
        
        Args:
            thermal_camera: Initialized SeekThermal camera instance
            save: Whether to save calibration to disk
            
        Returns:
            True if successful, False otherwise
        """
        print("\n=== Starting Flat Field Calibration ===")
        print("Point the thermal camera at a uniform temperature surface")
        print("(e.g., a wall, ceiling, or large flat object)")
        print("Calibration will start in 3 seconds...")
        time.sleep(3)
        
        # Capture calibration frame
        cal_frame = self.capture_calibration_frame(thermal_camera)
        if cal_frame is None:
            print("Calibration failed: Could not capture frames")
            return False
        
        # Store calibration
        self.calibration_frame = cal_frame
        
        # Compute gain map if using gain method
        if config.FFC_METHOD == "gain":
            self.gain_map = self.compute_gain_map(cal_frame)
            print("Gain map computed")
        
        # Save to disk
        if save:
            if not self.save_calibration(cal_frame):
                print("Warning: Calibration captured but not saved to disk")
        
        self.is_loaded = True
        print("=== Calibration Complete ===\n")
        return True


# Global calibration instance
_calibration_instance = None


def get_calibration_instance() -> ThermalCalibration:
    """Get or create global calibration instance"""
    global _calibration_instance
    if _calibration_instance is None:
        _calibration_instance = ThermalCalibration()
    return _calibration_instance


def initialize_calibration() -> bool:
    """
    Initialize calibration system by loading existing calibration if available.
    
    Returns:
        True if calibration loaded, False if no calibration available
    """
    if not config.FFC_ENABLED:
        print("Flat field calibration is disabled in config")
        return False
    
    calibration = get_calibration_instance()
    return calibration.load_calibration()


def apply_correction(raw_frame: np.ndarray) -> np.ndarray:
    """
    Convenience function to apply flat field correction to a frame.
    
    Args:
        raw_frame: Raw thermal frame (uint16)
        
    Returns:
        Corrected frame (uint16), or original if correction disabled/unavailable
    """
    if not config.FFC_ENABLED:
        return raw_frame
    
    calibration = get_calibration_instance()
    return calibration.apply_flat_field_correction(raw_frame)

