"""The Plan page, computed from one Snapshot: is each account on plan, does every thesis still hold, and how are the
goals coming along?"""

from __future__ import annotations

import datetime as dt
import math
from typing import Literal

from ..contract import Account, Goal, Snapshot, Target, Thesis, ValuePoint
from ..profile import Profile
from ._base import View
from .home import CATEGORY_LABELS, Attention, net_points, round_step

PASSED_ROUNDS = 8  # how many crossed round numbers the record keeps

Status = Literal["on", "over", "under", "unknown"]
Rebalance = Literal["trades", "contributions", "hold"]
HEALTH_RANK = {"alert": 0, "watch": 1, "ok": 2, "none": 3}


GapUnit = Literal["money", "pts", "x"]

# What each rebalance policy means for a target off its band, said once (spec 2026-10-08 §2)
POLICY_WHY = {
    ("trades", "under"): "The plan brings it back with a trade.",
    ("trades", "over"): "The plan brings it back with a trade.",
    ("contributions", "under"): "The plan rebalances with new money only, so the next deposits go here.",
    ("contributions", "over"): "No sale: it comes down as new money goes elsewhere.",
    ("hold", "over"): "No sale: it comes down as new money goes elsewhere.",
    ("hold", "under"): "Held and diluted by plan: under its band is a decision to revisit, not a buy.",
}


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
    rebalance: Rebalance = "trades"  # how the plan brings it back: the words for what to do follow it
    # the id of the multi-symbol row in the same account whose symbols include all of this row's (a sleeve's
    # member): the two are never summed together; None for a top-level row
    parent: str | None = None


class AccountTargets(View):
    account_id: str
    name: str  # the account's name, or its bare id when no source ever sent it (see `known`)
    known: bool  # False: this account_id names no account any source sent — kestrel can't link to it
    rows: list[TargetRow]
    # the share of the account held in no symbol any of its "%" targets names, cash included; None when kestrel
    # can't measure it (no value, or no holdings reported)
    untargeted_pct: float | None = None


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


class PacePoint(View):
    date: dt.date
    value: float


class GoalPace(View):
    """Since the window opened (1 January: of `by`'s year for a deposits goal, this year for a value goal): the
    actual each day, and the straight line from where it started to the target on `by`."""
    start: dt.date
    start_value: float
    points: list[PacePoint]  # the actual, from `start` to today
    required_now: float  # where the straight line is today
    ahead: float  # current minus required_now: above zero is ahead of the line, below it behind


class GoalRow(View):
    id: str
    label: str
    scope_text: str
    measure: Literal["value", "deposits"]  # what `current` is: a value today, or deposits since the goal's year began
    # None when a scoped account isn't in any source (see `missing_accounts`), or a deposits goal can't see every
    # scoped account's deposits (see `unknown_reason`)
    current: float | None
    target: float
    progress_pct: float | None  # 0..100, capped; None when current is unknown
    by: dt.date | None
    months_left: int | None  # None without `by`, or once `by` is overdue and not reached
    # a straight line to the target: for a value goal, before any market growth; None without `by`, once reached,
    # overdue, or current is unknown
    monthly_needed: float | None
    reached: bool
    reached_on: dt.date | None = None  # the first day the scope's value met the target, from history; None without
    overdue: bool  # `by` has passed and the goal isn't reached (a far placeholder date such as 9999-12-31 never is)
    missing_accounts: list[str] = []  # account id(s) this goal names that no source sent; current is None when set
    unknown_reason: str = ""  # why current is unknown when no account is missing ("" otherwise)
    # other unreached value goals whose accounts include every one of this goal's: money in here moves them too
    part_of: list[str] = []
    pace: GoalPace | None = None  # the actual against the straight line, when the history can be trusted
    pace_note: str = ""  # why there is no pace ("" when there is one, or when none is expected: reached, undated)


