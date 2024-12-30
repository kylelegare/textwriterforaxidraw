from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

# Constants for AxiDraw Mini A4
FIXED_SCALE = 0.004
AXIDRAW_WIDTH_MM = 152.4
AXIDRAW_HEIGHT_MM = 101.6

def get_glyph_info(character):
    try:
        tree = ET.parse("static/fonts/PremiumUltra54.svg")
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

def create_plotter_svg(text):
    if not text:
        raise ValueError("Text cannot be empty")

    paths = []
    x_offset = 0
    y_offset = 0
    line_height = 1000  # SVG font units
    max_width = 30000   # Calibrated for physical width

    # Split into words
    words = text.split()
    current_line = []
    current_width = 0

    for word in words:
        word_width = 0
        # Calculate word width using glyph metrics
        for char in word:
            glyph_info = get_glyph_info(char)
            if glyph_info:
                word_width += glyph_info['advance']

        # Add space width if not first word
        if current_line:
            word_width += 750  # space width

        # Check if adding this word would exceed max width
        if current_width + word_width > max_width and current_line:
            # Create paths for current line
            x_offset = 0
            for char in ' '.join(current_line):
                if char == ' ':
                    x_offset += 750
                    continue
                glyph_info = get_glyph_info(char)
                if glyph_info:
                    path = f'<path d="{glyph_info["path"]}" transform="translate({x_offset},{y_offset})" />'
                    paths.append(path)
                    x_offset += glyph_info['advance']

            # Reset for next line
            current_line = [word]
            current_width = word_width
            y_offset += line_height
        else:
            current_line.append(word)
            current_width += word_width

    # Handle last line
    x_offset = 0
    for char in ' '.join(current_line):
        if char == ' ':
            x_offset += 750
            continue
        glyph_info = get_glyph_info(char)
        if glyph_info:
            path = f'<path d="{glyph_info["path"]}" transform="translate({x_offset},{y_offset})" />'
            paths.append(path)
            x_offset += glyph_info['advance']

    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" 
     viewBox="0 0 {AXIDRAW_WIDTH_MM} {AXIDRAW_HEIGHT_MM}"
     height="{AXIDRAW_HEIGHT_MM}mm" width="{AXIDRAW_WIDTH_MM}mm">
    <g stroke="black" stroke-width="0.3" fill="none" 
       transform="translate(40,60) scale({FIXED_SCALE},-{FIXED_SCALE})">
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
        if not data or 'text' not in data:
            return jsonify({'status': 'error', 'message': 'No text provided'}), 400

        text = data['text']
        svg_content = create_plotter_svg(text)

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
        ad.plot_run()
        ad.disconnect()

        return jsonify({'status': 'success'})

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)