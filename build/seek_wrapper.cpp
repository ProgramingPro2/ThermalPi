/*
 * C wrapper for libseek-thermal (OpenThermal official library)
 * Provides a simple C interface for Python ctypes
 */

#include <seek/SeekThermal.h>
#include <opencv2/opencv.hpp>
#include <cstring>
#include <cstdint>

using namespace LibSeek;

extern "C" {
    // Opaque pointer type for Python
    typedef void* SeekThermalHandle;
    
    // Create new SeekThermal instance
    SeekThermalHandle seek_thermal_create() {
        try {
            SeekThermal* camera = new SeekThermal();
            return static_cast<SeekThermalHandle>(camera);
        } catch (...) {
            return nullptr;
        }
    }
    
    // Open/initialize the camera
    int seek_thermal_open(SeekThermalHandle handle) {
        if (!handle) return 0;
        try {
            SeekThermal* camera = static_cast<SeekThermal*>(handle);
            return camera->open() ? 1 : 0;
        } catch (...) {
            return 0;
        }
    }
    
    // Check if camera is opened
    int seek_thermal_is_opened(SeekThermalHandle handle) {
        if (!handle) return 0;
        try {
            SeekThermal* camera = static_cast<SeekThermal*>(handle);
            return camera->isOpened() ? 1 : 0;
        } catch (...) {
            return 0;
        }
    }
    
    // Capture a frame (returns 14-bit thermal data)
    int seek_thermal_read_frame(SeekThermalHandle handle, uint16_t* buffer, 
                                 int width, int height) {
        if (!handle || !buffer) return 0;
        
        try {
            SeekThermal* camera = static_cast<SeekThermal*>(handle);
            cv::Mat frame;
            
            if (!camera->read(frame)) {
                return 0;
            }
            
            // Check if frame is empty
            if (frame.empty()) {
                return 0;
            }
            
            // Thermal dimensions are 207x156, but allow some flexibility
            int frame_width = frame.cols;
            int frame_height = frame.rows;
            
            // Use actual frame dimensions or provided dimensions
            int copy_width = (width <= frame_width) ? width : frame_width;
            int copy_height = (height <= frame_height) ? height : frame_height;
            
            // Convert frame to uint16_t array
            // SeekThermal returns 14-bit data in 16-bit containers
            if (frame.type() == CV_16UC1) {
                // Already 16-bit single channel
                if (frame_width == width && frame_height == height) {
                    // Direct copy
                    memcpy(buffer, frame.data, width * height * sizeof(uint16_t));
                } else {
                    // Copy with size adjustment
                    for (int y = 0; y < copy_height; y++) {
                        memcpy(buffer + y * width, 
                               frame.data + y * frame_width * sizeof(uint16_t),
                               copy_width * sizeof(uint16_t));
                    }
                }
            } else if (frame.type() == CV_16SC1) {
                // Signed 16-bit, convert to unsigned
                cv::Mat unsigned_frame;
                frame.convertTo(unsigned_frame, CV_16UC1);
                if (frame_width == width && frame_height == height) {
                    memcpy(buffer, unsigned_frame.data, width * height * sizeof(uint16_t));
                } else {
                    for (int y = 0; y < copy_height; y++) {
                        memcpy(buffer + y * width,
                               unsigned_frame.data + y * frame_width * sizeof(uint16_t),
                               copy_width * sizeof(uint16_t));
                    }
                }
            } else {
                // Try to convert to 16-bit unsigned
                cv::Mat converted;
                frame.convertTo(converted, CV_16UC1);
                if (converted.type() == CV_16UC1 && !converted.empty()) {
                    if (converted.cols == width && converted.rows == height) {
                        memcpy(buffer, converted.data, width * height * sizeof(uint16_t));
                    } else {
                        int cpy_w = (width <= converted.cols) ? width : converted.cols;
                        int cpy_h = (height <= converted.rows) ? height : converted.rows;
                        for (int y = 0; y < cpy_h; y++) {
                            memcpy(buffer + y * width,
                                   converted.data + y * converted.cols * sizeof(uint16_t),
                                   cpy_w * sizeof(uint16_t));
                        }
                    }
                } else {
                    return 0;
                }
            }
            
            return 1;
        } catch (...) {
            return 0;
        }
    }
    
    // Get frame dimensions (returns thermal dimensions: 207x156)
    void seek_thermal_get_dimensions(SeekThermalHandle handle, int* width, int* height) {
        // Seek Thermal Compact/CompactXR fixed dimensions
        if (width) *width = 207;
        if (height) *height = 156;
    }
    
    // Close camera
    void seek_thermal_close(SeekThermalHandle handle) {
        if (!handle) return;
        try {
            SeekThermal* camera = static_cast<SeekThermal*>(handle);
            camera->close();
        } catch (...) {
            // Ignore errors on close
        }
    }
    
    // Destroy instance
    void seek_thermal_destroy(SeekThermalHandle handle) {
        if (!handle) return;
        try {
            SeekThermal* camera = static_cast<SeekThermal*>(handle);
            delete camera;
        } catch (...) {
            // Ignore errors on destroy
        }
    }
}

