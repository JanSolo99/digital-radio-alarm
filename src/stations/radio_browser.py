"""Client for the Radio Browser API (api.radio-browser.info).

The bare api.radio-browser.info domain only serves docs - it 404s on real API
paths. The actual service lives on rotating mirror hosts discovered via DNS,
per the project's own reference clients, because hardcoding one mirror is
explicitly discouraged (they come and go).
"""

import random
import socket
import time

import requests

USER_AGENT = "DigitalRadioAlarm/0.1"
_MIRROR_CACHE_TTL = 1800  # seconds
_mirror_cache = {"hosts": [], "resolved_at": 0.0}


def _resolve_mirrors():
    hosts = []
    for _, _, _, _, sockaddr in socket.getaddrinfo(
        "all.api.radio-browser.info", 80, 0, socket.SOCK_STREAM
    ):
        ip = sockaddr[0]
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except socket.herror:
            continue
        if hostname not in hosts:
            hosts.append(hostname)
    hosts.sort()
    return [f"https://{host}" for host in hosts]


def _get_mirrors():
    stale = time.time() - _mirror_cache["resolved_at"] > _MIRROR_CACHE_TTL
    if stale or not _mirror_cache["hosts"]:
        hosts = _resolve_mirrors()
        if hosts:
            _mirror_cache["hosts"] = hosts
            _mirror_cache["resolved_at"] = time.time()
    return _mirror_cache["hosts"]


def _request(path, params=None):
    mirrors = _get_mirrors()
    if not mirrors:
        raise RuntimeError("No Radio Browser mirrors found - check network/DNS")

    last_error = None
    for base in random.sample(mirrors, len(mirrors)):
        try:
            response = requests.get(
                f"{base}{path}",
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=5,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            last_error = error
            continue
    raise RuntimeError(f"All Radio Browser mirrors failed: {last_error}")


def search_stations(query, limit=30):
    """Search stations by name. Returns only the fields the UI needs."""
    results = _request(
        "/json/stations/search",
        {"name": query, "limit": limit, "hidebroken": "true"},
    )
    return [
        {
            "id": station["stationuuid"],
            "name": station["name"],
            "stream_url": station.get("url_resolved") or station["url"],
            "homepage": station.get("homepage", ""),
            "country": station.get("countrycode", ""),
            "tags": station.get("tags", ""),
            "codec": station.get("codec", ""),
            "bitrate": station.get("bitrate", ""),
        }
        for station in results
    ]


def register_click(stationuuid):
    """Best-effort 'this station was played' ping - marks it popular in Radio
    Browser's stats. Not called from anywhere yet; hook this up from the audio
    module once playback exists.
    """
    try:
        _request(f"/json/url/{stationuuid}")
    except RuntimeError:
        pass
