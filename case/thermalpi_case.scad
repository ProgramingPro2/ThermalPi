// ThermalPi 3D Printed Case
// OpenSCAD parametric design for Raspberry Pi 4 + ILI9341 Display + USB Cameras
// 
// Usage:
// 1. Open in OpenSCAD (free software: https://openscad.org/)
// 2. Adjust parameters below if needed
// 3. Render (F6) and export as STL (File > Export > Export as STL)
// 4. Print with 15-20% infill, 0.2mm layer height recommended

// ============================================
// PARAMETERS - Adjust these for your printer
// ============================================

// Raspberry Pi 4 dimensions
pi_length = 85;          // Pi 4 length (mm)
pi_width = 56;           // Pi 4 width (mm)
pi_height = 17;          // Pi 4 PCB height (excluding GPIO header)
gpio_height = 8.5;       // GPIO header height (mm)
pi_total_height = pi_height + gpio_height;

// Case wall thickness
wall_thickness = 2.5;    // Base and side walls (mm)
top_thickness = 1.5;     // Top cover thickness (mm)
standoff_height = 3;     // Space between Pi PCB and case bottom

// Display cutout (ILI9341 2.8" display module)
display_width = 62;      // Display module width (mm)
display_height = 62;     // Display module height (mm)
display_thickness = 4;   // Display module thickness (mm)

// Clearances
clearance = 0.5;         // General clearance for snug fit
usb_clearance = 5;       // Space for USB connectors
cable_clearance = 10;    // Space for jumper wires

// Ventilation
vent_hole_size = 4;      // Diameter of ventilation holes
vent_spacing = 8;        // Spacing between vent holes

// Screw holes (M2.5 screws for mounting Pi)
screw_hole_diameter = 2.5;
screw_head_diameter = 5;
pi_screw_positions = [
    [3.5, 3.5],           // Bottom left
    [pi_length - 3.5, 3.5], // Bottom right
    [3.5, pi_width - 3.5],  // Top left
    [pi_length - 3.5, pi_width - 3.5] // Top right
];

// ============================================
// MAIN CASE BODY
// ============================================

module base_case() {
    difference() {
        // Outer shell
        translate([-wall_thickness, -wall_thickness, 0])
            cube([pi_length + 2*wall_thickness + display_width + cable_clearance,
                  pi_width + 2*wall_thickness,
                  pi_total_height + standoff_height + wall_thickness]);
        
        // Inner cavity for Pi
        translate([0, 0, standoff_height])
            cube([pi_length, pi_width, pi_total_height + 1]);
        
        // Display cavity (front of case)
        translate([pi_length + cable_clearance, 
                   (pi_width - display_width) / 2, 
                   standoff_height])
            cube([display_width + 1, display_width, display_thickness + 1]);
        
        // Display window (visible area - typically smaller than module)
        translate([pi_length + cable_clearance + (display_width - 50) / 2,
                   (pi_width - 37) / 2,
                   -1])
            cube([50, 37, wall_thickness + 2]); // 2.8" display visible area ~50x37mm
        
        // USB ports (left side of Pi)
        translate([-wall_thickness - 1, pi_width - 32, pi_total_height + standoff_height - 14])
            cube([wall_thickness + 2, 32, 14]);
        
        // USB-C power port (bottom edge, near USB ports)
        translate([pi_length - 15, -wall_thickness - 1, pi_total_height + standoff_height - 8])
            cube([12, wall_thickness + 2, 8]);
        
        // MicroSD card slot (bottom edge)
        translate([10, -wall_thickness - 1, pi_total_height + standoff_height - 2])
            cube([12, wall_thickness + 2, 2]);
        
        // GPIO header access (top edge, offset for display wires)
        translate([pi_length - 25, pi_width, pi_total_height + standoff_height - gpio_height])
            cube([40, wall_thickness + 2, gpio_height + 1]);
        
        // Ethernet port (if using)
        translate([pi_length - 35, -wall_thickness - 1, pi_total_height + standoff_height - 14])
            cube([20, wall_thickness + 2, 14]);
        
        // HDMI ports (right side)
        translate([pi_length, (pi_width - 30) / 2, pi_total_height + standoff_height - 11])
            cube([wall_thickness + 2, 30, 11]);
        
        // USB camera cables (top edge, camera openings)
        translate([pi_length + cable_clearance + display_width / 2 - 10, 
                   pi_width + wall_thickness - 5, 
                   -1])
            cube([20, 10, wall_thickness + 2]);
        
        // Ventilation holes in bottom
        for (x = [10:vent_spacing:pi_length + display_width - 10]) {
            for (y = [10:vent_spacing:pi_width - 10]) {
                translate([x, y, -1])
                    cylinder(h = wall_thickness + 2, d = vent_hole_size, $fn=20);
            }
        }
        
        // Ventilation holes in sides
        for (z = [standoff_height + 5:vent_spacing:pi_total_height + standoff_height - 5]) {
            // Left side
            translate([-wall_thickness - 1, pi_width / 2, z])
                rotate([0, 90, 0])
                    cylinder(h = wall_thickness + 2, d = vent_hole_size, $fn=20);
            // Right side
            translate([pi_length + cable_clearance + display_width + wall_thickness - 1, 
                       pi_width / 2, z])
                rotate([0, 90, 0])
                    cylinder(h = wall_thickness + 2, d = vent_hole_size, $fn=20);
        }
    }
    
    // Standoffs for Pi mounting
    for (pos = pi_screw_positions) {
        translate([pos[0], pos[1], 0])
            difference() {
                cylinder(h = standoff_height + pi_height, d = 6, $fn=30);
                translate([0, 0, -1])
                    cylinder(h = standoff_height + pi_height + 2, 
                            d = screw_hole_diameter, $fn=20);
            }
    }
}

// ============================================
// TOP COVER (optional, for protection)
// ============================================

module top_cover() {
    translate([0, 0, pi_total_height + standoff_height + wall_thickness + 1]) {
        difference() {
            // Cover plate
            translate([-wall_thickness, -wall_thickness, 0])
                cube([pi_length + 2*wall_thickness + display_width + cable_clearance,
                      pi_width + 2*wall_thickness,
                      top_thickness]);
            
            // Ventilation holes
            for (x = [15:vent_spacing*1.5:pi_length + display_width - 15]) {
                for (y = [15:vent_spacing*1.5:pi_width - 15]) {
                    translate([x, y, -1])
                        cylinder(h = top_thickness + 2, d = vent_hole_size, $fn=20);
                }
            }
        }
    }
}

// ============================================
// RENDER OPTIONS
// ============================================

// Uncomment one of these to render:
base_case();
// top_cover();

// To print both parts, render twice with different lines uncommented

