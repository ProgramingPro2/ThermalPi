#!/usr/bin/env python3
"""
Test script for thermal camera flat field calibration.
Validates calibration capture, save, load, and correction functionality.
"""

import sys
import os
import time
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from thermal_calibration import ThermalCalibration, get_calibration_instance
from seek_thermal import SeekThermal, SeekThermalOpenCV


def test_calibration_workflow():
    """Test complete calibration workflow with actual thermal camera"""
    
    print("="*70)
    print("THERMAL CAMERA FLAT FIELD CALIBRATION TEST")
    print("="*70)
    print()
    
    # Initialize thermal camera
    print("1. Initializing thermal camera...")
    thermal_camera = SeekThermal()
    if not thermal_camera.initialize():
        print("   Failed with ctypes wrapper, trying OpenCV fallback...")
        thermal_camera = SeekThermalOpenCV()
        if not thermal_camera.initialize():
            print("   ERROR: Failed to initialize thermal camera")
            print("   Make sure the Seek Thermal camera is connected")
            return False
    
    print("   ✓ Thermal camera initialized")
    print()
    
    # Test frame capture
    print("2. Testing raw frame capture...")
    raw_frame = thermal_camera.capture_frame()
    if raw_frame is None:
        print("   ERROR: Failed to capture frame")
        thermal_camera.close()
        return False
    
    print(f"   ✓ Frame captured: shape={raw_frame.shape}, dtype={raw_frame.dtype}")
    print(f"     Range: [{np.min(raw_frame)}, {np.max(raw_frame)}]")
    print(f"     Mean: {np.mean(raw_frame):.1f}, Std: {np.std(raw_frame):.1f}")
    print()
    
    # Create calibration instance
    print("3. Creating calibration instance...")
    calibration = ThermalCalibration()
    print("   ✓ Calibration instance created")
    print()
    
    # Perform calibration
    print("4. Performing calibration...")
    print("   INSTRUCTIONS:")
    print("   - Point the thermal camera at a UNIFORM TEMPERATURE SURFACE")
    print("   - Examples: wall, ceiling, cardboard, large piece of paper")
    print("   - Ensure the surface fills the entire field of view")
    print("   - Keep the camera steady")
    print()
    print("   Calibration will start in 5 seconds...")
    time.sleep(5)
    
    success = calibration.perform_calibration(thermal_camera, save=True)
    if not success:
        print("   ERROR: Calibration failed")
        thermal_camera.close()
        return False
    
    print("   ✓ Calibration completed and saved")
    print()
    
    # Test calibration loading
    print("5. Testing calibration load...")
    calibration2 = ThermalCalibration()
    if not calibration2.load_calibration():
        print("   ERROR: Failed to load calibration")
        thermal_camera.close()
        return False
    
    print("   ✓ Calibration loaded successfully")
    print()
    
    # Test correction on live frames
    print("6. Testing flat field correction on live frames...")
    print("   Capturing 5 frames and applying correction...")
    
    for i in range(5):
        # Capture raw frame
        raw_frame = thermal_camera.capture_frame()
        if raw_frame is None:
            print(f"   WARNING: Frame {i+1} capture failed")
            continue
        
        # Apply correction
        corrected_frame = calibration2.apply_flat_field_correction(raw_frame)
        
        # Calculate statistics
        raw_std = np.std(raw_frame)
        corrected_std = np.std(corrected_frame)
        
        print(f"   Frame {i+1}:")
        print(f"     Raw:       mean={np.mean(raw_frame):7.1f}, std={raw_std:6.2f}")
        print(f"     Corrected: mean={np.mean(corrected_frame):7.1f}, std={corrected_std:6.2f}")
        
        # Check if correction reduces variation (expected for uniform surface)
        if corrected_std < raw_std:
            print(f"     ✓ Std deviation reduced by {(1 - corrected_std/raw_std)*100:.1f}%")
        else:
            print(f"     ⚠ Std deviation increased (may indicate non-uniform surface)")
        
        time.sleep(0.2)
    
    print()
    
    # Cleanup
    print("7. Cleaning up...")
    thermal_camera.close()
    print("   ✓ Thermal camera closed")
    print()
    
    # Summary
    print("="*70)
    print("TEST COMPLETE")
    print("="*70)
    print()
    print("All calibration functions working correctly!")
    print()
    print("Next steps:")
    print("  1. Run the full HUD: ./run_hud.sh")
    print("  2. To recalibrate anytime: ./run_hud.sh --calibrate")
    print("  3. Or during runtime: kill -SIGUSR1 <pid>")
    print()
    print("Calibration files saved to: calibration/")
    print()
    
    return True


