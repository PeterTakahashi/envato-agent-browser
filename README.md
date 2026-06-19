# envato-agent-browser

**MCP + Claude Code skill** that gives an AI agent access to your
[Envato](https://elements.envato.com/) Stock subscription — search and
download stock video, sound effects, music, and motion graphics from a
logged-in browser session.

```
You:    "Find a 4K Burj Khalifa drone clip and save it to ./assets/"
Claude: <envato_search> → list of items
        <envato_download> → assets/MAIN_10.mov
```

## Why

Envato Stock is one of the best paid libraries for premium 4K footage,
broadcast SFX, BGM, and motion graphics. **Envato does not publish an API**
for its subscription product (Elements / Stock), so the only way to access
the assets you've paid for from automation is by driving the web UI.

This project does exactly that — using
[`agent-browser`](https://github.com/anthropics/agent-browser) under the
hood, wrapped in a clean MCP server, with a companion Claude Code skill
that tells the agent **when and how to use it well**.

## What's in this repo

| Path | What it is |
|------|------------|
| [`envato_mcp/`](envato_mcp/) | MCP server (Python, FastMCP). Exposes `envato_session_status`, `envato_login`, `envato_search`, `envato_get_item`, `envato_download`. |
| [`envato-stock-skill/`](envato-stock-skill/) | Companion skill (`SKILL.md`). Tells an agent when Envato beats free libraries, how to phrase search queries, what to do at each step. |

## Quick start

### Prerequisites

- Python ≥ 3.10
- Node ≥ 18
- An active Envato subscription
- [`agent-browser`](https://github.com/anthropics/agent-browser) installed:
  ```bash
  npm i -g agent-browser
  agent-browser install   # downloads Chromium
  ```

### Install the MCP server

```bash
cd envato_mcp
pip install -e .
```

### Register with Claude Code

```bash
mkdir -p ~/.claude
cat <<'JSON' >> ~/.claude/mcp_servers.json
{
  "mcpServers": {
    "envato": {
      "command": "envato-mcp",
      "transport": { "type": "stdio" }
    }
  }
}
JSON
```

Or per-project, add to `.mcp.json` in the project root.

### Install the skill

Copy or symlink the skill into your Claude Code skills directory:

```bash
ln -s "$PWD/envato-stock-skill" ~/.claude/skills/envato-stock
```

### First-time sign-in

The MCP keeps a persistent Chrome profile in `~/.envato-mcp/profile`.
Sign in once:

```
You:    "Sign in to Envato"
Claude: <envato_login>  # headed Chrome opens
You:    <sign in with Envato or Google in the open window>
You:    "Check status"
Claude: <envato_session_status>  → {logged_in: true}
```

Subsequent runs reuse the saved cookies.

## Example: downloading a video

```
You:    "I'm making a short about the world's tallest buildings. Find me a
        few good drone shots of Burj Khalifa and download the best one."

Claude: <envato_search query="Burj Khalifa drone aerial cinematic"
                       item_type="stock-video" max_results=8>
        → 8 items

        <envato_get_item item_id=<top> item_type="stock-video">
        → title, tags, 4K, 157 MB

        <envato_download item_id=<top> out_dir="./assets/burj"
                         item_type="stock-video" extract=true>
        → ["./assets/burj/MAIN_10.mov"]

        Got it — a 4K hyperlapse by Vegastock, saved to
        ./assets/burj/MAIN_10.mov.
```

## Status & limitations

- **No bulk scraping.** This MCP is for a logged-in subscriber making the
  same clicks they'd make by hand — it does not bypass any access control
  or Envato's terms of service.
- **No license registration / upgrades.** Anything beyond the default
  subscription license is out of scope; do it in the Envato UI.
- **Web UI breakage.** Envato can change page markup at any time. The
  search-result and Download-button selectors are encoded in
  [`envato_mcp/envato_mcp/server.py`](envato_mcp/envato_mcp/server.py);
  PRs welcome when something breaks.

## Contributing

PRs and issues welcome. Particularly useful contributions:

- selectors for `sound-effect`, `music`, `motion-graphic` result cards
  that match the same metadata level as `stock-video`
- a `envato_recent_downloads()` tool that reads the user's download history
- robust handling of license modals for items that require an upgrade

## License

[MIT](LICENSE)
