from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET
import random

app = Flask(__name__)
CORS(app)

# --------------------------------------------------------------------
# Constants & Font Handling
# --------------------------------------------------------------------
# Recalculated scaling factor to maintain proportions between screen and physical output
FIXED_SCALE = 0.0025           # Scale from font units → device space
AXIDRAW_WIDTH_MM = 152.4       # Physical width in mm (Mini)
AXIDRAW_HEIGHT_MM = 101.6      # Physical height in mm (Mini)
MARGIN_MM = 7                  # Margin in mm (reduced from 15mm to maximize printing area)
PRINT_SAFETY_RATIO = 0.97      # Ratio to scale down printable area to prevent edge clipping
LINE_SPACING_UNITS = 2700      # Vertical spacing in "font units" (example)
SPACE_ADVANCE = 750            # "Width" in font units for space

def get_glyph_info(character):
    """Look up glyph path/advance from PremiumUltra54.svg."""
    tree = ET.parse("static/fonts/PremiumUltra54.svg")
    root = tree.getroot()
    for glyph in root.findall(".//*[@unicode]"):
        if glyph.get('unicode') == character:
            return {
                'path': glyph.get('d'),
                'advance': float(glyph.get('horiz-adv-x', 1000))
            }
    return None

# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')  # Renders the HTML file below

@app.route('/static/fonts/<path:filename>')
def serve_font(filename):
    return send_from_directory('static/fonts', filename)

@app.route('/api/axidraw_control', methods=['POST'])
def axidraw_control():
    """Control AxiDraw motor functions"""
    try:
        data = request.json
        command = data.get('command', '')
        
        ad = axidraw.AxiDraw()
        
        if command == 'disable_motors':
            # Comprehensive approach to disable motors using direct EBB commands
            ad.interactive()            # Enter interactive mode
            if not ad.connect():        # Connect to the device
                raise Exception("Failed to connect to AxiDraw")
                
            # Send direct EBB command "EM,0,0" to disable both motors
            # This is the raw EBB command to disable both stepper motors
            ad.usb_command("EM,0,0\r")  # Direct command to disable
            print("Sent motor disable command...")
            
            # Additional commands that might help ensure motors are off
            ad.usb_command("EM,0,0\r")  # Send it again to be sure
            
            # Delay to allow command to process
            ad.delay(200)               # Wait 200ms
            
            ad.disconnect()
            result = "Motors disabled - you should be able to move the carriage freely"
            
        elif command == 'enable_motors':
            # Enable motors
            ad.interactive()
            if not ad.connect():
                raise Exception("Failed to connect to AxiDraw")
                
            # Send direct EBB command to enable both motors
            ad.usb_command("EM,1,1\r")  # Enable both motors
            result = "Motors enabled"
            ad.disconnect()
            
        elif command == 'pen_up':
            # Raise the pen
            ad.interactive()
            if not ad.connect():
                raise Exception("Failed to connect to AxiDraw")
                
            ad.penup()
            result = "Pen raised"
            ad.disconnect()
            
        elif command == 'pen_down':
            # Lower the pen
            ad.interactive()
            if not ad.connect():
                raise Exception("Failed to connect to AxiDraw")
                
            ad.pendown()
            result = "Pen lowered"
            ad.disconnect()
            
        elif command == 'home':
            # Return to home position using walk_home command
            ad.plot_setup()
            ad.options.mode = "manual"
            ad.options.manual_cmd = "walk_home"
            ad.plot_run()
            result = "Moved to home position"
            
        return jsonify({'status': 'success', 'result': result})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/test_plot', methods=['POST'])
def test_plot():
    """
    Expects JSON of the form:
      {
         "lines": ["Line 1 text", "Line 2 text", "Line 3 text", ...],
         "font_size": 12  // Font size in points
      }
    """
    try:
        data = request.json
        lines = data.get('lines', [])
        font_size = float(data.get('font_size', 12))
        
        # ----------------------------------------------------------------
        # BASIC APPROACH: Keep it simple to ensure legible output
        # ----------------------------------------------------------------
        
        # Convert points to mm for physical scaling (1pt = 0.3528mm)
        PT_TO_MM = 0.3528
        font_size_mm = font_size * PT_TO_MM
        
        # Use standard margin
        PRINT_MARGIN_MM = 10  # 10mm margin
        
        # Standard scale factor based on font size
        scale_factor = FIXED_SCALE * (font_size / 12.0)
        
        # Calculate line spacing
        line_spacing = LINE_SPACING_UNITS * (font_size / 12.0)
        
        # Print debugging information
        print(f"------- BASIC PLOTTING SETUP -------")
        print(f"AXIDRAW_WIDTH_MM: {AXIDRAW_WIDTH_MM}mm")
        print(f"AXIDRAW_HEIGHT_MM: {AXIDRAW_HEIGHT_MM}mm")
        print(f"Print margin: {PRINT_MARGIN_MM}mm")
        print(f"Font size: {font_size}pt ({font_size_mm}mm)")
        print(f"Scale factor: {scale_factor}")
        print(f"Line spacing: {line_spacing} font units")
        print(f"----------------------------------")
        
        # ------------------------------------------------------------
        # Build a single SVG that contains all lines at once
        # ------------------------------------------------------------
        paths = []
        y_offset = 0

        # For each line of text:
        for line_index, text_line in enumerate(lines):
            # Skip drawing for empty lines but still add spacing
            if text_line.strip() == '':
                y_offset += line_spacing
                continue
                
            x_offset = 0
            for char in text_line:
                if char == ' ':
                    # Move x_offset by space width
                    x_offset += SPACE_ADVANCE
                    continue

                glyph_info = get_glyph_info(char)
                if glyph_info:
                    # Offset in font units
                    path_str = (
                        f'<path d="{glyph_info["path"]}" '
                        f'transform="translate({x_offset}, -{y_offset})" />'
                    )
                    paths.append(path_str)
                    x_offset += glyph_info['advance']
                else:
                    # fallback if glyph not found
                    x_offset += 750

            y_offset += line_spacing

        # Combine all paths into a single <svg>
        combined_svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             width="{AXIDRAW_WIDTH_MM}mm"
             height="{AXIDRAW_HEIGHT_MM}mm"
             viewBox="0 0 {AXIDRAW_WIDTH_MM} {AXIDRAW_HEIGHT_MM}">
          <g stroke="black"
             stroke-width="0.3"
             fill="none"
             transform="translate({PRINT_MARGIN_MM}, {PRINT_MARGIN_MM}) scale({scale_factor}, -{scale_factor})">
             {''.join(paths)}
          </g>
        </svg>"""

        # Debug SVG dimensions
        print(f"SVG dimensions: {AXIDRAW_WIDTH_MM}mm x {AXIDRAW_HEIGHT_MM}mm")
        
        # ------------------------------------------------------------
        # Initialize AxiDraw and Plot
        # ------------------------------------------------------------
        ad = axidraw.AxiDraw()
        ad.interactive()  # Use interactive mode as before
        
        connected = ad.connect()
        if not connected:
            raise Exception("Failed to connect to AxiDraw")

        # Basic settings
        ad.options.pen_pos_down = 60
        ad.options.pen_pos_up = 40
        ad.options.speed_pendown = 25

        # Send the SVG for plotting
        ad.plot_setup(combined_svg)
        ad.plot_run()
        
        # Return to home position
        ad.penup()
        ad.moveto(0, 0)
        ad.disconnect()
        
        return jsonify({'status': 'success'})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)