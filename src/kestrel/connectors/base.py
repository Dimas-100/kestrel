"""What every connector provides."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..contract import Snapshot

DETAIL_LIMIT = 200  # how much of a source's error its row keeps: a sidebar line, not a log


class Connector(Protocol):
    source_id: str

    def snapshot(self, now: datetime) -> Snapshot:
        """Everything this source knows, as of `now`. Read-only: a connector never writes to its source."""
        ...


class ConnectorUnavailable(Exception):
    """The profile names a connector kind this version of kestrel does not have."""


class ConnectorError(Exception):
    """A source that can't be read, worded so a person can fix it. It shows as that source's error."""
