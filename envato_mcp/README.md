# envato-mcp

MCP server that gives an AI agent access to your **Envato Stock** subscription
— search and download stock video, sound effects, music, motion graphics
through a logged-in browser session.

> **No official API.** Envato does not publish an API for the Elements / Stock
> subscription. This server drives the same browser UI a human subscriber
> uses, via [`agent-browser`](https://github.com/anthropics/agent-browser).
> It does not bypass any access control — it just clicks the Download button
> on items your subscription already entitles you to.

## Tools

| Tool | Purpose |
|------|---------|
| `envato_session_status` | Check whether the persistent browser session is signed in |
| `envato_login` | Open a headed Chrome window so you can sign in once (cookies persist) |
| `envato_search` | Search by query + item type, return list of items |
| `envato_get_item` | Open an item's detail page and return metadata |
| `envato_download` | Click Download and save the ZIP (optionally unpack) |

## Prerequisites

- Python ≥ 3.10
- Node ≥ 18 (for the `agent-browser` CLI)
- An active Envato subscription
- `agent-browser` installed and on PATH:
  ```bash
  npm i -g agent-browser
  agent-browser install   # downloads Chromium
  ```

## Install

```bash
pip install -e .
```

## Run standalone (stdio)

```bash
envato-mcp
```

## Register with Claude Code

Add to `~/.claude/mcp_servers.json` (or your project's `.mcp.json`):

```jsonc
{
  "mcpServers": {
    "envato": {
      "command": "envato-mcp",
      "transport": { "type": "stdio" }
    }
  }
}
```

## First-time login

The session is persisted to `~/.envato-mcp/profile`. Sign in once:

```
You:    "Log in to Envato"
Claude: <calls envato_login → headed Chrome opens>
You:    <signs in with Envato or Google in the Chrome window>
You:    "Check status"
Claude: <calls envato_session_status → {logged_in: true, ...}>
```

After this, headless calls work without re-prompting.

## Example usage

```
You:    "Find 5 stock video clips of Burj Khalifa drone shots and download
        the first one to ./assets/"
Claude: <envato_search query="Burj Khalifa drone" item_type="stock-video"
         max_results=5>
        <envato_download item_id=<first id> out_dir="./assets/" extract=True>
```

## Configuration (env vars)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVATO_MCP_SESSION` | `envato` | agent-browser session name |
| `ENVATO_MCP_PROFILE` | `~/.envato-mcp/profile` | persistent Chrome profile dir |
| `ENVATO_MCP_DOWNLOADS` | `~/.envato-mcp/downloads` | temp dir for incoming files |

## License compliance

Each download you trigger is governed by the **Envato Stock license** tied
to your subscription. This MCP does not register downloads on your behalf —
if your plan requires per-project license registration, do it in the Envato
UI after the fact. Refer to your subscription terms for commercial-use limits.

## License

MIT — see top-level [LICENSE](../LICENSE).
