"""MCP server for Envato Stock via agent-browser.

Drives a logged-in browser session against app.envato.com to search and
download stock video / sound effects / music / motion graphics for a user
who already holds an active Envato subscription.

There is no public Envato API for the Elements/Stock subscription, so this
MCP automates the same UI a human subscriber uses. Use is bound by your
Envato Terms of Service — this server does not bypass any access control or
license; it just clicks the buttons your subscription already entitles you
to click.
"""
from __future__ import annotations

import json
import os
import re
import zipfile
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .browser import AgentBrowserError, Browser, BrowserConfig
from .envato import (
    DOWNLOADS_URL,
    HOME_URL,
    KNOWN_ITEM_TYPES,
    SIGN_IN_URL,
    item_url,
    search_url,
)


mcp = FastMCP("envato")

_browser: Browser | None = None


def _get_browser(headed: bool = False) -> Browser:
    global _browser
    if _browser is None or (headed and not _browser.cfg.headed):
        _browser = Browser(BrowserConfig(headed=headed))
    return _browser


def _is_logged_in(b: Browser) -> bool:
    try:
        b.open(HOME_URL, wait=True, timeout=45.0)
    except AgentBrowserError:
        return False
    expr = (
        "(!!document.querySelector('[data-test-selector=\"user-menu\"]') "
        "|| document.body.innerText.includes('My account'))"
    )
    try:
        out = b.eval_js(expr)
        return out.strip().lower() == "true"
    except AgentBrowserError:
        return False


_PATH_TO_TYPE = {
    "search/stock-video": "stock-video",
    "stock-video": "stock-video",
    "sound-effects": "sound-effect",
    "music": "music",
    "motion-graphics": "motion-graphic",
    "photos": "photo",
    "search/graphic-template": "graphic-template",
    "search/presentation-template": "presentation-template",
    "search/video-template": "video-template",
    "search/3d": "3d",
    "search/font": "font",
    "search/add-on": "add-on",
}


def _decode_eval_json(raw: str) -> list[dict]:
    try:
        s = raw.strip().strip('"').replace('\\"', '"').replace("\\\\", "\\")
        return json.loads(s)
    except json.JSONDecodeError:
        return []


def _parse_search_items(b: Browser) -> list[dict]:
    expr = (
        "JSON.stringify("
        "Array.from(document.querySelectorAll("
        "'a[href*=\"/search/stock-video/\"], a[href*=\"/sound-effects/\"], "
        "a[href*=\"/music/\"], a[href*=\"/motion-graphics/\"], "
        "a[href*=\"/photos/\"], a[href*=\"/search/graphic-template/\"], "
        "a[href*=\"/search/presentation-template/\"], "
        "a[href*=\"/search/video-template/\"], a[href*=\"/search/3d/\"], "
        "a[href*=\"/search/font/\"], a[href*=\"/search/add-on/\"]'))"
        ".map(a => {"
        "  const m = a.href.match(/app\\.envato\\.com(\\/[\\w\\-\\/]+?)\\/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/);"
        "  if (!m) return null;"
        "  const card = a.closest('[class*=\"card\"], [data-test-selector], li, article, div');"
        "  const title = (card && (card.getAttribute('aria-label') || "
        "    (card.querySelector('[class*=\"title\" i]') || {}).textContent)) || '';"
        "  const author = ((card && card.querySelector('a[href*=\"/profile/\"], a[href*=\"filter.portfolio=\"]')) || {}).textContent || '';"
        "  const preview = ((card && card.querySelector('video, img, audio')) || {}).src || '';"
        "  return {pathPrefix: m[1].replace(/^\\//, ''), id: m[2], title: title.trim(), "
        "          author: author.trim(), preview, url: a.href};"
        "})"
        ".filter(Boolean))"
    )
    items = _decode_eval_json(b.eval_js(expr))
    seen: set[str] = set()
    out: list[dict] = []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        it["type"] = _PATH_TO_TYPE.get(it.pop("pathPrefix", ""), "unknown")
        out.append(it)
    return out


