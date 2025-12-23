"""
Image processing functions for thermal fusion HUD.
Includes CLAHE normalization, Canny edge detection, and alpha-blending fusion.
"""

import numpy as np
import cv2
import config
from thermal_calibration import apply_correction


def normalize_thermal(thermal_frame):
    """
    Apply aggressive Min-Max normalization to thermal frame with percentile-based range.
    Uses percentiles to ignore outliers and maximize contrast.
    Applies flat field correction first if enabled.
    
    Args:
        thermal_frame: numpy array of uint16 thermal data
        
    Returns:
        Normalized array as float32 in range [0, 1] with maximum contrast
    """
    if thermal_frame is None or thermal_frame.size == 0:
        return None
    
    # Apply flat field correction first (before normalization)
    # This removes fixed pattern noise while preserving thermal detail
    if config.FFC_ENABLED:
        thermal_frame = apply_correction(thermal_frame)
    
    # Convert to float for processing
    frame_float = thermal_frame.astype(np.float32)
    
    # Use percentiles to ignore extreme outliers (top/bottom 1%)
    # This maximizes contrast by ignoring noise
    min_val = np.percentile(frame_float, 1)
    max_val = np.percentile(frame_float, 99)
    
    # Fallback to min/max if percentiles are too close
    if max_val - min_val < 100:
        min_val = np.min(frame_float)
        max_val = np.max(frame_float)
    
    if max_val > min_val:
        # Aggressive normalization with clipping
        normalized = (frame_float - min_val) / (max_val - min_val)
        # Clip outliers for clean output
        normalized = np.clip(normalized, 0.0, 1.0)
    else:
        normalized = np.zeros_like(frame_float)
    
    return normalized


def apply_human_detection_threshold(thermal_normalized):
    """
    Apply threshold mask to normalized thermal data for human detection.
    Pixels below the threshold are set to 0.0 (coldest), showing only warm objects.
    
    Args:
        thermal_normalized: Normalized thermal array in range [0, 1] (float32)
        
    Returns:
        Thresholded thermal array in range [0, 1] (float32)
        Pixels below threshold are set to 0.0
    """
    if thermal_normalized is None:
        return None
    
    # Validate threshold value from config
    threshold = config.HUMAN_DETECTION_THRESHOLD
    if threshold < 0.0 or threshold > 1.0:
        # Invalid threshold, return original data
        return thermal_normalized
    
    # Create binary mask: pixels >= threshold are True (keep), others False (set to 0)
    mask = thermal_normalized >= threshold
    
    # Apply mask: keep values above threshold, set others to 0.0
    thresholded = np.where(mask, thermal_normalized, 0.0)
    
    return thresholded.astype(np.float32)


def apply_clahe(thermal_normalized):
    """
    Apply Contrast Limited Adaptive Histogram Equalization to thermal data.
    
    Args:
        thermal_normalized: Normalized thermal array in range [0, 1]
        
    Returns:
        Enhanced thermal array in range [0, 1]
    """
    if thermal_normalized is None:
        return None
    
    # Convert to uint8 for CLAHE (0-255 range)
    thermal_uint8 = (thermal_normalized * 255).astype(np.uint8)
    
    # Create CLAHE object
    clahe = cv2.createCLAHE(
        clipLimit=config.CLAHE_CLIP_LIMIT,
        tileGridSize=config.CLAHE_TILE_GRID_SIZE
    )
    
    # Apply CLAHE
    enhanced = clahe.apply(thermal_uint8)
    
    # Convert back to float32 in range [0, 1]
    enhanced_float = enhanced.astype(np.float32) / 255.0
    
    return enhanced_float


