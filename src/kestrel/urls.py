"""A URL fit to show a person, shared by the feed connector's messages and the Settings page."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def shown_url(url: str) -> str:
    """The URL with no user name or password, no query and no fragment, any of which could carry a secret. Raises
    ValueError, as urlsplit does, on an address it can't read: the caller decides what to show instead."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.rpartition("@")[2], parts.path, "", ""))
