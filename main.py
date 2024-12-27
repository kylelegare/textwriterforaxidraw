from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

# Constants
PT_TO_MM = 0.352778  # 1 point = 0.352778 mm
MM_TO_PT = 2.83465   # 1mm = 2.83465pt

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
    scale = font_size_mm / units_per_em  # Now using mm-based scale

    base_y = 90

    for char in text:
        if char == ' ':
            current_x += 500 * scale
            continue

        glyph_info = get_glyph_info(char)
        if glyph_info:
            transform = f'translate({current_x * units_per_em},{0})'
            path = f'<path d="{glyph_info["path"]}" transform="{transform}" />'
            paths.append(path)
            current_x += glyph_info['advance'] * scale

    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             version="1.1"
             viewBox="0 0 152.4 101.6"
             height="101.6mm"
             width="152.4mm">
            <g stroke="black"
               stroke-width="0.3"
               fill="none"
               transform="translate(10,{base_y}) scale({scale},-{scale})">
                {"".join(paths)}
            </g>
        </svg>'''
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

        # Create SVG for plotting
        svg_content = create_plotter_svg(text, font_size)

        # Setup AxiDraw
        ad = axidraw.AxiDraw()

        # Configure and plot
        ad.plot_setup(svg_content)
        ad.options.speed_pendown = 50  # 50% speed
        ad.plot_run()

        return jsonify({
            'status': 'success',
            'message': 'Plot completed successfully'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)