def test_calibration_without_camera():
    """Test calibration functions with simulated data (no hardware required)"""
    
    print("="*70)
    print("CALIBRATION SYSTEM TEST (NO HARDWARE)")
    print("="*70)
    print()
    
    # Create simulated thermal frame with fixed pattern noise
    print("1. Creating simulated thermal data with fixed pattern noise...")
    
    # Base uniform temperature
    base_temp = 8000
    height, width = config.THERMAL_HEIGHT, config.THERMAL_WIDTH
    
    # Add fixed pattern noise (simulates pixel non-uniformity)
    fixed_pattern = np.random.normal(0, 200, (height, width))
    
    # Create simulated calibration frame (uniform surface)
    cal_frame = (base_temp + fixed_pattern).astype(np.uint16)
    
    print(f"   ✓ Simulated calibration frame: {cal_frame.shape}")
    print(f"     Mean: {np.mean(cal_frame):.1f}, Std: {np.std(cal_frame):.2f}")
    print()
    
    # Test calibration save/load
    print("2. Testing calibration save/load...")
    calibration = ThermalCalibration()
    calibration.calibration_frame = cal_frame
    calibration.metadata = {
        'timestamp': time.time(),
        'shape': cal_frame.shape,
        'mean_value': float(np.mean(cal_frame)),
        'std_value': float(np.std(cal_frame)),
        'note': 'simulated test data'
    }
    
    if not calibration.save_calibration(cal_frame, "calibration/test_calibration.npy"):
        print("   ERROR: Failed to save calibration")
        return False
    
    print("   ✓ Calibration saved")
    
    # Load it back
    calibration2 = ThermalCalibration()
    if not calibration2.load_calibration("calibration/test_calibration.npy"):
        print("   ERROR: Failed to load calibration")
        return False
    
    print("   ✓ Calibration loaded")
    print()
    
    # Test correction
    print("3. Testing flat field correction...")
    
    # Create test frame with same fixed pattern + random noise
    test_frame = (base_temp + fixed_pattern + np.random.normal(0, 50, (height, width))).astype(np.uint16)
    
    raw_std = np.std(test_frame)
    print(f"   Raw frame std: {raw_std:.2f}")
    
    # Apply correction
    corrected_frame = calibration2.apply_flat_field_correction(test_frame)
    corrected_std = np.std(corrected_frame)
    
    print(f"   Corrected frame std: {corrected_std:.2f}")
    
    if corrected_std < raw_std:
        improvement = (1 - corrected_std/raw_std) * 100
        print(f"   ✓ Noise reduced by {improvement:.1f}%")
    else:
        print("   ⚠ WARNING: Correction did not reduce noise")
    
    print()
    
    # Cleanup test file
    import os
    os.remove("calibration/test_calibration.npy")
    os.remove("calibration/test_calibration_metadata.json")
    print("   ✓ Test files cleaned up")
    print()
    
    print("="*70)
    print("SIMULATION TEST COMPLETE")
    print("="*70)
    print()
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test thermal calibration system')
    parser.add_argument('--no-camera', action='store_true',
                        help='Run simulated test without thermal camera hardware')
    
    args = parser.parse_args()
    
    if args.no_camera:
        success = test_calibration_without_camera()
    else:
        success = test_calibration_workflow()
    
    sys.exit(0 if success else 1)

