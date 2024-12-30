from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)
CORS(app)

# Physical size of your AxiDraw Mini area in mm
AXIDRAW_WIDTH_MM = 152.4
AXIDRAW_HEIGHT_MM = 101.6

# Relationship between px (at 96 dpi) and mm
# 1 px ~ 0.2645833 mm => 1 mm ~ 3.7795275591 px
MM_PER_PX = 1.0 / 3.7795275591

# Base scale for glyphs (ex: your old FIXED_SCALE of 0.004 at 12px font)
BASE_SCALE = 0.004
BASE_FONT_SIZE_PX = 12  # If the user picks 12px => scale = BASE_SCALE

FONT_SVG_PATH = "static/fonts/PremiumUltra54.svg"


def get_glyph_info(character):
    """
    Look up the <glyph> for the given character in the SVG font file,
    return its path 'd' plus an advance width if needed.
    """
    try:
        tree = ET.parse(FONT_SVG_PATH)
        root = tree.getroot()
        for glyph in root.findall(".//*[@unicode]"):
            if glyph.get('unicode') == character:
                return {
                    'path': glyph.get('d'),
                    'advance': float(glyph.get('horiz-adv-x', 1000))
                }
        return None
    except (ET.ParseError, FileNotFoundError) as e:
        raise Exception(f"Error loading font file: {str(e)}")


def create_svg_from_layout(layout, font_size_px):
    """
    layout: array of { 'char': 'H', 'x': 123.45, 'y': 67.89 } in pixel coordinates
    font_size_px: the user-chosen font size in px
    """
    # Suppose scale is linear w.r.t. font size.
    # If user chooses 12 px => scale = BASE_SCALE
    # If user chooses 24 px => scale = BASE_SCALE * 2
    # etc.
    scale_factor = BASE_SCALE * (font_size_px / BASE_FONT_SIZE_PX)

    paths = []

    for item in layout:
        ch = item['char']
        px_x = float(item['x'])
        px_y = float(item['y'])

        # Convert from px to mm
        mm_x = px_x * MM_PER_PX
        mm_y = px_y * MM_PER_PX

        glyph_info = get_glyph_info(ch)
        if glyph_info and glyph_info['path']:
            # Place each glyph at (mm_x, mm_y), then apply scale in X and Y
            # Negative Y scale flips the font so that +Y goes downwards for the plotter
            path_elt = f'<path d="{glyph_info["path"]}" ' \
                       f'transform="translate({mm_x:.3f},{mm_y:.3f}) ' \
                       f'scale({scale_factor:.4f},-{scale_factor:.4f})" />'
            paths.append(path_elt)

    svg_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1"
     viewBox="0 0 {AXIDRAW_WIDTH_MM} {AXIDRAW_HEIGHT_MM}"
     width="{AXIDRAW_WIDTH_MM}mm" height="{AXIDRAW_HEIGHT_MM}mm">
  <g stroke="black" stroke-width="0.3" fill="none">
    {''.join(paths)}
  </g>
</svg>
'''
    return svg_content


@app.route('/')
def home():
    # Render the index.html from templates folder
    return render_template('index.html')


@app.route('/static/fonts/<path:filename>')
def serve_font(filename):
    # Serve your TTF or SVG font from /static/fonts
    return send_from_directory(os.path.join(app.root_path, 'static', 'fonts'), filename)


@app.route('/api/test_plot', methods=['POST'])
def test_plot():
    """
    Receives JSON: { layout: [...], fontSizePx: 12 }
    layout => array of { 'char': 'H', 'x': 100, 'y': 50 } in px
    """
    try:
        data = request.json
        if 'layout' not in data or not data['layout']:
            return jsonify({'status': 'error', 'message': 'No layout data provided'}), 400

        layout = data['layout']
        font_size_px = data.get('fontSizePx', 12)

        # Build the final SVG
        svg_content = create_svg_from_layout(layout, font_size_px)

        # Connect to AxiDraw and plot
        ad = axidraw.AxiDraw()
        ad.interactive()
        ad.connect()
        if not ad.connected:
            raise Exception("Failed to connect to AxiDraw")

        # Configure pen and speed
        ad.options.mode = "align"
        ad.update()
        ad.options.mode = "plot"
        ad.options.speed_pendown = 25
        ad.options.pen_pos_down = 60
        ad.options.pen_pos_up = 40

        # Plot
        ad.plot_setup(svg_content)
        ad.plot_run()
        ad.disconnect()

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    # Run on localhost:8080, adjust as desired
    app.run(host='0.0.0.0', port=8080, debug=True)
