"""The Plan page, computed from one Snapshot: is each account on plan, does every thesis still hold, and how are the
goals coming along?"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from ..contract import Account, Goal, Snapshot, Target, Thesis, ValuePoint
from ..profile import Profile
from ._base import View
from .home import CATEGORY_LABELS, Attention

Status = Literal["on", "over", "under", "unknown"]
HEALTH_RANK = {"alert": 0, "watch": 1, "ok": 2, "none": 3}


GapUnit = Literal["money", "pts", "x"]


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
    gap: float | None  # in gap_unit's unit; None when unknown or when gap_unit is None
    gap_unit: GapUnit | None  # what `gap` is measured in — never inferred from where the row is grouped
    gap_text: str  # "under the low end" / "over the high end" / "on plan" / "" when unknown
    note: str


class AccountTargets(View):
    account_id: str
    name: str  # the account's name, or its bare id when no source ever sent it (see `known`)
    known: bool  # False: this account_id names no account any source sent — kestrel can't link to it
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
    current: float | None  # None when a scoped account isn't in any source (see `missing_accounts`)
    target: float
    progress_pct: float | None  # 0..100, capped; None when current is unknown
    by: dt.date | None
    months_left: int | None  # None without `by`, or once `by` is overdue and not reached
    monthly_needed: float | None  # None without `by`, once reached, overdue, or current is unknown
    reached: bool
    missing_accounts: list[str] = []  # account id(s) this goal names that no source sent; current is None when set


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


def _held_sum(t: Target, account: Account, holdings) -> float:
    return sum(h.value for h in holdings if h.account_id == account.id and h.symbol in t.symbols)


REL_TOL = 1e-9  # for a comparison with no money to round to the cent: an actual the feed measured, not one kestrel
# divided, so a relative floating-point tolerance is enough to absorb representation noise without hiding a real gap


def _edge_decide(low: float | None, high: float | None, exact_value: float, has_money: bool,
                 account_value: float | None) -> tuple[Status, float]:
    """Status and gap decided from the SIGN of the gap itself, at cent precision when there is money to convert
    against — never from a raw `exact_value < low` / `> high` comparison, which can misfire at an exact band edge
    (570 / 1000 * 100 can compute as 56.99999999999999, strictly less than 57). Without money to convert against,
    the same test runs on the points/ratio gap with a small relative tolerance, since that value came straight from
    a feed rather than from kestrel's own division."""
    def gap_to(edge: float) -> float:
        points = edge - exact_value
        return round(points / 100 * account_value, 2) if has_money else points

    low_gap = None if low is None else gap_to(low)
    high_gap = None if high is None else gap_to(high)
    if has_money:
        under = low_gap is not None and low_gap > 0
        over = high_gap is not None and high_gap < 0
    else:
        tol = REL_TOL * max(abs(exact_value), 1.0)
        under = low_gap is not None and low_gap > tol
        over = high_gap is not None and high_gap < -tol
    if under:
        return "under", low_gap
    if over:
        return "over", high_gap
    return "on", 0.0


def _percent_row_fields(t: Target, account: Account | None,
                        holdings) -> tuple[float | None, Status, float | None, GapUnit | None]:
    """(actual for display, status, gap, gap_unit) for a "%" target.

    The feed's own `actual` is trusted at face value (it already measured the share). Otherwise kestrel computes it
    from holdings — but only when the target names symbols to sum, and the account is known, has a positive value,
    and has reported at least one holding; anything else is unknown, never a fake 0%. Status and the gap are both
    decided on the UNROUNDED ratio (see `_edge_decide`) — `actual` is rounded only for display, after status and gap
    are already settled.
    """
    has_money = account is not None and account.value > 0
    if t.actual is not None:
        exact_value = t.actual
    elif (not t.symbols or account is None or account.value <= 0
          or not any(h.account_id == account.id for h in holdings)):
        return None, "unknown", None, None
    else:
        exact_value = _held_sum(t, account, holdings) / account.value * 100
    status, gap = _edge_decide(t.low, t.high, exact_value, has_money, account.value if has_money else None)
    gap_unit: GapUnit = "money" if has_money else "pts"
    return round(exact_value, 2), status, round(gap, 2), gap_unit


