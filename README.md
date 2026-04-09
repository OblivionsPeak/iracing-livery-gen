# iRacing Livery Generator — Lite

A programmatic livery builder for iRacing. Upload your car's UV template, pick colors and a design pattern, and download a Trading Paints-ready 2048×2048 PNG. **No GPU or AI required.**

![Livery Generator](https://img.shields.io/badge/Python-3.12-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Features

- 8 design patterns: Solid, Racing Stripes, Diagonal, Gradient, GT Sweep, Split, Chevron, Two-Tone
- 3 finish textures: Carbon Fiber, Brushed Metal, Matte
- 8 preset color schemes (Gulf, Rothmans, Martini, etc.)
- Live preview — updates as you change colors
- "Generate 4 Variations" for quick exploration
- Download as 2048×2048 PNG, ready for Trading Paints

## Running Locally

**Requirements:** Python 3.10+

```bash
git clone https://github.com/OblivionsPeak/iracing-livery-gen.git
cd iracing-livery-gen
python -m venv venv

# Windows
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe app.py

# Mac/Linux
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5002** in your browser.

## Getting Templates

iRacing provides official UV paint templates for every car:

1. Log in at **members.iracing.com**
2. Go to **Garage** → select your car → **Paint Templates**
3. Download the PNG or PSD
4. Upload it in the app under "Download / Load Template"

## Deploying to Railway

1. Fork this repo on GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Select your fork — Railway auto-detects Python and uses the `Procfile`
4. Click **Deploy**. Done.

The app will be live at a `*.up.railway.app` URL within ~2 minutes.

> **Note:** Railway uses an ephemeral filesystem. Uploaded templates and generated liveries are stored temporarily and cleared on redeploy. For persistent storage, connect a Cloudinary or S3 bucket (see `CONTRIBUTING.md`).

## Cars Supported

Edit `cars.json` to add any iRacing car. The `iracing_folder` value should match the folder name under `Documents/iRacing/paint/`.

## License

MIT
