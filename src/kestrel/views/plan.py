"""The Plan page, computed from one Snapshot: is each account on plan, does every thesis still hold, and how are the
goals coming along?"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from ..contract import Account, Goal, Snapshot, Target, Thesis, ValuePoint
from ..profile import Profile
from .home import CATEGORY_LABELS, Attention, View

Status = Literal["on", "over", "under", "unknown"]
HEALTH_RANK = {"alert": 0, "watch": 1, "ok": 2, "none": 3}


class TargetRow(View):
    id: str
    label: str
    symbols: list[str]
    unit: Literal["%", "x"]
    target: float | None
    low: float | None
    high: float | None
    actual: float | None
    status: Status
    gap: float | None  # money for a scoped "%" target, percentage points or ratio units otherwise; None when unknown
    gap_text: str  # "under the low end" / "over the high end" / "on plan" / "" when unknown
    note: str


class AccountTargets(View):
    account_id: str
    name: str
    rows: list[TargetRow]


class ThesisRow(View):
    symbol: str
    name: str
    health: Literal["ok", "watch", "alert", "none"]
    reasons: list[str]
    conviction: str
    status: str
    opened: dt.date | None
    last_reviewed: dt.date | None
    days_since_review: int | None
    held: bool
    held_value: float
    account_names: list[str]
    wrong_if: list[str]


class GoalRow(View):
    id: str
    label: str
    scope_text: str
    current: float
    target: float
    progress_pct: float  # 0..100, capped
    by: dt.date | None
    months_left: int | None
    monthly_needed: float | None  # None without `by`, or once reached
    reached: bool


class Counts(View):
    off_plan: int
    theses_alert: int
    theses_watch: int


class PlanView(View):
    as_of: dt.datetime
    accounts: list[AccountTargets]
    unscoped: list[TargetRow]
    theses: list[ThesisRow]
    goals: list[GoalRow]
    counts: Counts


def _percent_actual(t: Target, account: Account | None, holdings) -> float | None:
    if t.actual is not None:
        return t.actual
    if account is None or account.value == 0:
        return None
    return round(sum(h.value for h in holdings if h.account_id == account.id and h.symbol in t.symbols)
                / account.value * 100, 2)


def _status(actual: float | None, low: float | None, high: float | None) -> Status:
    if actual is None:
        return "unknown"
    if low is not None and actual < low:
        return "under"
    if high is not None and actual > high:
        return "over"
    return "on"


def _gap(unit: str, status: Status, actual: float | None, low: float | None, high: float | None,
        account_value: float | None) -> tuple[float | None, str]:
    """Money to the nearest band end for a "%" target with an account to convert against; otherwise percentage
    points ("%") or ratio units ("x") — kestrel can't turn a feed-sent actual into money without a denominator."""
    if status == "unknown":
        return None, ""
    if status == "on":
        return 0.0, "on plan"
    edge = low if status == "under" else high
    points = edge - actual
    value = round(points / 100 * account_value, 2) if unit == "%" and account_value else round(points, 2)
    word = "under the low end" if status == "under" else "over the high end"
    return value, word


def _target_row(t: Target, account: Account | None, holdings) -> TargetRow:
    actual = t.actual if t.unit == "x" else _percent_actual(t, account, holdings)
    status = _status(actual, t.low, t.high)
    gap, gap_text = _gap(t.unit, status, actual, t.low, t.high, account.value if account else None)
    return TargetRow(id=t.id, label=t.label, symbols=list(t.symbols), unit=t.unit, target=t.target, low=t.low,
                     high=t.high, actual=actual, status=status, gap=gap, gap_text=gap_text, note=t.note)


def _sort_key(row: TargetRow) -> tuple[bool, str]:
    return (row.status not in ("over", "under"), row.label)


def target_rows(snapshot: Snapshot) -> list[tuple[Target, TargetRow, Account | None]]:
    """Every target evaluated, with the account it resolved to (None: unscoped, or its account_id names no known
    account)."""
    by_id = {a.id: a for a in snapshot.accounts}
    out = []
    for t in snapshot.targets:
        account = by_id.get(t.account_id) if t.account_id is not None else None
        out.append((t, _target_row(t, account, snapshot.holdings), account))
    return out


def plan_targets(snapshot: Snapshot) -> tuple[list[AccountTargets], list[TargetRow]]:
    """Targets grouped by the account they scope to (largest account first, its rows off-plan first then by label),
    and the rest (no account_id, or one that names no known account) as `unscoped`."""
    by_account: dict[str, list[TargetRow]] = {}
    unscoped: list[TargetRow] = []
    for t, row, account in target_rows(snapshot):
        if account is None:
            unscoped.append(row)
        else:
            by_account.setdefault(account.id, []).append(row)
    accounts = sorted((a for a in snapshot.accounts if a.id in by_account), key=lambda a: (-a.value, a.name))
    grouped = [AccountTargets(account_id=a.id, name=a.name, rows=sorted(by_account[a.id], key=_sort_key))
              for a in accounts]
    return grouped, sorted(unscoped, key=_sort_key)