def _gap_text(status: Status) -> str:
    return {"unknown": "", "on": "on plan", "under": "under the low end", "over": "over the high end"}[status]


def _target_row(t: Target, account: Account | None, holdings) -> TargetRow:
    if t.unit == "x":
        if t.actual is None:
            actual, status, gap, gap_unit = None, "unknown", None, None
        else:
            status, raw_gap = _edge_decide(t.low, t.high, t.actual, False, None)
            actual, gap, gap_unit = round(t.actual, 2), round(raw_gap, 2), "x"
    else:
        actual, status, gap, gap_unit = _percent_row_fields(t, account, holdings)
    return TargetRow(id=t.id, label=t.label, symbols=list(t.symbols), unit=t.unit, target=t.target, low=t.low,
                     high=t.high, actual=actual, status=status, gap=gap, gap_unit=gap_unit,
                     gap_text=_gap_text(status), note=t.note)


def _sort_key(row: TargetRow) -> tuple[bool, str]:
    return (row.status not in ("over", "under"), row.label)


def target_rows(snapshot: Snapshot) -> list[tuple[Target, TargetRow, Account | None]]:
    """Every target evaluated, with the account it resolved to (None: genuinely unscoped by design — `account_id`
    is None — or `account_id` names no account any source sent)."""
    by_id = {a.id: a for a in snapshot.accounts}
    out = []
    for t in snapshot.targets:
        account = by_id.get(t.account_id) if t.account_id is not None else None
        out.append((t, _target_row(t, account, snapshot.holdings), account))
    return out


def plan_targets(snapshot: Snapshot) -> tuple[list[AccountTargets], list[TargetRow]]:
    """Targets grouped by the account they scope to (known accounts largest first, then any account_id no source
    sent, by id, each off-plan rows first then by label); `unscoped` is only for `account_id: None` (by design, "for
    every account") — never a dangling reference, which stays grouped under its own id instead."""
    by_id = {a.id: a for a in snapshot.accounts}
    grouped: dict[str, list[TargetRow]] = {}
    unscoped: list[TargetRow] = []
    for t, row, account in target_rows(snapshot):
        if t.account_id is None:
            unscoped.append(row)
        else:
            grouped.setdefault(t.account_id, []).append(row)
    known_ids = [aid for aid in grouped if aid in by_id]
    unknown_ids = sorted(aid for aid in grouped if aid not in by_id)
    known = [AccountTargets(account_id=aid, name=by_id[aid].name, known=True, rows=sorted(grouped[aid], key=_sort_key))
            for aid in sorted(known_ids, key=lambda aid: (-by_id[aid].value, by_id[aid].name))]
    unknown = [AccountTargets(account_id=aid, name=aid, known=False, rows=sorted(grouped[aid], key=_sort_key))
              for aid in unknown_ids]
    return [*known, *unknown], sorted(unscoped, key=_sort_key)


def _thesis_row(t: Thesis, accounts: dict[str, Account], holdings, today: dt.date) -> ThesisRow:
    held_holdings = [h for h in holdings if h.symbol == t.symbol]
    # "held in" reflects reality (the holdings), never the feed's own declared account_ids, which can go stale
    names = sorted({accounts[h.account_id].name for h in held_holdings if h.account_id in accounts})
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


def _signed(a: Account) -> float:
    """An account's contribution to a sum of "what's really yours": owned adds, owed (a debt account) subtracts."""
    return -a.value if a.category == "debt" else a.value


def _goal_scope(g: Goal, accounts: list[Account]) -> tuple[list[str], str, list[str]]:
    """The accounts a goal is measured against, a short description of that scope, and any account id(s) it names
    that no source sent (when non-empty, the first two are incomplete: the caller must treat `current` as unknown,
    never partially summing what it does have)."""
    by_id = {a.id: a for a in accounts}
    if g.account_id is not None:
        a = by_id.get(g.account_id)
        if a is None:
            return [], g.account_id, [g.account_id]
        return [g.account_id], a.name, []
    if g.account_ids:
        missing = [i for i in g.account_ids if i not in by_id]
        if missing:
            names = sorted(by_id[i].name for i in g.account_ids if i in by_id)
            return [], (", ".join(names) if names else "those accounts"), missing
        return list(g.account_ids), ", ".join(sorted(by_id[i].name for i in g.account_ids)), []
    if g.category is not None:
        return [a.id for a in accounts if a.category == g.category], f"{CATEGORY_LABELS[g.category]} accounts", []
    return [a.id for a in accounts], "Net worth", []


