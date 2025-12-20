#!/usr/bin/env python3
"""
Minimal thermal test - simplest possible processing
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import time

import config
from seek_thermal import SeekThermal
from display_controller import DisplayController


def simple_normalize(frame):
    """Very simple normalization - just min-max scale"""
    if frame is None or frame.size == 0:
        return None
    
    frame_float = frame.astype(np.float32)
    min_val = np.min(frame_float)
    max_val = np.max(frame_float)
    
    if max_val > min_val:
        normalized = (frame_float - min_val) / (max_val - min_val)
    else:
        normalized = np.zeros_like(frame_float)
    
    return np.clip(normalized, 0.0, 1.0)


def main():
    print("=" * 50)
    print("Simple Thermal Test")
    print("=" * 50)
    
    # Initialize camera
    print("\n1. Initializing thermal camera...")
    camera = SeekThermal()
    if not camera.initialize():
        print("Failed to initialize camera")
        return
    print("✓ Camera initialized")
    
    # Initialize display
    print("\n2. Initializing display...")
    display = DisplayController()
    if not display.is_ready():
        print("Failed to initialize display")
        return
    print("✓ Display initialized")
    
    # Warmup
    print("\n3. Warmup (10 seconds)...")
    for i in range(10):
        frame = camera.capture_frame()
        time.sleep(1)
        print(f"  {i+1}/10", end='\r')
    print("\n✓ Warmup complete")
    
    print("\n4. Starting display loop (Ctrl+C to stop)...")
    print("   Try putting your hand over the camera!")
    print()
    
    frame_count = 0
    error_count = 0
    
    try:
        while True:
            frame = camera.capture_frame()
            
            if frame is not None:
                try:
                    # Clip to valid range
                    frame_clipped = np.clip(frame, 0, 16383).astype(np.uint16)
                    
                    # Simple normalization
                    normalized = simple_normalize(frame_clipped)
                    if normalized is None:
                        error_count += 1
                        continue
                    
                    # Resize to display size
                    import cv2
                    resized = cv2.resize(
                        normalized,
                        (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
                        interpolation=cv2.INTER_LINEAR
                    )
                    
                    # Display
                    display.update_frame(resized)
                    
                    frame_count += 1
                    
                    # Print stats every second
                    if frame_count % 9 == 0:
                        min_val = frame_clipped.min()
                        max_val = frame_clipped.max()
                        mean_val = frame_clipped.mean()
                        print(f"Frames: {frame_count} | Errors: {error_count} | Range: {min_val}-{max_val} (mean: {mean_val:.0f})")
                        
                except Exception as e:
                    error_count += 1
                    print(f"ERROR at frame {frame_count}: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(0.5)  # Wait before retrying
            else:
                time.sleep(0.05)
                
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        print(f"\nTotal frames: {frame_count}, Errors: {error_count}")
        camera.close()
        display.close()
        print("Done")


if __name__ == "__main__":
    main()

