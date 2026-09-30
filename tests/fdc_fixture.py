"""A small, fictional financial-data-collector warehouse for the fdc connector's tests.

The tables and views are the subset of the collector's schema the connector reads, copied from its migrations
(financial-data-collector: src/financial_data_collector/migrations/0001_init.sql, 0002_views.sql and
0003_derived.sql and 0006_connections.sql), so the connector meets the same shapes. The accounts, symbols and numbers are made up.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

# name -> statement, in creation order (the views need their tables first)
SCHEMA = {
    "schema_version": "CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)",
    # 0001_init.sql
    "accounts": """CREATE TABLE accounts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  label         TEXT NOT NULL UNIQUE,
  slug          TEXT NOT NULL DEFAULT 'other',
  institution   TEXT NOT NULL DEFAULT 'unknown',
  account_type  TEXT NOT NULL DEFAULT 'other',
  first_seen    TEXT NOT NULL,
  external_key  TEXT,
  origin        TEXT NOT NULL DEFAULT 'file',
  kind_confirmed INTEGER NOT NULL DEFAULT 1,
  credit_limit  REAL,
  rate_pct      REAL,
  flows         TEXT NOT NULL DEFAULT 'transactions'
)""",
    "securities": """CREATE TABLE securities (
  symbol          TEXT PRIMARY KEY,
  description     TEXT,
  asset_type      TEXT NOT NULL DEFAULT 'unknown',
  cik             TEXT,
  sec_name        TEXT,
  first_seen      TEXT NOT NULL,
  last_sec_fetch  TEXT,
  price_source    TEXT
)""",
    "position_snapshots": """CREATE TABLE position_snapshots (
  as_of_date        TEXT NOT NULL,
  account_id        INTEGER NOT NULL REFERENCES accounts(id),
  symbol            TEXT NOT NULL REFERENCES securities(symbol),
  quantity          REAL NOT NULL,
  price             REAL,
  market_value      REAL,
  cost_basis_total  REAL,
  avg_cost          REAL,
  unrealized_pnl    REAL,
  source            TEXT NOT NULL,
  source_fetched_at TEXT,
  PRIMARY KEY (as_of_date, account_id, symbol)
)""",
    "cash_balances": """CREATE TABLE cash_balances (
  as_of_date  TEXT NOT NULL,
  account_id  INTEGER NOT NULL REFERENCES accounts(id),
  currency    TEXT NOT NULL DEFAULT 'USD',
  amount      REAL NOT NULL,
  available   REAL,
  source      TEXT NOT NULL,
  PRIMARY KEY (as_of_date, account_id, currency)
)""",
    "transactions": """CREATE TABLE transactions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id      INTEGER NOT NULL REFERENCES accounts(id),
  trade_date      TEXT NOT NULL,
  settlement_date TEXT,
  type            TEXT NOT NULL,
  symbol          TEXT,
  units           REAL,
  price           REAL,
  amount          REAL,
  fee             REAL,
  description     TEXT NOT NULL DEFAULT '',
  source          TEXT NOT NULL,
  dedupe_key      TEXT NOT NULL UNIQUE
)""",
    "prices": """CREATE TABLE prices (
  symbol        TEXT NOT NULL,
  date          TEXT NOT NULL,
  close         REAL NOT NULL,
  adj_close     REAL NOT NULL,
  dividend      REAL NOT NULL DEFAULT 0,
  split_factor  REAL NOT NULL DEFAULT 1,
  source        TEXT NOT NULL,
  PRIMARY KEY (symbol, date)
)""",
    "sync_runs": """CREATE TABLE sync_runs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id        TEXT NOT NULL,
  step          TEXT NOT NULL,
  started_at    TEXT NOT NULL,
  finished_at   TEXT NOT NULL,
  status        TEXT NOT NULL,
  rows_written  INTEGER NOT NULL DEFAULT 0,
  message       TEXT NOT NULL DEFAULT ''
)""",
    # 0006_connections.sql
    "connections": """CREATE TABLE connections (
  name           TEXT PRIMARY KEY,
  key_ref        TEXT NOT NULL,
  created_at     TEXT NOT NULL,
  removed_at     TEXT,
  last_fetch_at  TEXT,
  last_ok_at     TEXT,
  last_error     TEXT NOT NULL DEFAULT ''
)""",
    # 0003_derived.sql
    "holdings_daily": """CREATE TABLE holdings_daily (
  as_of_date    TEXT NOT NULL,
  account_id    INTEGER NOT NULL REFERENCES accounts(id),
  symbol        TEXT NOT NULL,
  units         REAL NOT NULL,
  close         REAL,
  market_value  REAL,
  basis         TEXT NOT NULL,
  PRIMARY KEY (as_of_date, account_id, symbol)
)""",
    "cash_daily": """CREATE TABLE cash_daily (
  as_of_date  TEXT NOT NULL,
  account_id  INTEGER NOT NULL REFERENCES accounts(id),
  amount      REAL NOT NULL,
  basis       TEXT NOT NULL,
  PRIMARY KEY (as_of_date, account_id)
)""",
    # 0002_views.sql
    "positions_latest": """CREATE VIEW positions_latest AS
