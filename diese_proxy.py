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
        "https://audocuments.diesesoftware.com/tmp-903-VmdRNFZpDA9WC1RfV15VClFeBClTWQ8BVQQHdQYzAGE=.html?mode=html&uid=QWpGVk9sQmw=&idProds=312,289,290,246,264,254,253,258,221,220,284,263,261,295,218,219,208,247,252,251,256,255,257,243,244,228,242,223,240,233,231,229,249,250,245,225,226&ta=235,236,198,231,232,69,71,199,72,70,68,74,200,95,186,94,180,44,43,45,213,214,215,254,212,218,219,220,1,223,224,225,228,226,247,5,185,164,8,195,280,183,255,165,188,13,230,251,253,252,4,14,12,11,7,2,9,211,6,20,221,222,256,229,17,18,19,209,208,22,34,3,21,64,23,24,248,16,26,27,28,29,33,35,25,38,31,36,37,194,39,40,41,207,42,158,190,193,61,273,46,276,47,216,52,53,65,63,62,55,268,269,249,160,161,179,257,189,148,182,184,60,110,181,97,250,86,85,87,210,50,203,54,175,176,178,177,204,166,168,202,169,170,171,172,173,174,89,117,90,88,136,137,111,138,91,140,139,141,142,99,104,109,106,105,150,151,152,153,154,155,156,157,217,121,116,122,123,124,125,163,126,127,128,133,162,134,135,159,270,271,118,119,120,143,144,233,234,240,241,237,239,238,275,274,259,262,263,264,265,277,278,279,258,243,244,245,246&tp=6,1,11,7,2,8,3,5&lieux=164,79,1,2,10,4,5,3,204,9,155,154,8,331,378,6,167,181,148,168,7,180,314&statuts=3&date_from=2026-01-01&date_to=2030-12-31&smartgroup=663&externe=1"
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
