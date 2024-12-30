from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pyaxidraw import axidraw
import os

app = Flask(__name__)
CORS(app)

# Physical size of AxiDraw Mini area in mm
AXIDRAW_WIDTH_MM = 152.4
AXIDRAW_HEIGHT_MM = 101.6

# 1 px ~ 0.264583 mm at 96 dpi
MM_PER_PX = 1.0 / 3.7795275591

@app.route('/')
def home():
    return render_template('index.html')

# Serve your single-stroke SVG font from static/fonts
@app.route('/static/fonts/<path:filename>')
def serve_font(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'fonts'), filename)

@app.route('/api/plot_svg_paths', methods=['POST'])
def plot_svg_paths():
    """
    Receives JSON like:
      {
        shapes: [
          { path: "M10 -20 L30 -40...", x: 123.45, y: 67.89, scale: 0.02 },
          ...
        ]
      }
    We'll build an <svg> that places each path in the correct position,
    then plot with the AxiDraw.
    """
    try:
        data = request.json
        shapes = data.get('shapes', [])
        if not shapes:
            return jsonify({'status': 'error', 'message': 'No shapes provided'}), 400

        # Build an SVG string
        svg_content = create_plot_svg(shapes)

        # Plot with AxiDraw
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

        # Plot
        ad.plot_setup(svg_content)
        ad.plot_run()
        ad.disconnect()

        return jsonify({'status': 'success'})

    except Exception as e:
        print("Error in /api/plot_svg_paths:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

def create_plot_svg(shapes):
    """
    shapes: array of { path, x, y, scale }
    - x, y are in px from the front-end
    - scale is dimensionless
    We'll convert px->mm, and apply the scale in the SVG transform.
    """
    path_elems = []
    for s in shapes:
        path_data = s['path']
        px_x = float(s['x'])
        px_y = float(s['y'])
        sc = float(s['scale'])

        mm_x = px_x * MM_PER_PX
        mm_y = px_y * MM_PER_PX
        # We'll do "scale(sc, -sc)" if you want Y downward in the plotter,
        # but let's do scale(sc, sc) for now and see how it goes.
        # If text appears upside down or mirrored, switch to -(sc) in Y.
        path_elems.append(f'''
          <path d="{path_data}"
                transform="translate({mm_x:.2f},{mm_y:.2f}) scale({sc:.4f},{sc:.4f})"
                fill="none" stroke="black" stroke-width="0.3"/>
        ''')

    svg = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1"
     width="{AXIDRAW_WIDTH_MM}mm" height="{AXIDRAW_HEIGHT_MM}mm"
     viewBox="0 0 {AXIDRAW_WIDTH_MM} {AXIDRAW_HEIGHT_MM}">
  <g>
    {''.join(path_elems)}
  </g>
</svg>
'''
    return svg

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
