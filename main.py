from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

FIXED_SCALE = 0.02
AXIDRAW_WIDTH_MM = 152.4
AXIDRAW_HEIGHT_MM = 101.6

def get_glyph_info(character):
    tree = ET.parse("static/fonts/PremiumUltra54.svg")
    root = tree.getroot()
    for glyph in root.findall(".//*[@unicode]"):
        if glyph.get('unicode') == character:
            return {
                'path': glyph.get('d'),
                'advance': float(glyph.get('horiz-adv-x', 1000))
            }
    return None

def create_plotter_svg(text):
    paths = []
    x_offset = 0

    for char in text:
        if char == ' ':
            x_offset += 500
            continue

        glyph_info = get_glyph_info(char)
        if glyph_info:
            path = f'<path d="{glyph_info["path"]}" transform="translate({x_offset},0)" />'
            paths.append(path)
            x_offset += glyph_info['advance']

    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             version="1.1"
             viewBox="0 0 {AXIDRAW_WIDTH_MM} {AXIDRAW_HEIGHT_MM}"
             height="{AXIDRAW_HEIGHT_MM}mm"
             width="{AXIDRAW_WIDTH_MM}mm">
            <g stroke="black"
               stroke-width="0.3"
               fill="none"
               transform="translate(40,60) scale({FIXED_SCALE},-{FIXED_SCALE})">
                {"".join(paths)}
            </g>
        </svg>'''
    print("Generated SVG:", svg)
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

        svg_content = create_plotter_svg(text)
        print("Generated SVG:", svg_content)

        ad = axidraw.AxiDraw()
        ad.interactive()
        ad.connect()

        if not ad.connected:
            raise Exception("Failed to connect to AxiDraw")

        ad.options.mode = "align"
        ad.update()

        ad.options.mode = "plot"
        ad.options.speed_pendown = 25
        ad.options.pen_pos_down = 60
        ad.options.pen_pos_up = 40

        ad.plot_setup(svg_content)
        print("Plot setup complete")
        ad.plot_run()
        print("Plot run complete")
        ad.disconnect()

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)