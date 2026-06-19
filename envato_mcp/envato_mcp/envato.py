"""Envato URL builders and item-type constants.

Envato Stock (app.envato.com) has no public API for downloads. This module
encodes the URL patterns observed in the web UI so a browser-automation MCP
can drive the same routes.

URL conventions vary by category:

  stock-video    → /search?itemType=stock-video&term=<q>
                   item: /search/stock-video/<UUID> (also /stock-video/<UUID>)
  sound-effect   → /sound-effects?term=<q>
                   item: /sound-effects/<UUID>
  music          → /music?term=<q>
                   item: /music/<UUID>
  motion-graphic → /motion-graphics?term=<q>
                   item: /motion-graphics/<UUID>
  photo          → /photos?term=<q>
                   item: /photos/<UUID>
"""
from __future__ import annotations

from typing import Literal
from urllib.parse import urlencode

BASE_APP = "https://app.envato.com"

ItemType = Literal[
    "stock-video",
    "sound-effect",
    "music",
    "motion-graphic",
    "photo",
    "graphic-template",
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
    "photo",
    "graphic-template",
    "presentation-template",
    "video-template",
    "3d",
    "font",
    "add-on",
)

# Category → (search-path-template, item-path-template).
# The placeholder `{q}` is the URL-encoded query; `{id}` is the item UUID.
# For categories that route through /search?itemType=..., search_path is None.
_CATEGORY_PATHS: dict[str, tuple[str | None, str]] = {
    "stock-video": (None, "/search/stock-video/{id}"),
    "sound-effect": ("/sound-effects?term={q}", "/sound-effects/{id}"),
    "music": ("/music?term={q}", "/music/{id}"),
    "motion-graphic": ("/motion-graphics?term={q}", "/motion-graphics/{id}"),
    "photo": ("/photos?term={q}", "/photos/{id}"),
    # Less common; routed through generic /search as a fallback.
    "graphic-template": (None, "/search/graphic-template/{id}"),
    "presentation-template": (None, "/search/presentation-template/{id}"),
    "video-template": (None, "/search/video-template/{id}"),
    "3d": (None, "/search/3d/{id}"),
    "font": (None, "/search/font/{id}"),
    "add-on": (None, "/search/add-on/{id}"),
}


def _check(item_type: str) -> None:
    if item_type not in KNOWN_ITEM_TYPES:
        raise ValueError(
            f"unknown item_type {item_type!r}; expected one of {KNOWN_ITEM_TYPES}"
        )


def search_url(query: str, item_type: str = "stock-video") -> str:
    """Build a search URL for the given query and item type."""
    _check(item_type)
    pattern, _ = _CATEGORY_PATHS[item_type]
    if pattern is None:
        q = urlencode({"itemType": item_type, "term": query})
        return f"{BASE_APP}/search?{q}"
    q = urlencode({"term": query})[5:]  # strip leading 'term=' to inline below
    return BASE_APP + pattern.format(q=q)


def item_url(item_id: str, item_type: str = "stock-video", term: str | None = None) -> str:
    """Build an item-detail URL given the UUID (item_id)."""
    _check(item_type)
    _, item_pattern = _CATEGORY_PATHS[item_type]
    path = item_pattern.format(id=item_id)
    params: dict[str, str] = {}
    if "/search/" in path:
        params["itemType"] = item_type
    if term:
        params["term"] = term
    qs = ("?" + urlencode(params)) if params else ""
    return BASE_APP + path + qs


SIGN_IN_URL = "https://elements.envato.com/sign-in"
HOME_URL = f"{BASE_APP}/"
DOWNLOADS_URL = f"{BASE_APP}/downloads"
