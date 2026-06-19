"""Thin wrapper around the agent-browser CLI.

A single agent-browser daemon owns the browser session. We address it via a
named session (default: "envato") backed by a persistent Chrome profile dir.

We shell out instead of using a Python CDP client because agent-browser
already implements snapshot/refs/click/download/etc., and the binary is the
user-installed surface they trust.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SESSION = "envato"
DEFAULT_PROFILE = Path(os.path.expanduser("~/.envato-mcp/profile"))
DEFAULT_DOWNLOAD = Path(os.path.expanduser("~/.envato-mcp/downloads"))


class AgentBrowserError(RuntimeError):
    pass


@dataclass
class BrowserConfig:
    session: str = DEFAULT_SESSION
    profile: Path = DEFAULT_PROFILE
    download_path: Path = DEFAULT_DOWNLOAD
    headed: bool = False

    def base_args(self) -> list[str]:
        args = [
            "--session-name",
            self.session,
            "--profile",
            str(self.profile),
            "--download-path",
            str(self.download_path),
        ]
        if self.headed:
            args.append("--headed")
        return args


def _agent_browser_path() -> str:
    p = shutil.which("agent-browser")
    if not p:
        raise AgentBrowserError(
            "agent-browser CLI not found on PATH. "
            "Install with: npm i -g agent-browser  (or brew install agent-browser)"
        )
    return p


class Browser:
    def __init__(self, cfg: BrowserConfig | None = None):
        self.cfg = cfg or BrowserConfig()
        self.cfg.profile.mkdir(parents=True, exist_ok=True)
        self.cfg.download_path.mkdir(parents=True, exist_ok=True)
        self.bin = _agent_browser_path()

    def run(self, *cmd: str, timeout: float = 60.0, stdin: str | None = None) -> str:
        full = [self.bin, *self.cfg.base_args(), *cmd]
        proc = subprocess.run(
            full,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            raise AgentBrowserError(
                f"agent-browser {' '.join(shlex.quote(c) for c in cmd)!r} failed "
                f"(rc={proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
            )
        return proc.stdout

    def open(self, url: str, *, wait: bool = True, timeout: float = 60.0) -> None:
        self.run("open", url, timeout=timeout)
        if wait:
            self.run("wait", "--load", "networkidle", timeout=timeout)

    def url(self) -> str:
        return self.run("get", "url").strip()

    def close(self) -> None:
        try:
            self.run("close", timeout=15.0)
        except AgentBrowserError:
            pass

    def snapshot_text(self) -> str:
        return self.run("snapshot", "-i", timeout=45.0)

    def click_ref(self, ref: str) -> None:
        self.run("click", ref)

    def click_text(self, text: str) -> None:
        self.run("find", "text", text, "click")

    def screenshot(self, path: Path) -> Path:
        self.run("screenshot", str(path))
        return path

    def eval_js(self, expr: str) -> str:
        return self.run("eval", "--stdin", stdin=expr).strip()

    def list_downloaded_files(self, since_seconds: float = 600.0) -> list[Path]:
        cutoff = time.time() - since_seconds
        out: list[Path] = []
        for f in self.cfg.download_path.iterdir():
            if f.is_file() and f.stat().st_mtime > cutoff and not f.name.endswith(".crdownload"):
                out.append(f)
        return sorted(out, key=lambda p: p.stat().st_mtime)

    def wait_download_complete(self, *, timeout_s: float = 180.0, poll_s: float = 1.0) -> Path:
        """Wait until a new .crdownload finishes; return the resolved file path."""
        start = time.time()
        snapshot_before = {f.name for f in self.cfg.download_path.iterdir() if f.is_file()}
        while time.time() - start < timeout_s:
            time.sleep(poll_s)
            files = list(self.cfg.download_path.iterdir())
            partials = [f for f in files if f.name.endswith(".crdownload")]
            new_complete = [
                f for f in files
                if f.is_file()
                and not f.name.endswith(".crdownload")
                and f.name not in snapshot_before
            ]
            if new_complete and not partials:
                return max(new_complete, key=lambda p: p.stat().st_mtime)
        raise AgentBrowserError(f"download did not complete in {timeout_s:.0f}s")
