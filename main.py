from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

# Constants
PT_TO_MM = 0.352778  # 1 point = 0.352778 mm
MM_TO_PT = 2.83465   # 1mm = 2.83465pt
AXIDRAW_WIDTH_MM = 152.4
AXIDRAW_HEIGHT_MM = 101.6

def get_glyph_info(character):
    """Get path data and metrics for a character from SVG font"""
    tree = ET.parse("static/fonts/PremiumUltra54.svg")
    root = tree.getroot()
    for glyph in root.findall(".//*[@unicode]"):
        if glyph.get('unicode') == character:
            return {
                'path': glyph.get('d'),
                'advance': float(glyph.get('horiz-adv-x', 1000))
            }
    return None

def create_plotter_svg(text, font_size):
    # Convert font size from points to mm
    font_size_mm = font_size * PT_TO_MM

    paths = []
    current_x = 0
    units_per_em = 1000
    scale = font_size / units_per_em  # Use points for consistent scaling

    base_y = font_size  # Adjust baseline to font size
    margin = 10 * MM_TO_PT  # 10mm margin in points

    for char in text:
        if char == ' ':
            current_x += 250 * scale  # Reduced space width
            continue

        glyph_info = get_glyph_info(char)
        if glyph_info:
            x_pos = margin + (current_x * scale)
            transform = f'translate({x_pos},{base_y + margin})'
            path = f'<path d="{glyph_info["path"]}" transform="{transform}" />'
            paths.append(path)
            current_x += glyph_info['advance']

    # Convert dimensions to points for consistent scaling
    width_pt = AXIDRAW_WIDTH_MM * MM_TO_PT
    height_pt = AXIDRAW_HEIGHT_MM * MM_TO_PT

    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             version="1.1"
             viewBox="0 0 {width_pt} {height_pt}"
             height="{height_pt}pt"
             width="{width_pt}pt">
            <g stroke="black"
               stroke-width="0.3"
               fill="none"
               transform="scale({scale},-{scale})">
                {"".join(paths)}
            </g>
        </svg>'''
    print("Generated SVG:", svg)  # Debug print
    return svg

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/fonts/<path:filename>')
def serve_font(filename):
    return send_from_directory('static/fonts', filename)

@app.route('/api/test_plot', methods=['POST'])
def test_plot():
    try:
        data = request.json
        text = data.get('text', '')
        font_size = data.get('fontSize', 12)

        print(f"Starting plot with text: {text}, size: {font_size}")

        svg_content = create_plotter_svg(text, font_size)
        print("SVG generated")

        ad = axidraw.AxiDraw()
        print("Created AxiDraw instance")

        ad.plot_setup(svg_content)
        print("Plot setup complete")

        ad.options.speed_pendown = 25
        ad.options.pen_pos_down = 60
        ad.options.pen_pos_up = 40
        print("Options set")

        ad.plot_run()
        print("Plot run complete")

        return jsonify({
            'status': 'success',
            'message': 'Plot completed successfully'
        })
    except Exception as e:
        print(f"Error during plotting: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)