SELECT p.as_of_date, a.label AS account, a.institution, a.account_type,
       p.symbol, s.description, s.asset_type,
       p.quantity, p.price, p.market_value, p.cost_basis_total, p.avg_cost, p.unrealized_pnl, p.source
FROM position_snapshots p
JOIN accounts a ON a.id = p.account_id
JOIN securities s ON s.symbol = p.symbol
WHERE p.as_of_date = (SELECT MAX(p2.as_of_date) FROM position_snapshots p2 WHERE p2.account_id = p.account_id)""",
    "account_values_daily": """CREATE VIEW account_values_daily AS
WITH h AS (SELECT as_of_date, account_id, SUM(market_value) AS holdings_value FROM position_snapshots GROUP BY 1, 2),
     c AS (SELECT as_of_date, account_id, SUM(amount) AS cash FROM cash_balances GROUP BY 1, 2),
     d AS (SELECT as_of_date, account_id FROM h UNION SELECT as_of_date, account_id FROM c)
SELECT d.as_of_date, a.label AS account, a.institution, a.account_type,
       COALESCE(h.holdings_value, 0) AS holdings_value,
       COALESCE(c.cash, 0) AS cash,
       COALESCE(h.holdings_value, 0) + COALESCE(c.cash, 0) AS total
FROM d
JOIN accounts a ON a.id = d.account_id
LEFT JOIN h ON h.as_of_date = d.as_of_date AND h.account_id = d.account_id
LEFT JOIN c ON c.as_of_date = d.as_of_date AND c.account_id = d.account_id""",
}

Day = dt.date | str


def _iso(day: Day) -> str:
    return day if isinstance(day, str) else day.isoformat()


class Warehouse:
    """A fictional warehouse under construction: each method adds rows, `close()` returns the file's path."""

    def __init__(self, path: Path, *, version: int = 6, without: tuple[str, ...] = (), wal: bool = False) -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        if wal:
            self.conn.execute("PRAGMA journal_mode=WAL")  # how the collector opens its own warehouse
        self.conn.executescript(";\n".join(sql for name, sql in SCHEMA.items() if name not in without) + ";")
        if "schema_version" not in without:
            self.conn.executemany("INSERT INTO schema_version VALUES (?, '2026-09-01T00:00:00Z')",
                                  [(v,) for v in range(1, version + 1)])
        self._tx = 0

    def account(self, label: str, institution: str = "fidelity", account_type: str = "brokerage", *,
                flows: str = "transactions", credit_limit: float | None = None, rate_pct: float | None = None,
                origin: str = "file") -> int:
        cur = self.conn.execute(
            "INSERT INTO accounts (label, institution, account_type, first_seen, flows, credit_limit, rate_pct, origin) "
            "VALUES (?, ?, ?, '2026-01-02', ?, ?, ?, ?)",
            (label, institution, account_type, flows, credit_limit, rate_pct, origin))
        return int(cur.lastrowid)

    def snapshot(self, account_id: int, day: Day, positions=(), cash: float | None = None,
                 available: float | None = None) -> None:
        """A broker snapshot: positions as (symbol, description, quantity, price, market_value, cost_basis_total);
        `available` is a card's remaining credit as the bank reported it."""
        for symbol, description, quantity, price, value, cost in positions:
            self.conn.execute("INSERT OR IGNORE INTO securities (symbol, description, first_seen) "
                              "VALUES (?, ?, '2026-01-02')", (symbol, description))
            self.conn.execute("INSERT INTO position_snapshots (as_of_date, account_id, symbol, quantity, price, "
                              "market_value, cost_basis_total, source) VALUES (?, ?, ?, ?, ?, ?, ?, 'fixture')",
                              (_iso(day), account_id, symbol, quantity, price, value, cost))
        if cash is not None:
            self.conn.execute("INSERT INTO cash_balances (as_of_date, account_id, amount, available, source) "
                              "VALUES (?, ?, ?, ?, 'fixture')", (_iso(day), account_id, cash, available))

    def day(self, account_id: int, day: Day, holdings: dict[str, float | None], cash: float | None = None) -> None:
        """One replayed day: each symbol's market value (None when its close is unknown) and the cash."""
        for symbol, value in holdings.items():
            self.conn.execute("INSERT INTO holdings_daily VALUES (?, ?, ?, 1, ?, ?, 'reconstructed')",
                              (_iso(day), account_id, symbol, value, value))
        if cash is not None:
            self.conn.execute("INSERT INTO cash_daily VALUES (?, ?, ?, 'reconstructed')", (_iso(day), account_id, cash))

    def flow(self, account_id: int, day: Day, kind: str, amount: float | None) -> None:
        self._tx += 1
        self.conn.execute("INSERT INTO transactions (account_id, trade_date, type, amount, source, dedupe_key) "
                          "VALUES (?, ?, ?, ?, 'fixture', ?)", (account_id, _iso(day), kind, amount, f"k{self._tx}"))

    def prices(self, symbol: str, closes: dict[Day, float]) -> None:
        self.conn.executemany("INSERT INTO prices (symbol, date, close, adj_close, source) VALUES (?, ?, ?, ?, 'x')",
                              [(symbol, _iso(d), v, v) for d, v in closes.items()])

    def run(self, step: str, status: str, finished_at: str) -> None:
        self.conn.execute("INSERT INTO sync_runs (run_id, step, started_at, finished_at, status) VALUES "
                          "('r', ?, ?, ?, ?)", (step, finished_at, finished_at, status))

    def close(self) -> Path:
        self.conn.commit()
        self.conn.close()
        return self.path


