"""Reads a trading-rails install's paper account and run log: kestrel never imports `trading_rails` (the read-only
guard forbids it) — it only reads the two files its own `PaperBroker` (`paper.py`) and runner (`runner.py`) write,
by their own keys, in `folder` (`paper.json` and `runs.jsonl`).

trading-rails' state never persists a "last price" (it is always priced fresh, live, against its own bar source,
which kestrel has no access to and must not import): the best a read-only reader can do is the price of that
symbol's most recent fill since its current position opened, falling back to the position's average cost when the
fills don't reach that far (a position the state file was seeded with, say). Likewise the run log names no strategy
of its own today; a future log that sends one (top-level `strategy`, on its newest row) is honoured, and otherwise
the book is simply "rails" — the generic stand-in name, not a guess.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from ..contract import Book, Position, Run, Series, Snapshot, Source, Strategy, Trade, ValuePoint
from .base import ConnectorError

STATE_FILE = "paper.json"
LOG_FILE = "runs.jsonl"
BOOK_ID = "rails-paper"
DEFAULT_STRATEGY_ID = "rails"
DEFAULT_STRATEGY_NAME = "trading-rails"
# trading-rails never rotates runs.jsonl, and this connector re-reads it on every request (there is no cache here,
# unlike a feed's command): read only its most recent bytes, so a read never grows with the log's whole history.
LOG_TAIL_LIMIT = 2 * 1024 * 1024


def _parse_time(text: str) -> datetime:
    value = datetime.fromisoformat(text)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _row_date(row: dict) -> date:
    return _parse_time(row["ts"]).date()


def _read_state(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConnectorError(f"trading-rails' {path.name} couldn't be read ({exc.strerror or exc})") from None
    try:
        state = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"trading-rails' {path.name} isn't valid JSON (line {exc.lineno}: {exc.msg})") from None
    if not isinstance(state, dict):
        raise ConnectorError(f"trading-rails' {path.name} isn't a paper account (expected an object)")
    return state


def _read_runs(path: Path) -> list[dict]:
    """The run log's most recent rows, oldest of those first: at most its last LOG_TAIL_LIMIT bytes, since
    trading-rails never rotates this file and it is re-read on every request. A missing log is no runs, not an
    error — the file may not exist yet. An unreadable or non-UTF-8 file is a readable ConnectorError, the same as
    paper.json's. A torn line — the first line after a seek into the middle of the file, almost certainly cut in
    half, or a last line the file may still be mid-write on — is skipped, not fatal."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise ConnectorError(f"trading-rails' {path.name} couldn't be read ({exc.strerror or exc})") from None
    try:
        with path.open("rb") as fh:
            if size > LOG_TAIL_LIMIT:
                fh.seek(size - LOG_TAIL_LIMIT)
            raw = fh.read()
    except FileNotFoundError:
        return []  # removed between the stat above and this read: no runs, not an error
    except OSError as exc:
        raise ConnectorError(f"trading-rails' {path.name} couldn't be read ({exc.strerror or exc})") from None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ConnectorError(f"trading-rails' {path.name} isn't UTF-8 text") from None
    lines = text.splitlines()
    if size > LOG_TAIL_LIMIT and lines:
        lines = lines[1:]  # almost certainly a partial line, cut in half by the seek
    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and isinstance(row.get("ts"), str):
            rows.append(row)
    return sorted(rows, key=lambda r: r["ts"])


def _stop_price(symbol: str, open_orders: dict) -> float | None:
    for order in open_orders.values():
        if not isinstance(order, dict):
            continue
        if (order.get("symbol") == symbol and order.get("side") == "SELL"
                and order.get("order_type") in ("STOP", "STOP_LIMIT") and order.get("stop_price") is not None):
            try:
                return float(order["stop_price"])
            except (TypeError, ValueError):
                continue
    return None


def _valid_fill(fill: object) -> bool:
    if not (isinstance(fill, dict) and isinstance(fill.get("symbol"), str) and fill.get("side") in ("BUY", "SELL")):
        return False
    try:
        float(fill["quantity"])
        float(fill["price"])
        _parse_time(fill["ts"])
    except (KeyError, TypeError, ValueError):
        return False
    return True


EPSILON = 1e-9  # a quantity this small is none: fills are floats, and a position sold down to it is flat


