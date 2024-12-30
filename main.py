from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

FIXED_SCALE = 0.002  # Reduced base scale
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

def create_plotter_svg(text, font_size_pt=12):
    # Calculate size multiplier based on requested point size
    size_multiplier = font_size_pt / 12.0

    paths = []
    x_offset = 0
    y_offset = 0
    line_height = 1200  # Base line height
    max_width = (AXIDRAW_WIDTH_MM - 80) / (FIXED_SCALE * size_multiplier)  # Convert mm to font units

    words = text.split()
    current_line = []
    current_line_width = 0

    for word in words:
        # Calculate width of this word
        word_width = 0
        word_paths = []
        word_offsets = []

        for char in word:
            glyph_info = get_glyph_info(char)
            if glyph_info:
                word_width += glyph_info['advance']
                word_paths.append(glyph_info['path'])
                word_offsets.append(x_offset + word_width - glyph_info['advance'])

        # Check if adding this word would exceed line width
        if current_line_width + word_width + (750 if current_line else 0) <= max_width:
            # Add word to current line
            if current_line:
                x_offset += 750  # Word spacing
                current_line_width += 750
            current_line.extend(zip(word_paths, word_offsets))
            current_line_width += word_width
            x_offset += word_width
        else:
            # Add current line to paths
            for path, offset in current_line:
                paths.append(f'<path d="{path}" transform="translate({offset},{y_offset})" />')

            # Start new line
            y_offset -= line_height
            x_offset = word_width
            word_offsets = [0]
            for char_idx in range(1, len(word_paths)):
                glyph_info = get_glyph_info(word[char_idx])
                if glyph_info:
                    word_offsets.append(word_offsets[-1] + glyph_info['advance'])
            current_line = list(zip(word_paths, word_offsets))
            current_line_width = word_width

    # Add remaining line
    for path, offset in current_line:
        paths.append(f'<path d="{path}" transform="translate({offset},{y_offset})" />')

    # Apply size multiplier to the base scale
    adjusted_scale = FIXED_SCALE * size_multiplier

    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             version="1.1"
             viewBox="0 0 {AXIDRAW_WIDTH_MM} {AXIDRAW_HEIGHT_MM}"
             height="{AXIDRAW_HEIGHT_MM}mm"
             width="{AXIDRAW_WIDTH_MM}mm">
            <g stroke="black"
               stroke-width="0.3"
               fill="none"
               transform="translate(40,60) scale({adjusted_scale},-{adjusted_scale})">
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
        font_size = float(data.get('fontSize', 12))  # Default to 12pt if not specified

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