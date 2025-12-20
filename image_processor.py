"""
Image processing functions for thermal fusion HUD.
Includes CLAHE normalization, Canny edge detection, and alpha-blending fusion.
"""

import numpy as np
import cv2
import config


def normalize_thermal(thermal_frame):
    """
    Apply aggressive Min-Max normalization to thermal frame with percentile-based range.
    Uses percentiles to ignore outliers and maximize contrast.
    
    Args:
        thermal_frame: numpy array of uint16 thermal data
        
    Returns:
        Normalized array as float32 in range [0, 1] with maximum contrast
    """
    if thermal_frame is None or thermal_frame.size == 0:
        return None
    
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


def apply_white_hot_colormap(thermal_enhanced):
    """
    Simple White-Hot colormap with aggressive contrast stretch.
    
    Args:
        thermal_enhanced: Enhanced thermal array in range [0, 1]
        
    Returns:
        Grayscale image in range [0, 1] (bright = hot) with maximum contrast
    """
    if thermal_enhanced is None:
        return None
    
    # Aggressive contrast stretch using percentiles
    # Ignore bottom 5% and top 5% to maximize contrast in the important range
    min_percentile = np.percentile(thermal_enhanced, 5)
    max_percentile = np.percentile(thermal_enhanced, 95)
    
    # If range is too small, use full min/max
    if max_percentile - min_percentile < 0.01:
        min_percentile = np.min(thermal_enhanced)
        max_percentile = np.max(thermal_enhanced)
    
    if max_percentile > min_percentile:
        # Stretch the middle 90% to full range [0, 1]
        thermal_stretched = (thermal_enhanced - min_percentile) / (max_percentile - min_percentile)
        thermal_stretched = np.clip(thermal_stretched, 0.0, 1.0)
    else:
        thermal_stretched = thermal_enhanced
    
    return thermal_stretched