def apply_white_hot_colormap(thermal_enhanced, alpha_mask=None):
    """
    Apply OpenCV colormap to thermal data with aggressive contrast stretch and brightness boost.
    Returns RGBA image with transparency for background removal.
    
    Args:
        thermal_enhanced: Enhanced thermal array in range [0, 1]
        alpha_mask: Optional alpha mask (same shape as thermal_enhanced) for transparency.
                    If None, creates alpha based on thermal intensity threshold.
        
    Returns:
        RGBA color image in range [0, 1] with colormap applied (shape: H, W, 4)
        Alpha channel: 0.0 = transparent (cold background), 1.0 = opaque (warm objects)
    """
    if thermal_enhanced is None:
        return None
    
    # Create alpha mask from thermal data before stretching (to preserve original intensity)
    # Use threshold to determine what should be visible
    if alpha_mask is None:
        threshold = config.HUMAN_DETECTION_THRESHOLD
        # Create smooth alpha transition instead of hard threshold
        # Values below threshold fade to transparent
        alpha_base = np.clip((thermal_enhanced - threshold) / (1.0 - threshold + 1e-6), 0.0, 1.0)
        # Smooth the transition with a power curve for better blending
        alpha_mask = np.power(alpha_base, 0.5)  # Square root for smoother fade
    else:
        # Use provided mask, ensure it's in [0, 1] range
        alpha_mask = np.clip(alpha_mask, 0.0, 1.0)
    
    # Very aggressive contrast stretch using percentiles (1st/99th for maximum contrast)
    # Ignore outliers to maximize contrast in the important range
    min_percentile = np.percentile(thermal_enhanced, 1)
    max_percentile = np.percentile(thermal_enhanced, 99)
    
    # If range is too small, use full min/max
    if max_percentile - min_percentile < 0.01:
        min_percentile = np.min(thermal_enhanced)
        max_percentile = np.max(thermal_enhanced)
    
    if max_percentile > min_percentile:
        # Stretch the middle 98% to full range [0, 1]
        thermal_stretched = (thermal_enhanced - min_percentile) / (max_percentile - min_percentile)
        thermal_stretched = np.clip(thermal_stretched, 0.0, 1.0)
    else:
        thermal_stretched = thermal_enhanced
    
    # Apply gamma correction to brighten the image (gamma < 1.0 makes image brighter)
    # Using gamma = 0.7 for brightness boost
    gamma = 0.7
    thermal_brightened = np.power(thermal_stretched, gamma)
    
    # Additional brightness boost: shift curve upward
    # This makes mid-tones brighter while preserving highlights
    thermal_brightened = thermal_brightened * 0.85 + 0.15  # Add base brightness
    thermal_brightened = np.clip(thermal_brightened, 0.0, 1.0)
    
    # Convert to uint8 for colormap application
    thermal_uint8 = (thermal_brightened * 255).astype(np.uint8)
    
    # Get OpenCV colormap constant from config string
    colormap_name = config.THERMAL_COLORMAP
    colormap_const = getattr(cv2, colormap_name, cv2.COLORMAP_INFERNO)  # Default to INFERNO if not found
    
    # Apply colormap (returns BGR image)
    thermal_colored = cv2.applyColorMap(thermal_uint8, colormap_const)
    
    # Convert BGR to RGB (display expects RGB)
    thermal_rgb = cv2.cvtColor(thermal_colored, cv2.COLOR_BGR2RGB)
    
    # Additional brightness boost on the final color image
    # Multiply RGB channels to increase overall brightness
    thermal_rgb = thermal_rgb.astype(np.float32) * 1.2  # 20% brightness boost
    thermal_rgb = np.clip(thermal_rgb, 0, 255)
    
    # Normalize to [0, 1] range
    thermal_rgb = (thermal_rgb / 255.0).astype(np.float32)
    
    # Add alpha channel for transparency (cold areas = transparent)
    # Ensure alpha_mask matches thermal_rgb shape
    if alpha_mask.shape != thermal_rgb.shape[:2]:
        alpha_mask = cv2.resize(alpha_mask, (thermal_rgb.shape[1], thermal_rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
    
    # Combine RGB with alpha channel
    thermal_rgba = np.dstack([thermal_rgb, alpha_mask.astype(np.float32)])
    
    return thermal_rgba


def process_webcam_frame(webcam_frame):
    """
    Process webcam frame: keep color, apply zoom, and resize/crop to display size.
    
    Args:
        webcam_frame: BGR frame from OpenCV (height, width, 3)
        
    Returns:
        RGB color frame resized/cropped to (DISPLAY_HEIGHT, DISPLAY_WIDTH, 3)
    """
    if webcam_frame is None:
        return None
    
    # Convert BGR to RGB for color display
    if len(webcam_frame.shape) == 3:
        if webcam_frame.shape[2] == 3:
            # BGR to RGB
            frame_rgb = cv2.cvtColor(webcam_frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = webcam_frame
    else:
        # Grayscale input - convert to RGB
        frame_rgb = cv2.cvtColor(webcam_frame, cv2.COLOR_GRAY2RGB)
    
    # Apply zoom if configured
    if config.WEBCAM_ZOOM != 1.0:
        h, w = frame_rgb.shape[:2]
        # Calculate center and crop region
        center_x = w // 2
        center_y = h // 2
        
        # Calculate zoomed crop size
        crop_w = int(w / config.WEBCAM_ZOOM)
        crop_h = int(h / config.WEBCAM_ZOOM)
        
        # Calculate crop boundaries (centered)
        start_x = max(0, center_x - crop_w // 2)
        start_y = max(0, center_y - crop_h // 2)
        end_x = min(w, start_x + crop_w)
        end_y = min(h, start_y + crop_h)
        
        # Crop (zoom in)
        frame_rgb = frame_rgb[start_y:end_y, start_x:end_x]
    
    # Calculate scaling to fill display while maintaining aspect ratio
    h, w = frame_rgb.shape[:2]
    display_w = config.DISPLAY_WIDTH
    display_h = config.DISPLAY_HEIGHT
    
    scale_w = display_w / w
    scale_h = display_h / h
    scale = max(scale_w, scale_h)  # Use larger scale to fill display
    
    # Resize
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(frame_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Center crop to display size
    start_x = (new_w - display_w) // 2
    start_y = (new_h - display_h) // 2
    cropped = resized[start_y:start_y + display_h, start_x:start_x + display_w]
    
    # Normalize to [0, 1] range (keep RGB color)
    return (cropped.astype(np.float32) / 255.0)


def extract_canny_edges(webcam_frame, thermal_fov_region=False):
    """
    Extract Canny edges from webcam frame with zoom applied.
    
    Args:
        webcam_frame: Raw webcam frame (BGR or grayscale)
        thermal_fov_region: If True, crop to center region matching thermal FOV (deprecated - use False)
        
    Returns:
        Binary edge image (0 or 255) at display resolution
    """
    if webcam_frame is None:
        return None
    
    # Convert to uint8 if needed and ensure grayscale
    if webcam_frame.dtype != np.uint8:
        frame_uint8 = (webcam_frame * 255).astype(np.uint8)
    else:
        frame_uint8 = webcam_frame
    
    # Convert to grayscale if color image
    if len(frame_uint8.shape) == 3:
        frame_uint8 = cv2.cvtColor(frame_uint8, cv2.COLOR_BGR2GRAY)
    
    # Apply zoom if configured (same as process_webcam_frame)
    if config.WEBCAM_ZOOM != 1.0:
        h, w = frame_uint8.shape
        # Calculate center and crop region
        center_x = w // 2
        center_y = h // 2
        
        # Calculate zoomed crop size
        crop_w = int(w / config.WEBCAM_ZOOM)
        crop_h = int(h / config.WEBCAM_ZOOM)
        
        # Calculate crop boundaries (centered)
        start_x = max(0, center_x - crop_w // 2)
        start_y = max(0, center_y - crop_h // 2)
        end_x = min(w, start_x + crop_w)
        end_y = min(h, start_y + crop_h)
        
        # Crop (zoom in)
        frame_uint8 = frame_uint8[start_y:end_y, start_x:end_x]
    
    # Resize to display resolution for full-screen edges
    if frame_uint8.shape != (config.DISPLAY_HEIGHT, config.DISPLAY_WIDTH):
        frame_uint8 = cv2.resize(
            frame_uint8,
            (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
            interpolation=cv2.INTER_LINEAR
        )
    
    # Apply Canny edge detection
    edges = cv2.Canny(
        frame_uint8,
        config.CANNY_THRESHOLD_LOW,
        config.CANNY_THRESHOLD_HIGH
    )
    
    return edges


def alpha_composite(thermal_rgba, visible_frame, blend_ratio=0.6):
    """
    Alpha-composite thermal RGBA image over visible frame with transparency.
    Handles both RGBA thermal (with alpha channel) and RGB visible frames.
    
    Args:
        thermal_rgba: Thermal frame in range [0, 1], shape (H, W, 4) with alpha channel
                     or shape (H, W, 3) without alpha
        visible_frame: Visible frame in range [0, 1], shape (H, W, 3) RGB
        blend_ratio: Additional blend ratio (0.0 = all visible, 1.0 = all thermal)
                    Applied on top of the alpha channel
        
    Returns:
        Blended RGB frame in range [0, 1], shape (H, W, 3)
    """
    if thermal_rgba is None or visible_frame is None:
        return None
    
    # Extract alpha channel if thermal has one
    if len(thermal_rgba.shape) == 3 and thermal_rgba.shape[2] == 4:
        thermal_rgb = thermal_rgba[:, :, :3]
        thermal_alpha = thermal_rgba[:, :, 3:4]  # Keep as (H, W, 1) for broadcasting
    else:
        # No alpha channel, use full opacity
        thermal_rgb = thermal_rgba
        thermal_alpha = np.ones((thermal_rgb.shape[0], thermal_rgb.shape[1], 1), dtype=np.float32)
    
    # Ensure same spatial dimensions
    if thermal_rgb.shape[:2] != visible_frame.shape[:2]:
        # Resize thermal to match visible
        thermal_rgb = cv2.resize(
            thermal_rgb,
            (visible_frame.shape[1], visible_frame.shape[0]),
            interpolation=cv2.INTER_LINEAR
        )
        thermal_alpha = cv2.resize(
            thermal_alpha[:, :, 0],
            (visible_frame.shape[1], visible_frame.shape[0]),
            interpolation=cv2.INTER_LINEAR
        )
        thermal_alpha = thermal_alpha[:, :, np.newaxis]  # Restore (H, W, 1) shape
    
    # Ensure visible_frame is RGB (3 channels)
    if len(visible_frame.shape) == 2:
        visible_frame = np.stack([visible_frame] * 3, axis=2)
    elif visible_frame.shape[2] == 1:
        visible_frame = np.repeat(visible_frame, 3, axis=2)
    
    # Validate inputs don't contain NaN/Inf
    if np.any(np.isnan(thermal_rgb)) or np.any(np.isinf(thermal_rgb)):
        return None
    if np.any(np.isnan(visible_frame)) or np.any(np.isinf(visible_frame)):
        return None
    if np.any(np.isnan(thermal_alpha)) or np.any(np.isinf(thermal_alpha)):
        return None
    
    # Combine alpha channel with blend ratio
    # Final alpha = thermal_alpha * blend_ratio (makes thermal more/less prominent)
    final_alpha = thermal_alpha * blend_ratio
    
    # Alpha composite: result = alpha * thermal + (1 - alpha) * visible
    # This formula properly handles transparency
    blended = final_alpha * thermal_rgb + (1.0 - final_alpha) * visible_frame
    
    # Clip and validate output
    blended = np.clip(blended, 0.0, 1.0)
    
    # Final check for NaN/Inf
    if np.any(np.isnan(blended)) or np.any(np.isinf(blended)):
        return None
    
    return blended


def alpha_blend(thermal_frame, visible_frame, alpha=0.6):
    """
    Alpha-blend thermal and visible frames (backward compatibility).
    If thermal has alpha channel, uses alpha_composite. Otherwise, simple blending.
    
    Args:
        thermal_frame: Thermal frame in range [0, 1], shape (H, W, 3) or (H, W, 4)
        visible_frame: Visible frame in range [0, 1], shape (H, W, 3)
        alpha: Blend ratio (0.0 = all visible, 1.0 = all thermal)
        
    Returns:
        Blended frame in range [0, 1]
    """
    # Check if thermal has alpha channel
    if len(thermal_frame.shape) == 3 and thermal_frame.shape[2] == 4:
        return alpha_composite(thermal_frame, visible_frame, blend_ratio=alpha)
    else:
        # Simple alpha blend (old behavior)
        if thermal_frame is None or visible_frame is None:
            return None
        
        # Ensure same shape
        if thermal_frame.shape != visible_frame.shape:
            # Resize thermal to match visible
            thermal_frame = cv2.resize(
                thermal_frame,
                (visible_frame.shape[1], visible_frame.shape[0]),
                interpolation=cv2.INTER_LINEAR
            )
        
        # Validate inputs don't contain NaN/Inf
        if np.any(np.isnan(thermal_frame)) or np.any(np.isinf(thermal_frame)):
            return None
        if np.any(np.isnan(visible_frame)) or np.any(np.isinf(visible_frame)):
            return None
        
        # Alpha blend: result = alpha * thermal + (1 - alpha) * visible
        blended = alpha * thermal_frame + (1.0 - alpha) * visible_frame
        
        # Clip and validate output
        blended = np.clip(blended, 0.0, 1.0)
        
        # Final check for NaN/Inf
        if np.any(np.isnan(blended)) or np.any(np.isinf(blended)):
            return None
        
        return blended


def overlay_edges(blended_frame, edges):
    """
    Overlay Canny edges on top of blended frame. Supports both grayscale and color frames.
    
    Args:
        blended_frame: Blended thermal/visible frame in range [0, 1], shape (H, W) or (H, W, 3)
        edges: Binary edge image (0 or 255), shape (H, W)
        
    Returns:
        Frame with edges overlaid (same shape as input)
    """
    if blended_frame is None:
        return None
    
    result = blended_frame.copy()
    
    if edges is not None:
        # Ensure edges match frame size
        if edges.shape[:2] != blended_frame.shape[:2]:
            edges = cv2.resize(
                edges,
                (blended_frame.shape[1], blended_frame.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )
        
        # Convert edges to float and overlay (bright edges)
        if edges.dtype != np.uint8:
            edges_uint8 = (edges * 255).astype(np.uint8)
        else:
            edges_uint8 = edges
        
        edges_float = (edges_uint8 > 127).astype(np.float32)
        
        # If frame is color (3D), expand edges to 3 channels
        if len(result.shape) == 3:
            edges_float = np.stack([edges_float] * 3, axis=2)
        
        # Overlay: edges make pixels brighter (white edges)
        # Use maximum to overlay bright edges
        result = np.maximum(result, edges_float * 1.0)  # Edges at full brightness for visibility
    
    return result


def fuse_thermal_hud(thermal_frame, webcam_frame):
    """
    Complete fusion pipeline: process thermal and webcam, then fuse.
    Includes error handling to prevent crashes on extreme thermal gradients.
    
    Args:
        thermal_frame: Raw thermal frame (uint16, 206x156 or 207x156)
        webcam_frame: Raw webcam frame (BGR, variable size)
        
    Returns:
        Final composite frame (float32, 320x240) in range [0, 1], or None on error
    """
    try:
        # Validate inputs
        if thermal_frame is None or webcam_frame is None:
            return None
        if thermal_frame.size == 0 or webcam_frame.size == 0:
            return None
        
        # Clip thermal data to valid 14-bit range to prevent overflow
        thermal_frame = np.clip(thermal_frame, 0, 16383).astype(np.uint16)
        
        # Process thermal: normalize -> background removal -> CLAHE -> white-hot with transparency
        thermal_norm = normalize_thermal(thermal_frame)
        if thermal_norm is None:
            return None
        
        # Create alpha mask BEFORE thresholding (preserve original intensity for smooth transparency)
        threshold = config.HUMAN_DETECTION_THRESHOLD
        alpha_mask = np.clip((thermal_norm - threshold) / (1.0 - threshold + 1e-6), 0.0, 1.0)
        alpha_mask = np.power(alpha_mask, 0.5)  # Smooth transition
        
        # Apply background removal threshold for CLAHE processing (this affects the data, not just transparency)
        thermal_thresholded = apply_human_detection_threshold(thermal_norm)
        if thermal_thresholded is None:
            return None
        
        thermal_clahe = apply_clahe(thermal_thresholded)
        if thermal_clahe is None:
            return None
        
        # Validate CLAHE output (check for NaN/Inf)
        if np.any(np.isnan(thermal_clahe)) or np.any(np.isinf(thermal_clahe)):
            return None
        
        # Resize alpha mask to match CLAHE output if needed
        if alpha_mask.shape != thermal_clahe.shape:
            alpha_mask = cv2.resize(alpha_mask, (thermal_clahe.shape[1], thermal_clahe.shape[0]), interpolation=cv2.INTER_LINEAR)
            
        thermal_white_hot = apply_white_hot_colormap(thermal_clahe, alpha_mask=alpha_mask)
        if thermal_white_hot is None:
            return None
        
        # Validate white-hot output
        if np.any(np.isnan(thermal_white_hot)) or np.any(np.isinf(thermal_white_hot)):
            return None
        
        # Debug: print thermal shape
        # print(f"Thermal shape after colormap: {thermal_white_hot.shape}")
        
        # Process webcam: grayscale + resize/crop
        webcam_processed = process_webcam_frame(webcam_frame)
        if webcam_processed is None:
            return None
        
        # Validate webcam processed dimensions (accept both grayscale and color)
        # Just check that we have valid dimensions (be flexible)
        if webcam_processed.shape[0] < 100 or webcam_processed.shape[1] < 100:
            return None
        
        # Webcam should already be RGB color from process_webcam_frame
        # But handle grayscale case just in case
        if len(webcam_processed.shape) == 2:
            webcam_processed = np.stack([webcam_processed] * 3, axis=2)
        
        # Extract edges from webcam (full frame, not just thermal region)
        edges = None
        try:
            edges = extract_canny_edges(webcam_frame, thermal_fov_region=False)
        except:
            pass  # Edges are optional
        
        # Create center region for fusion
        center_y = config.DISPLAY_HEIGHT // 2
        center_x = config.DISPLAY_WIDTH // 2
        
        # Use actual thermal image dimensions (may differ from config after processing)
        if len(thermal_white_hot.shape) >= 2:
            thermal_h = thermal_white_hot.shape[0]
            thermal_w = thermal_white_hot.shape[1]
        else:
            thermal_h = config.THERMAL_HEIGHT
            thermal_w = config.THERMAL_WIDTH
        
        # Apply offsets for parallax correction (can be negative)
        # Negative Y offset moves thermal DOWN (toward bottom of screen, larger Y value)
        # Negative X offset moves thermal LEFT (toward left of screen, smaller X value)
        # Positive Y offset moves thermal UP (toward top of screen, smaller Y value)
        # Positive X offset moves thermal RIGHT (toward right of screen, larger X value)
        offset_x = config.THERMAL_OFFSET_X
        offset_y = config.THERMAL_OFFSET_Y
        
        # Calculate desired thermal position (may be negative or extend beyond display)
        # For Y: larger value = lower on screen (bottom is larger Y)
        # Offset interpretation: negative Y = move DOWN (increase Y), positive Y = move UP (decrease Y)
        # Center position without offset: center_y - thermal_h // 2
        # To move DOWN with negative offset, we subtract the offset (double negative = positive)
        desired_start_y = center_y - thermal_h // 2 - offset_y
        desired_start_x = center_x - thermal_w // 2 + offset_x
        
        # Debug output (uncomment to troubleshoot offset issues)
        # if offset_y != 0 or offset_x != 0:
        #     print(f"DEBUG Offset: X={offset_x}, Y={offset_y}, Thermal: {thermal_w}x{thermal_h}, Center: ({center_x}, {center_y}), Desired: ({desired_start_x}, {desired_start_y})")
        
        # Get display dimensions
        actual_display_h = webcam_processed.shape[0]
        actual_display_w = webcam_processed.shape[1]
        
        # Calculate the actual overlap region between thermal and display
        # Handle negative offsets by calculating crop regions
        thermal_crop_y = 0  # Crop from top of thermal if it extends above display
        thermal_crop_x = 0  # Crop from left of thermal if it extends left of display
        thermal_crop_bottom = 0  # Crop from bottom of thermal if it extends below display
        thermal_crop_right = 0  # Crop from right of thermal if it extends right of display
        
        # Adjust if thermal extends above/left of display (negative start)
        if desired_start_y < 0:
            thermal_crop_y = -desired_start_y
            start_y = 0
        else:
            start_y = desired_start_y
            
        if desired_start_x < 0:
            thermal_crop_x = -desired_start_x
            start_x = 0
        else:
            start_x = desired_start_x
        
        # Calculate end positions (clamp to display bounds)
        # Account for thermal crop when calculating available thermal size
        available_thermal_h = thermal_h - thermal_crop_y
        available_thermal_w = thermal_w - thermal_crop_x
        end_y = min(start_y + available_thermal_h, actual_display_h)
        end_x = min(start_x + available_thermal_w, actual_display_w)
        
        # Adjust thermal crop if it extends beyond bottom/right of display
        thermal_crop_bottom = max(0, (start_y + available_thermal_h) - actual_display_h)
        thermal_crop_right = max(0, (start_x + available_thermal_w) - actual_display_w)
        
        # Calculate actual visible region size
        actual_h = end_y - start_y
        actual_w = end_x - start_x
        
        if actual_h <= 0 or actual_w <= 0:
            return None
        
        # Extract visible region matching the overlap area
        try:
            visible_region = webcam_processed[start_y:end_y, start_x:end_x].copy()
        except Exception as e:
            return None
        
        # Crop and resize thermal to match visible region
        # Handle negative offsets by cropping thermal image appropriately
        # Thermal is now RGBA (4 channels) with transparency
        if len(thermal_white_hot.shape) == 2:
            # Grayscale thermal - shouldn't happen, but handle it
            # Crop thermal if needed (for negative offsets)
            thermal_cropped = thermal_white_hot[thermal_crop_y:thermal_white_hot.shape[0]-thermal_crop_bottom,
                                                 thermal_crop_x:thermal_white_hot.shape[1]-thermal_crop_right]
            if thermal_cropped.shape[0] != actual_h or thermal_cropped.shape[1] != actual_w:
                thermal_resized = cv2.resize(thermal_cropped, (actual_w, actual_h), interpolation=cv2.INTER_LINEAR)
            else:
                thermal_resized = thermal_cropped
            # Convert grayscale to 3-channel RGB (no alpha for backward compatibility)
            thermal_resized = np.stack([thermal_resized] * 3, axis=2)
        elif len(thermal_white_hot.shape) == 3:
            if thermal_white_hot.shape[2] == 4:
                # RGBA image - crop and resize preserving alpha channel
                # Crop thermal if needed (for negative offsets)
                thermal_cropped = thermal_white_hot[thermal_crop_y:thermal_white_hot.shape[0]-thermal_crop_bottom,
                                                     thermal_crop_x:thermal_white_hot.shape[1]-thermal_crop_right, :]
                if thermal_cropped.shape[0] != actual_h or thermal_cropped.shape[1] != actual_w:
                    # Resize RGB and alpha separately, then combine
                    thermal_rgb = thermal_cropped[:, :, :3]
                    thermal_alpha = thermal_cropped[:, :, 3]
                    thermal_rgb_resized = cv2.resize(thermal_rgb, (actual_w, actual_h), interpolation=cv2.INTER_LINEAR)
                    thermal_alpha_resized = cv2.resize(thermal_alpha, (actual_w, actual_h), interpolation=cv2.INTER_LINEAR)
                    thermal_resized = np.dstack([thermal_rgb_resized, thermal_alpha_resized])
                else:
                    thermal_resized = thermal_cropped
            else:
                # RGB image (3 channels) - no alpha, crop and resize normally
                thermal_cropped = thermal_white_hot[thermal_crop_y:thermal_white_hot.shape[0]-thermal_crop_bottom,
                                                     thermal_crop_x:thermal_white_hot.shape[1]-thermal_crop_right]
                if thermal_cropped.shape[0] != actual_h or thermal_cropped.shape[1] != actual_w:
                    thermal_resized = cv2.resize(thermal_cropped, (actual_w, actual_h), interpolation=cv2.INTER_LINEAR)
                else:
                    thermal_resized = thermal_cropped
        else:
            return None
        
        # Ensure visible region is also 3-channel for blending
        if len(visible_region.shape) == 2:
            # Convert grayscale visible to RGB
            visible_region = np.stack([visible_region] * 3, axis=2)
        
        # Alpha-composite thermal (with transparency) over visible in center region
        # Uses alpha channel from thermal for transparency, plus blend ratio for intensity
        blended_region = alpha_blend(
            thermal_resized,
            visible_region,
            alpha=config.ALPHA_BLEND_RATIO
        )
        if blended_region is None:
            return None
        
        # Create final composite: webcam background with fused center region
        try:
            composite = webcam_processed.copy()
            # Ensure blended_region matches the region size
            if blended_region.shape[0] != actual_h or blended_region.shape[1] != actual_w:
                blended_region = cv2.resize(blended_region, (actual_w, actual_h), interpolation=cv2.INTER_LINEAR)
            
            # Debug output (uncomment to troubleshoot offset issues)
            # if offset_y != 0 or offset_x != 0:
            #     print(f"DEBUG Placing at: start_y={start_y}, end_y={end_y}, start_x={start_x}, end_x={end_x}, size={actual_h}x{actual_w}, crop_y={thermal_crop_y}")
            
            # Place the blended region at the calculated position (with offset applied)
            composite[start_y:end_y, start_x:end_x] = blended_region
        except Exception as e:
            return None
        
        # Overlay edges on full screen (not just thermal region)
        if edges is not None:
            try:
                # Resize edges to full display size
                edges_fullscreen = cv2.resize(
                    edges,
                    (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT),
                    interpolation=cv2.INTER_NEAREST
                )
                # Overlay edges on composite
                composite = overlay_edges(composite, edges_fullscreen)
                if composite is None:
                    # Fallback if overlay fails
                    composite = webcam_processed.copy()
                    composite[start_y:end_y, start_x:end_x] = blended_region
            except:
                pass  # Edge overlay is optional, continue without it
        
        # Final validation - ensure composite is valid
        if composite is None or composite.size == 0:
            return None
        # Accept both grayscale (2D) and color (3D) composites
        if len(composite.shape) not in [2, 3]:
            return None
        
        return composite
        
    except Exception as e:
        # Silent failure - return None for graceful degradation
        return None

