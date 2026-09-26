"""Connectors turn a profile's sources into one Snapshot."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..contract import Snapshot, Source, merge
from ..profile import Profile, SourceCfg
from .base import Connector, ConnectorError, ConnectorUnavailable
from .demo import DemoConnector
from .fdc import FdcConnector

__all__ = ["Connector", "ConnectorError", "ConnectorUnavailable", "build", "collect"]


def build(cfg: SourceCfg, profile: Profile) -> Connector:
    if cfg.kind == "demo":
        return DemoConnector(cfg.id, tz=profile.tz, seed=int(getattr(cfg, "seed", 340)))
    if cfg.kind == "fdc":
        path = getattr(cfg, "path", None)
        if not isinstance(path, str) or not path:
            raise ConnectorError("an fdc source needs a path to the warehouse, "
                                 'e.g. path = "../financial-data-collector/data/warehouse.db"')
        return FdcConnector(cfg.id, cfg.label or cfg.id, Path(path), categories=getattr(cfg, "categories", None),
                            benchmark=profile.benchmark)
    raise ConnectorUnavailable(f"connector kind {cfg.kind!r} is not available in this version of kestrel")


def _with_staleness(sources: list[Source], cfg: SourceCfg, now: datetime) -> list[Source]:
    out = []
    for s in sources:
        old = s.last_success is not None and now - s.last_success > cfg.stale_delta
        out.append(s.model_copy(update={"status": "stale"}) if s.status == "ok" and old else s)
    return out


def collect(profile: Profile, now: datetime) -> Snapshot:
    """Ask every source for its snapshot. One broken source shows as an error; it never takes the page down."""
    parts: list[Snapshot] = []
    failed: list[Source] = []
    for cfg in profile.sources:
        try:
            part = build(cfg, profile).snapshot(now)
        except Exception as exc:  # noqa: BLE001 - any connector failure becomes a visible source error
            failed.append(Source(id=cfg.id, label=cfg.label or cfg.id, kind=cfg.kind, status="error",
                                 detail=str(exc)[:200]))
            continue
        parts.append(part.model_copy(update={"sources": _with_staleness(list(part.sources), cfg, now)}))
    snapshot = merge(parts, generated_at=now)
    return snapshot.model_copy(update={"sources": [*snapshot.sources, *failed]})