def process_webcam_frame(webcam_frame):
    """
    Process webcam frame: convert to grayscale, apply zoom, and resize/crop to display size.
    
    Args:
        webcam_frame: BGR frame from OpenCV (height, width, 3)
        
    Returns:
        Grayscale frame resized/cropped to (DISPLAY_HEIGHT, DISPLAY_WIDTH)
    """
    if webcam_frame is None:
        return None
    
    # Convert to grayscale
    if len(webcam_frame.shape) == 3:
        gray = cv2.cvtColor(webcam_frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = webcam_frame
    
    # Apply zoom if configured
    if config.WEBCAM_ZOOM != 1.0:
        h, w = gray.shape
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
        gray = gray[start_y:end_y, start_x:end_x]
    
    # Calculate scaling to fill display while maintaining aspect ratio
    h, w = gray.shape
    display_w = config.DISPLAY_WIDTH
    display_h = config.DISPLAY_HEIGHT
    
    scale_w = display_w / w
    scale_h = display_h / h
    scale = max(scale_w, scale_h)  # Use larger scale to fill display
    
    # Resize
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Center crop to display size
    start_x = (new_w - display_w) // 2
    start_y = (new_h - display_h) // 2
    cropped = resized[start_y:start_y + display_h, start_x:start_x + display_w]
    
    # Normalize to [0, 1]
    return (cropped.astype(np.float32) / 255.0)


def extract_canny_edges(webcam_frame, thermal_fov_region=False):
    """
    Extract Canny edges from webcam frame.
    
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


def alpha_blend(thermal_frame, visible_frame, alpha=0.6):
    """
    Alpha-blend thermal and visible frames.
    
    Args:
        thermal_frame: Thermal frame in range [0, 1], shape (H, W)
        visible_frame: Visible frame in range [0, 1], shape (H, W)
        alpha: Blend ratio (0.0 = all visible, 1.0 = all thermal)
        
    Returns:
        Blended frame in range [0, 1]
    """
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
    Overlay Canny edges on top of blended frame.
    
    Args:
        blended_frame: Blended thermal/visible frame in range [0, 1]
        edges: Binary edge image (0 or 255)
        
    Returns:
        Frame with edges overlaid
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
        
        # Convert edges to float and overlay (white edges)
        if edges.dtype != np.uint8:
            edges_uint8 = (edges * 255).astype(np.uint8)
        else:
            edges_uint8 = edges
        
        edges_float = (edges_uint8 > 127).astype(np.float32)
        
        # Overlay: edges make pixels brighter (more visible on dark backgrounds)
        result = np.maximum(result, edges_float * 0.9)  # Edges at 90% brightness
    
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
        
        # Process thermal: normalize -> CLAHE -> white-hot
        thermal_norm = normalize_thermal(thermal_frame)
        if thermal_norm is None:
            return None
        
        thermal_clahe = apply_clahe(thermal_norm)
        if thermal_clahe is None:
            return None
        
        # Validate CLAHE output (check for NaN/Inf)
        if np.any(np.isnan(thermal_clahe)) or np.any(np.isinf(thermal_clahe)):
            return None
            
        thermal_white_hot = apply_white_hot_colormap(thermal_clahe)
        if thermal_white_hot is None:
            return None
        
        # Validate white-hot output
        if np.any(np.isnan(thermal_white_hot)) or np.any(np.isinf(thermal_white_hot)):
            return None
        
        # Process webcam: grayscale + resize/crop
        webcam_processed = process_webcam_frame(webcam_frame)
        if webcam_processed is None:
            return None
        
        # Validate webcam processed dimensions
        if len(webcam_processed.shape) != 2:
            return None
        # Just check that we have valid dimensions (be flexible)
        if webcam_processed.shape[0] < 100 or webcam_processed.shape[1] < 100:
            return None
        
        # Extract edges from webcam (full frame, not just thermal region)
        edges = None
        try:
            edges = extract_canny_edges(webcam_frame, thermal_fov_region=False)
        except:
            pass  # Edges are optional
        
        # Create center region for fusion
        center_y = config.DISPLAY_HEIGHT // 2
        center_x = config.DISPLAY_WIDTH // 2
        thermal_h = config.THERMAL_HEIGHT
        thermal_w = config.THERMAL_WIDTH
        
        # Apply offsets for parallax correction
        offset_x = config.THERMAL_OFFSET_X
        offset_y = config.THERMAL_OFFSET_Y
        
        start_y = center_y - thermal_h // 2 + offset_y
        start_x = center_x - thermal_w // 2 + offset_x
        
        # Ensure bounds are within display
        actual_display_h = webcam_processed.shape[0]
        actual_display_w = webcam_processed.shape[1]
        
        start_y = max(0, min(start_y, actual_display_h - thermal_h))
        start_x = max(0, min(start_x, actual_display_w - thermal_w))
        end_y = min(start_y + thermal_h, actual_display_h)
        end_x = min(start_x + thermal_w, actual_display_w)
        
        # Adjust thermal size if bounds are smaller
        actual_h = end_y - start_y
        actual_w = end_x - start_x
        
        if actual_h <= 0 or actual_w <= 0:
            return None
        
        # Extract visible region matching thermal size
        try:
            visible_region = webcam_processed[start_y:end_y, start_x:end_x].copy()
        except Exception as e:
            return None
        
        # Resize thermal to match visible region if dimensions differ
        if thermal_white_hot.shape[0] != actual_h or thermal_white_hot.shape[1] != actual_w:
            thermal_resized = cv2.resize(thermal_white_hot, (actual_w, actual_h), interpolation=cv2.INTER_LINEAR)
        else:
            thermal_resized = thermal_white_hot
        
        # Alpha-blend thermal and visible in center region
        # Higher alpha = more thermal visible
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
        if len(composite.shape) != 2:
            return None
        
        return composite
        
    except Exception as e:
        # Silent failure - return None for graceful degradation
        return None

