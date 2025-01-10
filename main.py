@app.route('/api/test_plot', methods=['POST'])
def test_plot():
    try:
        data = request.json
        text = data.get('text', '')

        # Calculate max width based on available space
        available_width_mm = AXIDRAW_WIDTH_MM - (2 * MARGIN_MM)
        max_width = int(available_width_mm / FIXED_SCALE)

        # Split text into lines
        words = text.split()
        lines = []
        current_line = []
        current_width = 0

        for word in words:
            # Calculate word width
            word_width = sum(get_glyph_info(c)['advance'] if get_glyph_info(c) else 750 for c in word)

            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width + 750  # Add space width
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width + 750

        if current_line:
            lines.append(' '.join(current_line))

        # Initialize AxiDraw connection
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

        # Plot each line separately
        y_offset = 0
        for line_number, line in enumerate(lines):
            # Create SVG for just this line
            paths = []
            x_offset = 0
            for char in line:
                if char == ' ':
                    x_offset += 750
                    continue
                glyph_info = get_glyph_info(char)
                if glyph_info:
                    path = f'<path d="{glyph_info["path"]}" transform="translate({x_offset},0)" />'
                    paths.append(path)
                    x_offset += glyph_info['advance']

            # Create SVG with just this line
            line_svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
                <svg xmlns="http://www.w3.org/2000/svg"
                     version="1.1"
                     viewBox="0 0 {AXIDRAW_WIDTH_MM} {AXIDRAW_HEIGHT_MM}"
                     height="{AXIDRAW_HEIGHT_MM}mm"
                     width="{AXIDRAW_WIDTH_MM}mm">
                    <g stroke="black"
                       stroke-width="0.3"
                       fill="none"
                       transform="translate({MARGIN_MM},{MARGIN_MM + 45 + y_offset}) scale({FIXED_SCALE},-{FIXED_SCALE})">
                        {"".join(paths)}
                    </g>
                </svg>'''

            print(f"Plotting line {line_number + 1} of {len(lines)}")
            ad.plot_setup(line_svg)
            ad.plot_run()
            y_offset += 1000 * FIXED_SCALE  # Approximate line height

        ad.disconnect()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500