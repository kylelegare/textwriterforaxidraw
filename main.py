from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

# Constants for unit conversion
POINTS_PER_INCH = 72
MM_PER_INCH = 25.4
POINTS_TO_MM = MM_PER_INCH / POINTS_PER_INCH  # 0.35277777...

# Physical dimensions
POSTCARD_WIDTH_MM = 152.4  # 6 inches
POSTCARD_HEIGHT_MM = 101.6  # 4 inches

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

def create_plotter_svg(text, font_size_pt):
    # Calculate the scale factor to convert from font units to physical mm
    # Standard PostScript font size is 1000 units = 1 em = font_size in points
    # So if font_size is 12pt, we want 1000 units = 12pt = 12 * POINTS_TO_MM mm
    scale_factor = (font_size_pt * POINTS_TO_MM) / 1000

    paths = []
    x_offset = 0
    y_offset = 0
    margin_mm = 20 * POINTS_TO_MM  # 20pt margins converted to mm

    words = text.split()
    current_line = []
    current_line_width = 0

    # Word wrapping
    for word in words:
        word_width = 0
        word_paths = []
        word_offsets = []

        # Calculate word width and collect paths
        for char in word:
            glyph_info = get_glyph_info(char)
            if glyph_info:
                word_width += glyph_info['advance'] * scale_factor
                word_paths.append(glyph_info['path'])
                word_offsets.append(x_offset + word_width - (glyph_info['advance'] * scale_factor))

        # Check if word fits on current line
        if current_line_width + word_width + (750 * scale_factor if current_line else 0) <= POSTCARD_WIDTH_MM - 2 * margin_mm:
            # Add word to current line
            if current_line:
                x_offset += 750 * scale_factor  # Word spacing
                current_line_width += 750 * scale_factor
            current_line.extend(zip(word_paths, word_offsets))
            current_line_width += word_width
        else:
            # Add current line to paths
            for path, offset in current_line:
                paths.append(f'<path d="{path}" transform="translate({offset + margin_mm},{y_offset + margin_mm})" />')

            # Start new line
            y_offset += font_size_pt * POINTS_TO_MM * 1.5  # Line spacing
            x_offset = 0
            current_line = list(zip(word_paths, word_offsets))
            current_line_width = word_width

            # Check if we've exceeded the postcard height
            if y_offset > POSTCARD_HEIGHT_MM - 2 * margin_mm:
                break

    # Add remaining line
    for path, offset in current_line:
        paths.append(f'<path d="{path}" transform="translate({offset + margin_mm},{y_offset + margin_mm})" />')

    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             version="1.1"
             viewBox="0 0 {POSTCARD_WIDTH_MM} {POSTCARD_HEIGHT_MM}"
             height="{POSTCARD_HEIGHT_MM}mm"
             width="{POSTCARD_WIDTH_MM}mm">
            <g stroke="black"
               stroke-width="0.3"
               fill="none"
               transform="scale(1,-1)">
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
        font_size = float(data.get('fontSize', 12))  # Default to 12pt

        svg_content = create_plotter_svg(text, font_size)
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