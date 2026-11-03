"""
DIESE Screen View
=================
One Render service that does two jobs:

  /            serves board.html, the studio day board
  /schedule    fetches the DIESE report server-side and returns it
  /health      returns "ok", handy for checking the service is awake

Because the board and its data come from the same origin, the browser
never applies CORS rules to the fetch at all.

Requirements:
    pip install flask flask-cors requests gunicorn

Render settings:
    Build command:  pip install -r requirements.txt
    Start command:  gunicorn diese_proxy:app

Repository layout (both files sit next to each other in the repo root):
    diese_proxy.py
    board.html
    requirements.txt
"""

import os
from urllib.parse import urlparse

import requests
from flask import Flask, Response, abort, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Configuration -----------------------------------------------------------

# Only these hosts may be fetched, so the service cannot be used as an
# open proxy for arbitrary websites.
ALLOWED_HOSTS = {"audocuments.diesesoftware.com"}

# Named report sources. Add an entry here when a new report URL settles.
REPORTS = {
    "screen": (
        "https://tab.diesesoftware.com/sp-AnQFMwJs-UmYHZgI9-A0lWVVYXXU0=-VWYBbgI3"
    ),
}

DEFAULT_REPORT = "screen"
TIMEOUT_SECONDS = 20
PORT = int(os.environ.get("PORT", 5050))

# -----------------------------------------------------------------------------


def _host_allowed(url: str) -> bool:
    try:
        return urlparse(url).netloc.lower() in ALLOWED_HOSTS
    except ValueError:
        return False


def _no_cache(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/")
def board():
    """Serve the studio day board."""
    return _no_cache(send_from_directory(BASE_DIR, "board.html"))


@app.route("/health")
def health():
    return Response("ok", mimetype="text/plain")


@app.route("/schedule")
def schedule():
    """Fetch a DIESE report page and hand it back to the board."""
    url = request.args.get("url")

    if url:
        if not _host_allowed(url):
            abort(403, description="That host is not on the allow list.")
    else:
        name = request.args.get("report", DEFAULT_REPORT)
        url = REPORTS.get(name)
        if not url:
            abort(404, description=f"No report registered under '{name}'.")

    try:
        upstream = requests.get(url, timeout=TIMEOUT_SECONDS)
        upstream.raise_for_status()
    except requests.RequestException as exc:
        abort(502, description=f"Could not reach DIESE: {exc}")

    return _no_cache(
        Response(upstream.text, mimetype="text/html; charset=utf-8")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
