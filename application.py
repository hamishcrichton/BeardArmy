from __future__ import annotations

from pathlib import Path
from flask import Flask, jsonify, send_from_directory


ROOT = Path(__file__).parent.resolve()
PREVIEW_DIR = ROOT / "preview"
PUBLIC_DATA_DIR = ROOT / "public" / "data"


# Serve the static preview as the site root
application = Flask(
    __name__,
    static_folder=str(PREVIEW_DIR),
    static_url_path="",  # expose preview files at '/'
)


@application.get("/")
def index():
    # Serve preview/index.html at root
    return application.send_static_file("index.html")


@application.get("/public/data/<path:filename>")
def public_data(filename: str):
    # Serve published artifacts (created by `publish --out ./public/data`)
    directory = PUBLIC_DATA_DIR
    return send_from_directory(directory, filename)


@application.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    # Local dev: `python application.py` then visit http://127.0.0.1:5000
    # For production, EBS will use gunicorn per Procfile.
    application.run(host="0.0.0.0", port=5000, debug=True)