def _find_download_button_ref(b: Browser) -> str:
    snap = b.snapshot_text()
    m = re.search(r'button "Download[^"]*" \[ref=(@?e\d+)\]', snap)
    if not m:
        raise AgentBrowserError(
            "no Download button found on item page — are you logged in and subscribed?"
        )
    ref = m.group(1)
    if not ref.startswith("@"):
        ref = "@" + ref
    return ref


@mcp.tool(
    description=(
        "Check whether the Envato browser session is currently signed in. "
        "Returns {logged_in: bool, current_url: str}. Use before any search "
        "or download — if false, call `envato_login` first."
    )
)
def envato_session_status() -> dict:
    b = _get_browser()
    return {"logged_in": _is_logged_in(b), "current_url": b.url()}


@mcp.tool(
    description=(
        "Open a headed Chrome window so the user can sign in to Envato "
        "(elements.envato.com) interactively. The session and cookies are "
        "persisted to ~/.envato-mcp/profile and reused on later calls. "
        "Returns instructions for the user."
    )
)
def envato_login() -> dict:
    b = _get_browser(headed=True)
    b.open(SIGN_IN_URL, wait=True, timeout=60.0)
    return {
        "action": "browser opened",
        "instructions": (
            "A Chrome window has opened to elements.envato.com/sign-in. Sign "
            "in with your Envato (or Google) account. Once you reach the "
            "Envato home page, the session is saved automatically. Call "
            "`envato_session_status` after signing in to confirm."
        ),
    }


@mcp.tool(
    description=(
        "Search Envato Stock for items matching `query`. `item_type` is one "
        "of: stock-video, sound-effect, music, motion-graphic, photo, "
        "graphic-template, presentation-template, video-template, 3d, font, "
        "add-on (default: stock-video). Returns up to `max_results` items, "
        "each with id (UUID), type, title, author, preview-asset URL, and "
        "page URL."
    )
)
def envato_search(
    query: Annotated[str, Field(description="search keywords in English")],
    item_type: Annotated[
        str,
        Field(description=f"one of: {', '.join(KNOWN_ITEM_TYPES)}"),
    ] = "stock-video",
    max_results: Annotated[
        int,
        Field(description="maximum items to return", ge=1, le=60),
    ] = 12,
) -> dict:
    b = _get_browser()
    url = search_url(query, item_type=item_type)
    b.open(url, wait=True, timeout=60.0)
    items = _parse_search_items(b)
    return {
        "query": query,
        "item_type": item_type,
        "url": url,
        "count": len(items[:max_results]),
        "items": items[:max_results],
    }


@mcp.tool(
    description=(
        "Open an Envato item by UUID and return metadata visible on the "
        "detail page — title, description, tags, and (if visible) the "
        "download size. Useful for verifying the right item before calling "
        "`envato_download`."
    )
)
def envato_get_item(
    item_id: Annotated[str, Field(description="Envato item UUID")],
    item_type: Annotated[
        str, Field(description="one of stock-video/sound-effect/..."),
    ] = "stock-video",
) -> dict:
    b = _get_browser()
    url = item_url(item_id, item_type=item_type)
    b.open(url, wait=True, timeout=60.0)
    expr = (
        "JSON.stringify({"
        "title: document.title,"
        "tags: Array.from(document.querySelectorAll('a[href*=\"/search\"]'))"
        ".map(a => a.textContent.trim()).filter(Boolean).slice(0,40),"
        "description: ((document.querySelector('meta[name=\"description\"]') "
        "|| {}).content) || ''"
        "})"
    )
    raw = b.eval_js(expr).strip().strip('"').replace('\\"', '"').replace("\\\\", "\\")
    try:
        meta = json.loads(raw)
    except json.JSONDecodeError:
        meta = {}
    snap = b.snapshot_text()
    size_m = re.search(r'button "Download ([\w\.\s]+)"', snap)
    return {
        "id": item_id,
        "type": item_type,
        "url": url,
        "title": meta.get("title", ""),
        "description": meta.get("description", ""),
        "tags": meta.get("tags", []),
        "download_size": size_m.group(1).strip() if size_m else None,
        "downloadable": size_m is not None,
    }


