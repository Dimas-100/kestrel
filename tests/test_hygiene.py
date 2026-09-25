"""Public-repo hygiene.

kestrel is public. Everything personal (names, account numbers, balances, holdings, paths and keys) reaches the
app at runtime through a gitignored profile and the user's own data sources, never through a tracked file. These
tests fail the build when a tracked file carries a machine path, a private host or a personal email address, and
when a file that must stay private is not ignored. The patterns are generic on purpose: this file is public too.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

FORBIDDEN = re.compile(
    r"("
    r"[A-Za-z]:[\\/]+Users[\\/]"  # a Windows user-profile path
    r"|/Users/[^/\s]+/"  # a macOS home directory
    r"|/home/[^/\s]+/"  # a Linux home directory
    r"|AppData[\\/]"  # Windows app data
    r"|OneDrive[\\/]"  # a synced personal folder
    r"|project-warehouse"  # the author's local folder layout
    r"|webullbroker\.com"  # broker-internal hosts
    r")",
    re.IGNORECASE,
)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ALLOWED_EMAIL = re.compile(r"@(example\.(com|org|net)|users\.noreply\.github\.com)$", re.IGNORECASE)

MUST_BE_IGNORED = [
    "profile.toml",
    ".env",
    ".env.local",
    "data/warehouse.db",
    "web/dist/index.html",
    "web/node_modules/react/index.js",
    "secrets.json",
]


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [ROOT / p for p in out.decode("utf-8").split("\0") if p]


def text_of(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return None  # binary or deleted-but-staged: nothing to scan


def test_no_machine_paths_or_private_hosts():
    offenders = []
    for path in tracked_files():
        if path.resolve() == SELF:
            continue
        text = text_of(path)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if FORBIDDEN.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:120]}")
    assert not offenders, "machine paths or private hosts in tracked files:\n" + "\n".join(offenders)


def test_no_personal_email_addresses():
    offenders = []
    for path in tracked_files():
        if path.resolve() == SELF:
            continue
        text = text_of(path)
        if text is None:
            continue
        for match in EMAIL.finditer(text):
            if not ALLOWED_EMAIL.search(match.group(0)):
                offenders.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
    assert not offenders, "personal email addresses in tracked files:\n" + "\n".join(offenders)


def test_private_files_are_gitignored():
    not_ignored = [
        p for p in MUST_BE_IGNORED
        if subprocess.run(["git", "check-ignore", "-q", p], cwd=ROOT).returncode != 0
    ]
    assert not not_ignored, f"these must be gitignored: {not_ignored}"


def test_patterns_catch_what_they_should():
    for bad in [
        r"C:\Users\someone\Documents\x.txt",
        "c:/Users/someone/x",
        "/Users/someone/code",
        "/home/someone/code",
        r"%LOCALAPPDATA%\..\AppData\Local\thing",
        "api.uat.webullbroker.com",
    ]:
        assert FORBIDDEN.search(bad), bad
    for fine in ["../financial-data-collector/data/warehouse.db", "http://127.0.0.1:8000/api/feed", "docs/specs/x.md"]:
        assert not FORBIDDEN.search(fine), fine
    assert not ALLOWED_EMAIL.search("someone@gmail.com")
    assert ALLOWED_EMAIL.search("alex@example.com")