@dataclass
class _Held:
    """One symbol's position as its fills build it, the way trading-rails' PaperBroker keeps it: a buy moves the
    average cost, a sell leaves it where it is, and a position sold to nothing starts afresh with the next buy."""

    quantity: float = 0.0
    avg_cost: float = 0.0
    commission_per_share: float = 0.0  # buy commissions carried with the shares, averaged the same way
    opened: str | None = None  # the ts of the buy that opened the current position
    last_price: float | None = None  # the newest fill's price since then


def _replay(fills: list[dict]) -> tuple[dict[str, _Held], list[Trade]]:
    """Every valid fill in time order: each symbol's current position, and the trades its sells closed.

    Sells are matched at the AVERAGE COST held at the time of the sale - trading-rails keeps `avg_cost` unchanged on
    a sell - so the entry price is that average and the P/L is (sell - average) x quantity, less the sell's own
    commission and the sold shares' part of the buy commissions: the realized P/L then adds up to what trading-rails'
    cash says. A trade opens on the buy that opened its position (after the symbol was last flat). A sell with no
    position to match (the fill history doesn't reach back far enough) is skipped, never invented an entry for; one
    larger than the position closes only what was held. trading-rails' own fills carry no commission today
    (`PaperBroker._apply` charges its `CostModel.commission` but never persists it per fill); a `commission` key, if
    a future format ever sends one, is netted out of the P/L."""
    held: dict[str, _Held] = {}
    trades: list[Trade] = []
    valid = sorted((f for f in fills if _valid_fill(f)), key=lambda f: _parse_time(f["ts"]))
    for fill in valid:
        symbol, quantity, price = fill["symbol"], float(fill["quantity"]), float(fill["price"])
        try:
            commission = float(fill.get("commission") or 0.0)
        except (TypeError, ValueError):
            commission = 0.0
        position = held.setdefault(symbol, _Held())
        if fill["side"] == "BUY":
            if quantity <= EPSILON:
                continue
            if position.quantity <= EPSILON:  # flat: this buy opens a new position
                position = held[symbol] = _Held(opened=fill["ts"])
            total = position.quantity + quantity
            position.avg_cost = (position.quantity * position.avg_cost + quantity * price) / total
            position.commission_per_share = (position.quantity * position.commission_per_share + commission) / total
            position.quantity = total
            position.last_price = price
            continue
        if position.quantity <= EPSILON or quantity <= EPSILON:
            continue  # an unmatched sell: skipped, not invented
        matched = min(quantity, position.quantity)
        cost = matched * position.avg_cost
        commissions = commission * (matched / quantity) + position.commission_per_share * matched
        pnl = (price - position.avg_cost) * matched - commissions
        trades.append(Trade(
            book_id=BOOK_ID, symbol=symbol, opened=_parse_time(position.opened).date(),
            closed=_parse_time(fill["ts"]).date(), entry_price=round(position.avg_cost, 4), exit_price=price,
            quantity=matched, pnl=round(pnl, 2), return_pct=round(pnl / cost * 100, 2) if cost else 0.0,
        ))
        position.quantity -= matched
        position.last_price = price
        if position.quantity <= EPSILON:
            held[symbol] = _Held()  # flat: nothing of it carries into the next position
    return held, sorted(trades, key=lambda t: (t.closed, t.opened, t.symbol))


def _positions(state: dict, held: dict[str, _Held], fallback_date: date) -> list[Position]:
    """The state file's positions. Each opens on the buy that started it and is priced at its newest fill since
    then; one the fills don't explain (they end flat, or never reach it) opens on `fallback_date` at its own average
    cost - never a date or a price from a position that has since closed."""
    open_orders = state.get("open_orders") or {}
    positions = state.get("positions") or {}
    out = []
    for symbol, pos in positions.items():
        if not isinstance(pos, dict):
            continue
        try:
            quantity = float(pos.get("quantity", 0))
        except (TypeError, ValueError):
            continue
        if quantity <= 0:
            continue
        try:
            avg_cost = float(pos.get("avg_cost", 0.0))
        except (TypeError, ValueError):
            avg_cost = 0.0
        replayed = held.get(symbol)
        known = (replayed is not None and replayed.quantity > EPSILON and replayed.opened is not None
                 and replayed.last_price is not None)
        out.append(Position(book_id=BOOK_ID, symbol=symbol, quantity=quantity, entry_price=avg_cost,
                            last_price=replayed.last_price if known else avg_cost,
                            stop_price=_stop_price(symbol, open_orders),
                            opened=_parse_time(replayed.opened).date() if known else fallback_date))
    return sorted(out, key=lambda p: p.symbol)


def _value(state: dict, positions: list[Position]) -> float:
    try:
        cash = float(state.get("cash", 0.0))
    except (TypeError, ValueError):
        cash = 0.0
    return round(cash + sum(p.quantity * p.last_price for p in positions), 2)


