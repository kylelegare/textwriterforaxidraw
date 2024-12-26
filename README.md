# AxiDraw Text Plotter

A web interface for plotting text using the AxiDraw Mini plotter. Uses a single-stroke font for natural handwriting simulation.

## Setup

1. Clone the repository

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install AxiDraw API:
   ```bash
   python -m pip install https://cdn.evilmadscientist.com/dl/ad/public/AxiDraw_API.zip
   ```

4. Place fonts in the `static/fonts` directory:
   - `PremiumUltra54.ttf` - Display font
   - `PremiumUltra54.svg` - Plotter font

5. Run the application:
   ```bash
   python main.py
   ```

## Project Structure
```
/
├── main.py              # Flask application
├── static/
│   └── fonts/          # Font files
│       ├── PremiumUltra54.svg
│       └── PremiumUltra54.ttf
└── templates/
    └── index.html      # Web interface
```

## Features
- Live preview of text with proper font rendering
- Font size adjustment
- Text wrapping to match AxiDraw Mini dimensions
- Direct plotting via web interface

## Dependencies
- Flask and Flask-CORS (see requirements.txt)
- AxiDraw API (installed separately)