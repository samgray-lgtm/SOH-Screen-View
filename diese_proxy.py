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
        "https://audocuments.diesesoftware.com/tmp-903-CThWMwc4DwxWC1NYBg8KVVFeVXheVFFfBFUBcwA1AGE=.html"
        "?mode=html"
        "&idUtilisateur=189"
        "&idProds=289,246,221,220,263,261,218,219,208,243,228,223,240,233,231,245,225,226"
        "&ta=180,44,43,45,213,214,215,254,212,218,219,220,1,223,224,225,228,226,247,5,185,164,8,195,183,165,188,13,230,251,253,252,4,14,12,11,7,2,9,211,6,179,249,189,150,152,153,217"
        "&tp=6,1,11,7,2,8,3,5"
        "&lieux=133,117,48,134,120,121,118,119,371,124,123,122,125,374,375,126,127,130,147,129,128,231,175,341,293,294,176,315,321,316,317,318,319,320,174,113,221,229,228,311,179,323,333,332"
        "&statuts=3"
        "&date_from=2026-01-01"
        "&date_to=2030-12-31"
        "&smartgroup=540"
        "&externe=1"
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