class Passed(View):
    date: dt.date
    label: str  # "$15,000" or the goal's label
    kind: Literal["round", "goal"]


class Counts(View):
    off_plan: int
    theses_alert: int
    theses_watch: int
    unknown: int = 0  # targets kestrel can't measure
    need_trade: int = 0  # off-band targets whose plan brings them back with a trade


class PlanAction(View):
    """One thing to do this month, ranked (spec 2026-10-08 §3): the first three are the page's priorities."""
    level: Literal["warning", "note"]
    kind: Literal["target", "thesis", "goal"]
    title: str
    why: str  # the reason it is on the list, in a sentence
    detail: str  # the figures behind it
    anchor: str  # the element on the page that backs it: "target-<id>", "goal-<id>", "thesis-<symbol>", "theses"


class PlanView(View):
    as_of: dt.datetime
    summary: str  # the header's sentence: goals ahead and the next, targets off plan, theses needing a look
    actions: list[PlanAction]  # this month's to-do, ranked: the first three are the priorities
    passed: list[Passed]  # round numbers the net worth crossed and goals reached, newest first (spec §2.2)
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
                     gap_text=_gap_text(status), note=t.note, rebalance=t.rebalance)


def _with_parents(rows: list[TargetRow]) -> list[TargetRow]:
    """Each row's `parent`: the smallest multi-symbol row of the same list whose symbols include every one of its
    own (a sleeve and its members). Rows naming no symbols, or the same symbols, are never nested."""
    out = []
    for row in rows:
        mine = set(row.symbols)
        holders = [p for p in rows if p.id != row.id and len(p.symbols) > 1 and mine
                   and mine < set(p.symbols)]
        parent = min(holders, key=lambda p: (len(p.symbols), p.id)).id if holders else None
        out.append(row.model_copy(update={"parent": parent}))
    return out