@mcp.tool(
    description=(
        "Download an Envato item by UUID to a local directory. Triggers the "
        "Download button as if a human subscriber clicked it. Envato "
        "delivers a ZIP; if `extract=True` (default), the ZIP is unpacked "
        "and removed. Returns the list of local file paths."
    )
)
def envato_download(
    item_id: Annotated[str, Field(description="Envato item UUID")],
    out_dir: Annotated[str, Field(description="local directory to save into")],
    item_type: Annotated[
        str, Field(description="one of stock-video/sound-effect/..."),
    ] = "stock-video",
    extract: Annotated[
        bool, Field(description="unzip the delivered ZIP and remove the ZIP"),
    ] = True,
    timeout_seconds: Annotated[
        float, Field(description="max time to wait for the download", ge=10.0, le=900.0),
    ] = 300.0,
) -> dict:
    b = _get_browser()
    url = item_url(item_id, item_type=item_type)
    b.open(url, wait=True, timeout=60.0)
    ref = _find_download_button_ref(b)
    b.click_ref(ref)
    zip_path = b.wait_download_complete(timeout_s=timeout_seconds)
    out = Path(os.path.expanduser(out_dir))
    out.mkdir(parents=True, exist_ok=True)
    final_path = out / zip_path.name
    zip_path.replace(final_path)
    files = [str(final_path)]
    if extract and final_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(final_path, "r") as zf:
            zf.extractall(out)
            files = [str(out / name) for name in zf.namelist()]
        final_path.unlink(missing_ok=True)
    return {"id": item_id, "type": item_type, "files": files, "count": len(files)}


@mcp.tool(
    description=(
        "List the most recent items the signed-in account has downloaded "
        "from Envato. Useful for cross-checking that an asset is already "
        "present locally before re-downloading. Returns id, type, title, "
        "author, page URL for each."
    )
)
def envato_recent_downloads(
    limit: Annotated[
        int,
        Field(description="maximum entries to return", ge=1, le=200),
    ] = 30,
) -> dict:
    b = _get_browser()
    b.open(DOWNLOADS_URL, wait=True, timeout=60.0)
    expr = (
        "JSON.stringify("
        "Array.from(document.querySelectorAll("
        "'a[href*=\"/stock-video/\"], a[href*=\"/sound-effects/\"], "
        "a[href*=\"/music/\"], a[href*=\"/motion-graphics/\"], "
        "a[href*=\"/photos/\"]'))"
        ".map(a => {"
        "  const m = a.href.match(/app\\.envato\\.com\\/([\\w\\-]+)\\/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/);"
        "  if (!m) return null;"
        "  const card = a.closest('div, li, article');"
        "  const text = (card && card.textContent.trim()) || '';"
        "  const author = ((card && card.querySelector('a[href*=\"filter.portfolio=\"]')) "
        "    || {}).textContent || '';"
        "  return {pathPrefix: m[1], id: m[2], text: text.slice(0,200), "
        "          author: author.trim(), url: a.href};"
        "})"
        ".filter(Boolean))"
    )
    items = _decode_eval_json(b.eval_js(expr))
    seen: set[str] = set()
    out: list[dict] = []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        prefix = it.pop("pathPrefix", "")
        item_type = _PATH_TO_TYPE.get(prefix, "unknown")
        # text typically looks like "0:15 • Burj KhalifaVegastock" — split out
        # the duration token if present and strip the author suffix.
        text = it.pop("text", "")
        title = text
        if " • " in text:
            _, _, after = text.partition(" • ")
            title = after
        author = it.get("author", "")
        if author and title.endswith(author):
            title = title[: -len(author)]
        out.append(
            {
                "id": it["id"],
                "type": item_type,
                "title": title.strip(),
                "author": author,
                "url": it["url"],
            }
        )
        if len(out) >= limit:
            break
    return {"count": len(out), "items": out}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
