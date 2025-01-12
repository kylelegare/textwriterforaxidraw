from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

# --------------------------------------------------------------------
# Constants & Font Handling
# --------------------------------------------------------------------
FIXED_SCALE = 0.0025           # Scale from font units → device space
AXIDRAW_WIDTH_MM = 152.4       # Physical width in mm (Mini)
AXIDRAW_HEIGHT_MM = 101.6      # Physical height in mm (Mini)
MARGIN_MM = 15                 # Margin in mm
LINE_SPACING_UNITS = 2200      # Vertical spacing in "font units" (example)
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
    return render_template('index.html')

@app.route('/static/fonts/<path:filename>')
def serve_font(filename):
    return send_from_directory('static/fonts', filename)

@app.route('/api/test_plot', methods=['POST'])
def test_plot():
    """
    Expects JSON of the form:
      {
         "lines": ["Line 1 text", "Line 2 text", "Line 3 text", ...]
      }
    """
    try:
        data = request.json
        lines = data.get('lines', [])

        # ------------------------------------------------------------
        # Build a single SVG that contains all lines at once
        # ------------------------------------------------------------
        paths = []
        y_offset = 0

        # For each line of text:
        for line_index, text_line in enumerate(lines):
            x_offset = 0
            for char in text_line:
                if char == ' ':
                    # Move x_offset by space width
                    x_offset += SPACE_ADVANCE
                    continue

                glyph_info = get_glyph_info(char)
                if glyph_info:
                    # IMPORTANT CHANGE: include y_offset in transform
                    # Negative sign because we often invert Y in pen plots.
                    path_str = (
                        f'<path d="{glyph_info["path"]}" '
                        f'transform="translate({x_offset}, -{y_offset})" />'
                    )
                    paths.append(path_str)
                    x_offset += glyph_info['advance']
                else:
                    x_offset += 750  # fallback if glyph not found

            # Move y_offset down for the next line
            y_offset += LINE_SPACING_UNITS

        # Combine all paths into a single <svg>
        combined_svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             width="{AXIDRAW_WIDTH_MM}mm"
             height="{AXIDRAW_HEIGHT_MM}mm"
             viewBox="0 0 {AXIDRAW_WIDTH_MM} {AXIDRAW_HEIGHT_MM}">
          <g stroke="black"
             stroke-width="0.3"
             fill="none"
             transform="translate({MARGIN_MM}, {MARGIN_MM + 45}) scale({FIXED_SCALE}, -{FIXED_SCALE})">
             {''.join(paths)}
          </g>
        </svg>"""

        # ------------------------------------------------------------
        # Initialize AxiDraw and Plot
        # ------------------------------------------------------------
        ad = axidraw.AxiDraw()
        ad.interactive()
        connected = ad.connect()
        if not connected:
            raise Exception("Failed to connect to AxiDraw")

        # Optional settings
        ad.options.pen_pos_down = 60
        ad.options.pen_pos_up = 40
        ad.options.speed_pendown = 25

        # Send the single combined SVG
        ad.plot_setup(combined_svg)
        ad.plot_run()

        # Clean up
        ad.disconnect()
        return jsonify({'status': 'success'})

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)