def _untargeted_pct(rows: list[TargetRow], account: Account | None, holdings) -> float | None:
    """The share of the account in no symbol its "%" targets name (cash and everything else), from holdings; None
    when the account has no positive value or reported no holdings — never a fake 100 %."""
    if account is None or account.value <= 0:
        return None
    mine = [h for h in holdings if h.account_id == account.id]
    if not mine:
        return None
    covered = {s for r in rows if r.unit == "%" for s in r.symbols}
    covered_value = sum(h.value for h in mine if h.symbol in covered)
    return round(max(0.0, (account.value - covered_value) / account.value * 100), 2)


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
    known = [AccountTargets(account_id=aid, name=by_id[aid].name, known=True,
                            rows=_with_parents(sorted(grouped[aid], key=_sort_key)),
                            untargeted_pct=_untargeted_pct(grouped[aid], by_id[aid], snapshot.holdings))
             for aid in sorted(known_ids, key=lambda aid: (-by_id[aid].value, by_id[aid].name))]
    unknown = [AccountTargets(account_id=aid, name=aid, known=False,
                              rows=_with_parents(sorted(grouped[aid], key=_sort_key)))
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


def _scope_history(scope_ids: list[str], by_id: dict[str, Account],
                   history: dict[str, list[ValuePoint]]) -> list[tuple[dt.date, float]]:
    """The scope's signed value on each day its accounts have history, each account carried forward from its last
    point; a day counts only once every account in the scope has started. Empty when any account has no history."""
    series = {aid: {p.date: p.value for p in history.get(aid, [])} for aid in scope_ids}
    if not scope_ids or any(not s for s in series.values()):
        return []
    sign = {aid: -1.0 if by_id[aid].category == "debt" else 1.0 for aid in scope_ids}
    days = sorted({day for s in series.values() for day in s})
    last: dict[str, float] = {}
    out = []
    for day in days:
        for aid, s in series.items():
            if day in s:
                last[aid] = s[day]
        if len(last) == len(scope_ids):
            out.append((day, round(sum(sign[aid] * last[aid] for aid in scope_ids), 2)))
    return out


def _reached_on(g: Goal, scope_ids: list[str], by_id: dict[str, Account],
                history: dict[str, list[ValuePoint]]) -> dt.date | None:
    if g.measure == "deposits":
        return None
    return next((day for day, value in _scope_history(scope_ids, by_id, history) if value >= g.target), None)


def passed_list(snapshot: Snapshot, goals: list[GoalRow]) -> list[Passed]:
    """Round numbers the net-worth history crossed, each on the first day it did (the last PASSED_ROUNDS), and the
    goals reached on a known day; newest first, a round number before a goal on the same day."""
    points = net_points(snapshot)
    rounds: dict[float, dt.date] = {}
    for prev, cur in zip(points, points[1:]):
        step = round_step(cur.value)
        r = math.floor(cur.value / step) * step
        while r > prev.value and r > 0:
            rounds.setdefault(r, cur.date)
            r -= step
    newest = sorted(rounds.items(), key=lambda item: item[1])[-PASSED_ROUNDS:]
    items = [Passed(date=day, label=f"${r:,.0f}", kind="round") for r, day in newest]
    items += [Passed(date=g.reached_on, label=g.label, kind="goal") for g in goals if g.reached and g.reached_on]
    return sorted(items, key=lambda m: (-m.date.toordinal(), m.kind != "round"))


def _goal_row(g: Goal, accounts: list[Account], history: dict[str, list[ValuePoint]], today: dt.date) -> GoalRow:
    by_id = {a.id: a for a in accounts}
    scope_ids, scope_text, missing = _goal_scope(g, accounts)
    # deposits are read from history: an account with none (a bank feed with only today's balance) hides its own,
    # and a sum over the rest would be a number kestrel can't stand behind
    blind = sorted(by_id[i].name for i in scope_ids if not history.get(i)) if g.measure == "deposits" else []
    if missing or blind:
        return GoalRow(id=g.id, label=g.label, scope_text=scope_text, measure=g.measure, current=None,
                       target=g.target, progress_pct=None, by=g.by, months_left=None, monthly_needed=None,
                       reached=False, overdue=False, missing_accounts=missing,
                       unknown_reason="" if missing else f"no deposit history for {', '.join(blind)}")
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
    return GoalRow(id=g.id, label=g.label, scope_text=scope_text, measure=g.measure, current=current,
                   target=g.target, progress_pct=progress, by=g.by, months_left=months_left,
                   monthly_needed=monthly_needed, reached=reached,
                   reached_on=_reached_on(g, scope_ids, by_id, history) if reached else None, overdue=overdue,
                   missing_accounts=[])


PACE_GRACE_DAYS = 7  # history that starts this close after the window opens still counts as from the start
PACE_MIN_POINTS = 8  # fewer days than this since the window opened is too little to draw a pace from
PACE_MAX_POINTS = 60  # a small chart: the series is thinned to about this many points, the last always kept
PACE_MAX_YEARS = 5  # a value goal further out than this gets no straight-line pace: market growth is most of its story


def _pace(g: Goal, row: GoalRow, scope_ids: list[str], by_id: dict[str, Account],
          history: dict[str, list[ValuePoint]], today: dt.date) -> tuple[GoalPace | None, str]:
    """The goal's actual since its window opened against the straight line to its target (spec 2026-10-08 §3), or
    None and why. Only drawn when it can be trusted: every account in scope has history from within
    PACE_GRACE_DAYS of the window's first day, and there are PACE_MIN_POINTS days since."""
    if row.current is None or row.reached or row.overdue or g.by is None or g.by <= today:
        return None, ""
    if g.measure == "value" and (g.by - today).days > PACE_MAX_YEARS * 365:
        return None, "no pace: too far out for a straight line, market growth is most of the way there"
    start = dt.date(g.by.year if g.measure == "deposits" else today.year, 1, 1)
    if start > today:
        return None, f"its year opens {_day_text(start)}"
    late = [(min(p.date for p in history[i]), by_id[i].name) for i in scope_ids if history.get(i)]
    late = [(first, name) for first, name in late if first > start + dt.timedelta(days=PACE_GRACE_DAYS)]
    if late or any(not history.get(i) for i in scope_ids):
        first, name = max(late) if late else (None, "")
        why = (f"history for {name} starts {_day_text(first)}" if first else "an account in it has no history")
        return None, f"no pace yet: {why}"
    if g.measure == "deposits":
        days = sorted({p.date for i in scope_ids for p in history[i] if start <= p.date <= today})
        flows = sorted((p.date, p.net_flow) for i in scope_ids for p in history[i] if start <= p.date <= today)
        series, total, k = [], 0.0, 0
        for day in days:
            while k < len(flows) and flows[k][0] <= day:
                total += flows[k][1]
                k += 1
            series.append((day, round(total, 2)))
        start_value = 0.0
    else:
        series = [(day, value) for day, value in _scope_history(scope_ids, by_id, history) if start <= day <= today]
        start_value = series[0][1] if series else 0.0
    if len(series) < PACE_MIN_POINTS:
        return None, "no pace yet: too little history since 1 January"
    if series[-1][0] < today:
        series.append((today, row.current))
    step = math.ceil(len(series) / PACE_MAX_POINTS)
    series = series[::step] if series[::step][-1] == series[-1] else [*series[::step], series[-1]]
    span = (g.by - start).days
    required_now = round(start_value + (g.target - start_value) * (today - start).days / span, 2)
    return GoalPace(start=start, start_value=start_value, points=[PacePoint(date=d_, value=v) for d_, v in series],
                    required_now=required_now, ahead=round(row.current - required_now, 2)), ""


def goal_rows(snapshot: Snapshot, today: dt.date) -> list[GoalRow]:
    """Every goal, with the goals it is part of and its pace."""
    accounts = snapshot.accounts
    by_id = {a.id: a for a in accounts}
    history = {s.id: list(s.points) for s in snapshot.account_history}
    rows = [_goal_row(g, accounts, history, today) for g in snapshot.goals]
    scopes = {g.id: set(_goal_scope(g, accounts)[0]) for g in snapshot.goals}
    out = []
    for g, row in zip(snapshot.goals, rows):
        mine = scopes[g.id]
        # inside another: its accounts a strict subset of the other's, or the same accounts measured as deposits
        # (deposits raise that value); two value goals over the same accounts are milestones of one number, and
        # never part of each other
        part_of = [o.id for o, other in zip(snapshot.goals, rows)
                   if o.id != g.id and o.measure == "value" and not other.reached and other.current is not None
                   and mine and (mine < scopes[o.id] or (mine == scopes[o.id] and g.measure == "deposits"))]
        pace, note = _pace(g, row, sorted(mine), by_id, history, today)
        out.append(row.model_copy(update={"part_of": part_of, "pace": pace, "pace_note": note}))
    return out


def _attention_for(row: TargetRow) -> tuple[Literal["warning", "note"], str] | None:
    """Whether an off-band target belongs on Home's Needs you, and how loudly: a trade is a warning; new money to
    steer there, or a decision to revisit, a note; one that dilutes on its own needs nothing from you."""
    if row.status not in ("over", "under"):
        return None
    if row.rebalance == "trades":
        return "warning", row.gap_text
    if row.status == "under" and row.rebalance == "contributions":
        return "note", f"{row.gap_text} · steer new money here"
    if row.status == "under" and row.rebalance == "hold":
        return "note", f"{row.gap_text} · a decision to revisit, not a buy"
    return None


def target_attention(snapshot: Snapshot) -> list[Attention]:
    """Off-plan targets that need something from you, as Needs-you items (see `_attention_for`): one that dilutes on
    its own is left out. An account no source sent is still named, by its bare id, so the item is actionable rather
    than silently vague."""
    items = []
    for t, row, account in target_rows(snapshot):
        loud = _attention_for(row)
        if loud is None:
            continue
        word = "over" if row.status == "over" else "under"
        where = account.name if account is not None else t.account_id
        title = f"{row.label} is {word} plan in {where}" if where else f"{row.label} is {word} plan"
        items.append(Attention(level=loud[0], title=title, detail=loud[1], link="/plan"))
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


def _day_text(day: dt.date) -> str:
    """"25 Jul 2027": the day without a leading zero, the month's short name, the year."""
    return f"{day.day} {day.strftime('%b')} {day.year}"


def _money_text(value: float) -> str:
    return f"${value:,.2f}"


def _unit_text(value: float, unit: str) -> str:
    return f"{value:.1f}%" if unit == "%" else f"{value:.1f}x"


def _band_text(low: float | None, high: float | None, unit: str) -> str:
    """"band 18–22%" / "band 4–8x": whole numbers plainly, else one decimal; an open end says "from" or "up to"."""
    def short(v: float) -> str:
        return str(int(v)) if float(v).is_integer() else f"{v:.1f}"
    suffix = "%" if unit == "%" else "x"
    if low is not None and high is not None:
        return f"band {short(low)}–{short(high)}{suffix}"
    if low is not None:
        return f"band from {short(low)}{suffix}"
    if high is not None:
        return f"band up to {short(high)}{suffix}"
    return "no band"


def _pct_there(row: GoalRow) -> str:
    return f"{int(round(row.progress_pct or 0))}% there"



def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _joined(words: list[str], last: str = "and") -> str:
    """"A", "A and B", "A, B and C"."""
    if len(words) <= 1:
        return "".join(words)
    return f"{', '.join(words[:-1])} {last} {words[-1]}"


def _targets_sentence(counts: Counts, total: int) -> str:
    """The summary's word on the targets: how many sit outside their bands and how many of those need a trade.
    "Every target sits on plan." only when every target is measured and on plan; a target kestrel can't measure is
    named as such, never counted as on plan."""
    if total == 0:
        return ""
    off, unknown, trade = counts.off_plan, counts.unknown, counts.need_trade
    if off == 1:
        text = "1 target is outside its band and needs a trade." if trade else \
            "1 target is outside its band; it needs no trade."
    elif off > 1:
        need = "none needs a trade" if trade == 0 else "all need a trade" if trade == off else \
            f"{trade} {'needs' if trade == 1 else 'need'} a trade"
        text = f"{off} targets are outside their bands; {need}."
    elif unknown == 0:
        return "Every target sits on plan."
    elif unknown == total:
        return "No target can be measured yet."
    else:
        return f"{total - unknown} of {total} targets on plan; {unknown} can't be measured yet."
    if unknown:
        text += f" {_plural(unknown, 'target', 'targets')} can't be measured yet."
    return text


def plan_summary(goals: list[GoalRow], counts: Counts, total_targets: int) -> str:
    """The header's sentence, in three parts: the goals ahead and the next dated one, the targets (spec 2026-10-08
    §3), and the theses that need a look. Each part is left out when there is nothing to say about it."""
    parts = []
    ahead = [g for g in goals if not g.reached]
    dated = sorted((g for g in ahead if g.by is not None), key=lambda g: g.by)
    if not goals:
        parts.append("No goals yet.")
    elif not ahead:
        parts.append("Every goal is reached.")
    else:
        count = f"{len(ahead)} goal{'s' if len(ahead) != 1 else ''} ahead"
        if dated:
            g = dated[0]
            parts.append(f"{count}. The next is {g.label}, {_pct_there(g)}, by {_day_text(g.by)}.")
        else:
            parts.append(f"{count}, none dated.")
    targets = _targets_sentence(counts, total_targets)
    if targets:
        parts.append(targets)
    needing = counts.theses_alert + counts.theses_watch
    if needing:
        parts.append(f"{needing} {'thesis needs' if needing == 1 else 'theses need'} a look.")
    return " ".join(parts)


DUE_WITHIN_MONTHS = 12  # a dated goal this close gets a monthly line in this month's actions

# The ranking of this month's actions (spec 2026-10-08 §3): the first three are the page's priorities
RANK_ALERT, RANK_OVERDUE, RANK_TRADE, RANK_PACE, RANK_STEER, RANK_WATCH, RANK_REVISIT, RANK_DILUTE, RANK_INNER = \
    range(9)


def _figures(row: TargetRow) -> str:
    """"10.0% held · aim 20.0% · band 18–22%": the numbers behind a target's action."""
    actual = "—" if row.actual is None else _unit_text(row.actual, row.unit)
    held = "actual" if row.unit == "x" else "held"
    aim = f" · aim {_unit_text(row.target, row.unit)}" if row.target is not None else ""
    return f"{actual} {held}{aim} · {_band_text(row.low, row.high, row.unit)}"


def _target_action(row: TargetRow, where: str) -> tuple[int, PlanAction] | None:
    """What to do about one off-band target, by its rebalance policy, with its rank: "Add $80.00 to XLP in Roth
    IRA" for a trade with a money gap, "XLP is 4.0 pts under its band in Roth IRA" for one in points or a ratio,
    "Steer new money to …" or "Revisit …" otherwise. Nothing for a row on plan or unknown, or one over its band
    whose plan never sells (those dilute: see `_dilute_action`)."""
    if row.status not in ("over", "under") or row.gap is None or row.gap_unit is None:
        return None
    suffix = f" in {where}" if where else ""
    anchor = f"target-{row.id}"
    why = POLICY_WHY[(row.rebalance, row.status)]
    detail = _figures(row)
    if row.rebalance == "trades":
        amount = abs(row.gap)
        if row.gap_unit == "money":
            title = (f"Add {_money_text(amount)} to {row.label}{suffix}" if row.status == "under"
                     else f"Trim {_money_text(amount)} from {row.label}{suffix}")
        else:
            digits = 2 if amount < 0.1 else 1
            figure = f"{amount:.{digits}f}{'x' if row.gap_unit == 'x' else ' pts'}"
            title = f"{row.label} is {figure} {row.status} its band{suffix}"
        return RANK_TRADE, PlanAction(level="warning", kind="target", title=title, why=why, detail=detail,
                                      anchor=anchor)
    if row.status == "over":
        return None
    if row.rebalance == "contributions":
        if row.gap_unit == "money":
            detail += f" · {_money_text(abs(row.gap))} to its low end"
        return RANK_STEER, PlanAction(level="note", kind="target", title=f"Steer new money to {row.label}{suffix}",
                                      why=why, detail=detail, anchor=anchor)
    return RANK_REVISIT, PlanAction(level="note", kind="target", title=f"Revisit {row.label}{suffix}: under its band",
                                    why=why, detail=detail, anchor=anchor)


def _dilute_action(rows: list[TargetRow], where: str) -> PlanAction | None:
    """One note per account for the targets over their bands whose plan never sells: they come down on their own as
    new money goes elsewhere, so the only thing to do is not to add to them."""
    over = [r for r in rows if r.status == "over" and r.rebalance in ("contributions", "hold")]
    if not over:
        return None
    suffix = f" in {where}" if where else ""
    names = _joined([r.label for r in over], "or")
    each = "It sits" if len(over) == 1 else "Each sits"
    detail = " · ".join(f"{r.label} {_unit_text(r.actual, r.unit) if r.actual is not None else '—'} "
                        f"({_band_text(r.low, r.high, r.unit)})" for r in over)
    return PlanAction(level="note", kind="target", title=f"Send no new money to {names}{suffix}",
                      why=f"{each} over its band and comes down as new money goes elsewhere: no sale.",
                      detail=detail, anchor=f"target-{over[0].id}")


def _thesis_detail(t: ThesisRow) -> str:
    parts = [f"{t.conviction} conviction"] if t.conviction else []
    parts.append(f"held in {', '.join(t.account_names) or 'an account'}" if t.held else "not held")
    if t.days_since_review is not None:
        parts.append(f"reviewed {t.days_since_review}d ago")
    return " · ".join(parts)


def _reasons(t: ThesisRow) -> str:
    """The reasons as sentences: "Sales fell. The price closed below its 200-day average."."""
    return " ".join(r.rstrip(".") + "." for r in t.reasons)


def _watch_action(watch: list[ThesisRow]) -> PlanAction | None:
    """The theses on watch as one note: one names its reasons, several name each one's first."""
    if not watch:
        return None
    if len(watch) == 1:
        t = watch[0]
        return PlanAction(level="note", kind="thesis", title=f"Look at {t.symbol}: thesis on watch",
                          why=_reasons(t) or "Its thesis is on watch.", detail=_thesis_detail(t),
                          anchor=f"thesis-{t.symbol}")
    why = "; ".join(f"{t.symbol} — {t.reasons[0].rstrip('.')}" if t.reasons else t.symbol for t in watch) + "."
    return PlanAction(level="note", kind="thesis",
                      title=f"Look at {len(watch)} theses on watch: {_joined([t.symbol for t in watch])}",
                      why=why, detail="", anchor="theses")


def _monthly_title(g: GoalRow) -> str:
    how = " in deposits" if g.measure == "deposits" else ""
    return f"Put about {_money_text(g.monthly_needed)} a month{how} toward {g.label}"


def _goal_detail(g: GoalRow) -> str:
    return f"to reach {_money_text(g.target)} by {_day_text(g.by)} · {_pct_there(g)}"


def _pace_actions(goals: list[GoalRow]) -> list[tuple[int, PlanAction]]:
    """The money a month toward each goal due within a year. A goal whose accounts sit inside another such goal's
    (a deposit into one account raises the total over all of them) is named inside that one's action, with its
    share, and listed itself further down as part of it: the amounts are never independent of each other."""
    due = [g for g in goals if g.by is not None and not g.reached and not g.overdue and g.months_left is not None
           and g.months_left <= DUE_WITHIN_MONTHS and g.monthly_needed is not None]
    due.sort(key=lambda g: (g.by, g.label))
    labels = {g.id: g.label for g in goals}
    ids = {g.id for g in due}
    umbrella = {g.id: next((o for o in due if o.id in g.part_of and o.id != g.id), None) for g in due}
    # a goal inside another is never itself an umbrella: the outermost one carries the explanation
    umbrella = {gid: (u if u is None or umbrella.get(u.id) is None else umbrella[u.id]) for gid, u in umbrella.items()}
    out: list[tuple[int, PlanAction]] = []
    for g in due:
        u = umbrella[g.id]
        anchor = f"goal-{g.id}"
        if u is not None:
            why = f"Counts toward {u.label} too: the two amounts overlap, they don't add up."
            out.append((RANK_INNER, PlanAction(level="note", kind="goal", title=_monthly_title(g), why=why,
                                               detail=_goal_detail(g), anchor=anchor)))
            continue
        inner = [o for o in due if umbrella[o.id] is not None and umbrella[o.id].id == g.id]
        if inner:
            names = _joined([f"{o.label} ({_money_text(o.monthly_needed)} a month)" for o in inner])
            share = round(sum(o.monthly_needed for o in inner), 2)
            verb = "is" if len(inner) == 1 else "are"
            if share <= g.monthly_needed:
                why = (f"{names} {verb} part of this, not on top of it: {_money_text(share)} of the "
                       f"{_money_text(g.monthly_needed)}.")
            else:
                why = f"{names} {verb} part of this, and alone {'covers' if len(inner) == 1 else 'cover'} it."
        elif g.measure == "deposits":
            why = f"Deposits since 1 January count; this spreads the rest evenly to {_day_text(g.by)}."
        else:
            why = "A straight line to the target by its date, before any market growth."
        also = [labels[o] for o in g.part_of if o not in ids]
        if also:
            why += f" It also moves {_joined(also)}."
        out.append((RANK_PACE, PlanAction(level="note", kind="goal", title=_monthly_title(g), why=why,
                                          detail=_goal_detail(g), anchor=anchor)))
    return out


def plan_actions(accounts: list[AccountTargets], unscoped: list[TargetRow], theses: list[ThesisRow],
                 goals: list[GoalRow]) -> list[PlanAction]:
    """This month's to-do, ranked (spec 2026-10-08 §3): theses on alert, overdue goals and targets that need a trade
    (the largest money gap first) are warnings; then the money a month toward goals due within a year, new money to
    steer, theses on watch, holdings to revisit, holdings to leave to dilute, and goals already named inside
    another's action. Within a rank, the page's own order."""
    ranked: list[tuple[int, float, PlanAction]] = []
    groups = [*((a.rows, a.name) for a in accounts), (unscoped, "")]
    for rows, where in groups:
        for row in rows:
            item = _target_action(row, where)
            if item:
                rank, action = item
                size = -abs(row.gap) if row.gap_unit == "money" and row.gap is not None else 0.0
                ranked.append((rank, size, action))
        dilute = _dilute_action(rows, where)
        if dilute:
            ranked.append((RANK_DILUTE, 0.0, dilute))
    for t in theses:
        if t.health == "alert":
            ranked.append((RANK_ALERT, 0.0, PlanAction(
                level="warning", kind="thesis", title=f"Review {t.symbol}: thesis on alert",
                why=_reasons(t) or "Its thesis is on alert.", detail=_thesis_detail(t), anchor=f"thesis-{t.symbol}")))
    watch = _watch_action([t for t in theses if t.health == "watch"])
    if watch:
        ranked.append((RANK_WATCH, 0.0, watch))
    for g in goals:
        if g.overdue and g.by is not None:
            current = "—" if g.current is None else _money_text(g.current)
            ranked.append((RANK_OVERDUE, 0.0, PlanAction(
                level="warning", kind="goal", title=f"{g.label} was due {_day_text(g.by)}",
                why=f"Its date has passed at {_pct_there(g)}.", detail=f"{current} of {_money_text(g.target)}",
                anchor=f"goal-{g.id}")))
    ranked.extend((rank, 0.0, action) for rank, action in _pace_actions(goals))
    # sorted() is stable: within a rank and a gap size, the order the page lists things in
    return [action for _, _, action in sorted(ranked, key=lambda item: (item[0], item[1]))]


def plan_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> PlanView:
    today = now.astimezone(profile.tz).date()
    accounts, unscoped = plan_targets(snapshot)
    theses = thesis_rows(snapshot, today)
    goals = goal_rows(snapshot, today)
    every_row = [*(r for a in accounts for r in a.rows), *unscoped]
    off = [r for r in every_row if r.status in ("over", "under")]
    counts = Counts(off_plan=len(off), theses_alert=sum(1 for t in theses if t.health == "alert"),
                    theses_watch=sum(1 for t in theses if t.health == "watch"),
                    unknown=sum(1 for r in every_row if r.status == "unknown"),
                    need_trade=sum(1 for r in off if r.rebalance == "trades"))
    return PlanView(
        as_of=now, summary=plan_summary(goals, counts, len(every_row)),
        actions=plan_actions(accounts, unscoped, theses, goals), passed=passed_list(snapshot, goals),
        accounts=accounts, unscoped=unscoped, theses=theses, goals=goals, counts=counts,
    )