def _thesis_row(t: Thesis, accounts: dict[str, Account], holdings, today: dt.date) -> ThesisRow:
    held_holdings = [h for h in holdings if h.symbol == t.symbol]
    names = sorted({accounts[a].name for a in t.account_ids if a in accounts})
    return ThesisRow(
        symbol=t.symbol, name=t.name, health=t.health, reasons=list(t.reasons), conviction=t.conviction,
        status=t.status, opened=t.opened, last_reviewed=t.last_reviewed,
        days_since_review=(today - t.last_reviewed).days if t.last_reviewed else None,
        held=bool(held_holdings), held_value=round(sum(h.value for h in held_holdings), 2), account_names=names,
        wrong_if=list(t.wrong_if),
    )


def thesis_rows(snapshot: Snapshot, today: dt.date) -> list[ThesisRow]:
    accounts = {a.id: a for a in snapshot.accounts}
    rows = [_thesis_row(t, accounts, snapshot.holdings, today) for t in snapshot.theses]
    rows.sort(key=lambda r: (HEALTH_RANK[r.health], not r.held, r.symbol))
    return rows


def _goal_scope(g: Goal, accounts: list[Account]) -> tuple[list[str], str]:
    """The accounts a goal is measured against, and a short description of that scope."""
    by_id = {a.id: a for a in accounts}
    if g.account_id is not None:
        a = by_id.get(g.account_id)
        return ([g.account_id] if a else []), (a.name if a else g.account_id)
    if g.account_ids:
        names = sorted(by_id[i].name for i in g.account_ids if i in by_id)
        return list(g.account_ids), (", ".join(names) if names else "those accounts")
    if g.category is not None:
        return [a.id for a in accounts if a.category == g.category], f"{CATEGORY_LABELS[g.category]} accounts"
    return [a.id for a in accounts], "Net worth"


def _goal_value(g: Goal, accounts: list[Account]) -> float:
    by_id = {a.id: a for a in accounts}
    if g.account_id is not None:
        a = by_id.get(g.account_id)
        return a.value if a else 0.0
    if g.account_ids:
        return round(sum(by_id[i].value for i in g.account_ids if i in by_id), 2)
    if g.category is not None:
        return round(sum(a.value for a in accounts if a.category == g.category), 2)
    owned = sum(a.value for a in accounts if a.category != "debt")
    owed = sum(a.value for a in accounts if a.category == "debt")
    return round(owned - owed, 2)


def _goal_deposits(scope_ids: list[str], history: dict[str, list[ValuePoint]], start: dt.date, today: dt.date) -> float:
    return round(sum(p.net_flow for aid in scope_ids for p in history.get(aid, []) if start <= p.date <= today), 2)


def _months_between(today: dt.date, by: dt.date) -> int:
    """Whole months from today to `by` (0 or more): a month only counts once its day of the month has come round."""
    months = (by.year - today.year) * 12 + (by.month - today.month)
    if by.day < today.day:
        months -= 1
    return max(0, months)


def _goal_row(g: Goal, accounts: list[Account], history: dict[str, list[ValuePoint]], today: dt.date) -> GoalRow:
    scope_ids, scope_text = _goal_scope(g, accounts)
    if g.measure == "deposits":
        start = dt.date((g.by or today).year, 1, 1)
        current = _goal_deposits(scope_ids, history, start, today)
    else:
        current = _goal_value(g, accounts)
    progress = 0.0 if g.target <= 0 else round(min(100.0, max(0.0, current / g.target * 100)), 1)
    reached = current >= g.target
    months_left = _months_between(today, g.by) if g.by else None
    monthly_needed = None if reached or months_left is None else round((g.target - current) / max(1, months_left), 2)
    return GoalRow(id=g.id, label=g.label, scope_text=scope_text, current=current, target=g.target,
                  progress_pct=progress, by=g.by, months_left=months_left, monthly_needed=monthly_needed,
                  reached=reached)


def target_attention(snapshot: Snapshot) -> list[Attention]:
    """Off-plan targets as Needs-you items."""
    items = []
    for t, row, account in target_rows(snapshot):
        if row.status not in ("over", "under"):
            continue
        word = "over" if row.status == "over" else "under"
        title = f"{row.label} is {word} plan in {account.name}" if account is not None else \
            f"{row.label} is {word} plan"
        items.append(Attention(level="warning", title=title, detail=row.gap_text, link="/plan"))
    return items


def thesis_attention(snapshot: Snapshot) -> list[Attention]:
    """Theses that need a look, as Needs-you items: alert is a warning, watch a note."""
    items = []
    for t in snapshot.theses:
        if t.health not in ("alert", "watch"):
            continue
        level = "warning" if t.health == "alert" else "note"
        detail = t.reasons[0] if t.reasons else ""
        items.append(Attention(level=level, title=f"{t.symbol}: thesis needs a look", detail=detail, link="/plan"))
    return items


def plan_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> PlanView:
    today = now.astimezone(profile.tz).date()
    accounts, unscoped = plan_targets(snapshot)
    theses = thesis_rows(snapshot, today)
    history = {s.id: list(s.points) for s in snapshot.account_history}
    goals = [_goal_row(g, snapshot.accounts, history, today) for g in snapshot.goals]
    off_plan = sum(1 for a in accounts for r in a.rows if r.status in ("over", "under")) + \
        sum(1 for r in unscoped if r.status in ("over", "under"))
    return PlanView(
        as_of=now, accounts=accounts, unscoped=unscoped, theses=theses, goals=goals,
        counts=Counts(off_plan=off_plan, theses_alert=sum(1 for t in theses if t.health == "alert"),
                     theses_watch=sum(1 for t in theses if t.health == "watch")),
    )