def _goal_deposits(scope_ids: list[str], history: dict[str, list[ValuePoint]], start: dt.date, today: dt.date) -> float:
    return round(sum(p.net_flow for aid in scope_ids for p in history.get(aid, []) if start <= p.date <= today), 2)


def _months_between(start: dt.date, by: dt.date) -> int | None:
    """Whole months from `start` up to and including `by` (0 or more), decided by the day-of-month rule applied to
    the day AFTER `by` — so a fixed `by` counts down by exactly one each time `start` crosses a monthly boundary,
    never up then back down around the 1st (an earlier version special-cased `start` landing on the 1st, which
    made a fixed `by` look one month further away on the 1st than on the 2nd — not monotonic as time passes).

    None when `by` is `date.max` (9999-12-31, a common "no real deadline" placeholder): the day-after trick above
    would overflow past the last date Python can represent. A goal with such a `by` still shows its progress; it
    just has no monthly pace to reach it by."""
    try:
        end = by + dt.timedelta(days=1)
    except OverflowError:
        return None
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)


def _goal_pace_start(g: Goal, today: dt.date) -> dt.date:
    """Where "months left" and the monthly pace are measured from: for a deposits goal whose tracking year hasn't
    opened yet, 1 January of `by`'s year (there is nothing to pace before the window opens); otherwise today."""
    if g.measure == "deposits" and g.by is not None:
        return max(today, dt.date(g.by.year, 1, 1))
    return today


def _goal_row(g: Goal, accounts: list[Account], history: dict[str, list[ValuePoint]], today: dt.date) -> GoalRow:
    by_id = {a.id: a for a in accounts}
    scope_ids, scope_text, missing = _goal_scope(g, accounts)
    if missing:
        return GoalRow(id=g.id, label=g.label, scope_text=scope_text, current=None, target=g.target,
                       progress_pct=None, by=g.by, months_left=None, monthly_needed=None, reached=False,
                       missing_accounts=missing)
    if g.measure == "deposits":
        start = dt.date((g.by or today).year, 1, 1)
        current = _goal_deposits(scope_ids, history, start, today)
    else:
        # signed: a debt account in the scope reduces the total, never adds to it (owed isn't owned)
        current = round(sum(_signed(by_id[i]) for i in scope_ids), 2)
    reached = current >= g.target
    # a reached goal is 100% regardless of the target (a debt-payoff goal's target is often 0, which the
    # division-by-zero guard below would otherwise show as 0% even once the debt is actually paid off)
    progress = 100.0 if reached else \
        (0.0 if g.target <= 0 else round(min(100.0, max(0.0, current / g.target * 100)), 1))
    overdue = g.by is not None and g.by < today and not reached
    months_left = None if g.by is None or overdue else _months_between(_goal_pace_start(g, today), g.by)
    monthly_needed = None if reached or months_left is None else round((g.target - current) / max(1, months_left), 2)
    return GoalRow(id=g.id, label=g.label, scope_text=scope_text, current=current, target=g.target,
                  progress_pct=progress, by=g.by, months_left=months_left, monthly_needed=monthly_needed,
                  reached=reached, missing_accounts=[])


def target_attention(snapshot: Snapshot) -> list[Attention]:
    """Off-plan targets as Needs-you items. An account no source sent is still named, by its bare id, so the item
    is actionable rather than silently vague."""
    items = []
    for t, row, account in target_rows(snapshot):
        if row.status not in ("over", "under"):
            continue
        word = "over" if row.status == "over" else "under"
        where = account.name if account is not None else t.account_id
        title = f"{row.label} is {word} plan in {where}" if where else f"{row.label} is {word} plan"
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
