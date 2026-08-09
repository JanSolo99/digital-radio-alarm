"""Local favorites list - the alarm's station picker and the web UI both read
and write this same file.
"""

import json
import uuid
from pathlib import Path

FAVORITES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "favorites.json"


def load_favorites():
    if not FAVORITES_PATH.exists():
        return []
    with FAVORITES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_favorites(favorites):
    with FAVORITES_PATH.open("w", encoding="utf-8") as f:
        json.dump(favorites, f, indent=2)
        f.write("\n")


def add_favorite(name, stream_url, homepage="", description="", source_id=None, source="manual"):
    favorites = load_favorites()
    favorite_id = source_id or str(uuid.uuid4())

    if any(f["id"] == favorite_id for f in favorites):
        return favorites

    favorites.append(
        {
            "id": favorite_id,
            "name": name,
            "description": description,
            "stream_url": stream_url,
            "homepage": homepage,
            "source": source,
        }
    )
    save_favorites(favorites)
    return favorites


def remove_favorite(favorite_id):
    favorites = [f for f in load_favorites() if f["id"] != favorite_id]
    save_favorites(favorites)
    return favorites
