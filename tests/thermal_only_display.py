#!/usr/bin/env python3
"""
Thermal-only display for testing Seek Thermal camera
Displays raw thermal feed without webcam fusion
"""

import cv2
import numpy as np
import time
import signal
import sys

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from seek_thermal import SeekThermal
from display_controller import DisplayController
from image_processor import normalize_thermal, apply_clahe, apply_white_hot_colormap


class ThermalOnlyDisplay:
    """Display only thermal camera feed"""
    
    def __init__(self):
        self.running = False
        self.thermal_camera = None
        self.display = None
        
    def initialize_devices(self):
        """Initialize thermal camera and display"""
        print("Initializing thermal camera...")
        try:
            self.thermal_camera = SeekThermal()
            if not self.thermal_camera.initialize():
                print("Failed to initialize thermal camera")
                return False
            print("Thermal camera initialized")
        except Exception as e:
            print(f"Error initializing thermal camera: {e}")
            return False
        
        print("Initializing display...")
        try:
            self.display = DisplayController()
            if not self.display.is_ready():
                print("Display initialization failed")
                return False
            print("Display initialized")
        except Exception as e:
            print(f"Error initializing display: {e}")
            return False
        
        return True
    
    def run(self):
        """Main display loop"""
        print("Starting thermal-only display...")
        
        if not self.initialize_devices():
            print("Failed to initialize devices")
            return False
        
        # Warmup period
        print("Thermal camera warmup (10 seconds)...")
        warmup_start = time.time()
        frame_count = 0
        
        while time.time() - warmup_start < 10:
            frame = self.thermal_camera.capture_frame()
            if frame is not None:
                frame_count += 1
            time.sleep(0.1)
        
        print(f"Warmup complete ({frame_count} frames captured)")
        print("Starting display loop...")
        
        self.running = True
        last_frame_time = time.time()
        fps_counter = 0
        fps_start_time = time.time()
        
        while self.running:
            try:
                # Capture thermal frame
                thermal_frame = self.thermal_camera.capture_frame()
                
                if thermal_frame is not None:
                    try:
                        # Clip thermal data to valid range
                        thermal_frame = np.clip(thermal_frame, 0, 16383).astype(np.uint16)
                        
                        # Process thermal: normalize -> CLAHE -> white-hot
                        thermal_norm = normalize_thermal(thermal_frame)
                        if thermal_norm is None:
                            continue
                        
                        thermal_clahe = apply_clahe(thermal_norm)
                        if thermal_clahe is None:
                            continue
                        
                        thermal_display = apply_white_hot_colormap(thermal_clahe)
                        if thermal_display is None:
                            continue
                        
                        # Resize to display size
                        if thermal_display.shape != (config.DISPLAY_HEIGHT, config.DISPLAY_WIDTH):
                            # Use OpenCV resize
                            thermal_display = cv2.resize(
                                thermal_display,
                                (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
                                interpolation=cv2.INTER_LINEAR
                            )
                        
                        # Display the frame
                        self.display.update_frame(thermal_display)
                        
                        fps_counter += 1
                        current_time = time.time()
                        if current_time - fps_start_time >= 1.0:
                            fps = fps_counter / (current_time - fps_start_time)
                            min_val = thermal_frame.min()
                            max_val = thermal_frame.max()
                            mean_val = thermal_frame.mean()
                            print(f"FPS: {fps:.1f} | Thermal range: min={min_val}, max={max_val}, mean={mean_val:.1f}")
                            fps_counter = 0
                            fps_start_time = current_time
                        
                    except Exception as e:
                        print(f"Error processing thermal frame: {e}")
                        import traceback
                        traceback.print_exc()
                        # Wait a bit before retrying
                        time.sleep(0.1)
                else:
                    time.sleep(0.05)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
        
        print("Shutting down...")
        self.shutdown()
        return True
    
    def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        
        if self.thermal_camera:
            try:
                self.thermal_camera.close()
            except:
                pass
        
        if self.display:
            try:
                self.display.clear()
                self.display.close()
            except:
                pass
        
        print("Shutdown complete")


def signal_handler(sig, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown"""
    print("\nReceived shutdown signal")
    if 'display' in globals():
        display.shutdown()
    sys.exit(0)


def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    global display
    display = ThermalOnlyDisplay()
    
    try:
        display.run()
    except KeyboardInterrupt:
        pass
    finally:
        display.shutdown()


if __name__ == "__main__":
    main()

