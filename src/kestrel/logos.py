"""Your own logo files, from the folder the profile names. Nothing is fetched: a missing logo is just no logo."""

from __future__ import annotations

import re
from pathlib import Path

from .profile import Profile

EXTENSIONS = (".svg", ".png", ".webp", ".jpg", ".jpeg")
KEY = re.compile(r"^[a-z0-9]{1,64}$")


def logo_files(profile: Profile) -> dict[str, Path]:
    """Each usable logo by its key (the file's name, lower case): only plain files with an image extension."""
    folder = profile.logos.folder
    if not folder:
        return {}
    try:
        entries = sorted(Path(folder).iterdir())
    except OSError:
        return {}
    found: dict[str, Path] = {}
    for entry in entries:
        key = entry.stem.lower()
        if entry.suffix.lower() in EXTENSIONS and KEY.match(key) and key not in found and entry.is_file():
            found[key] = entry
    return found
