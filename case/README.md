# ThermalPi 3D Printed Case

This directory contains OpenSCAD files for 3D printing a custom case for the ThermalPi project.

## Files

- **`thermalpi_case.scad`** - Main parametric case design in OpenSCAD format

## Requirements

- **OpenSCAD** (free, open-source): https://openscad.org/
  - Windows/Mac/Linux versions available
- **3D Printer** (FDM/FFF type recommended)
  - Print bed: At least 180mm x 100mm
  - Recommended: 200mm x 200mm or larger

## Usage Instructions

### Step 1: Install OpenSCAD

Download and install OpenSCAD from https://openscad.org/

### Step 2: Open the Design

1. Open `thermalpi_case.scad` in OpenSCAD
2. Review the parameters at the top of the file
3. Adjust any dimensions if needed for your specific components

### Step 3: Customize (Optional)

You can adjust these parameters in the SCAD file:

- **Wall thickness**: Increase for stronger case, decrease to save material
- **Clearances**: Adjust if components don't fit properly
- **Ventilation**: Modify hole size/spacing for better airflow
- **Display window**: Adjust if your display visible area differs

### Step 4: Render and Export

1. **Render the base case:**
   - Ensure `base_case();` is uncommented at the bottom
   - Press **F6** to render (or Design > Render)
   - Wait for rendering to complete
   - Export as STL: **File > Export > Export as STL...**
   - Save as `thermalpi_base.stl`

2. **Render the top cover (optional):**
   - Comment out `base_case();`
   - Uncomment `top_cover();`
   - Press **F6** to render
   - Export as `thermalpi_top.stl`

### Step 5: 3D Printing Settings

Recommended print settings:

- **Material**: PLA or PETG
- **Layer Height**: 0.2mm (0.15mm for smoother finish)
- **Infill**: 15-20%
- **Supports**: None required
- **Bed Temperature**: 60°C (PLA) or 80°C (PETG)
- **Nozzle Temperature**: 200-210°C (PLA) or 230-240°C (PETG)
- **Print Speed**: 50-60 mm/s
- **Bed Adhesion**: Brim or skirt recommended

### Step 6: Post-Processing

1. Remove support material if any
2. Clean up any stringing or imperfections
3. Test fit Raspberry Pi before final assembly
4. (Optional) Sand smooth surfaces for better finish
5. (Optional) Paint or apply surface finish

### Step 7: Assembly

1. Place Raspberry Pi in base case with screws through mounting holes
2. Connect display to GPIO header (cables will route through cable clearance area)
3. Connect USB cameras (cables exit through top opening)
4. Route power cable through USB-C opening
5. (Optional) Attach top cover if printed
6. Secure with M2.5 screws if needed

## Design Features

### Base Case

- **Raspberry Pi 4 compartment**: Secure mounting with standoffs and screw holes
- **Display cavity**: Front-mounted ILI9341 display with viewing window
- **Cable routing**: Dedicated space for GPIO jumper wires between Pi and display
- **Port access**: Openings for:
  - USB ports (2x USB 3.0, 2x USB 2.0)
  - USB-C power
  - MicroSD card
  - GPIO header
  - Ethernet (optional)
  - HDMI ports
  - USB camera cables
- **Ventilation**: Multiple ventilation holes for cooling
- **Standoffs**: Raised mounting points to protect Pi PCB

### Top Cover (Optional)

- **Protection**: Covers exposed components
- **Ventilation**: Additional ventilation holes
- **Removable**: Easy access for maintenance

## Troubleshooting

### Pi Doesn't Fit

- Check that `pi_length`, `pi_width`, and `pi_height` match your specific Pi model
- Increase `clearance` parameter slightly
- Verify standoff heights

### Display Not Visible

- Adjust `display_window` dimensions to match your display's visible area
- Check that display is seated correctly in cavity

### Cables Too Tight

- Increase `cable_clearance` parameter
- Verify GPIO header opening size

### Overheating

- Increase `vent_hole_size` and/or `vent_spacing` for better airflow
- Consider adding more ventilation holes
- Use PETG instead of PLA for better heat resistance

### Print Quality Issues

- Use a brim for better bed adhesion
- Slow down print speed for better quality
- Increase wall thickness if parts are too fragile
- Check bed leveling and first layer adhesion

## Alternative: Using TinkerCAD

If you prefer a visual editor, you can import the STL files into TinkerCAD (free online) for modifications:

1. Go to https://www.tinkercad.com/
2. Create a new design
3. Import the STL file
4. Modify as needed
5. Export updated STL

## Alternative: Fusion 360

For more advanced modifications:

1. Import STL into Fusion 360
2. Convert to solid (Mesh > Convert to Solid)
3. Modify using parametric modeling
4. Export updated STL

## License

This case design is provided as-is for use with the ThermalPi project. Modify as needed for your specific requirements.

