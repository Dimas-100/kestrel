"""financial-data-collector's SQLite warehouse, read-only: accounts, their values and where the data came from.

The warehouse is opened read-only twice over (mode=ro, then query_only) and closed after every snapshot. Nothing
here ever writes to it.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from ..contract import Account, Category, Snapshot, Source
from .base import ConnectorError

TIMEOUT = 5.0  # seconds to wait for a warehouse another process is writing
MIN_VERSION = 3  # holdings_daily and cash_daily arrived in the collector's migration 3
REQUIRED = ("accounts", "transactions", "prices", "sync_runs", "holdings_daily", "cash_daily", "positions_latest",
            "account_values_daily")
CLOSE = time(16, 0, tzinfo=ZoneInfo("America/New_York"))  # a day's values are the US close
UPDATE = "update financial-data-collector and run `fdc sync`"

INSTITUTIONS = {"fidelity": "Fidelity", "webull": "Webull", "unknown": ""}
TYPES = {"roth_ira": "Roth IRA", "traditional_ira": "Traditional IRA", "brokerage": "Brokerage", "crypto": "Crypto",
         "401k": "401(k)", "403b": "403(b)", "457b": "457(b)", "ira": "IRA", "rollover_ira": "Rollover IRA",
         "sep_ira": "SEP IRA", "simple_ira": "SIMPLE IRA", "hsa": "HSA"}
LONG_TERM = {"roth_ira", "traditional_ira", "ira", "rollover_ira", "sep_ira", "simple_ira", "401k", "403b", "457b",
             "hsa", "pension", "brokerage"}
CASH = {"checking", "savings", "cash", "money_market"}


def slug(label: str) -> str:
    """A label as an id: "Alex Roth IRA" is alex-roth-ira. Accents fold to their letter first ("É" is e); a label
    with nothing left is "account"."""
    folded = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-") or "account"


def account_ids(labels: list[str]) -> list[str]:
    """Each label's slug, in order; a clash gets -2, -3 (the collector's own slug column isn't unique)."""
    taken: set[str] = set()
    ids = []
    for label in labels:
        base = candidate = slug(label)
        n = 2
        while candidate in taken:
            candidate, n = f"{base}-{n}", n + 1
        taken.add(candidate)
        ids.append(candidate)
    return ids


def _words(code: str) -> str:
    return code.replace("_", " ").strip().title()


def institution_text(code: str) -> str:
    return INSTITUTIONS.get(code, _words(code))


def type_text(code: str) -> str:
    return TYPES.get(code, _words(code))


def category_of(account_type: str) -> Category:
    return "long_term" if account_type in LONG_TERM else "cash" if account_type in CASH else "other"


def _close(day: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), CLOSE)


def _utc(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@contextmanager
def connect(path: Path, timeout: float = TIMEOUT) -> Iterator[sqlite3.Connection]:
    """The warehouse, read-only: opened with mode=ro, then query_only on top. Always closed."""
    if not path.is_file():
        raise ConnectorError(f"no warehouse at {path}")  # checked first, so SQLite never creates one
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=timeout)
    try:
        conn.execute("PRAGMA query_only = 1")
        yield conn
    finally:
        conn.close()


def check_schema(conn: sqlite3.Connection, path: Path) -> None:
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
    if "schema_version" not in names:
        raise ConnectorError(f"{path} is not a financial-data-collector warehouse (it has no schema_version table)")
    version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
    if version < MIN_VERSION:
        raise ConnectorError(f"this warehouse is at schema version {version} and kestrel needs {MIN_VERSION}: {UPDATE}")
    missing = [name for name in REQUIRED if name not in names]
    if missing:
        raise ConnectorError(f"this warehouse is missing {', '.join(missing)}: {UPDATE}")


def last_success(conn: sqlite3.Connection) -> datetime | None:
    """When the warehouse last finished a good `derive` step (the one that rebuilds the daily history), else any
    good step; None when nothing has ever gone right."""
    query = "SELECT MAX(finished_at) FROM sync_runs WHERE status = 'ok'"
    derived = conn.execute(query + " AND step = 'derive'").fetchone()[0]
    return _utc(derived or conn.execute(query).fetchone()[0])


class FdcConnector:
    """Reads one warehouse. `categories` maps an account id or exact label to a category."""

    def __init__(self, source_id: str, label: str, path: Path, categories: dict[str, str] | None = None,
                 timeout: float = TIMEOUT) -> None:
        self.source_id = source_id
        self.label = label
        self.path = path
        self.categories = dict(categories or {})
        self.timeout = timeout

    def snapshot(self, now: datetime) -> Snapshot:
        try:
            with connect(self.path, self.timeout) as conn:
                check_schema(conn, self.path)
                accounts = self._accounts(conn, now)
                synced = last_success(conn)
        except sqlite3.Error as exc:
            raise ConnectorError(f"the warehouse couldn't be read: {exc}") from None
        notes = [f"{len(accounts)} account{'' if len(accounts) == 1 else 's'}"]
        unmatched = sorted(set(self.categories) - {a.id for a in accounts} - {a.name for a in accounts})
        if unmatched:
            notes.append(f"no account matches categories {', '.join(repr(k) for k in unmatched)}")
        source = Source(id=self.source_id, label=self.label, kind="fdc", last_success=synced,
                        status="ok" if synced else "stale", detail=" · ".join(notes))
        return Snapshot(generated_at=now, sources=[source], accounts=accounts)

    def _category(self, account_id: str, label: str, account_type: str) -> Category:
        chosen = self.categories.get(account_id) or self.categories.get(label)
        return cast(Category, chosen) if chosen else category_of(account_type)

    def _accounts(self, conn: sqlite3.Connection, now: datetime) -> list[Account]:
        rows = conn.execute("SELECT label, institution, account_type FROM accounts ORDER BY id").fetchall()
        # the latest daily value of each account; SQLite takes the bare columns from the row MAX() picked
        latest = {label: (day, total, cash) for label, day, total, cash in conn.execute(
            "SELECT account, MAX(as_of_date), total, cash FROM account_values_daily GROUP BY account")}
        accounts = []
        for account_id, (label, institution, kind) in zip(account_ids([r[0] for r in rows]), rows):
            day, total, cash = latest.get(label, (None, 0.0, 0.0))
            accounts.append(Account(
                id=account_id, name=label, institution=institution_text(institution), account_type=type_text(kind),
                category=self._category(account_id, label, kind), value=round(total, 2), cash=round(cash, 2),
                as_of=_close(day) if day else now,
            ))
        return accounts