def d(day: int) -> dt.date:
    """A day in September 2026: d(25) is Friday the 25th."""
    return dt.date(2026, 9, day)


def household(folder: Path, name: str = "warehouse.db", **options) -> Path:
    """Alex's fictional household, Wed 16 to Fri 25 September 2026.

    - Alex Roth IRA: replayed history (holdings + cash) every weekday, flows of every kind, and a snapshot on
      Thu 24 that the newer history point outranks.
    - Alex Brokerage: a snapshot on Fri 25 that outranks the history point of the same day; one position without a
      market value, one without a price.
    - Alex Trading: a snapshot only, with a margin debit (negative cash).
    - Alex Crypto: replayed history only.
    - Alex Old 401k: closed; its last snapshot holds nothing and no cash.
    """
    w = Warehouse(folder / name, **options)
    roth = w.account("Alex Roth IRA", "fidelity", "roth_ira")
    brokerage = w.account("Alex Brokerage", "fidelity", "brokerage")
    trading = w.account("Alex Trading", "webull", "brokerage")
    crypto = w.account("Alex Crypto", "coinbase", "crypto")
    old = w.account("Alex Old 401k", "fidelity", "401k")

    roth_days = {16: 7950.0, 17: 8000.0, 18: 8050.0, 21: 8600.0, 22: 8420.0, 23: 8330.0, 24: 8650.0, 25: 8700.0}
    for day, total in roth_days.items():
        w.day(roth, d(day), {"SPY": total - 2150.0, "AGG": 2000.0}, cash=150.0)
    w.flow(roth, d(15), "contribution", 100.0)  # before the first point: lands on Wed 16
    w.flow(roth, d(19), "contribution", 500.0)  # a Saturday deposit: lands on Monday
    w.flow(roth, d(22), "withdrawal", 200.0)  # a withdrawal is always money out, whatever its sign
    w.flow(roth, d(23), "contribution", -100.0)  # a reversed contribution
    w.flow(roth, d(24), "transfer", 300.0)
    w.flow(roth, d(24), "transfer", None)  # shares moved in, no cash amount
    w.flow(roth, d(24), "dividend", 12.34)  # growth, not a flow
    w.flow(roth, d(25), "withdrawal", -50.0)
    w.flow(roth, d(26), "contribution", 1000.0)  # after the last point: dropped
    w.snapshot(roth, d(24), [("SPY", "S&P 500 index fund", 10.0, 600.0, 6000.0, 5000.0),
                             ("AGG", "Bond index fund", 20.0, 100.0, 2000.0, 2100.0)], cash=150.0)

    w.day(brokerage, d(24), {"SPY": 3900.0, "MSFT": 400.0}, cash=100.0)
    w.day(brokerage, d(25), {"SPY": 3950.0, "MSFT": 400.0}, cash=100.0)
    w.snapshot(brokerage, d(25), [("SPY", "S&P 500 index fund", 5.0, 600.0, 3000.0, 2500.0),
                                  ("MSFT", "Microsoft", 2.0, None, 1000.0, None),  # no price: 1000 / 2
                                  ("DIS", "Walt Disney", 3.0, 100.0, None, 290.0)],  # no market value: left out
               cash=500.0)

    w.snapshot(trading, d(25), [("AAPL", "Apple", 3.0, 250.0, 750.0, 700.0)], cash=-200.0)

    for day, total in {23: 300.0, 24: 310.0, 25: 320.0}.items():
        w.day(crypto, d(day), {"BTC": total})

    w.snapshot(old, d(21), [], cash=0.0)

    w.prices("SPY", {d(14): 590.0, d(15): 592.0, d(16): 595.0, d(17): 597.0, d(18): 596.0, d(21): 598.0,
                     d(22): 601.0, d(23): 599.0, d(24): 600.0, d(25): 603.0})
    w.prices("AGG", {d(24): 100.0})
    w.run("ingest", "ok", "2026-09-25T12:00:00Z")
    w.run("derive", "ok", "2026-09-25T12:05:00Z")
    w.run("derive", "error", "2026-09-25T20:00:00Z")
    w.run("export", "ok", "2026-09-25T20:01:00Z")
    return w.close()
