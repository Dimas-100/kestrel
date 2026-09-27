"""A small fictional feed payload for the feed connector's tests: a trading desk with two books on one strategy.

Every name and number here is made up.
"""

from __future__ import annotations

import json
from pathlib import Path

MADE = "2026-09-25T21:05:00+00:00"  # three minutes before the tests' NOW


def desk(**changes) -> dict:
    """The payload as JSON-ready data; keyword arguments replace its top-level fields."""
    payload = {
        "contract_version": "1",
        "generated_at": MADE,
        "sources": [{"id": "desk-broker", "label": "Broker link", "kind": "api", "status": "ok"}],
        "books": [
            {"id": "swing-real", "name": "Swing", "money": "real", "strategy_id": "swing", "status": "running",
             "started": "2026-03-02", "value": 2150.0, "slots_total": 4},
            {"id": "swing-paper", "name": "Swing (paper)", "money": "paper", "strategy_id": "swing",
             "status": "running", "started": "2026-01-05", "value": 10480.0, "slots_total": 6},
        ],
        "book_history": [
            {"id": "swing-real", "points": [{"date": "2026-09-24", "value": 2131.4},
                                            {"date": "2026-09-25", "value": 2150.0}]},
        ],
        "positions": [
            {"book_id": "swing-real", "symbol": "KO", "quantity": 5, "entry_price": 61.2, "last_price": 62.05,
             "stop_price": 56.3, "opened": "2026-09-22"},
        ],
        "trades": [
            {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "closed": "2026-09-11",
             "entry_price": 158.4, "exit_price": 162.1, "quantity": 3, "pnl": 11.1, "return_pct": 2.34,
             "exit_reason": "closed above its 5-day average"},
            {"book_id": "swing-paper", "symbol": "JNJ", "opened": "2026-09-14", "closed": "2026-09-18",
             "entry_price": 171.0, "exit_price": 168.2, "quantity": 10, "pnl": -28.0, "return_pct": -1.64,
             "exit_reason": "time stop"},
        ],
        "strategies": [{"id": "swing", "name": "Swing pullbacks",
                        "summary": "Buy a dip in an uptrend; sell the bounce."}],
        "runs": [{"time": "2026-09-25T19:56:00+00:00", "label": "Evening run", "book_id": "swing-real",
                  "status": "done"}],
        "alerts": [{"level": "warning", "title": "KO is near its stop", "detail": "8.2% of room left",
                    "link": "/strategies/swing"}],
        "benchmark": {"symbol": "SPY", "label": "S&P 500", "points": [{"date": "2026-09-24", "value": 655.1},
                                                                    {"date": "2026-09-25", "value": 657.3}]},
    }
    payload.update(changes)
    return payload


def feed_file(folder: Path, payload: dict | None = None, name: str = "feed.json") -> Path:
    """The payload saved as a feed file (the desk's payload when none is given)."""
    path = folder / name
    path.write_text(json.dumps(desk() if payload is None else payload), encoding="utf-8")
    return path
