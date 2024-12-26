from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

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
    """Create SVG for plotting with proper scaling and positioning"""
    paths = []
    x_offset = 0
    scale = 0.02 * (font_size / 12)  # Scale based on font size

    # Collect path data for each character
    for char in text:
        if char == ' ':
            x_offset += 500  # Space width
            continue

        glyph_info = get_glyph_info(char)
        if glyph_info:
            path = f'<path d="{glyph_info["path"]}" transform="translate({x_offset},0)" />'
            paths.append(path)
            x_offset += glyph_info['advance']

    # Create complete SVG document
    svg = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg
            xmlns="http://www.w3.org/2000/svg"
            version="1.1"
            viewBox="0 0 152.4 101.6"
            height="101.6mm"
            width="152.4mm">
            <g 
                stroke="black"
                stroke-width="0.3"
                fill="none"
                transform="translate(40,60) scale({scale},-{scale})">
                {"".join(paths)}
            </g>
        </svg>"""

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

app.run(host='0.0.0.0', port=8080)