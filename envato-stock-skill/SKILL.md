---
name: envato-stock
description: |
  Search and download stock video, sound effects, music, and motion graphics
  from an Envato subscription via the envato-mcp MCP server. Use this skill
  whenever the user wants premium 4K stock footage, broadcast-quality SFX,
  royalty-free BGM, or polished motion-graphics templates for video
  production — especially when free libraries (Pexels, Pixabay) have weak
  coverage on the topic. Triggers on phrases like "Envato で素材を探して",
  "stock video が欲しい", "premium SFX", "high-quality drone footage",
  "motion graphic template", or building shorts / long-form videos where
  visual quality matters.
---

# Envato Stock

This skill guides an agent through the right way to use the **`envato-mcp`**
MCP server to source assets from a logged-in Envato subscription.

The MCP exposes five tools:

- `envato_session_status` — am I signed in?
- `envato_login` — open Chrome so the user can sign in (one-time)
- `envato_search` — return a list of items matching a query
- `envato_get_item` — open one item's detail page
- `envato_download` — click Download and save the file

## When to reach for Envato vs free alternatives

Use Envato when:

- The topic is **niche, premium, or commercially-shot** — landmark drone
  shots (Burj Khalifa, Shanghai), polished business/corporate B-roll,
  high-end medical/lab footage, specific cars or products
- You need **broadcast-quality SFX or BGM** (Pixabay free sounds are
  limited and often watermarked-feeling)
- You need a **motion-graphic overlay** (transitions, lower thirds, intros)
  — Envato has whole categories for this; Pexels has none
- You're building **multiple shorts on the same topic** and want unique
  clips per video (Pexels search exhausts quickly)

Fall back to free libraries (Pexels / Pixabay) when the topic is broad and
well-covered (nature, generic city b-roll, basic kitchen / food) — saves a
download credit.

## First-time setup

Before any search or download, confirm the session:

```
envato_session_status() → {logged_in: bool, current_url: str}
```

If `logged_in: false`, call `envato_login()`. The MCP opens a headed Chrome
window pointed at `elements.envato.com/sign-in`. **Tell the user to sign in
in that window** — do not try to fill credentials yourself. The session
persists to `~/.envato-mcp/profile`, so this is a one-time cost per machine.

After sign-in, re-check with `envato_session_status` and confirm
`logged_in: true` before proceeding.

## Searching well

Envato indexes by **English keywords** even if the user asked in another
language. Translate the intent before searching.

### Query craft

- **Be specific**: `"Burj Khalifa drone aerial"` beats `"tall building"`
- **Include shot / style cues**: `cinematic`, `slow motion`, `top down`,
  `time lapse`, `4K`, `60fps`, `drone`, `handheld`
- **Subject + setting**: `"Tokyo Shibuya crossing night neon"` is far
  better than `"city night"`
- **One concept per query** — if you need both "old film projector" and
  "vintage TV static", run two searches and pick the best from each

### Item types

| `item_type` | Use for |
|-------------|---------|
| `stock-video` (default) | b-roll, cinematic shots, all narrative footage |
| `sound-effect` | impacts, whooshes, animal cries, ambient one-shots |
| `music` | full BGM tracks, intro / outro stings |
| `motion-graphic` | lower thirds, animated titles, overlays, transitions |
| `photo` | static images (nanobanana usually beats stock photos for custom shots) |
| `graphic-template`, `presentation-template`, `video-template`, `3d`, `font`, `add-on` | rarely needed for video shorts; available if asked |

### Pacing the search

A reasonable single search returns **8–12 items**. The default
`max_results=12` is usually right. Don't request 60 — you'll just have to
filter them down yourself.

## Choosing the right clip

After `envato_search`, inspect the returned `items` list. Each entry has:

- `id` — UUID; pass to `envato_download`
- `title` — display title
- `author` — creator (good for crediting)
- `preview` — preview image / video URL
- `url` — Envato detail page

For high-stakes picks (the hero clip of a short), call `envato_get_item`
on the top 1–2 candidates to see the full description and tags. For
routine picks, just take `items[0]`.

## Downloading

```
envato_download(
  item_id=<UUID>,
  out_dir=<local path>,
  item_type=<same as the search>,
  extract=True,   # default; unzips the delivered ZIP
)
```

- `out_dir` must be writable; the MCP creates it if missing.
- Envato delivers a **ZIP** containing the asset (a `.mov` / `.mp4` for
  video, `.mp3` / `.wav` for audio, `.aep` / `.mogrt` for motion graphics,
  etc.). With `extract=True` the ZIP is unpacked and removed; the tool
  returns the list of extracted file paths.
- **A typical 4K video download is 100–300 MB**; budget a few seconds at
  good bandwidth.

## Attribution

Envato Stock items do **not** require on-screen attribution for most
licenses, but it is good practice to log the source. The MCP returns the
item id and author — write them to a local manifest (e.g.
`<project>/.envato_credits.json`) so you can reference them later if the
project ships somewhere that does require credits.

## Failure modes you'll hit

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `envato_session_status` returns `logged_in: false` after the user signed in | They may have signed in via Google in an iframe that the home-page detector misses | Re-call `envato_login`; ask them to navigate to the Envato home page, then re-check |
| `envato_search` returns empty `items` | Query too obscure, or Envato changed result-card markup | Try synonyms; if still empty, screenshot via `agent-browser` and inspect |
| `envato_download` errors "no Download button found" | Not logged in, or item requires a license tier your plan doesn't cover | Call `envato_session_status`; if true, check the Envato UI for license restrictions |
| Download hangs > 5 min | Very large 4K master file, or Envato is slow | Bump `timeout_seconds=600`; consider lower-res item if available |

## Caching

The MCP does not cache results. To avoid re-downloading the same asset
across runs, your project should check whether the local file exists
before calling `envato_download` again. A common pattern:

```
out_dir/
  <project>/<topic>/<item_id>.mov   ← stable filename keyed on item_id
  <project>/<topic>/.manifest.json  ← {item_id: {title, author, downloaded_at}}
```

## What this skill won't do

- **Bulk scraping** — Envato's ToS prohibits automated scraping. This
  skill is for legitimate subscriber downloads, one at a time.
- **License registration** — if your subscription requires per-project
  license registration, do it in the Envato UI.
- **License upgrades** (e.g. extended commercial licenses) — handle in UI.
- **Account creation / sign-up** — only `envato_login` for an existing
  subscriber account.

## Quick reference

```
status = envato_session_status()
if not status.logged_in: envato_login()   # one-time

results = envato_search(query="cheetah running savanna 4K",
                        item_type="stock-video",
                        max_results=10)
pick = results.items[0]

files = envato_download(item_id=pick.id,
                        out_dir="./assets/cheetah",
                        item_type="stock-video",
                        extract=True)
# → files: ["./assets/cheetah/MAIN_10.mov"]
```
