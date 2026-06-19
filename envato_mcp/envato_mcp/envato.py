"""Envato URL builders and item-type constants.

Envato Stock (app.envato.com) has no public API for downloads. This module
encodes the URL patterns observed in the web UI so a browser-automation MCP
can drive the same routes.
"""
from __future__ import annotations

from typing import Literal
from urllib.parse import urlencode

BASE_APP = "https://app.envato.com"

# Item-type slugs used in /search?itemType=...
ItemType = Literal[
    "stock-video",
    "sound-effect",
    "music",
    "motion-graphic",
    "graphic-template",
    "photo",
    "presentation-template",
    "video-template",
    "3d",
    "font",
    "add-on",
]

KNOWN_ITEM_TYPES: tuple[str, ...] = (
    "stock-video",
    "sound-effect",
    "music",
    "motion-graphic",
    "graphic-template",
    "photo",
    "presentation-template",
    "video-template",
    "3d",
    "font",
    "add-on",
)


def search_url(query: str, item_type: str = "stock-video") -> str:
    """Build a search URL for the given query and item type."""
    if item_type not in KNOWN_ITEM_TYPES:
        raise ValueError(
            f"unknown item_type {item_type!r}; expected one of {KNOWN_ITEM_TYPES}"
        )
    q = urlencode({"itemType": item_type, "term": query})
    return f"{BASE_APP}/search?{q}"


def item_url(item_id: str, item_type: str = "stock-video", term: str | None = None) -> str:
    """Build an item-detail URL given the UUID (item_id)."""
    if item_type not in KNOWN_ITEM_TYPES:
        raise ValueError(
            f"unknown item_type {item_type!r}; expected one of {KNOWN_ITEM_TYPES}"
        )
    params = {"itemType": item_type}
    if term:
        params["term"] = term
    q = urlencode(params)
    return f"{BASE_APP}/search/{item_type}/{item_id}?{q}"


SIGN_IN_URL = "https://elements.envato.com/sign-in"
HOME_URL = f"{BASE_APP}/"
