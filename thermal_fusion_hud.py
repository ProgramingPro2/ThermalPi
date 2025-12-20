#!/usr/bin/env python3
"""
Thermal Fusion HUD for Raspberry Pi 4
Fuses Seek Thermal Compact XR and USB webcam imagery on ILI9341 SPI display.
"""

import cv2
import numpy as np
import threading
import queue
import time
import signal
import sys
import argparse
from collections import deque

import config
from seek_thermal import SeekThermal, SeekThermalOpenCV
from image_processor import fuse_thermal_hud
from display_controller import DisplayController
from thermal_calibration import get_calibration_instance, initialize_calibration


class ThermalFusionHUD:
    """Main application class for thermal fusion HUD"""
    
    def __init__(self):
        self.running = False
        self.webcam_cap = None
        self.thermal_camera = None
        self.display = None
        
        # Threading components
        self.webcam_thread = None
        self.thermal_thread = None
        self.webcam_queue = queue.Queue(maxsize=config.MAX_QUEUE_SIZE)
        self.thermal_queue = queue.Queue(maxsize=config.MAX_QUEUE_SIZE)
        self.shutdown_event = threading.Event()
        
        # Frame statistics
        self.webcam_fps = 0.0
        self.thermal_fps = 0.0
        self.display_fps = 0.0
        self.webcam_frame_count = 0
        self.thermal_frame_count = 0
        self.display_frame_count = 0
        self.last_stats_time = time.time()
        
        # Performance monitoring
        self.webcam_times = deque(maxlen=30)
        self.thermal_times = deque(maxlen=30)
        self.display_times = deque(maxlen=30)
        
        # Calibration
        self.calibration_requested = False
        self.calibration_in_progress = False
    
    def perform_calibration(self):
        """Perform thermal camera calibration"""
        if self.thermal_camera is None or not self.thermal_camera.is_ready():
            print("Error: Thermal camera not available for calibration")
            return False
        
        print("\n" + "="*60)
        print("THERMAL CAMERA CALIBRATION")
        print("="*60)
        
        self.calibration_in_progress = True
        
        # Get calibration instance
        calibration = get_calibration_instance()
        
        # Perform calibration
        success = calibration.perform_calibration(self.thermal_camera, save=True)
        
        self.calibration_in_progress = False
        self.calibration_requested = False
        
        if success:
            print("Calibration successful!")
        else:
            print("Calibration failed!")
        
        return success
    
    def request_calibration(self):
        """Request calibration (can be called from signal handler)"""
        if not self.calibration_in_progress:
            print("\nCalibration requested...")
            self.calibration_requested = True
        else:
            print("\nCalibration already in progress, please wait...")
    
    def initialize_devices(self):
        """Initialize all hardware devices"""
        print("Initializing devices...")
        
        # Initialize webcam
        try:
            self.webcam_cap = cv2.VideoCapture(config.WEBCAM_DEVICE_ID)
            if not self.webcam_cap.isOpened():
                raise RuntimeError(f"Failed to open webcam device {config.WEBCAM_DEVICE_ID}")
            
            # Set webcam properties
            self.webcam_cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.WEBCAM_WIDTH)
            self.webcam_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.WEBCAM_HEIGHT)
            self.webcam_cap.set(cv2.CAP_PROP_FPS, config.WEBCAM_FPS)
            
            # Verify actual resolution
            actual_width = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.webcam_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"Webcam initialized: {actual_width}x{actual_height}")
            
        except Exception as e:
            print(f"Error initializing webcam: {e}")
            return False
        
        # Initialize thermal camera
        try:
            # Try ctypes wrapper first
            self.thermal_camera = SeekThermal()
            if not self.thermal_camera.initialize():
                print("ctypes wrapper failed, trying OpenCV fallback...")
                self.thermal_camera = SeekThermalOpenCV()
                if not self.thermal_camera.initialize():
                    raise RuntimeError("Failed to initialize thermal camera with both methods")
            
            print("Thermal camera initialized")
            
        except Exception as e:
            print(f"Error initializing thermal camera: {e}")
            print("Continuing without thermal camera (webcam-only mode)")
            self.thermal_camera = None
        
        # Initialize display
        try:
            self.display = DisplayController()
            if not self.display.is_ready():
                raise RuntimeError("Display initialization failed")
            print("Display initialized")
            
        except Exception as e:
            print(f"Error initializing display: {e}")
            return False
        
        return True
    
    def webcam_capture_loop(self):
        """Webcam capture thread (60fps target)"""
        print("Webcam capture thread started")
        frame_time_target = 1.0 / config.WEBCAM_FPS
        
        while not self.shutdown_event.is_set():
            loop_start = time.time()
            
            try:
                ret, frame = self.webcam_cap.read()
                if not ret:
                    print("Warning: Failed to read webcam frame")
                    time.sleep(0.01)
                    continue
                
                # Put frame in queue (latest-frame policy: drop old if full)
                try:
                    self.webcam_queue.put_nowait(frame)
                except queue.Full:
                    # Remove old frame and add new one
                    try:
                        self.webcam_queue.get_nowait()
                        self.webcam_queue.put_nowait(frame)
                    except queue.Empty:
                        pass
                
                self.webcam_frame_count += 1
                
            except Exception as e:
                print(f"Error in webcam capture: {e}")
                time.sleep(0.1)
            
            # Maintain target frame rate
            elapsed = time.time() - loop_start
            sleep_time = max(0, frame_time_target - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            self.webcam_times.append(time.time() - loop_start)
        
        print("Webcam capture thread stopped")
    
    def thermal_capture_loop(self):
        """Thermal capture thread (9Hz target)"""
        print("Thermal capture thread started")
        frame_time_target = 1.0 / config.THERMAL_FPS
        
        # Reconnection handling
        reconnect_delay = 1.0
        max_reconnect_delay = 10.0
        
        while not self.shutdown_event.is_set():
            loop_start = time.time()
            
            if self.thermal_camera is None or not self.thermal_camera.is_ready():
                # Try to reinitialize
                try:
                    if self.thermal_camera is None:
                        self.thermal_camera = SeekThermal()
                    if not self.thermal_camera.initialize():
                        self.thermal_camera = SeekThermalOpenCV()
                        if not self.thermal_camera.initialize():
                            raise RuntimeError("Reconnection failed")
                    print("Thermal camera reconnected")
                    reconnect_delay = 1.0
                except Exception as e:
                    print(f"Thermal camera reconnection failed: {e}")
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    continue
            
            try:
                frame = self.thermal_camera.capture_frame()
                if frame is not None:
                    # Put frame in queue (latest-frame policy)
                    try:
                        self.thermal_queue.put_nowait(frame)
                    except queue.Full:
                        try:
                            self.thermal_queue.get_nowait()
                            self.thermal_queue.put_nowait(frame)
                        except queue.Empty:
                            pass
                    
                    self.thermal_frame_count += 1
                else:
                    # Frame capture failed, might need reconnection
                    print("Warning: Thermal frame capture returned None")
                    
            except Exception as e:
                print(f"Error in thermal capture: {e}")
                # Mark camera as not ready for reconnection attempt
                if self.thermal_camera:
                    try:
                        self.thermal_camera.close()
                    except:
                        pass
                    self.thermal_camera = None
            
            # Maintain target frame rate
            elapsed = time.time() - loop_start
            sleep_time = max(0, frame_time_target - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            self.thermal_times.append(time.time() - loop_start)
        
        print("Thermal capture thread stopped")
    
    def update_statistics(self):
        """Update and print frame rate statistics"""
        current_time = time.time()
        elapsed = current_time - self.last_stats_time
        
        if elapsed >= 1.0:  # Update every second
            self.webcam_fps = self.webcam_frame_count / elapsed
            self.thermal_fps = self.thermal_frame_count / elapsed
            self.display_fps = self.display_frame_count / elapsed
            
            avg_webcam_time = np.mean(self.webcam_times) if self.webcam_times else 0
            avg_thermal_time = np.mean(self.thermal_times) if self.thermal_times else 0
            avg_display_time = np.mean(self.display_times) if self.display_times else 0
            
            print(f"FPS - Webcam: {self.webcam_fps:.1f}, "
                  f"Thermal: {self.thermal_fps:.1f}, "
                  f"Display: {self.display_fps:.1f} | "
                  f"Avg times - Webcam: {avg_webcam_time*1000:.1f}ms, "
                  f"Thermal: {avg_thermal_time*1000:.1f}ms, "
                  f"Display: {avg_display_time*1000:.1f}ms")
            
            self.webcam_frame_count = 0
            self.thermal_frame_count = 0
            self.display_frame_count = 0
            self.last_stats_time = current_time
    
    def run(self, perform_initial_calibration=False):
        """Main fusion and display loop"""
        print("Starting Thermal Fusion HUD...")
        
        if not self.initialize_devices():
            print("Failed to initialize devices")
            return False
        
        # Initialize calibration system
        if config.FFC_ENABLED:
            print("\nInitializing flat field calibration...")
            if initialize_calibration():
                print("Existing calibration loaded successfully")
            else:
                print("No existing calibration found")
                if perform_initial_calibration and self.thermal_camera:
                    print("Performing initial calibration...")
                    self.perform_calibration()
        
        self.running = True
        
        # Start capture threads
        self.webcam_thread = threading.Thread(
            target=self.webcam_capture_loop,
            daemon=True
        )
        self.thermal_thread = threading.Thread(
            target=self.thermal_capture_loop,
            daemon=True
        )
        
        self.webcam_thread.start()
        self.thermal_thread.start()
        
        # Give threads time to start capturing
        time.sleep(0.5)
        
        print("Main fusion loop started")
        
        # Main fusion loop
        last_thermal_frame = None
        last_webcam_frame = None
        
        while self.running and not self.shutdown_event.is_set():
            loop_start = time.time()
            
            # Check for calibration request
            if self.calibration_requested and not self.calibration_in_progress:
                if self.thermal_camera and self.thermal_camera.is_ready():
                    self.perform_calibration()
                else:
                    print("Cannot calibrate: thermal camera not available")
                    self.calibration_requested = False
            
            # Get latest frames (non-blocking)
            try:
                while not self.webcam_queue.empty():
                    last_webcam_frame = self.webcam_queue.get_nowait()
            except queue.Empty:
                pass
            
            try:
                while not self.thermal_queue.empty():
                    last_thermal_frame = self.thermal_queue.get_nowait()
            except queue.Empty:
                pass
            
            # Perform fusion if we have frames
            if last_webcam_frame is not None:
                if last_thermal_frame is not None:
                    # Full fusion mode
                    try:
                        composite = fuse_thermal_hud(last_thermal_frame, last_webcam_frame)
                        if composite is not None:
                            self.display.update_frame(composite)
                            self.display_frame_count += 1
                        else:
                            # Fusion failed, fall back to webcam-only for this frame
                            from image_processor import process_webcam_frame
                            import numpy as np
                            processed = process_webcam_frame(last_webcam_frame)
                            if processed is not None:
                                # Convert to RGB if grayscale
                                if len(processed.shape) == 2:
                                    processed = np.stack([processed] * 3, axis=2)
                                self.display.update_frame(processed)
                                self.display_frame_count += 1
                    except Exception as e:
                        print(f"Fusion error: {e}")
                        import traceback
                        traceback.print_exc()
                        # On error, fall back to webcam-only mode for this frame
                        try:
                            from image_processor import process_webcam_frame
                            import numpy as np
                            processed = process_webcam_frame(last_webcam_frame)
                            if processed is not None:
                                # Convert to RGB if grayscale
                                if len(processed.shape) == 2:
                                    processed = np.stack([processed] * 3, axis=2)
                                self.display.update_frame(processed)
                                self.display_frame_count += 1
                        except:
                            pass  # Skip this frame if everything fails
                else:
                    # Webcam-only mode (thermal not available)
                    try:
                        from image_processor import process_webcam_frame
                        processed = process_webcam_frame(last_webcam_frame)
                        if processed is not None:
                            self.display.update_frame(processed)
                            self.display_frame_count += 1
                    except Exception as e:
                        print(f"Error processing webcam frame: {e}")
            
            # Update statistics
            self.update_statistics()
            
            # Small sleep to prevent CPU spinning
            elapsed = time.time() - loop_start
            self.display_times.append(elapsed)
            time.sleep(0.001)  # 1ms sleep
        
        print("Main fusion loop stopped")
        return True
    
    def shutdown(self):
        """Graceful shutdown"""
        print("Shutting down...")
        self.running = False
        self.shutdown_event.set()
        
        # Wait for threads to finish
        if self.webcam_thread and self.webcam_thread.is_alive():
            self.webcam_thread.join(timeout=2.0)
        if self.thermal_thread and self.thermal_thread.is_alive():
            self.thermal_thread.join(timeout=2.0)
        
        # Close devices
        if self.webcam_cap:
            self.webcam_cap.release()
        
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
    if 'hud' in globals():
        hud.shutdown()
    sys.exit(0)


def calibration_signal_handler(sig, frame):
    """Handle SIGUSR1 for runtime calibration"""
    print("\nReceived calibration signal (SIGUSR1)")
    if 'hud' in globals():
        hud.request_calibration()
    else:
        print("HUD not initialized yet")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Thermal Fusion HUD for Raspberry Pi 4')
    parser.add_argument('--offset-x', type=int, default=config.THERMAL_OFFSET_X,
                        help='Thermal layer X offset for parallax correction')
    parser.add_argument('--offset-y', type=int, default=config.THERMAL_OFFSET_Y,
                        help='Thermal layer Y offset for parallax correction')
    parser.add_argument('--alpha', type=float, default=config.ALPHA_BLEND_RATIO,
                        help='Alpha blend ratio (0.0=all visible, 1.0=all thermal)')
    parser.add_argument('--calibrate', action='store_true',
                        help='Perform flat field calibration on startup (point camera at uniform surface)')
    
    args = parser.parse_args()
    
    # Update config with command-line arguments
    config.THERMAL_OFFSET_X = args.offset_x
    config.THERMAL_OFFSET_Y = args.offset_y
    config.ALPHA_BLEND_RATIO = args.alpha
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGUSR1, calibration_signal_handler)
    
    # Create and run HUD
    global hud
    hud = ThermalFusionHUD()
    
    try:
        hud.run(perform_initial_calibration=args.calibrate)
    except KeyboardInterrupt:
        pass
    finally:
        hud.shutdown()


if __name__ == "__main__":
    main()