def _equity_points(rows: list[dict]) -> list[ValuePoint]:
    """Points from a run log that reports its equity after a cycle (a top-level `equity`, or one inside `extra`):
    today's runner sends neither, so this is ordinarily empty — a hook for a future log, not a guess at one."""
    points: dict[date, float] = {}
    for row in rows:
        extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
        raw = row.get("equity", extra.get("equity"))
        if raw is None:
            continue
        try:
            points[_row_date(row)] = float(raw)
        except (TypeError, ValueError):
            continue
    return [ValuePoint(date=d, value=v) for d, v in sorted(points.items())]


def _run_detail(group: list[dict], failed: bool) -> str:
    if failed:
        return next((r.get("detail", "") for r in group if r.get("status") == "error"), "")
    acted = [r for r in group if r.get("step") != "signal" and r.get("status") not in ("ok", "skipped")]
    if not acted:
        return "no changes"
    return ", ".join(f"{r.get('symbol', '?')} {r.get('step', '?')} {r.get('status', '?')}" for r in acted)


def _runs(rows: list[dict]) -> list[Run]:
    by_ts: dict[str, list[dict]] = {}
    for row in rows:
        by_ts.setdefault(row["ts"], []).append(row)
    out = []
    for ts, group in by_ts.items():
        failed = any(r.get("status") == "error" for r in group)
        out.append(Run(time=_parse_time(ts), label="trading-rails cycle", book_id=BOOK_ID,
                       status="failed" if failed else "done", detail=_run_detail(group, failed)))
    return sorted(out, key=lambda r: r.time)


def _strategy_of(latest: dict | None) -> tuple[str, str]:
    """(strategy_id, name): the newest run's own `strategy`, when a future log sends one, else the generic stand-in
    — today's run log names no strategy of its own."""
    if latest is not None:
        extra = latest.get("extra") if isinstance(latest.get("extra"), dict) else {}
        name = latest.get("strategy") or extra.get("strategy")
        if name:
            return str(name), str(name)
    return DEFAULT_STRATEGY_ID, DEFAULT_STRATEGY_NAME


class RailsConnector:
    """Reads one trading-rails install: its paper account (`paper.json`) and run log (`runs.jsonl`), in `folder`."""

    def __init__(self, source_id: str, label: str, folder: Path) -> None:
        self.source_id = source_id
        self.label = label
        self.folder = folder

    def snapshot(self, now: datetime) -> Snapshot:
        if not self.folder.is_dir():
            raise ConnectorError(f"no trading-rails data at {self.folder}")
        state_path = self.folder / STATE_FILE
        if not state_path.is_file():
            raise ConnectorError(f"no {STATE_FILE} in {self.folder}: run trading-rails' paper broker first")
        state = _read_state(state_path)
        rows = _read_runs(self.folder / LOG_FILE)  # oldest first; [] when the log doesn't exist yet

        fallback_date = now.date()
        as_of = state.get("as_of")
        if isinstance(as_of, str):
            try:
                fallback_date = date.fromisoformat(as_of)
            except ValueError:
                pass
        started = _row_date(rows[0]) if rows else fallback_date

        fills = [f for f in (state.get("fills") or []) if isinstance(f, dict)]
        held, trades = _replay(fills)
        positions = _positions(state, held, started)
        strategy_id, strategy_name = _strategy_of(rows[-1] if rows else None)
        # PaperBroker.armed() is always True (it is in-memory play money, never gated): "running" is simply a fact,
        # never a guess at a status the state file doesn't record.
        book = Book(id=BOOK_ID, name=self.label, money="paper", strategy_id=strategy_id, status="running",
                   started=started, value=_value(state, positions))
        strategy = Strategy(id=strategy_id, name=strategy_name, summary="From trading-rails")

        last_success = _parse_time(rows[-1]["ts"]) if rows else None
        detail = f"{len(positions)} position{'s' if len(positions) != 1 else ''} · {len(rows)} run row" \
                 f"{'s' if len(rows) != 1 else ''}"
        source = Source(id=self.source_id, label=self.label, kind="rails", last_success=last_success,
                        status="ok" if last_success else "stale", detail=detail)

        equity = _equity_points(rows)
        return Snapshot(generated_at=now, sources=[source], books=[book], positions=positions,
                        trades=trades, strategies=[strategy], runs=_runs(rows),
                        book_history=[Series(id=BOOK_ID, points=equity)] if equity else [])
