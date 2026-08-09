"""Local management page - search Radio Browser, favorite stations, and edit
the list the alarm's station picker reads from. Meant for the home LAN only.
"""

from flask import Flask, jsonify, render_template, request

from src.stations import favorites, radio_browser

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/favorites")
def list_favorites():
    return jsonify(favorites.load_favorites())


@app.post("/api/favorites")
def create_favorite():
    body = request.get_json(force=True)
    if not body.get("name") or not body.get("stream_url"):
        return jsonify({"error": "name and stream_url are required"}), 400

    updated = favorites.add_favorite(
        name=body["name"],
        stream_url=body["stream_url"],
        homepage=body.get("homepage", ""),
        description=body.get("description", ""),
        source_id=body.get("id"),
        source=body.get("source", "manual"),
    )
    return jsonify(updated), 201


@app.delete("/api/favorites/<favorite_id>")
def delete_favorite(favorite_id):
    return jsonify(favorites.remove_favorite(favorite_id))


@app.get("/api/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    try:
        return jsonify(radio_browser.search_stations(query))
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 502


if __name__ == "__main__":
    # Port and hostname match the build plan (radioclock.local:8080). LAN-only -
    # never port-forward this; there's no auth on it yet.
    app.run(host="0.0.0.0", port=8080)
