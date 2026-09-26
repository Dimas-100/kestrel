"""What every connector provides."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..contract import Snapshot


class Connector(Protocol):
    source_id: str

    def snapshot(self, now: datetime) -> Snapshot:
        """Everything this source knows, as of `now`. Read-only: a connector never writes to its source."""
        ...


class ConnectorUnavailable(Exception):
    """The profile names a connector kind this version of kestrel does not have."""
