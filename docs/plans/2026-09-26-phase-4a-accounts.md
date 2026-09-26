# Phase 4a — Accounts and your real data — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** kestrel reads the owner's real accounts through financial-data-collector's SQLite warehouse (the `fdc` connector), and gains the two Accounts pages: `/accounts` answers "what does each account hold, and how much of its growth was my deposits vs the market?" for every account together, and `/accounts/<id>` answers it for one. Home's net worth, allocation and "trading vs your index money" become real, and anyone with their own collector warehouse can do the same with one `[[sources]]` block.

**Architecture:**
- **Contract (additive, still version `"1"`):** `Account.account_type`, display text for the kind of account. The demo gains an account type on every account, fictional holdings and the cash they leave.
- **Profile and CLI:** a relative `path` in a source is relative to the profile's folder; an unknown category is a profile error; `serve --demo` and `check --demo` show the demo whatever `profile.toml` says; `check` lists each source's accounts (never a balance).
- **Connector:** `connectors/fdc.py` opens the warehouse read-only twice over (`mode=ro`, then `query_only`), checks its schema, and maps accounts, holdings, daily history with the money moved in and out, the benchmark's prices and the source's freshness onto the contract. The tests build a small fictional warehouse from the collector's own table and view definitions.
- **Server:** one pure module, `views/accounts.py`, builds `AccountsView` and `AccountView`; two GET routes and two `kestrel demo` views expose them; two generated fixtures pin the web types. Home's trading line falls back to the trading accounts until a real book has a history.
- **Web:** a growth bar in the chart kit; the stat block, sortable heading and category chip move into the shared pieces; `/accounts` and `/accounts/$accountId`; Home's account rows become links.

**Tech Stack:** unchanged from Phase 3a: Python ≥ 3.11 (FastAPI 0.141, pydantic 2.13, the standard library's `sqlite3`), pytest, ruff; Node 24, React 19.2, Vite 8, Tailwind 4.3, TanStack Router 1.170 / Query 5, d3-scale 4 / d3-shape 3 / d3-array 3, Vitest 4.1 + Testing Library 16 + jsdom 27, TypeScript ~6.0. No new dependencies.

**Spec:** `docs/specs/2026-09-26-phase-4a-accounts-design.md` (binding), with `docs/specs/2026-09-25-kestrel-design.md` (§4, §7, §8, §9, §11) and `docs/design-system.md`.

**Provenance:** every code block below was run in a scratch clone of this repo, task by task, before this plan was written, and the plan itself was then replayed into a second fresh clone, task by task, taking every block out with the helper below; the counts in each task come from that replay.
- End state: `pytest` 186 passed, `ruff check .` clean; `vitest` 145 passed, `tsc --noEmit` clean, `npm run build` succeeded.
- Spec §2.4, performance: measured: 57 ms on a household warehouse, under the spec's 100 ms line, so no cache goes in.
- `kestrel serve --demo` was checked at 390, 768, 1024, 1280 and 1440 px on `/`, `/accounts`, `/accounts/brokerage` and `/accounts/savings`: no sideways scroll and no panel overflow. The full screenshot pass in both themes is Task 10, Step 4.

### How to use this plan (read before Task 1)

- **Copy file blocks with a script, never by hand.** Earlier plans lost typographic apostrophes, minus signs and non-breaking characters to retyping. Save this helper **outside the repo** (for example in your temp folder) and use it for every file block:

````python
"""Write a plan task's file blocks to disk, byte for byte.

Usage (from the repo root):
  python copy_blocks.py PLAN TASK              list the task's file blocks
  python copy_blocks.py PLAN TASK PATH [...]   write those blocks
  python copy_blocks.py PLAN TASK --all        write every block of the task
  python copy_blocks.py PLAN TASK --check      compare the task's blocks (and every earlier task's) with the tree
"""

import re
import sys
from pathlib import Path

BLOCK = re.compile(r"^`([^`\n]+)`:\n\n````[a-z]*\n(.*?)\n````\n", re.M | re.S)


def tasks(plan: str) -> dict[int, list[tuple[str, str]]]:
    parts = re.split(r"^### Task (\d+):", plan, flags=re.M)
    return {int(num): BLOCK.findall(body) for num, body in zip(parts[1::2], parts[2::2])}


def main(argv: list[str]) -> int:
    plan_path, task, *rest = argv
    by_task = tasks(Path(plan_path).read_text(encoding="utf-8"))
    n = int(task)
    blocks = dict(by_task.get(n, []))
    if not rest:
        for path in blocks:
            print(path)
        print(f"{len(blocks)} block(s) in task {n}")
        return 0
    if rest == ["--check"]:
        expected: dict[str, str] = {}
        for num in sorted(k for k in by_task if k <= n):
            expected.update(dict(by_task[num]))
        bad = 0
        for path, block in expected.items():
            p = Path(path)
            if not p.exists():
                print("MISSING", path)
                bad += 1
            elif p.read_text(encoding="utf-8").rstrip("\n") != block.rstrip("\n"):
                print("DRIFT", path)
                bad += 1
        print(len(expected), "blocks checked,", bad, "problem(s)")
        return 1 if bad else 0
    paths = list(blocks) if rest == ["--all"] else rest
    for path in paths:
        if path not in blocks:
            print(f"no block for {path} in task {n}", file=sys.stderr)
            return 2
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as f:
            f.write(blocks[path].rstrip("\n") + "\n")
        print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
````

  Run it from the repo root, for example `python <temp>/copy_blocks.py docs/plans/2026-09-26-phase-4a-accounts.md 3 tests/fdc_fixture.py tests/test_fdc_connector.py`. Write the test files first (Step 1), run them, then write the code files (Step 3). After a task's Step 4, `python <temp>/copy_blocks.py docs/plans/2026-09-26-phase-4a-accounts.md N --check` must end with `0 problem(s)`.
- **Every file block is the complete file.** "Replace the whole file" means overwrite it with the block. There are no partial edits except the documentation lines in Task 10, which are given as exact old and new text.
- **Non-ASCII characters are exact:** − (minus), — (em dash), · (middle dot), ▲ ▼, … (ellipsis), ’ (apostrophe in copy), ↓ ↑, ★ and É (in the tests' fictional labels). The tests pin every sentence the pages show; if one fails on a character, the copy drifted.
- **Paste raw output.** When you report a step, paste the tool's own summary lines (for example `186 passed in 9.9s`, `Tests  145 passed (145)`), not a paraphrase.
- **Commands:** Python runs as `.venv/Scripts/python -m pytest` (on macOS and Linux, `.venv/bin/python`). `pyproject.toml` already adds `-q`; don't add another, or the summary line disappears. Web commands run in `web/`: `npx vitest run [files]`, `npx tsc --noEmit`, `npm run build`.
- **The commit trailer:** save the session's trailer line (`Co-Authored-By: Claude Opus 5.5 (1M context) <…>`, with the address) to `<temp>/trailer.txt`, next to the helper. Each commit step passes it as the message's last paragraph: `git commit -m "subject" -m "$(cat <temp>/trailer.txt)"`.
- If anything doesn't match what a step says, stop and report it rather than improvising.

## Global Constraints

- **Read-only, always:** GET routes only; the server binds `127.0.0.1`; no broker or trading import and no call named `place`, `place_order`, `submit_order`, `cancel`, `cancel_order`, `replace_order`, `modify_order`, `post`, `put`, `patch`, `delete`, `api_route`, `add_api_route` or `websocket` anywhere in `src/kestrel` (`tests/test_read_only_guard.py`). The warehouse is opened with `mode=ro` and `PRAGMA query_only = 1`, one connection per snapshot, always closed; nothing in kestrel writes to it, and nothing changes in financial-data-collector.
- **The contract only grows:** `contract_version` stays `"1"`; every new field is optional with a default; old payloads keep loading.
- **Nothing personal in git:** names, account numbers, balances, holdings and machine paths arrive only at runtime, through the gitignored `profile.toml` and the user's connectors. Demo data stays fictional ("Alex"). The test warehouse is built by the tests from the collector's own table and view definitions and filled with made-up accounts ("Alex …") and numbers — never a copy of real data; `data/` stays gitignored; `tests/test_hygiene.py` passes on every commit.
- **Money state encoding everywhere:** real = solid; paper = hatched fills and dashed lines (`5 3.5`); expected, backtest and benchmark (and the "Start + deposits" reference) = dotted (outline `1.5 2.5`, lines `1.5 3.5`) with a 4–6 % ink wash. Colour never carries meaning alone.
- **Numbers and copy:** a sign and ▲/▼ on every gain or loss; the true minus sign (−); an em dash (—) for a missing value; a zero written out (`$0.00`); sentence case; dates like `Fri 25 Sep`.
- **Tokens only:** no raw hex in `.ts`/`.tsx` (`web/src/styles/design.test.ts`); the type scale is px: 11, 12, 13, 14, 15, 20, 24, 28, 38, 48.
- **Every chart:** a Chart | Table switch, a hover and keyboard tooltip (←/→, Home/End, Escape), a table view, and a plain-English empty state. Every page works by keyboard.
- **No overflow:** panels grow with `min-height` (never a fixed height), tables scroll sideways inside `.table-scroll`, and the page never scrolls sideways at 390, 768, 1024, 1280 or 1440 px, in either theme.
- **Generated files** (`docs/contract/snapshot.schema.json`, `web/src/test/fixtures/*.json`) are only ever regenerated with the command a failing `tests/test_generated_files.py` prints, never edited.
- **CLI output:** JSON as UTF-8 bytes whatever the console code page; `kestrel check` writes its lines as UTF-8 too (an account's name can be any text) and never prints a balance.
- **Commits:** `feat(scope): …` / `fix(scope): …` / `docs: …`, each ending with the trailer line `Co-Authored-By: Claude Opus 5.5 (1M context)` followed by the Anthropic noreply address in angle brackets, exactly as the session gives it. The address is left out of this file on purpose: `tests/test_hygiene.py` fails on any email address in a tracked file other than an example.com or GitHub noreply one, and this plan is tracked. Every commit step below reads the line from `<temp>/trailer.txt` (see How to use).

## Review Focus

These are the inputs most likely to bite a real person that the spec is silent on. Each has a test in the task named after it.

- **A closed account at zero, holding nothing.** The collector keeps an account's row after it is emptied; its last snapshot is $0.00 with no positions and its history stops. It must still be listed (last, at 0.0%), with no holdings, no weights and no growth, and a household whose accounts are all at zero must not divide by zero. Tests: `test_a_closed_account_at_zero_with_no_holdings_is_still_listed` (Task 4), `test_a_closed_account_at_zero_sits_last_and_a_household_of_zeros_has_no_shares` (Task 5), `prints a margin debit with a true minus, and a closed account plainly` (Task 9).
- **A label that is only symbols, or full of accents.** Ids are slugs of the collector's labels and appear in URLs; `Épargne · Alex` folds to `epargne-alex`, `★ ★ ★` and `—` become `account` and `account-2`, and `kestrel check` prints the labels as they are, whatever the console. Tests: `test_ids_are_slugs_of_labels_and_a_clash_gets_a_number` (Task 3), `test_check_prints_a_warehouses_accounts_whatever_their_labels` (Task 6).
- **An empty warehouse, or an empty file.** A freshly initialised warehouse has the schema and no rows: the source is fine and says `0 accounts`, and the page says how to add one. A 0-byte file (or a file of another kind) at `path` is named as not a warehouse. Tests: `test_an_empty_file_or_another_kind_of_file_is_not_a_warehouse` (Task 3), `test_an_empty_warehouse_is_a_source_with_nothing_in_it_yet` (Task 4), `test_no_accounts_is_an_empty_page_and_an_unknown_account_is_none` (Task 5), `says so when there are no accounts yet` (Task 8).
- **A warehouse locked mid-sync.** `fdc sync` can hold the file while kestrel reads it: in the collector's own WAL mode kestrel reads the last committed data; a writer holding the whole file (an older journal mode) makes the source a red row after the timeout, the connection is still closed, and the next request recovers. Tests: `test_a_warehouse_locked_mid_sync_is_an_error_and_the_next_read_recovers` and `test_a_sync_in_progress_on_a_wal_warehouse_reads_the_last_committed_data` (Task 3), `test_a_broken_source_is_a_red_row_and_the_rest_still_arrives` (Task 4).
- **Negative cash (a margin debit).** A trading account can owe cash: the value nets it, the holdings then weigh more than 100% and the cash row a negative share, printed with a true minus; when the debit is bigger than the holdings there are no weights at all. Tests: `test_value_and_cash_come_from_the_latest_snapshot_at_the_us_close` (Task 3), `test_a_margin_debit_is_negative_cash_and_the_value_nets_it` (Task 4), `test_a_margin_debit_weighs_against_the_holdings_and_a_debit_bigger_than_the_holdings_has_no_weights` (Task 5), `prints a margin debit with a true minus, and a closed account plainly` (Task 9).

## File map

```
src/kestrel/contract.py                  + Account.account_type                                        (Task 1)
src/kestrel/connectors/demo.py           + account types, fictional holdings, the cash they leave      (Task 1)
src/kestrel/profile.py                   relative source paths, category check                         (Task 2)
src/kestrel/cli.py                       serve/check --demo, check's account lines (Task 2); demo --view accounts |
                                         account --id (Task 6)
src/kestrel/connectors/base.py           + ConnectorError                                               (Task 3)
src/kestrel/connectors/fdc.py            new: open, schema, ids, categories, values (Task 3); history, flows,
                                         holdings, benchmark, detail (Task 4)
src/kestrel/connectors/__init__.py       build() knows kind "fdc"                                       (Task 4)
src/kestrel/views/accounts.py            new: AccountsView, AccountView and their builders              (Task 5)
src/kestrel/views/home.py                the trading line falls back to the trading accounts            (Task 5)
src/kestrel/server.py                    GET /api/accounts, /api/accounts/{id}                          (Task 6)
docs/data-contract.md · docs/contract/snapshot.schema.json (generated)                                  (Task 1)
tests/fdc_fixture.py · tests/test_fdc_connector.py (new)                                                (Tasks 3, 4)
tests/test_accounts_view.py (new) · tests/test_{contract,demo_connector,profile,cli,home_view,server,
  generated_files}.py (extended)
web/src/components/bits.tsx              + Stat, Sort, toggleSort, SortHeader, CATEGORY_COLOR / _WORD, CategoryChip
web/src/charts/GrowthBar.tsx             new: the growth bar and its table                              (Task 7)
web/src/pages/home/NetWorthPanel.tsx · web/src/pages/strategy/TradesPanel.tsx   use the shared pieces    (Task 7)
web/src/lib/api.ts · test/renderApp.tsx · router.tsx · pages/home/AllocationPanel.tsx                  (Task 8)
web/src/pages/accounts/{Accounts,GrowthPanel}.tsx                                                       (Task 8)
web/src/pages/account/{Account,ValuePanel,AccountGrowth,HoldingsPanel}.tsx · router.tsx                 (Task 9)
web/src/test/fixtures/{accounts,account-roth}.json (generated)                                          (Task 6)
docs/connectors.md (new) · profile.example.toml · README.md · AGENTS.md · docs/specs/*                  (Task 10)
```

---

### Task 1: The contract grows an account type; the demo gains holdings

**Files:**
- Modify (replace the whole file): `src/kestrel/contract.py`, `src/kestrel/connectors/demo.py`, `docs/data-contract.md`
- Regenerate: `docs/contract/snapshot.schema.json`
- Test (replace the whole file): `tests/test_contract.py`, `tests/test_demo_connector.py`

**Interfaces:**
- Produces:
  - `contract.py` `Account.account_type: str = ""`, between `institution` and `category`.
  - `demo.py`: `LONG_TERM_HOLDINGS` (the Roth IRA's and the brokerage's fictional funds and large caps, each a share of the account and a cost as a share of today's value, `None` for KO), `PRICES`, `NAMES`; `_holdings(account_id, value) -> list[Holding]` (whole thousandths of a share, so the cash left over is never negative); `_cash(holdings, account_id, value) -> float`. The trading account holds the real book's open positions at their last price, cost = quantity × entry. Savings holds only cash. Account types: Roth IRA, Brokerage, Individual, Savings. Existing demo numbers don't move (`home.json` and the other fixtures stay current).

- [ ] **Step 1: Write the failing tests**

`tests/test_contract.py`:

````python
import datetime as dt

import pytest
from pydantic import ValidationError

from kestrel.contract import CONTRACT_VERSION, Snapshot, ValuePoint, merge

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


def minimal(**extra):
    return {"contract_version": "1", "generated_at": NOW.isoformat(), **extra}


@pytest.mark.parametrize("link", ["https://evil.example", "//evil.example", "/\\evil.example", "javascript:x"])
def test_an_alert_link_must_stay_inside_the_app(link):
    with pytest.raises(ValidationError):
        Snapshot.model_validate(minimal(alerts=[{"level": "note", "title": "x", "link": link}]))


@pytest.mark.parametrize("link", ["", "/", "/books", "/strategies/rsi2?tab=trades"])
def test_an_internal_alert_link_is_kept(link):
    snap = Snapshot.model_validate(minimal(alerts=[{"level": "note", "title": "x", "link": link}]))
    assert snap.alerts[0].link == link


def test_a_minimal_snapshot_loads_with_empty_lists():
    snap = Snapshot.model_validate(minimal())
    assert snap.contract_version == CONTRACT_VERSION
    assert snap.accounts == [] and snap.benchmark is None


def test_an_unknown_major_version_is_refused_with_a_reason():
    with pytest.raises(ValidationError, match="unsupported contract version '2'"):
        Snapshot.model_validate(minimal(contract_version="2"))


def test_a_newer_minor_version_and_unknown_fields_still_load():
    snap = Snapshot.model_validate(minimal(contract_version="1.3", something_new={"x": 1}))
    assert snap.contract_version == "1.3"


def test_timestamps_must_carry_an_offset():
    with pytest.raises(ValidationError):
        Snapshot.model_validate({"generated_at": "2026-09-25T21:08:00"})


def test_a_full_account_and_series_round_trip_through_json():
    snap = Snapshot.model_validate(minimal(
        accounts=[{"id": "roth", "name": "Roth IRA", "category": "long_term", "value": 100.0,
                   "as_of": NOW.isoformat()}],
        account_history=[{"id": "roth", "points": [{"date": "2026-09-24", "value": 99.0},
                                                    {"date": "2026-09-25", "value": 100.0, "net_flow": 0.5}]}],
    ))
    again = Snapshot.model_validate_json(snap.model_dump_json())
    assert again == snap
    assert again.account_history[0].points[1] == ValuePoint(date=dt.date(2026, 9, 25), value=100.0, net_flow=0.5)


def test_an_account_type_is_optional_and_round_trips():
    base = {"id": "roth", "name": "Roth IRA", "category": "long_term", "value": 100.0, "as_of": NOW.isoformat()}
    snap = Snapshot.model_validate(minimal(accounts=[base, {**base, "id": "ira", "account_type": "Roth IRA"}]))
    assert [a.account_type for a in snap.accounts] == ["", "Roth IRA"]
    assert Snapshot.model_validate_json(snap.model_dump_json()) == snap


def test_an_unknown_category_is_refused():
    with pytest.raises(ValidationError):
        Snapshot.model_validate(minimal(accounts=[{"id": "x", "name": "X", "category": "crypto", "value": 1,
                                                   "as_of": NOW.isoformat()}]))


def test_merge_concatenates_lists_and_keeps_the_first_benchmark():
    bench = {"symbol": "SPY", "label": "S&P 500", "points": [{"date": "2026-09-25", "value": 600.0}]}
    a = Snapshot.model_validate(minimal(sources=[{"id": "a", "label": "A", "kind": "demo"}], benchmark=bench))
    b = Snapshot.model_validate(minimal(sources=[{"id": "b", "label": "B", "kind": "feed"}]))
    merged = merge([a, b], generated_at=NOW)
    assert [s.id for s in merged.sources] == ["a", "b"]
    assert merged.benchmark is not None and merged.benchmark.symbol == "SPY"
    assert merge([], generated_at=NOW).sources == []


CHART = {
    "book_id": "real", "symbol": "HD", "opened": "2026-09-14",
    "bars": [{"date": "2026-09-11", "open": 220.1, "high": 221.0, "low": 217.9, "close": 218.4},
             {"date": "2026-09-14", "open": 218.67, "high": 220.2, "low": 217.5, "close": 219.9}],
    "indicator": {"label": "RSI(2)", "values": [None, 6.5],
                  "lines": [{"value": 10, "label": "buy under 10"}, {"value": 70, "label": "sell over 70"}]},
    "stop": 201.18,
}
STRATEGY = {
    "id": "rsi2", "name": "Mean reversion",
    "expected": {"win_rate": 66, "avg_trade_pct": 0.84, "avg_win_pct": 2.45, "avg_loss_pct": -2.28,
                 "trades_per_month": 3.1, "sd_trade_pct": 3.0, "cagr_pct": 23.4, "max_drawdown_pct": -11.7},
    "watch": [{"symbol": "KO", "label": "RSI(2)", "value": 12.4}],
}


def test_trade_charts_and_the_new_strategy_fields_round_trip_through_json():
    snap = Snapshot.model_validate(minimal(trade_charts=[CHART], strategies=[STRATEGY]))
    again = Snapshot.model_validate_json(snap.model_dump_json())
    assert again == snap
    chart = again.trade_charts[0]
    assert chart.bars[1].open == 218.67 and chart.indicator is not None and chart.indicator.values == [None, 6.5]
    assert [line.label for line in chart.indicator.lines] == ["buy under 10", "sell over 70"]
    strategy = again.strategies[0]
    assert strategy.expected is not None and strategy.expected.cagr_pct == 23.4
    assert strategy.expected.max_drawdown_pct == -11.7
    assert strategy.watch[0].symbol == "KO" and strategy.watch[0].note == ""


def test_the_new_fields_are_optional():
    snap = Snapshot.model_validate(minimal(strategies=[{"id": "s", "name": "S", "expected": {
        "win_rate": 50, "avg_trade_pct": 0.1, "avg_win_pct": 1, "avg_loss_pct": -1, "trades_per_month": 2,
        "sd_trade_pct": 1}}]))
    assert snap.trade_charts == [] and snap.strategies[0].watch == []
    assert snap.strategies[0].expected is not None and snap.strategies[0].expected.cagr_pct is None
    bare = Snapshot.model_validate(minimal(trade_charts=[{**CHART, "indicator": None, "stop": None}]))
    assert bare.trade_charts[0].indicator is None and bare.trade_charts[0].stop is None


def test_a_chart_for_a_trade_that_does_not_exist_still_loads():
    # the Strategy page matches charts to trades and skips the rest; a stray chart is never a reason to drop a source
    snap = Snapshot.model_validate(minimal(trade_charts=[CHART]))
    assert snap.trades == [] and len(snap.trade_charts) == 1


def test_merge_keeps_every_sources_trade_charts():
    a = Snapshot.model_validate(minimal(trade_charts=[CHART]))
    b = Snapshot.model_validate(minimal(trade_charts=[{**CHART, "symbol": "LOW"}]))
    assert [c.symbol for c in merge([a, b], generated_at=NOW).trade_charts] == ["HD", "LOW"]
````


`tests/test_demo_connector.py`:

````python
import datetime as dt
from zoneinfo import ZoneInfo

from kestrel.connectors import collect
from kestrel.connectors.demo import DemoConnector, weekdays_ending
from kestrel.profile import DEMO_PROFILE, Profile, SourceCfg

NY = ZoneInfo("America/New_York")
FRIDAY_EVENING = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)  # 17:08 in New York
SATURDAY = dt.datetime(2026, 9, 26, 15, 0, tzinfo=dt.timezone.utc)


def test_weekdays_ending_skips_weekends():
    days = weekdays_ending(dt.date(2026, 9, 27), 3)  # a Sunday
    assert days == [dt.date(2026, 9, 23), dt.date(2026, 9, 24), dt.date(2026, 9, 25)]


def test_the_demo_is_deterministic():
    a = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    b = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert a == b


def test_the_market_path_stays_put_as_the_dates_move():
    # monthly deposits follow the calendar, so account values shift a little; the market path does not
    today = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    a_week_on = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING + dt.timedelta(days=7))
    paper = lambda snap: next(b.value for b in snap.books if b.id == "rsi2-paper")  # noqa: E731
    assert paper(today) == paper(a_week_on)
    assert [t.return_pct for t in today.trades] == [t.return_pct for t in a_week_on.trades]
    assert a_week_on.account_history[0].points[-1].date == dt.date(2026, 10, 2)


def test_history_ends_today_and_accounts_match_their_last_point():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    history = {s.id: s.points for s in snap.account_history}
    for account in snap.accounts:
        assert history[account.id][-1].date == dt.date(2026, 9, 25)
        assert history[account.id][-1].value == account.value


def test_every_trade_and_position_belongs_to_a_book_and_every_book_to_a_strategy():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    books = {b.id for b in snap.books}
    strategies = {s.id for s in snap.strategies}
    assert {t.book_id for t in snap.trades} <= books
    assert {p.book_id for p in snap.positions} <= books
    assert {b.strategy_id for b in snap.books} <= strategies
    assert all(t.opened <= t.closed for t in snap.trades)


def test_runs_follow_the_clock_and_a_weekend_has_none():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    status = {r.label: r.status for r in snap.runs}
    assert status["Morning run"] == "done" and status["Nightly suite"] == "due"
    assert DemoConnector("demo", NY).snapshot(SATURDAY).runs == []


def test_collect_marks_an_unknown_connector_as_an_error_and_keeps_going():
    profile = Profile(sources=[SourceCfg(id="demo", kind="demo"), SourceCfg(id="desk", kind="feed", label="Desk")])
    snap = collect(profile, FRIDAY_EVENING)
    desk = next(s for s in snap.sources if s.id == "desk")
    assert desk.status == "error" and "not available" in desk.detail
    assert len(snap.accounts) == 4  # the demo still arrived


def test_collect_marks_a_source_stale_after_its_threshold():
    profile = Profile(sources=[SourceCfg(id="demo", kind="demo", stale_after="1m")])
    snap = collect(profile, FRIDAY_EVENING)
    assert {s.label: s.status for s in snap.sources}["Portfolio"] == "stale"  # last success 2 minutes ago


def test_the_demo_profile_greets_alex():
    assert DEMO_PROFILE.you.name == "Alex"


def _trade_for(snap, chart):
    matches = [t for t in snap.trades
               if (t.book_id, t.symbol, t.opened) == (chart.book_id, chart.symbol, chart.opened)]
    assert len(matches) == 1, (chart.book_id, chart.symbol, chart.opened)
    return matches[0]


def test_every_chart_matches_one_trade_and_its_prices_sit_inside_their_bars():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert snap.trade_charts
    for chart in snap.trade_charts:
        trade = _trade_for(snap, chart)
        dates = [b.date for b in chart.bars]
        assert dates == sorted(dates) and trade.opened in dates and trade.closed in dates
        assert all(b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high for b in chart.bars)
        entry = chart.bars[dates.index(trade.opened)]
        leave = chart.bars[dates.index(trade.closed)]
        assert entry.open == trade.entry_price
        # bought at an open and sold at a later open; a same-day trade sells at that day's close
        assert (leave.open if trade.closed > trade.opened else leave.close) == trade.exit_price
        assert entry.low <= trade.entry_price <= entry.high and leave.low <= trade.exit_price <= leave.high


def test_each_book_charts_its_eight_most_recent_trades_with_about_thirty_sessions():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    for book in snap.books:
        trades = sorted((t for t in snap.trades if t.book_id == book.id), key=lambda t: (t.closed, t.opened, t.symbol))
        charts = [c for c in snap.trade_charts if c.book_id == book.id]
        assert {(c.symbol, c.opened) for c in charts} == {(t.symbol, t.opened) for t in trades[-8:]}
        assert all(len(c.bars) == 30 for c in charts)


def test_mean_reversion_charts_carry_rsi2_and_an_8_percent_stop():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    strategy_of = {b.id: b.strategy_id for b in snap.books}
    rsi2_charts = 0
    for chart in snap.trade_charts:
        trade = _trade_for(snap, chart)
        if strategy_of[chart.book_id] != "rsi2":
            assert chart.indicator is None and chart.stop is None
            continue
        rsi2_charts += 1
        assert chart.indicator is not None and chart.indicator.label == "RSI(2)"
        assert len(chart.indicator.values) == len(chart.bars) and chart.indicator.values[:2] == [None, None]
        assert all(0 <= v <= 100 for v in chart.indicator.values[2:])
        assert [(line.value, line.label) for line in chart.indicator.lines] == [
            (10, "buy under 10"), (70, "sell over 70")]
        assert chart.stop == round(trade.entry_price * 0.92, 2)
    assert rsi2_charts == 16  # the real and the paper book, 8 each


def test_mean_reversion_has_backtest_figures_and_a_watch_list():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    rsi2 = next(s for s in snap.strategies if s.id == "rsi2")
    assert rsi2.expected is not None and (rsi2.expected.cagr_pct, rsi2.expected.max_drawdown_pct) == (23.4, -11.7)
    assert [(w.symbol, w.label) for w in rsi2.watch] == [("KO", "RSI(2)"), ("ABT", "RSI(2)"), ("UNP", "RSI(2)")]
    assert all(w.value is not None and w.value < 20 for w in rsi2.watch)
    assert all(s.watch == [] for s in snap.strategies if s.id != "rsi2")


def test_every_account_has_a_type_and_its_holdings_and_cash_add_up_to_its_value():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert [(a.id, a.account_type) for a in snap.accounts] == [
        ("roth", "Roth IRA"), ("brokerage", "Brokerage"), ("trading", "Individual"), ("savings", "Savings")]
    for account in snap.accounts:
        held = sum(h.value for h in snap.holdings if h.account_id == account.id)
        assert round(held + account.cash, 2) == account.value
        assert 0 <= account.cash <= account.value
    assert {h.account_id for h in snap.holdings} == {"roth", "brokerage", "trading"}  # savings holds only cash


def test_holdings_are_priced_consistently_and_the_trading_account_holds_the_real_books_positions():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert all(h.value == round(h.quantity * h.price, 2) and h.name for h in snap.holdings)
    trading = {h.symbol: h.quantity for h in snap.holdings if h.account_id == "trading"}
    assert trading == {p.symbol: p.quantity for p in snap.positions if p.book_id == "rsi2-real"}
    assert [h.symbol for h in snap.holdings if h.cost_basis is None] == ["KO"]  # a cost the broker never reported
    assert len({h.symbol for h in snap.holdings}) == 13
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_contract.py tests/test_demo_connector.py`
Expected: `3 failed, 32 passed`: `test_an_account_type_is_optional_and_round_trips` and `test_every_account_has_a_type_and_its_holdings_and_cash_add_up_to_its_value` (`AttributeError: 'Account' object has no attribute 'account_type'`), and `test_holdings_are_priced_consistently_and_the_trading_account_holds_the_real_books_positions` (`AssertionError: assert {} == {'MSFT': 6.0,..., 'JPM': 10.0}`: the demo holds nothing yet).

- [ ] **Step 3: Implement, document, regenerate the schema**

`src/kestrel/contract.py`:

````python
"""The kestrel data contract, version 1.

Every connector returns a Snapshot. A private system plugs in by serving a Snapshot as JSON (the feed connector).
Within a major version changes are additive only, so unknown fields are ignored and a newer minor still loads.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

CONTRACT_VERSION = "1"

Money = Literal["real", "paper"]
Category = Literal["long_term", "trading", "cash", "other"]


class Model(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class Source(Model):
    id: str
    label: str
    kind: str
    last_success: AwareDatetime | None = None
    status: Literal["ok", "stale", "error"] = "ok"
    detail: str = ""


class Account(Model):
    id: str
    name: str
    institution: str = ""
    account_type: str = ""  # display text for the kind of account: "Roth IRA", "Brokerage"
    category: Category
    value: float
    cash: float = 0.0
    as_of: AwareDatetime


class Holding(Model):
    account_id: str
    symbol: str
    name: str = ""
    quantity: float
    price: float
    value: float
    cost_basis: float | None = None


class ValuePoint(Model):
    date: dt.date
    value: float
    net_flow: float = 0.0  # deposits minus withdrawals on that day


class Series(Model):
    id: str  # the account id or book id the points belong to
    points: list[ValuePoint]


class Step(Model):
    label: str  # "Universe", "Entry", "Protect", "Exit"
    title: str
    text: str
    params: list[str] = []


class Expected(Model):
    win_rate: float  # percent, 0..100
    avg_trade_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    trades_per_month: float
    sd_trade_pct: float
    distribution: list[float] = []  # share of trades (%) in each 1-point bucket from -10% to +10%
    source: str = ""
    window: str = ""
    cagr_pct: float | None = None  # the backtest's yearly return
    max_drawdown_pct: float | None = None  # the backtest's worst drop, negative


class WatchItem(Model):
    """A name close to a signal, for "Where the money works"."""

    symbol: str
    label: str  # what is measured, e.g. "RSI(2)"
    value: float | None = None
    note: str = ""


class Strategy(Model):
    id: str
    name: str
    summary: str = ""
    steps: list[Step] = []
    sizing: str = ""
    expected: Expected | None = None
    review_at_trades: int | None = None
    watch: list[WatchItem] = []


class Book(Model):
    id: str
    name: str
    money: Money
    strategy_id: str
    account_id: str | None = None
    status: Literal["running", "paused", "parked"]
    started: dt.date
    value: float
    slots_total: int | None = None
    next_run: AwareDatetime | None = None


class Position(Model):
    book_id: str
    symbol: str
    quantity: float
    entry_price: float
    last_price: float
    stop_price: float | None = None
    opened: dt.date
    note: str = ""


class Trade(Model):
    book_id: str
    symbol: str
    opened: dt.date
    closed: dt.date
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float
    r_multiple: float | None = None
    exit_reason: str = ""


class Bar(Model):
    date: dt.date
    open: float
    high: float
    low: float
    close: float


class IndicatorLine(Model):
    value: float
    label: str  # "buy under 10"


class Indicator(Model):
    label: str  # "RSI(2)"
    values: list[float | None]  # aligned with the chart's bars; None where it isn't defined yet
    lines: list[IndicatorLine] = []  # thresholds, drawn dotted


class TradeChart(Model):
    """Daily bars around one closed trade. It matches a Trade by (book_id, symbol, opened); a chart whose bars
    don't include the open date, or that matches no trade, is ignored."""

    book_id: str
    symbol: str
    opened: dt.date
    bars: list[Bar]
    indicator: Indicator | None = None
    stop: float | None = None


class Run(Model):
    time: AwareDatetime
    label: str
    book_id: str | None = None
    status: Literal["done", "due", "late", "failed", "paused"]
    detail: str = ""


class Alert(Model):
    level: Literal["serious", "warning", "note"]
    title: str
    detail: str = ""
    # a page inside kestrel ("/books"), or empty: never another site, including "//host" and "/\host",
    # which browsers read as a link to another host
    link: str = Field(default="", pattern=r"^(/([^/\\\s].*)?)?$")


class Benchmark(Model):
    symbol: str
    label: str
    points: list[ValuePoint]  # value = the close


class Snapshot(Model):
    contract_version: str = CONTRACT_VERSION
    generated_at: AwareDatetime
    sources: list[Source] = []
    accounts: list[Account] = []
    holdings: list[Holding] = []
    account_history: list[Series] = []
    books: list[Book] = []
    book_history: list[Series] = []
    positions: list[Position] = []
    trades: list[Trade] = []
    trade_charts: list[TradeChart] = []
    strategies: list[Strategy] = []
    runs: list[Run] = []
    alerts: list[Alert] = []
    benchmark: Benchmark | None = None

    @field_validator("contract_version")
    @classmethod
    def _same_major(cls, value: str) -> str:
        if value.split(".")[0] != CONTRACT_VERSION:
            raise ValueError(
                f"unsupported contract version {value!r}; this kestrel reads major version {CONTRACT_VERSION}"
            )
        return value


_LIST_FIELDS = (
    "sources", "accounts", "holdings", "account_history", "books", "book_history",
    "positions", "trades", "trade_charts", "strategies", "runs", "alerts",
)


def merge(snapshots: list[Snapshot], generated_at: dt.datetime) -> Snapshot:
    """Combine the snapshots of several connectors into one. The first benchmark found wins."""
    fields: dict[str, object] = {name: [item for s in snapshots for item in getattr(s, name)] for name in _LIST_FIELDS}
    fields["benchmark"] = next((s.benchmark for s in snapshots if s.benchmark is not None), None)
    return Snapshot(generated_at=generated_at, **fields)
````


`src/kestrel/connectors/demo.py`:

````python
"""Fictional demo data: a believable year for "Alex".

Deterministic for a seed: the numbers never change, only the dates move so the last point is today.
Nothing here is anyone's real account; the tickers are ordinary large caps and sector funds.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..contract import (
    Account,
    Bar,
    Benchmark,
    Book,
    Expected,
    Holding,
    Indicator,
    IndicatorLine,
    Position,
    Run,
    Series,
    Snapshot,
    Source,
    Step,
    Strategy,
    Trade,
    TradeChart,
    ValuePoint,
    WatchItem,
)
from ..metrics import rsi

DAYS = 262  # about a year of weekdays
MARKET_DRIFT, MARKET_VOL = 0.00022, 0.0085  # a daily market factor every account leans on
STOCKS = ["HD", "LOW", "MRK", "PEP", "WMT", "TXN", "MCD", "KO", "ABT", "UNP", "ORCL", "COST", "UNH", "CSCO", "HON"]
FUNDS = ["XLE", "XLK", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "SPY"]
# backtest share of trades (%) per 1-point bucket from -10% to +10%; sums to 100
RSI2_DISTRIBUTION = [
    0.2, 3.1, 1.2, 0.3, 0.6, 1.1, 2.0, 4.9, 9.2, 10.9, 11.8, 14.6, 17.3, 12.1, 6.4, 2.6, 1.0, 0.4, 0.2, 0.1,
]
CHARTED = 8  # each book's most recent closed trades that get a chart
CHART_BARS = 30  # sessions of daily bars per chart
RSI2_LINES = [IndicatorLine(value=10, label="buy under 10"), IndicatorLine(value=70, label="sell over 70")]
# what the long-term accounts hold: (symbol, name, share of the account, cost as a share of today's value, or None
# when the broker never reported it); what is left over is cash
LONG_TERM_HOLDINGS = {
    "roth": [("SPY", "S&P 500 index fund", 0.62, 0.78), ("XLV", "Health care sector fund", 0.21, 0.93),
             ("XLP", "Consumer staples sector fund", 0.16, 1.04)],
    "brokerage": [("SPY", "S&P 500 index fund", 0.38, 0.81), ("XLK", "Technology sector fund", 0.22, 0.74),
                  ("COST", "Costco", 0.12, 0.66), ("HD", "Home Depot", 0.10, 0.97),
                  ("XLE", "Energy sector fund", 0.08, 1.12), ("KO", "Coca-Cola", 0.05, None),
                  ("XLI", "Industrials sector fund", 0.04, 0.90)],
}
PRICES = {"SPY": 661.20, "XLV": 142.35, "XLP": 79.10, "XLK": 281.40, "COST": 912.55, "HD": 404.66, "XLE": 88.25,
          "KO": 69.90, "XLI": 151.30}
NAMES = {"MSFT": "Microsoft", "CAT": "Caterpillar", "PG": "Procter & Gamble", "JPM": "JPMorgan Chase"}


def weekdays_ending(end: date, count: int) -> list[date]:
    """The `count` weekdays up to and including `end` (or the Friday before, on a weekend), oldest first."""
    days: list[date] = []
    day = end
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return days[::-1]


def _next_weekday_at(now: datetime, at: time) -> datetime:
    candidate = datetime.combine(now.date(), at, tzinfo=now.tzinfo)
    while candidate <= now or candidate.weekday() >= 5:
        candidate = datetime.combine(candidate.date() + timedelta(days=1), at, tzinfo=now.tzinfo)
    return candidate


def _monthly(days: list[date], amount: float) -> list[float]:
    return [amount if i > 0 and days[i].month != days[i - 1].month else 0.0 for i in range(len(days))]


def _walk(rng: random.Random, start: float, market: list[float], beta: float, drift: float, vol: float,
          flows: list[float]) -> list[float]:
    values = [start]
    for i in range(1, len(market)):
        step = drift + beta * market[i] + rng.gauss(0.0, vol)
        values.append(round(values[-1] * (1.0 + step) + flows[i], 2))
    return values


def _points(days: list[date], values: list[float], flows: list[float]) -> list[ValuePoint]:
    return [ValuePoint(date=d, value=v, net_flow=f) for d, v, f in zip(days, values, flows)]


def _holdings(account_id: str, value: float) -> list[Holding]:
    """Whole thousandths of a share, so the cash left over is never negative."""
    out = []
    for symbol, name, share, cost in LONG_TERM_HOLDINGS[account_id]:
        price = PRICES[symbol]
        quantity = math.floor(value * share / price * 1000) / 1000
        worth = round(quantity * price, 2)
        out.append(Holding(account_id=account_id, symbol=symbol, name=name, quantity=quantity, price=price,
                           value=worth, cost_basis=round(worth * cost, 2) if cost is not None else None))
    return out


def _cash(holdings: list[Holding], account_id: str, value: float) -> float:
    return round(value - sum(h.value for h in holdings if h.account_id == account_id), 2)


def _trades(rng: random.Random, book_id: str, days: list[date], count: int, *, win_p: float, win_mu: float,
            loss_mu: float, stop_every: int = 0, stop_pct: float | None = None, hold: tuple[int, int] = (1, 6),
            lot: float = 3000.0, pool: list[str] = STOCKS) -> list[Trade]:
    trades: list[Trade] = []
    span = max(1, len(days) - 8)
    for k in range(count):
        opened_i = min(len(days) - 2, 2 + (k * span) // count + rng.randint(0, 2))
        closed_i = min(opened_i + rng.randint(*hold), len(days) - 2)
        if stop_every and k % stop_every == stop_every - 1:
            ret, reason = -(stop_pct or 8.0) - rng.random() * 0.4, "stop"
        elif rng.random() < win_p:
            ret, reason = win_mu * (0.3 + rng.random() * 1.4), "signal"
        else:
            ret, reason = loss_mu * (0.3 + rng.random() * 1.4), "signal"
        entry = round(40 + rng.random() * 460, 2)
        quantity = max(1, int(lot // entry))
        exit_price = round(entry * (1 + ret / 100), 2)
        trades.append(Trade(
            book_id=book_id, symbol=pool[rng.randrange(len(pool))], opened=days[opened_i], closed=days[closed_i],
            entry_price=entry, exit_price=exit_price, quantity=quantity, pnl=round((exit_price - entry) * quantity, 2),
            return_pct=round(ret, 2), r_multiple=round(ret / stop_pct, 2) if stop_pct else None, exit_reason=reason,
        ))
    return trades


def _chart(trade: Trade, days: list[date], seed: str, rsi2: bool) -> TradeChart:
    """About 30 sessions of bars around a trade: the entry bar opens at the entry price and the exit bar at the exit
    price (a same-day trade closes at it). Mean reversion adds RSI(2) and its 8% stop."""
    rng = random.Random(seed)
    e, x = days.index(trade.opened), days.index(trade.closed)
    end = min(len(days) - 1, x + 5)
    start = max(0, end - CHART_BARS + 1)
    opens: dict[int, float] = {e: trade.entry_price}
    gaps = {i: rng.gauss(0.0, 0.002) for i in range(start, end + 1)}  # each close to the next open
    if x > e:
        opens[x] = trade.exit_price
        for i in range(e + 1, x):
            t = (i - e) / (x - e)
            wobble = rng.gauss(0.0, 0.012) * (t * (1 - t)) ** 0.5
            opens[i] = trade.entry_price + (trade.exit_price - trade.entry_price) * t + trade.entry_price * wobble
    else:
        opens[e + 1] = trade.exit_price  # sold at the close: the entry bar closes at the exit price
        gaps[e] = 0.0
    for i in range(e - 1, start - 1, -1):  # back from the entry: a slide into the signal, an uptrend before it
        move = -0.008 - rng.random() * 0.012 if i >= e - 2 else rng.gauss(0.002, 0.012)
        opens[i] = opens[i + 1] / (1 + move)
    for i in range(max(opens) + 1, end + 1):
        opens[i] = opens[i - 1] * (1 + rng.gauss(0.001, 0.012))
    bars: list[Bar] = []
    for i in range(start, end + 1):
        o = round(opens[i], 2)
        c = round(opens[i + 1] * (1 + gaps[i]) if i < end else o * (1 + rng.gauss(0.0, 0.01)), 2)
        high = round(max(o, c) * (1 + abs(rng.gauss(0.0, 0.005))), 2)
        low = round(min(o, c) * (1 - abs(rng.gauss(0.0, 0.005))), 2)
        bars.append(Bar(date=days[i], open=o, high=high, low=low, close=c))
    indicator = stop = None
    if rsi2:
        values = [None if v is None else round(v, 1) for v in rsi([b.close for b in bars])]
        indicator = Indicator(label="RSI(2)", values=values, lines=RSI2_LINES)
        stop = round(trade.entry_price * 0.92, 2)
    return TradeChart(book_id=trade.book_id, symbol=trade.symbol, opened=trade.opened, bars=bars,
                      indicator=indicator, stop=stop)


def _charts(book: Book, trades: list[Trade], days: list[date], seed: int) -> list[TradeChart]:
    own = [t for t in trades if t.book_id == book.id]
    recent = sorted(range(len(own)), key=lambda k: (own[k].closed, own[k].opened, own[k].symbol))[-CHARTED:]
    # seeded by the trade's place in its book, so a chart keeps its shape as the dates move
    return [_chart(own[k], days, f"{seed}:{book.id}:{k}", book.strategy_id == "rsi2") for k in recent]


STRATEGIES = [
    Strategy(
        id="rsi2", name="Mean reversion", summary="Buys large, liquid stocks after a sharp short-term drop inside an "
        "uptrend, and sells into the bounce — usually within a week.",
        steps=[
            Step(label="Universe", title="Large US stocks", text="Only while the stock sits above its 200-day average",
                 params=["200-day filter"]),
            Step(label="Entry", title="Buy after a sharp drop", text="RSI(2) closes under 10 → buy at the next open",
                 params=["RSI(2) < 10", "next open"]),
            Step(label="Protect", title="A stop rests at the broker", text="8% under the buy price — never lowered",
                 params=["−8% stop", "GTC"]),
            Step(label="Exit", title="Sell into the bounce",
                 text="RSI(2) closes over 70 → sell at the next open, or the stop fills",
                 params=["RSI(2) > 70", "or stop"]),
        ],
        sizing="Each position is the account value ÷ 6, at most 5 open.",
        expected=Expected(win_rate=66, avg_trade_pct=0.84, avg_win_pct=2.45, avg_loss_pct=-2.28, trades_per_month=3.1,
                          sd_trade_pct=3.0, distribution=RSI2_DISTRIBUTION, source="backtest", window="2006–2020",
                          cagr_pct=23.4, max_drawdown_pct=-11.7),
        review_at_trades=50,
        watch=[WatchItem(symbol="KO", label="RSI(2)", value=12.4), WatchItem(symbol="ABT", label="RSI(2)", value=16.8),
               WatchItem(symbol="UNP", label="RSI(2)", value=19.1)],
    ),
    Strategy(
        id="ibs", name="ETF close strength",
        summary="Buys a sector fund that closes near the bottom of its day's range and holds until it closes near "
        "the top.",
        expected=Expected(win_rate=62, avg_trade_pct=0.35, avg_win_pct=1.3, avg_loss_pct=-1.2, trades_per_month=6.0,
                          sd_trade_pct=1.6, source="backtest", window="2000–2020"),
        review_at_trades=30,
    ),
    Strategy(
        id="leader", name="Opening leader", summary="Buys the strongest name of the first fifteen minutes and is flat "
        "before lunch.",
        expected=Expected(win_rate=52, avg_trade_pct=0.10, avg_win_pct=1.0, avg_loss_pct=-0.9, trades_per_month=15.0,
                          sd_trade_pct=1.2, source="backtest", window="2021–2024"),
        review_at_trades=30,
    ),
    Strategy(
        id="verticals", name="Options verticals", summary="Expresses swing signals as debit spreads.",
        expected=Expected(win_rate=55, avg_trade_pct=4.0, avg_win_pct=38.0, avg_loss_pct=-40.0, trades_per_month=4.0,
                          sd_trade_pct=35.0, source="backtest", window="2015–2020"),
        review_at_trades=30,
    ),
]


class DemoConnector:
    """Serves the same fictional year to anyone who runs kestrel without a profile."""

    def __init__(self, source_id: str, tz: ZoneInfo, seed: int = 340) -> None:
        self.source_id = source_id
        self.tz = tz
        self.seed = seed

    def snapshot(self, now: datetime) -> Snapshot:
        local = now.astimezone(self.tz)
        days = weekdays_ending(local.date(), DAYS)
        rng = random.Random(self.seed)
        market = [0.0] + [rng.gauss(MARKET_DRIFT, MARKET_VOL) for _ in range(DAYS - 1)]
        zero = [0.0] * DAYS

        roth_flows, brokerage_flows, savings_flows = _monthly(days, 500), _monthly(days, 550), _monthly(days, 150)
        trading_flows = zero.copy()
        trading_flows[DAYS // 3] = 1500.0
        roth = _walk(rng, 50200.0, market, 0.95, 0.0001, 0.0015, roth_flows)
        brokerage = _walk(rng, 37400.0, market, 1.0, 0.0001, 0.0018, brokerage_flows)
        trading = _walk(rng, 14200.0, market, 0.45, 0.0006, 0.0045, trading_flows)
        savings = [21500.0]
        for i in range(1, DAYS):
            savings.append(round(savings[-1] * (1 + 0.041 / 260) + savings_flows[i], 2))
        spx = _walk(rng, 560.0, market, 1.0, 0.0, 0.0015, zero)
        paper = _walk(rng, 100000.0, market, 0.5, 0.0005, 0.004, zero)
        options = _walk(rng, 100000.0, market, 0.8, -0.0002, 0.012, zero)
        paused_at = DAYS - 20
        options = options[:paused_at] + [options[paused_at - 1]] * (DAYS - paused_at)
        ibs_days, leader_days = days[-12:], days[-10:]
        ibs = _walk(rng, 3200.0, market[-12:], 0.4, 0.0012, 0.004, zero[:12])
        leader = _walk(rng, 25000.0, market[-10:], 0.2, -0.0015, 0.003, zero[:10])

        positions = [
            Position(book_id="rsi2-real", symbol="MSFT", quantity=6, entry_price=508.20, last_price=512.40,
                     opened=days[-1]),
            Position(book_id="rsi2-real", symbol="CAT", quantity=6, entry_price=468.30, last_price=474.95,
                     stop_price=430.84, opened=days[-3]),
            Position(book_id="rsi2-real", symbol="PG", quantity=20, entry_price=152.40, last_price=155.08,
                     stop_price=140.21, opened=days[-4]),
            Position(book_id="rsi2-real", symbol="JPM", quantity=10, entry_price=301.10, last_price=297.85,
                     stop_price=277.01, opened=days[-2]),
            Position(book_id="rsi2-paper", symbol="HD", quantity=45, entry_price=398.10, last_price=404.66,
                     stop_price=366.25, opened=days[-3]),
            Position(book_id="rsi2-paper", symbol="TXN", quantity=95, entry_price=190.20, last_price=188.70,
                     stop_price=174.98, opened=days[-2]),
            Position(book_id="rsi2-paper", symbol="KO", quantity=260, entry_price=69.05, last_price=69.90,
                     stop_price=63.53, opened=days[-5]),
            Position(book_id="rsi2-paper", symbol="ABT", quantity=140, entry_price=128.40, last_price=130.02,
                     stop_price=118.13, opened=days[-4]),
            Position(book_id="rsi2-paper", symbol="UNP", quantity=75, entry_price=238.55, last_price=241.10,
                     stop_price=219.47, opened=days[-1]),
            Position(book_id="ibs-paper", symbol="XLF", quantity=17, entry_price=51.20, last_price=51.62,
                     opened=days[-1], note="Exits on strength"),
        ]
        holdings = _holdings("roth", roth[-1]) + _holdings("brokerage", brokerage[-1]) + [
            # the trading account holds what the real book has open
            Holding(account_id="trading", symbol=p.symbol, name=NAMES[p.symbol], quantity=p.quantity,
                    price=p.last_price, value=round(p.quantity * p.last_price, 2),
                    cost_basis=round(p.quantity * p.entry_price, 2))
            for p in positions if p.book_id == "rsi2-real"
        ]
        as_of = datetime.combine(days[-1], time(16, 0), tzinfo=self.tz)
        accounts = [
            Account(id="roth", name="Roth IRA", institution="Brokerage A", account_type="Roth IRA",
                    category="long_term", value=roth[-1], cash=_cash(holdings, "roth", roth[-1]), as_of=as_of),
            Account(id="brokerage", name="Brokerage", institution="Brokerage A", account_type="Brokerage",
                    category="long_term", value=brokerage[-1], cash=_cash(holdings, "brokerage", brokerage[-1]),
                    as_of=as_of),
            Account(id="trading", name="Trading account", institution="Brokerage B", account_type="Individual",
                    category="trading", value=trading[-1], cash=_cash(holdings, "trading", trading[-1]), as_of=as_of),
            Account(id="savings", name="High-yield savings", institution="Bank C", account_type="Savings",
                    category="cash", value=savings[-1], cash=savings[-1], as_of=as_of),
        ]
        account_history = [
            Series(id="roth", points=_points(days, roth, roth_flows)),
            Series(id="brokerage", points=_points(days, brokerage, brokerage_flows)),
            Series(id="trading", points=_points(days, trading, trading_flows)),
            Series(id="savings", points=_points(days, savings, savings_flows)),
        ]

        at = lambda hh, mm: _next_weekday_at(local, time(hh, mm))  # noqa: E731
        books = [
            Book(id="rsi2-real", name="Mean reversion", money="real", strategy_id="rsi2", account_id="trading",
                 status="running", started=days[0] - timedelta(days=5), value=trading[-1], slots_total=5,
                 next_run=at(9, 31)),
            Book(id="rsi2-paper", name="Mean reversion", money="paper", strategy_id="rsi2", status="running",
                 started=days[0] - timedelta(days=60), value=paper[-1], slots_total=6, next_run=at(17, 30)),
            Book(id="ibs-paper", name="ETF close strength", money="paper", strategy_id="ibs", status="running",
                 started=ibs_days[0], value=ibs[-1], slots_total=4, next_run=at(15, 56)),
            Book(id="leader-paper", name="Opening leader", money="paper", strategy_id="leader", status="running",
                 started=leader_days[0], value=leader[-1], slots_total=1, next_run=at(9, 25)),
            Book(id="verticals-paper", name="Options verticals", money="paper", strategy_id="verticals",
                 status="paused", started=days[0] - timedelta(days=70), value=options[-1], slots_total=3),
        ]
        book_history = [
            Series(id="rsi2-real", points=_points(days, trading, trading_flows)),
            Series(id="rsi2-paper", points=_points(days, paper, zero)),
            Series(id="ibs-paper", points=_points(ibs_days, ibs, zero[:12])),
            Series(id="leader-paper", points=_points(leader_days, leader, zero[:10])),
            Series(id="verticals-paper", points=_points(days, options, zero)),
        ]
        trades = (
            _trades(rng, "rsi2-real", days, 34, win_p=0.72, win_mu=2.4, loss_mu=-1.4, stop_every=17, stop_pct=8.0)
            + _trades(rng, "rsi2-paper", days, 71, win_p=0.72, win_mu=2.4, loss_mu=-1.4, stop_every=17, stop_pct=8.0,
                      lot=18000.0)
            + _trades(rng, "ibs-paper", ibs_days, 7, win_p=0.6, win_mu=1.2, loss_mu=-0.9, lot=800.0, pool=FUNDS)
            + _trades(rng, "leader-paper", leader_days, 11, win_p=0.3, win_mu=1.0, loss_mu=-1.6, hold=(0, 0),
                      lot=24000.0)
            + _trades(rng, "verticals-paper", days[:paused_at], 13, win_p=0.35, win_mu=30.0, loss_mu=-35.0, lot=600.0)
        )
        sid = self.source_id
        sources = [
            Source(id=f"{sid}-portfolio", label="Portfolio", kind="data collector",
                   last_success=now - timedelta(minutes=2)),
            Source(id=f"{sid}-desk", label="Trading desk", kind="feed", last_success=now - timedelta(minutes=1)),
            Source(id=f"{sid}-paper", label="Paper broker", kind="rails", last_success=now - timedelta(minutes=6)),
            Source(id=f"{sid}-savings", label="Savings", kind="bank link", last_success=now - timedelta(hours=26),
                   status="stale"),
        ]
        return Snapshot(
            generated_at=now, sources=sources, accounts=accounts, holdings=holdings, account_history=account_history,
            books=books, book_history=book_history, positions=positions, trades=trades,
            trade_charts=[chart for book in books for chart in _charts(book, trades, days, self.seed)],
            strategies=STRATEGIES,
            runs=self._runs(local), benchmark=Benchmark(symbol="SPY", label="S&P 500", points=_points(days, spx, zero)),
        )

    def _runs(self, local: datetime) -> list[Run]:
        if local.weekday() >= 5:
            return []
        plan = [
            (time(9, 25), "Opening leader · paper", "leader-paper", "Screens at 09:45", "Screened at 09:45 · no entry"),
            (time(9, 31), "Morning run", "rsi2-real", "Places queued entries and exits",
             "1 exit sold · MSFT entry filled"),
            (time(15, 56), "ETF close entries · paper", "ibs-paper", "Buys funds that close weak",
             "Bought XLF at the close"),
            (time(17, 30), "Nightly suite", None, "Signals, paper fills, the nightly note", "Nightly note written"),
            (time(17, 45), "Evening run", "rsi2-real", "Queues the next session's entries and exits",
             "Queued 1 entry"),
            (time(19, 0), "Watchdog", None, "Checks every run reported in", "All runs reported in"),
        ]
        runs = []
        for at, label, book_id, due_detail, done_detail in plan:
            when = datetime.combine(local.date(), at, tzinfo=local.tzinfo)
            done = when <= local
            runs.append(Run(time=when, label=label, book_id=book_id, status="done" if done else "due",
                            detail=done_detail if done else due_detail))
        return runs
````


`docs/data-contract.md`:

````markdown
# The kestrel data contract

Every source kestrel reads speaks one format: a **Snapshot**. The built-in connectors produce one, and so can any
system of your own — serve a Snapshot as JSON and the `feed` connector (Phase 4) plugs it in without a line of your
system's code entering this repo.

- **Schema:** [`contract/snapshot.schema.json`](contract/snapshot.schema.json), generated from
  `src/kestrel/contract.py` (`kestrel schema`); a test fails if the two drift.
- **A complete example:** `kestrel demo` prints the demo Snapshot — a year of fictional accounts, books, trades and runs.
- **Entities and fields:** the table in the [design spec](specs/2026-09-25-kestrel-design.md#7-data-contract-v1).

## Rules

- `contract_version` is `"1"`. Within a major version changes are **additive only**; kestrel ignores fields it does
  not know, and refuses an unknown major version (the source shows as `error` with the reason).
- Every timestamp carries an offset (`2026-09-25T17:08:00-04:00`); dates are `YYYY-MM-DD`.
- Money is in the profile's currency. `net_flow` on a value point is that day's deposits minus withdrawals, so
  performance is measured net of money moving in and out.
- `status` on a source is `ok`, `stale` or `error`; kestrel also marks a source stale once its `last_success` is older
  than the profile's `stale_after` for it.
- An alert's `link` is a page inside kestrel (`/books`) or empty. A link to another site (`https://…`, `//host`) fails
  validation, so the payload is dropped and the source shows as `error`.
- A connector only reads. Nothing in the contract asks a source to change anything.
- A strategy, book or account `id` appears directly in a URL path (`/strategies/{id}`); an id must not contain `/`.

## Optional extras

The Strategy and Accounts pages draw more when a source sends these. Each is optional; without it, the page shows a
plain "not reported" state for that part and everything else still works.

- `Account.account_type`: display text for the kind of account (`Roth IRA`, `Brokerage`), shown beside the
  institution on the Accounts pages. `holdings` and `Account.cash` fill an account's holdings table.

- `trade_charts`: daily bars around a closed trade (`date`, `open`, `high`, `low`, `close`). A chart matches its
  trade by `book_id`, `symbol` and `opened`. It may carry an `indicator` drawn in its own panel under the candles
  (`label`, `values` aligned with the bars, threshold `lines`) and the trade's `stop`. A chart whose bars don't
  include the open date, or that matches no trade, is ignored.
- `Expected.cagr_pct` and `Expected.max_drawdown_pct`: the backtest's yearly return and its worst drop (a negative
  percent), plotted on "Is it worth it?".
- `Strategy.watch`: names close to a signal (`symbol`, `label`, `value`, `note`), listed under "Where the money
  works".
````


```bash
.venv/Scripts/kestrel schema > docs/contract/snapshot.schema.json
```

(This is the command the failing drift test prints.)

- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `141 passed` (`test_contract.py` 20, `test_demo_connector.py` 15); `All checks passed!`. Before the schema is regenerated, `test_generated_file_is_current[snapshot.schema.json]` fails with ``out of date: run `kestrel schema > docs/contract/snapshot.schema.json` ``. `home.json` and the other fixtures stay current: no existing demo number moved.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/contract.py src/kestrel/connectors/demo.py docs/data-contract.md docs/contract/snapshot.schema.json tests/test_contract.py tests/test_demo_connector.py
git commit -m "feat(contract): Account.account_type; the demo's accounts gain types, holdings and cash" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 2: Relative source paths, the category check, `--demo`, and `check`'s account lines

**Files:**
- Modify (replace the whole file): `src/kestrel/profile.py`, `src/kestrel/cli.py`
- Test (replace the whole file): `tests/test_profile.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `Category` (contract).
- Produces:
  - `profile.py` `_resolve_paths(raw, folder)`: `load_profile` makes a relative `path` in any `[[sources]]` block absolute against the profile file's folder (the built-in demo profile has no paths).
  - `SourceCfg._known_categories`: a `categories` table whose values aren't `long_term`, `trading`, `cash` or `other` (or that isn't a table) is a validation error, so `load_profile` raises `ProfileError` with `sources.N: Value error, unknown category 'trade' for 'Brokerage' (use long_term, trading, cash or other)`.
  - `cli.py` `_profile(args) -> (Profile, origin)`: `--demo` gives `DEMO_PROFILE` and `"built-in demo profile"`. `serve` and `check` take `--profile` or `--demo` (mutually exclusive: both is exit 2).
  - `check` collects one source at a time, prints its source lines as before, then one line per account it returned: nine spaces, the id padded to 16, the category padded to 16, the name. All of `check`'s lines are written as UTF-8 (`_emit`).

- [ ] **Step 1: Write the failing tests**

`tests/test_profile.py`:

````python
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from kestrel.profile import DEMO_PROFILE, ProfileError, load_profile, parse_duration

ROOT = Path(__file__).resolve().parents[1]


def write(tmp_path, text):
    path = tmp_path / "profile.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_committed_example_profile_loads():
    profile, origin = load_profile(ROOT / "profile.example.toml")
    assert profile.you.name == "Alex"
    assert [s.kind for s in profile.sources] == ["demo"]
    assert origin.endswith("profile.example.toml")


def test_no_profile_file_means_the_demo_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profile, origin = load_profile()
    assert profile == DEMO_PROFILE and origin == "built-in demo profile"


def test_the_demo_profile_cannot_be_changed_by_a_caller():
    with pytest.raises(ValidationError):
        DEMO_PROFILE.you.name = "Mallory"
    with pytest.raises(ValidationError):
        DEMO_PROFILE.sources[0].kind = "feed"


def test_a_profile_in_the_working_directory_is_used(tmp_path, monkeypatch):
    write(tmp_path, '[you]\nname = "Sam"\n')
    monkeypatch.chdir(tmp_path)
    profile, _ = load_profile()
    assert profile.you.name == "Sam"
    assert profile.sources[0].kind == "demo"  # sources default to demo data


def test_a_bad_setting_names_the_field(tmp_path):
    with pytest.raises(ProfileError, match=r"app\.accent"):
        load_profile(write(tmp_path, '[app]\naccent = "purple"\n'))


def test_a_typo_in_a_section_is_refused(tmp_path):
    with pytest.raises(ProfileError, match="nmae"):
        load_profile(write(tmp_path, '[you]\nnmae = "Sam"\n'))


def test_broken_toml_is_reported_with_the_path(tmp_path):
    with pytest.raises(ProfileError, match="profile.toml"):
        load_profile(write(tmp_path, "[you\nname = 1\n"))


def test_a_missing_explicit_path_is_reported(tmp_path):
    with pytest.raises(ProfileError, match="file not found"):
        load_profile(tmp_path / "nope.toml")


def test_an_unknown_time_zone_is_refused(tmp_path):
    with pytest.raises(ProfileError, match="unknown time zone"):
        load_profile(write(tmp_path, '[app]\ntimezone = "Mars/Olympus"\n'))


def test_a_currency_must_be_a_three_letter_code(tmp_path):
    with pytest.raises(ProfileError, match=r"app\.currency"):
        load_profile(write(tmp_path, '[app]\ncurrency = "EURO"\n'))
    profile, _ = load_profile(write(tmp_path, '[app]\ncurrency = "EUR"\n'))
    assert profile.app.currency == "EUR"


def test_a_profile_saved_with_a_byte_order_mark_loads(tmp_path):
    path = tmp_path / "profile.toml"
    path.write_bytes('﻿[you]\nname = "Sam"\n'.encode("utf-8"))
    assert load_profile(path)[0].you.name == "Sam"


def test_a_profile_that_is_not_utf8_is_reported_plainly(tmp_path):
    path = tmp_path / "profile.toml"
    path.write_text('[you]\nname = "Sam"\n', encoding="utf-16")
    with pytest.raises(ProfileError, match="is not UTF-8 text"):
        load_profile(path)


def test_an_unreadable_profile_is_reported_plainly(tmp_path):
    folder = tmp_path / "profile.toml"
    folder.mkdir()  # reading a folder is an OSError on every platform
    with pytest.raises(ProfileError, match="could not read"):
        load_profile(folder)


def test_duplicate_source_ids_are_refused(tmp_path):
    text = '[[sources]]\nid = "a"\nkind = "demo"\n[[sources]]\nid = "a"\nkind = "demo"\n'
    with pytest.raises(ProfileError, match="duplicate source id"):
        load_profile(write(tmp_path, text))


def test_connector_specific_keys_are_kept_for_the_connector(tmp_path):
    profile, _ = load_profile(write(tmp_path, '[[sources]]\nid = "desk"\nkind = "feed"\nurl = "http://x"\n'))
    assert getattr(profile.sources[0], "url") == "http://x"


def test_durations():
    assert parse_duration("15m") == timedelta(minutes=15)
    assert parse_duration("36h") == timedelta(hours=36)
    assert parse_duration("2d") == timedelta(days=2)
    with pytest.raises(ValueError):
        parse_duration("soon")


def test_a_relative_source_path_is_relative_to_the_profile_not_the_working_directory(tmp_path, monkeypatch):
    home, elsewhere = tmp_path / "kestrel", tmp_path / "elsewhere"
    home.mkdir()
    elsewhere.mkdir()
    absolute = (tmp_path / "other" / "warehouse.db").as_posix()
    path = write(home, '[[sources]]\nid = "portfolio"\nkind = "fdc"\npath = "../collector/data/warehouse.db"\n'
                       f'[[sources]]\nid = "second"\nkind = "fdc"\npath = "{absolute}"\n')
    monkeypatch.chdir(elsewhere)
    profile, _ = load_profile(path)
    assert Path(getattr(profile.sources[0], "path")) == (tmp_path / "collector" / "data" / "warehouse.db").resolve()
    assert Path(getattr(profile.sources[1], "path")) == Path(absolute)
    assert not hasattr(DEMO_PROFILE.sources[0], "path")


def test_an_unknown_category_is_a_profile_error(tmp_path):
    source = '[[sources]]\nid = "portfolio"\nkind = "fdc"\npath = "w.db"\n'
    with pytest.raises(ProfileError, match=r"unknown category 'trade' for 'Brokerage' \(use long_term, trading"):
        load_profile(write(tmp_path, source + '[sources.categories]\n"Brokerage" = "trade"\n'))
    with pytest.raises(ProfileError, match="categories must be a table"):
        load_profile(write(tmp_path, source + 'categories = "trading"\n'))
    profile, _ = load_profile(write(tmp_path, source + '[sources.categories]\n"brokerage-2" = "trading"\n'))
    assert getattr(profile.sources[0], "categories") == {"brokerage-2": "trading"}
````


`tests/test_cli.py`:

````python
import json
import re

import pytest

import kestrel.cli
import kestrel.server
from kestrel.cli import main
from kestrel.profile import DEMO_PROFILE

NOW = "2026-09-25T21:08:00+00:00"


def run(capsysbinary, *argv):
    code = main(list(argv))
    out, err = capsysbinary.readouterr()
    return code, out.decode("utf-8"), err.decode("utf-8")


def test_demo_prints_a_valid_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--now", NOW)
    data = json.loads(out)
    assert code == 0 and data["contract_version"] == "1" and len(data["accounts"]) == 4


def test_demo_home_is_reproducible(capsysbinary):
    first = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    second = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    assert first == second and json.loads(first)["summary"]["needs_you"] == 2


def test_schema_describes_the_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "schema")
    schema = json.loads(out)
    assert code == 0 and schema["title"] == "Snapshot" and "accounts" in schema["properties"]


def test_check_passes_on_the_demo_and_fails_on_a_bad_profile(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsysbinary, "check")
    assert code == 0 and "hello, Alex" in out and "stale" in out
    bad = tmp_path / "bad.toml"
    bad.write_text('[app]\ntheme = "neon"\n', encoding="utf-8")
    code, _, err = run(capsysbinary, "check", "--profile", str(bad))
    assert code == 2 and "app.theme" in err


def test_serve_only_ever_listens_on_this_computer(capsys):
    assert kestrel.cli.HOST == "127.0.0.1"
    with pytest.raises(SystemExit) as done:
        main(["serve", "--help"])
    out = capsys.readouterr().out
    assert done.value.code == 0 and "--port" in out and "--host" not in out


def test_check_fails_when_a_source_cannot_be_read(capsysbinary, tmp_path):
    profile = tmp_path / "p.toml"
    profile.write_text('[[sources]]\nid = "desk"\nkind = "feed"\n', encoding="utf-8")
    code, out, _ = run(capsysbinary, "check", "--profile", str(profile))
    assert code == 1 and "error" in out


def test_demo_prints_the_strategy_views(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--view", "strategies", "--now", NOW)
    assert code == 0 and [c["id"] for c in json.loads(out)["strategies"]] == ["rsi2", "ibs", "leader", "verticals"]
    code, out, _ = run(capsysbinary, "demo", "--view", "strategy", "--id", "rsi2", "--now", NOW)
    assert code == 0 and json.loads(out)["book"] == "real"
    code, out, _ = run(capsysbinary, "demo", "--view", "strategy", "--id", "rsi2", "--book", "paper", "--now", NOW)
    assert code == 0 and json.loads(out)["primary"] == "rsi2-paper"


def test_demo_strategy_needs_a_known_id(capsysbinary):
    code, _, err = run(capsysbinary, "demo", "--view", "strategy", "--now", NOW)
    assert code == 2 and "--view strategy needs --id" in err
    code, _, err = run(capsysbinary, "demo", "--view", "strategy", "--id", "nope", "--now", NOW)
    assert code == 2 and "no strategy 'nope' in the demo data" in err


def test_check_lists_each_sources_accounts_but_never_a_balance(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsysbinary, "check")
    assert code == 0
    assert [line for line in out.splitlines() if line.startswith(" " * 9)] == [
        "         roth             long_term        Roth IRA",
        "         brokerage        long_term        Brokerage",
        "         trading          trading          Trading account",
        "         savings          cash             High-yield savings",
    ]
    assert "$" not in out and not re.search(r"\d{4}", out)  # no balances, no amounts


def test_the_demo_flag_shows_the_demo_whatever_profile_toml_says(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profile.toml").write_text('[you]\nname = "Sam"\n[[sources]]\nid = "desk"\nkind = "feed"\n',
                                           encoding="utf-8")
    code, out, _ = run(capsysbinary, "check")
    assert code == 1 and "hello, Sam" in out
    code, out, _ = run(capsysbinary, "check", "--demo")
    assert code == 0 and out.startswith("profile: built-in demo profile - hello, Alex")
    served = []
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: None)
    monkeypatch.setattr(kestrel.server, "create_app", lambda profile, **kwargs: served.append(profile))
    code, out, _ = run(capsysbinary, "serve", "--demo", "--no-open")
    assert code == 0 and served == [DEMO_PROFILE] and "profile: built-in demo profile" in out
    with pytest.raises(SystemExit) as refused:
        main(["check", "--demo", "--profile", "profile.toml"])
    assert refused.value.code == 2
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_profile.py tests/test_cli.py`
Expected: `4 failed, 24 passed`: the relative path (`AssertionError: assert WindowsPath('../collector/data/warehouse.db') == …`, `PosixPath` on macOS and Linux: the path is left as written), the unknown category (`Failed: DID NOT RAISE`), the account lines (`AssertionError: assert [] == ['         ro...ield savings']`) and the demo flag (`kestrel: error: unrecognized arguments: --demo`, a `SystemExit: 2`).

- [ ] **Step 3: Implement**

`src/kestrel/profile.py`:

````python
"""The personal profile: who you are, how kestrel looks, and where your data comes from.

profile.toml is gitignored. It never holds secrets: a source names the environment variable that holds its key.
"""

from __future__ import annotations

import re
import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Literal, get_args
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .contract import Category


class ProfileError(Exception):
    """A profile problem, worded so a person can fix it."""


_DURATION = re.compile(r"^\s*(\d+)\s*([mhd])\s*$")


def parse_duration(text: str) -> timedelta:
    match = _DURATION.match(text)
    if not match:
        raise ValueError(f"not a duration: {text!r} (use a number and m, h or d, e.g. 15m, 36h, 2d)")
    amount, unit = int(match.group(1)), match.group(2)
    return {"m": timedelta(minutes=amount), "h": timedelta(hours=amount), "d": timedelta(days=amount)}[unit]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class You(_Strict):
    name: str = "there"


class App(_Strict):
    name: str = "kestrel"
    accent: Literal["rufous", "slate", "mono"] = "rufous"
    theme: Literal["system", "dark", "light"] = "system"
    gain_loss: Literal["green-red", "blue-orange"] = "green-red"
    density: Literal["comfortable", "compact"] = "comfortable"
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")  # an ISO 4217 code, e.g. USD, EUR
    timezone: str = "America/New_York"

    @field_validator("timezone")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"unknown time zone {value!r} (use an IANA name such as America/New_York)") from None
        return value


class BenchmarkCfg(_Strict):
    symbol: str = "SPY"
    label: str = "S&P 500"


class SourceCfg(BaseModel):
    # connector-specific keys (path, url, token_env, seed) are allowed and read by the connector
    model_config = ConfigDict(extra="allow", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,31}$")
    kind: str
    label: str = ""
    stale_after: str = "36h"

    @field_validator("stale_after")
    @classmethod
    def _duration(cls, value: str) -> str:
        parse_duration(value)
        return value

    @model_validator(mode="after")
    def _known_categories(self) -> SourceCfg:
        # a typo in a category must stop the profile: silently falling back would file the money under another heading
        categories = getattr(self, "categories", None)
        if categories is None:
            return self
        if not isinstance(categories, dict):
            raise ValueError("categories must be a table: account id or label = category")
        known = get_args(Category)
        for key, value in categories.items():
            if value not in known:
                raise ValueError(f"unknown category {value!r} for {key!r} (use {', '.join(known[:-1])} or {known[-1]})")
        return self

    @property
    def stale_delta(self) -> timedelta:
        return parse_duration(self.stale_after)


def _demo_sources() -> list[SourceCfg]:
    return [SourceCfg(id="demo", kind="demo", label="Demo data")]


class Profile(_Strict):
    you: You = You()
    app: App = App()
    benchmark: BenchmarkCfg = BenchmarkCfg()
    sources: list[SourceCfg] = Field(default_factory=_demo_sources)

    @model_validator(mode="after")
    def _unique_source_ids(self) -> Profile:
        ids = [s.id for s in self.sources]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate source id(s): {', '.join(dupes)}")
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.app.timezone)


DEMO_PROFILE = Profile(you=You(name="Alex"))


def _resolve_paths(raw: dict, folder: Path) -> None:
    """A relative `path` in a source is relative to the profile's own folder, not to wherever kestrel was started."""
    sources = raw.get("sources")
    for source in sources if isinstance(sources, list) else []:
        if isinstance(source, dict) and isinstance(source.get("path"), str) and not Path(source["path"]).is_absolute():
            source["path"] = str((folder / source["path"]).resolve())


def load_profile(path: Path | None = None) -> tuple[Profile, str]:
    """Load a profile. With no path: ./profile.toml when it exists, else the built-in demo profile.

    Returns the profile and where it came from (for `kestrel check`). Relative source paths come back absolute.
    """
    if path is None:
        path = Path("profile.toml")
        if not path.exists():
            return DEMO_PROFILE, "built-in demo profile"
    try:
        text = path.read_text(encoding="utf-8-sig")  # -sig: Windows editors often save a byte-order mark
    except FileNotFoundError:
        raise ProfileError(f"{path}: file not found") from None
    except UnicodeDecodeError:
        raise ProfileError(f"{path}: is not UTF-8 text (save it as UTF-8 and try again)") from None
    except OSError as exc:
        raise ProfileError(f"{path}: could not read the file ({exc.strerror or exc})") from None
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"{path}: {exc}") from None
    _resolve_paths(raw, path.parent)
    try:
        return Profile.model_validate(raw), str(path)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors())
        raise ProfileError(f"{path}: {problems}") from None
````


`src/kestrel/cli.py`:

````python
"""kestrel's command line: serve, check, demo, schema."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from .contract import Snapshot
from .profile import DEMO_PROFILE, Profile, ProfileError, load_profile

HOST = "127.0.0.1"  # never listen beyond this computer


def _emit(text: str) -> None:
    """Write UTF-8 whatever the console's code page is (redirected output on Windows is cp1252 otherwise)."""
    sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
    sys.stdout.flush()


def _now(text: str | None) -> datetime:
    if not text:
        return datetime.now(timezone.utc)
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise SystemExit("--now needs a time zone offset, e.g. 2026-09-25T21:08:00+00:00")
    return value


def _profile(args: argparse.Namespace) -> tuple[Profile, str]:
    """--demo shows the demo whatever profile.toml says; otherwise --profile, else ./profile.toml, else the demo."""
    if args.demo:
        return DEMO_PROFILE, "built-in demo profile"
    return load_profile(args.profile)


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .server import WEB_DIST, create_app

    try:
        profile, origin = _profile(args)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    url = f"http://{HOST}:{args.port}"
    print(f"kestrel {url} - profile: {origin} - read-only - Ctrl+C to stop")
    if not (WEB_DIST / "index.html").is_file():
        print("web/dist is not built yet: run `npm ci && npm run build` in web/ (the API works without it)")
    if not args.no_open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(profile), host=HOST, port=args.port, log_level="warning")
    return 0


def _check(args: argparse.Namespace) -> int:
    from .connectors import collect
    from .views.home import age_text

    try:
        profile, origin = _profile(args)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc)
    # UTF-8 out: a source's detail or an account's name can carry any character
    _emit(f"profile: {origin} - hello, {profile.you.name}")
    failed = False
    for cfg in profile.sources:
        # one source at a time, so each source's accounts print under it; never a balance
        part = collect(profile.model_copy(update={"sources": [cfg]}), now)
        for s in part.sources:
            age = f"{age_text(now - s.last_success)} ago" if s.last_success else "never"
            _emit(f"  {s.status:<5}  {s.label:<16} {s.kind:<16} {age}  {s.detail}".rstrip())
            failed = failed or s.status == "error"
        for a in part.accounts:
            _emit(f"{'':9}{a.id:<16} {a.category:<16} {a.name}")
    return 1 if failed else 0


def _demo(args: argparse.Namespace) -> int:
    from .connectors import collect
    from .views.home import home_view
    from .views.shell import shell_view
    from .views.strategy import strategies_view, strategy_view

    now = _now(args.now)
    snapshot = collect(DEMO_PROFILE, now)
    if args.view == "home":
        _emit(home_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "shell":
        _emit(shell_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "strategies":
        _emit(strategies_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "strategy":
        if not args.id:
            print("--view strategy needs --id, e.g. --id rsi2", file=sys.stderr)
            return 2
        view = strategy_view(snapshot, DEMO_PROFILE, now, args.id, args.book)
        if view is None:
            print(f"no strategy {args.id!r} in the demo data", file=sys.stderr)
            return 2
        _emit(view.model_dump_json(indent=2))
    else:
        _emit(snapshot.model_dump_json(indent=2))
    return 0


def _schema(args: argparse.Namespace) -> int:
    _emit(json.dumps(Snapshot.model_json_schema(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kestrel", description="A calm, read-only home for all your money.")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the dashboard on this computer")
    serve.add_argument("--port", type=int, default=8030)
    serve.add_argument("--no-open", action="store_true", help="don't open a browser")
    serve.set_defaults(run=_serve)
    check = sub.add_parser("check", help="validate the profile and try every source")
    check.set_defaults(run=_check)
    for command in (serve, check):
        which = command.add_mutually_exclusive_group()
        which.add_argument("--profile", type=Path, help="profile file (default: ./profile.toml, else demo data)")
        which.add_argument("--demo", action="store_true", help="show the demo data, whatever profile.toml says")
    demo = sub.add_parser("demo", help="print the demo data as JSON (an example feed payload)")
    demo.add_argument("--view", choices=["snapshot", "home", "shell", "strategies", "strategy"], default="snapshot")
    demo.add_argument("--id", help="the strategy --view strategy shows, e.g. rsi2")
    demo.add_argument("--book", choices=["real", "paper"], default="real", help="the money --view strategy shows")
    demo.add_argument("--now", help="ISO time with offset, for reproducible output")
    demo.set_defaults(run=_demo)
    schema = sub.add_parser("schema", help="print the data contract as JSON Schema")
    schema.set_defaults(run=_schema)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `145 passed` (`test_profile.py` 18, `test_cli.py` 10); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/profile.py src/kestrel/cli.py tests/test_profile.py tests/test_cli.py
git commit -m "feat(profile,cli): source paths relative to the profile, a category check, --demo, and check's account lines" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 3: A fictional warehouse, and the `fdc` connector, part 1: open, check, name and file the accounts

**Files:**
- Create: `tests/fdc_fixture.py` (a test helper, written with the tests), `src/kestrel/connectors/fdc.py`
- Modify (replace the whole file): `src/kestrel/connectors/base.py`
- Test (create): `tests/test_fdc_connector.py`

**Interfaces:**
- Produces:
  - `tests/fdc_fixture.py`: `SCHEMA` (the collector's `schema_version`, `accounts`, `securities`, `position_snapshots`, `cash_balances`, `transactions`, `prices`, `sync_runs`, `holdings_daily`, `cash_daily` tables and `positions_latest`, `account_values_daily` views, copied from its migrations 0001–0003); `Warehouse(path, *, version=4, without=(), wal=False)` with `account`, `snapshot`, `day`, `flow`, `prices`, `run` and `close() -> Path`; `d(day)` (a day in September 2026); `household(folder, name="warehouse.db", **options) -> Path`: Alex's five fictional accounts (a Roth IRA with replayed history and flows of every kind, a brokerage whose snapshot and history share a day, a trading account with a margin debit and no history, a crypto account with history only, a closed 401(k)).
  - `base.py` `ConnectorError(Exception)`: a source that can't be read, worded for a person.
  - `fdc.py`: `connect(path, timeout=5.0)` (a context manager: `no warehouse at <path>` before SQLite is touched, then `mode=ro` and `query_only`, always closed); `check_schema(conn, path)` (not a warehouse / schema version under 3 / missing tables and views, each ending `update financial-data-collector and run \`fdc sync\``); `slug(label)`, `account_ids(labels)`; `institution_text(code)`, `type_text(code)`, `category_of(account_type)`; `last_success(conn)` (the latest `ok` `derive` run, else any `ok` run, else `None`); `FdcConnector(source_id, label, path, categories=None, timeout=5.0).snapshot(now)` returning the source (`kind="fdc"`, stale when it has never synced, detail `"5 accounts"` plus a note for a `categories` entry that matches no account) and the accounts, valued from each one's latest `account_values_daily` row at 16:00 New York. Any other SQLite error becomes `the warehouse couldn't be read: <error>`.

- [ ] **Step 1: Write the failing tests**

`tests/fdc_fixture.py`:

````python
"""A small, fictional financial-data-collector warehouse for the fdc connector's tests.

The tables and views are the subset of the collector's schema the connector reads, copied from its migrations
(financial-data-collector: src/financial_data_collector/migrations/0001_init.sql, 0002_views.sql and
0003_derived.sql), so the connector meets the same shapes. The accounts, symbols and numbers are made up.
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
  first_seen    TEXT NOT NULL
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

    def __init__(self, path: Path, *, version: int = 4, without: tuple[str, ...] = (), wal: bool = False) -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        if wal:
            self.conn.execute("PRAGMA journal_mode=WAL")  # how the collector opens its own warehouse
        self.conn.executescript(";\n".join(sql for name, sql in SCHEMA.items() if name not in without) + ";")
        if "schema_version" not in without:
            self.conn.executemany("INSERT INTO schema_version VALUES (?, '2026-09-01T00:00:00Z')",
                                  [(v,) for v in range(1, version + 1)])
        self._tx = 0

    def account(self, label: str, institution: str = "fidelity", account_type: str = "brokerage") -> int:
        cur = self.conn.execute("INSERT INTO accounts (label, institution, account_type, first_seen) "
                                "VALUES (?, ?, ?, '2026-01-02')", (label, institution, account_type))
        return int(cur.lastrowid)

    def snapshot(self, account_id: int, day: Day, positions=(), cash: float | None = None) -> None:
        """A broker snapshot: positions as (symbol, description, quantity, price, market_value, cost_basis_total)."""
        for symbol, description, quantity, price, value, cost in positions:
            self.conn.execute("INSERT OR IGNORE INTO securities (symbol, description, first_seen) "
                              "VALUES (?, ?, '2026-01-02')", (symbol, description))
            self.conn.execute("INSERT INTO position_snapshots (as_of_date, account_id, symbol, quantity, price, "
                              "market_value, cost_basis_total, source) VALUES (?, ?, ?, ?, ?, ?, ?, 'fixture')",
                              (_iso(day), account_id, symbol, quantity, price, value, cost))
        if cash is not None:
            self.conn.execute("INSERT INTO cash_balances (as_of_date, account_id, amount, source) "
                              "VALUES (?, ?, ?, 'fixture')", (_iso(day), account_id, cash))

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
````


`tests/test_fdc_connector.py`:

````python
import datetime as dt
import os
import sqlite3
from zoneinfo import ZoneInfo

import pytest
from fdc_fixture import Warehouse, household

from kestrel.connectors.base import ConnectorError
from kestrel.connectors.fdc import FdcConnector, category_of, connect, institution_text, slug, type_text

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
NY = ZoneInfo("America/New_York")


def connector(path, **options):
    return FdcConnector("portfolio", "Portfolio", path, **options)


@pytest.fixture
def warehouse(tmp_path):
    return household(tmp_path)


def test_no_file_is_an_error_and_sqlite_never_creates_one(tmp_path):
    path = tmp_path / "data" / "warehouse.db"
    with pytest.raises(ConnectorError, match=r"^no warehouse at .*warehouse\.db$"):
        connector(path).snapshot(NOW)
    assert not path.parent.exists()


@pytest.mark.parametrize("gone", ["holdings_daily", "positions_latest"])
def test_a_missing_table_or_view_names_itself_and_the_fix(tmp_path, gone):
    path = Warehouse(tmp_path / "w.db", without=(gone,)).close()
    with pytest.raises(ConnectorError) as error:
        connector(path).snapshot(NOW)
    assert str(error.value) == f"this warehouse is missing {gone}: update financial-data-collector and run `fdc sync`"


def test_an_old_schema_version_is_refused(tmp_path):
    path = Warehouse(tmp_path / "w.db", version=2).close()
    with pytest.raises(ConnectorError) as error:
        connector(path).snapshot(NOW)
    assert str(error.value) == ("this warehouse is at schema version 2 and kestrel needs 3: "
                                "update financial-data-collector and run `fdc sync`")


def test_an_empty_file_or_another_kind_of_file_is_not_a_warehouse(tmp_path):
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    with pytest.raises(ConnectorError, match="empty.db is not a financial-data-collector warehouse"):
        connector(empty).snapshot(NOW)
    notes = tmp_path / "notes.db"
    notes.write_text("shopping list\n" * 200, encoding="utf-8")
    with pytest.raises(ConnectorError, match="^the warehouse couldn't be read: file is not a database$"):
        connector(notes).snapshot(NOW)


def test_the_connection_is_read_only_and_a_snapshot_leaves_the_file_untouched(warehouse):
    before = warehouse.read_bytes()
    with connect(warehouse) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO accounts (label, first_seen) VALUES ('Mallory', '2026-01-02')")
    connector(warehouse).snapshot(NOW)
    assert warehouse.read_bytes() == before
    assert os.listdir(warehouse.parent) == ["warehouse.db"]  # not even a journal left behind


def test_a_warehouse_locked_mid_sync_is_an_error_and_the_next_read_recovers(warehouse):
    writer = sqlite3.connect(warehouse)
    writer.execute("BEGIN EXCLUSIVE")  # a sync holding the whole file, as an older journal mode does
    try:
        with pytest.raises(ConnectorError, match="^the warehouse couldn't be read: database is locked$"):
            connector(warehouse, timeout=0.1).snapshot(NOW)
    finally:
        writer.rollback()
        writer.close()
    assert len(connector(warehouse).snapshot(NOW).accounts) == 5


def test_a_sync_in_progress_on_a_wal_warehouse_reads_the_last_committed_data(tmp_path):
    path = household(tmp_path, wal=True)  # the collector's own journal mode
    writer = sqlite3.connect(path)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("DELETE FROM accounts WHERE label = 'Alex Crypto'")
    try:
        assert len(connector(path, timeout=0.1).snapshot(NOW).accounts) == 5
    finally:
        writer.rollback()
        writer.close()


def test_a_folder_with_spaces_a_hash_and_a_percent_in_its_name_still_opens(tmp_path):
    folder = tmp_path / "Alex money #1 at 100%"
    folder.mkdir()
    assert len(connector(household(folder)).snapshot(NOW).accounts) == 5


def test_ids_are_slugs_of_labels_and_a_clash_gets_a_number(tmp_path):
    w = Warehouse(tmp_path / "w.db")
    for label in ["Alex Brokerage", "alex brokerage!", "Épargne · Alex", "★ ★ ★", "—", "Alex  Brokerage 2"]:
        w.account(label)
    accounts = connector(w.close()).snapshot(NOW).accounts
    assert [a.id for a in accounts] == [
        "alex-brokerage", "alex-brokerage-2", "epargne-alex", "account", "account-2", "alex-brokerage-2-2"]
    assert accounts[2].name == "Épargne · Alex"
    assert slug("Alex's 401(k)") == "alex-s-401-k"


def test_names_institutions_and_types_read_the_way_a_person_writes_them(warehouse):
    accounts = connector(warehouse).snapshot(NOW).accounts
    assert [(a.id, a.institution, a.account_type) for a in accounts] == [
        ("alex-roth-ira", "Fidelity", "Roth IRA"), ("alex-brokerage", "Fidelity", "Brokerage"),
        ("alex-trading", "Webull", "Brokerage"), ("alex-crypto", "Coinbase", "Crypto"),
        ("alex-old-401k", "Fidelity", "401(k)")]
    assert [institution_text(c) for c in ["unknown", "charles_schwab"]] == ["", "Charles Schwab"]
    assert [type_text(c) for c in ["traditional_ira", "sep_ira", "joint_tenants", "other"]] == [
        "Traditional IRA", "SEP IRA", "Joint Tenants", "Other"]


def test_categories_come_from_the_type_unless_the_profile_names_the_account(warehouse):
    by_type = connector(warehouse).snapshot(NOW)
    assert {a.id: a.category for a in by_type.accounts} == {
        "alex-roth-ira": "long_term", "alex-brokerage": "long_term", "alex-trading": "long_term",
        "alex-crypto": "other", "alex-old-401k": "long_term"}
    assert [category_of(t) for t in ["hsa", "checking", "money_market", "crypto", "joint"]] == [
        "long_term", "cash", "cash", "other", "other"]
    mapped = connector(warehouse, categories={
        "alex-trading": "trading", "Alex Crypto": "cash", "alex-crypto": "trading", "brokerage-9": "cash",
    }).snapshot(NOW)
    categories = {a.id: a.category for a in mapped.accounts}
    assert (categories["alex-trading"], categories["alex-crypto"]) == ("trading", "trading")  # an id outranks a label
    assert mapped.sources[0].detail.endswith("no account matches categories 'brokerage-9'")


def test_value_and_cash_come_from_the_latest_snapshot_at_the_us_close(warehouse):
    accounts = {a.id: a for a in connector(warehouse).snapshot(NOW).accounts}
    assert (accounts["alex-brokerage"].value, accounts["alex-brokerage"].cash) == (4500.0, 500.0)
    assert (accounts["alex-trading"].value, accounts["alex-trading"].cash) == (550.0, -200.0)  # a margin debit
    assert accounts["alex-brokerage"].as_of == dt.datetime(2026, 9, 25, 16, 0, tzinfo=NY)
    assert accounts["alex-old-401k"].value == 0.0


def test_last_success_is_the_latest_good_derive_run(tmp_path, warehouse):
    source = connector(warehouse).snapshot(NOW).sources[0]
    assert (source.id, source.label, source.kind, source.status) == ("portfolio", "Portfolio", "fdc", "ok")
    assert source.last_success == dt.datetime(2026, 9, 25, 12, 5, tzinfo=dt.timezone.utc)
    w = Warehouse(tmp_path / "other.db")
    w.run("prices", "ok", "2026-09-24T08:00:00")  # no offset: UTC
    w.run("derive", "error", "2026-09-25T08:00:00Z")
    assert connector(w.close()).snapshot(NOW).sources[0].last_success == dt.datetime(2026, 9, 24, 8,
                                                                                     tzinfo=dt.timezone.utc)
    never = connector(Warehouse(tmp_path / "never.db").close()).snapshot(NOW).sources[0]
    assert (never.last_success, never.status) == (None, "stale")
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_fdc_connector.py`
Expected: a collection error, `ImportError: cannot import name 'ConnectorError' from 'kestrel.connectors.base'` (`1 error`).

- [ ] **Step 3: Implement**

`src/kestrel/connectors/base.py`:

````python
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


class ConnectorError(Exception):
    """A source that can't be read, worded so a person can fix it. It shows as that source's error."""
````


`src/kestrel/connectors/fdc.py`:

````python
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
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `159 passed` (`test_fdc_connector.py` 14: the missing-table test runs twice, for a table and a view); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add tests/fdc_fixture.py tests/test_fdc_connector.py src/kestrel/connectors/base.py src/kestrel/connectors/fdc.py
git commit -m "feat(fdc): open the collector's warehouse read-only, check its schema, name and file its accounts" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 4: The `fdc` connector, part 2: history and money moved, holdings, the benchmark; registered

**Files:**
- Modify (replace the whole file): `src/kestrel/connectors/fdc.py`, `src/kestrel/connectors/__init__.py`
- Test (replace the whole file): `tests/test_fdc_connector.py`

**Interfaces:**
- Consumes: `BenchmarkCfg` (profile); Task 3's fixture and helpers.
- Produces:
  - `fdc.py` `HISTORY` (each account's `SUM(holdings_daily.market_value)` plus `cash_daily.amount` per day, the join `portfolio_daily_full` uses, kept per account) and `history(conn)`; `FLOWS` and `flows(conn, days)` (a contribution counts as its signed amount, a withdrawal as `-abs(amount)`, a transfer as its signed amount; a flow on a day with no point goes to the next point, after the last point it is dropped); `FdcConnector(..., benchmark=None, ...)`.
  - The value is the newer of the last `account_values_daily` row and the last history point (the snapshot on a tie); holdings come from `positions_latest` (no market value: left out and counted; no price: value ÷ quantity), largest first within each account; the benchmark is the profile's symbol from `prices.adj_close`, from the last close on or before the first day of account history; `detail` is `"5 accounts · 5 holdings · prices to 25 Sep"` plus notes (`1 holding left out (no market value)`, `no QQQ prices in the warehouse`, the categories note), with `prices to` read per security through the prices index.
  - `connectors.build`: kind `"fdc"` builds an `FdcConnector` with the source's `path`, `categories` and the profile's benchmark; a source without a `path` is a `ConnectorError` (a red row).

- [ ] **Step 1: Write the failing tests (replace the whole file)**

`tests/test_fdc_connector.py`:

````python
import datetime as dt
import os
import sqlite3
from zoneinfo import ZoneInfo

import pytest
from fdc_fixture import Warehouse, d, household

from kestrel.connectors import collect
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.fdc import FdcConnector, category_of, connect, institution_text, slug, type_text
from kestrel.profile import BenchmarkCfg, Profile, SourceCfg, load_profile

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
NY = ZoneInfo("America/New_York")


def connector(path, **options):
    return FdcConnector("portfolio", "Portfolio", path, **options)


@pytest.fixture
def warehouse(tmp_path):
    return household(tmp_path)


def test_no_file_is_an_error_and_sqlite_never_creates_one(tmp_path):
    path = tmp_path / "data" / "warehouse.db"
    with pytest.raises(ConnectorError, match=r"^no warehouse at .*warehouse\.db$"):
        connector(path).snapshot(NOW)
    assert not path.parent.exists()


@pytest.mark.parametrize("gone", ["holdings_daily", "positions_latest"])
def test_a_missing_table_or_view_names_itself_and_the_fix(tmp_path, gone):
    path = Warehouse(tmp_path / "w.db", without=(gone,)).close()
    with pytest.raises(ConnectorError) as error:
        connector(path).snapshot(NOW)
    assert str(error.value) == f"this warehouse is missing {gone}: update financial-data-collector and run `fdc sync`"


def test_an_old_schema_version_is_refused(tmp_path):
    path = Warehouse(tmp_path / "w.db", version=2).close()
    with pytest.raises(ConnectorError) as error:
        connector(path).snapshot(NOW)
    assert str(error.value) == ("this warehouse is at schema version 2 and kestrel needs 3: "
                                "update financial-data-collector and run `fdc sync`")


def test_an_empty_file_or_another_kind_of_file_is_not_a_warehouse(tmp_path):
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    with pytest.raises(ConnectorError, match="empty.db is not a financial-data-collector warehouse"):
        connector(empty).snapshot(NOW)
    notes = tmp_path / "notes.db"
    notes.write_text("shopping list\n" * 200, encoding="utf-8")
    with pytest.raises(ConnectorError, match="^the warehouse couldn't be read: file is not a database$"):
        connector(notes).snapshot(NOW)


def test_the_connection_is_read_only_and_a_snapshot_leaves_the_file_untouched(warehouse):
    before = warehouse.read_bytes()
    with connect(warehouse) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO accounts (label, first_seen) VALUES ('Mallory', '2026-01-02')")
    connector(warehouse).snapshot(NOW)
    assert warehouse.read_bytes() == before
    assert os.listdir(warehouse.parent) == ["warehouse.db"]  # not even a journal left behind


def test_a_warehouse_locked_mid_sync_is_an_error_and_the_next_read_recovers(warehouse):
    writer = sqlite3.connect(warehouse)
    writer.execute("BEGIN EXCLUSIVE")  # a sync holding the whole file, as an older journal mode does
    try:
        with pytest.raises(ConnectorError, match="^the warehouse couldn't be read: database is locked$"):
            connector(warehouse, timeout=0.1).snapshot(NOW)
    finally:
        writer.rollback()
        writer.close()
    assert len(connector(warehouse).snapshot(NOW).accounts) == 5


def test_a_sync_in_progress_on_a_wal_warehouse_reads_the_last_committed_data(tmp_path):
    path = household(tmp_path, wal=True)  # the collector's own journal mode
    writer = sqlite3.connect(path)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("DELETE FROM accounts WHERE label = 'Alex Crypto'")
    try:
        assert len(connector(path, timeout=0.1).snapshot(NOW).accounts) == 5
    finally:
        writer.rollback()
        writer.close()


def test_a_folder_with_spaces_a_hash_and_a_percent_in_its_name_still_opens(tmp_path):
    folder = tmp_path / "Alex money #1 at 100%"
    folder.mkdir()
    assert len(connector(household(folder)).snapshot(NOW).accounts) == 5


def test_ids_are_slugs_of_labels_and_a_clash_gets_a_number(tmp_path):
    w = Warehouse(tmp_path / "w.db")
    for label in ["Alex Brokerage", "alex brokerage!", "Épargne · Alex", "★ ★ ★", "—", "Alex  Brokerage 2"]:
        w.account(label)
    accounts = connector(w.close()).snapshot(NOW).accounts
    assert [a.id for a in accounts] == [
        "alex-brokerage", "alex-brokerage-2", "epargne-alex", "account", "account-2", "alex-brokerage-2-2"]
    assert accounts[2].name == "Épargne · Alex"
    assert slug("Alex's 401(k)") == "alex-s-401-k"


def test_names_institutions_and_types_read_the_way_a_person_writes_them(warehouse):
    accounts = connector(warehouse).snapshot(NOW).accounts
    assert [(a.id, a.institution, a.account_type) for a in accounts] == [
        ("alex-roth-ira", "Fidelity", "Roth IRA"), ("alex-brokerage", "Fidelity", "Brokerage"),
        ("alex-trading", "Webull", "Brokerage"), ("alex-crypto", "Coinbase", "Crypto"),
        ("alex-old-401k", "Fidelity", "401(k)")]
    assert [institution_text(c) for c in ["unknown", "charles_schwab"]] == ["", "Charles Schwab"]
    assert [type_text(c) for c in ["traditional_ira", "sep_ira", "joint_tenants", "other"]] == [
        "Traditional IRA", "SEP IRA", "Joint Tenants", "Other"]


def test_categories_come_from_the_type_unless_the_profile_names_the_account(warehouse):
    by_type = connector(warehouse).snapshot(NOW)
    assert {a.id: a.category for a in by_type.accounts} == {
        "alex-roth-ira": "long_term", "alex-brokerage": "long_term", "alex-trading": "long_term",
        "alex-crypto": "other", "alex-old-401k": "long_term"}
    assert [category_of(t) for t in ["hsa", "checking", "money_market", "crypto", "joint"]] == [
        "long_term", "cash", "cash", "other", "other"]
    mapped = connector(warehouse, categories={
        "alex-trading": "trading", "Alex Crypto": "cash", "alex-crypto": "trading", "brokerage-9": "cash",
    }).snapshot(NOW)
    categories = {a.id: a.category for a in mapped.accounts}
    assert (categories["alex-trading"], categories["alex-crypto"]) == ("trading", "trading")  # an id outranks a label
    assert mapped.sources[0].detail.endswith("no account matches categories 'brokerage-9'")


def test_value_and_cash_come_from_the_latest_snapshot_at_the_us_close(warehouse):
    accounts = {a.id: a for a in connector(warehouse).snapshot(NOW).accounts}
    assert (accounts["alex-brokerage"].value, accounts["alex-brokerage"].cash) == (4500.0, 500.0)
    assert (accounts["alex-trading"].value, accounts["alex-trading"].cash) == (550.0, -200.0)  # a margin debit
    assert accounts["alex-brokerage"].as_of == dt.datetime(2026, 9, 25, 16, 0, tzinfo=NY)
    assert accounts["alex-old-401k"].value == 0.0


def test_last_success_is_the_latest_good_derive_run(tmp_path, warehouse):
    source = connector(warehouse).snapshot(NOW).sources[0]
    assert (source.id, source.label, source.kind, source.status) == ("portfolio", "Portfolio", "fdc", "ok")
    assert source.last_success == dt.datetime(2026, 9, 25, 12, 5, tzinfo=dt.timezone.utc)
    w = Warehouse(tmp_path / "other.db")
    w.run("prices", "ok", "2026-09-24T08:00:00")  # no offset: UTC
    w.run("derive", "error", "2026-09-25T08:00:00Z")
    assert connector(w.close()).snapshot(NOW).sources[0].last_success == dt.datetime(2026, 9, 24, 8,
                                                                                     tzinfo=dt.timezone.utc)
    never = connector(Warehouse(tmp_path / "never.db").close()).snapshot(NOW).sources[0]
    assert (never.last_success, never.status) == (None, "stale")


def test_the_newer_of_the_snapshot_and_the_history_sets_the_value_and_a_tie_goes_to_the_snapshot(warehouse):
    accounts = {a.id: a for a in connector(warehouse).snapshot(NOW).accounts}
    roth = accounts["alex-roth-ira"]  # a snapshot on Thu 24, history to Fri 25
    assert (roth.value, roth.cash, roth.as_of) == (8700.0, 150.0, dt.datetime(2026, 9, 25, 16, 0, tzinfo=NY))
    assert (accounts["alex-brokerage"].value, accounts["alex-brokerage"].cash) == (4500.0, 500.0)  # both on Fri 25
    assert (accounts["alex-crypto"].value, accounts["alex-crypto"].cash) == (320.0, 0.0)  # history only


def test_history_adds_holdings_and_cash_by_day_and_files_each_flow_under_a_history_day(warehouse):
    history = {s.id: s.points for s in connector(warehouse).snapshot(NOW).account_history}
    assert list(history) == ["alex-roth-ira", "alex-brokerage", "alex-crypto"]  # a snapshot-only account has none
    roth = history["alex-roth-ira"]
    assert [(p.date.day, p.value) for p in roth] == [
        (16, 7950.0), (17, 8000.0), (18, 8050.0), (21, 8600.0), (22, 8420.0), (23, 8330.0), (24, 8650.0), (25, 8700.0)]
    # Tue 15 lands on the first point and Saturday's deposit on Monday; a withdrawal is always out; a reversed
    # contribution counts against; a transfer keeps its sign; dividends are growth; Sat 26 is after the last point
    assert [p.net_flow for p in roth] == [100.0, 0.0, 0.0, 500.0, -200.0, -100.0, 300.0, -50.0]
    assert [p.value for p in history["alex-crypto"]] == [300.0, 310.0, 320.0]


def test_holdings_come_from_each_accounts_latest_snapshot(warehouse):
    snap = connector(warehouse).snapshot(NOW)
    assert [(h.account_id, h.symbol, h.name, h.quantity, h.price, h.value, h.cost_basis) for h in snap.holdings] == [
        ("alex-roth-ira", "SPY", "S&P 500 index fund", 10.0, 600.0, 6000.0, 5000.0),
        ("alex-roth-ira", "AGG", "Bond index fund", 20.0, 100.0, 2000.0, 2100.0),
        ("alex-brokerage", "SPY", "S&P 500 index fund", 5.0, 600.0, 3000.0, 2500.0),
        ("alex-brokerage", "MSFT", "Microsoft", 2.0, 500.0, 1000.0, None),  # no price: its value over its quantity
        ("alex-trading", "AAPL", "Apple", 3.0, 250.0, 750.0, 700.0),
    ]  # and Walt Disney had no market value, so it is left out and counted


def test_the_benchmark_comes_from_the_warehouses_prices_over_the_accounts_history(warehouse):
    snap = connector(warehouse, benchmark=BenchmarkCfg(symbol="SPY", label="S&P 500")).snapshot(NOW)
    assert snap.benchmark is not None and (snap.benchmark.symbol, snap.benchmark.label) == ("SPY", "S&P 500")
    assert [(p.date.day, p.value) for p in snap.benchmark.points][:2] == [(16, 595.0), (17, 597.0)]
    assert snap.benchmark.points[-1].value == 603.0
    other = connector(warehouse, benchmark=BenchmarkCfg(symbol="QQQ", label="Nasdaq 100")).snapshot(NOW)
    assert other.benchmark is None
    assert other.sources[0].detail == ("5 accounts · 5 holdings · prices to 25 Sep · 1 holding left out "
                                       "(no market value) · no QQQ prices in the warehouse")


def test_a_closed_account_at_zero_with_no_holdings_is_still_listed(warehouse):
    snap = connector(warehouse).snapshot(NOW)
    old = next(a for a in snap.accounts if a.id == "alex-old-401k")
    assert (old.value, old.cash, old.as_of.date()) == (0.0, 0.0, d(21))
    assert [h for h in snap.holdings if h.account_id == old.id] == []
    assert old.id not in {s.id for s in snap.account_history}


def test_a_margin_debit_is_negative_cash_and_the_value_nets_it(warehouse):
    snap = connector(warehouse).snapshot(NOW)
    trading = next(a for a in snap.accounts if a.id == "alex-trading")
    held = sum(h.value for h in snap.holdings if h.account_id == trading.id)
    assert (held, trading.cash, trading.value) == (750.0, -200.0, 550.0)


def test_an_empty_warehouse_is_a_source_with_nothing_in_it_yet(tmp_path):
    snap = connector(Warehouse(tmp_path / "w.db").close(), benchmark=BenchmarkCfg()).snapshot(NOW)
    assert (snap.accounts, snap.holdings, snap.account_history, snap.benchmark) == ([], [], [], None)
    assert snap.sources[0].detail == "0 accounts · 0 holdings · no prices yet · no SPY prices in the warehouse"


def test_a_profile_reads_its_warehouse_relative_to_its_own_folder(tmp_path, monkeypatch):
    (tmp_path / "collector").mkdir()
    household(tmp_path / "collector")
    (tmp_path / "kestrel").mkdir()
    (tmp_path / "kestrel" / "profile.toml").write_text(
        '[[sources]]\nid = "portfolio"\nkind = "fdc"\nlabel = "Portfolio"\npath = "../collector/warehouse.db"\n'
        '[sources.categories]\n"Alex Trading" = "trading"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path / "collector")  # anywhere but the profile's folder
    profile, _ = load_profile(tmp_path / "kestrel" / "profile.toml")
    snap = collect(profile, NOW)
    assert [(s.label, s.kind, s.status) for s in snap.sources] == [("Portfolio", "fdc", "ok")]
    assert {a.id: a.category for a in snap.accounts}["alex-trading"] == "trading"
    assert snap.benchmark is not None and snap.benchmark.label == "S&P 500"


def test_a_broken_source_is_a_red_row_and_the_rest_still_arrives(tmp_path):
    profile = Profile(sources=[
        SourceCfg(id="demo", kind="demo"),
        SourceCfg(id="portfolio", kind="fdc", label="Portfolio", path=str(tmp_path / "nope.db")),
        SourceCfg(id="unset", kind="fdc"),
    ])
    snap = collect(profile, NOW)
    errors = {s.id: s.detail for s in snap.sources if s.status == "error"}
    assert errors["portfolio"] == f"no warehouse at {tmp_path / 'nope.db'}"
    assert errors["unset"].startswith("an fdc source needs a path to the warehouse")
    assert len(snap.accounts) == 4  # the demo still arrived
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_fdc_connector.py`
Expected: `8 failed, 15 passed`: the value from the newer history day (`AssertionError: assert (8150.0, 150.... == (8700.0, 150....`), history (`assert [] == ['alex-roth-i...'alex-crypto']`), holdings (`assert [] == [('alex-roth-..., 750.0, ...)]`), the margin debit (no holdings yet), the benchmark and the empty warehouse (`TypeError: FdcConnector.__init__() got an unexpected keyword argument 'benchmark'`), and the two `collect` tests, where the source is an error row: ``connector kind 'fdc' is not available in this version of kestrel``. `test_a_closed_account_at_zero_with_no_holdings_is_still_listed` passes already on part 1; it pins that for part 2.

- [ ] **Step 3: Implement (replace the whole files)**

`src/kestrel/connectors/fdc.py`:

````python
"""financial-data-collector's SQLite warehouse, read-only: accounts, what they hold, their daily history with the
money moved in and out, and the benchmark's prices.

The warehouse is opened read-only twice over (mode=ro, then query_only) and closed after every snapshot. Nothing
here ever writes to it.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from ..contract import Account, Benchmark, Category, Holding, Series, Snapshot, Source, ValuePoint
from ..profile import BenchmarkCfg
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

# each account's value per day: its holdings plus its cash, the join portfolio_daily_full uses, kept per account
HISTORY = """
WITH h AS (SELECT as_of_date, account_id, SUM(market_value) AS holdings FROM holdings_daily GROUP BY 1, 2),
     c AS (SELECT as_of_date, account_id, amount AS cash FROM cash_daily),
     d AS (SELECT as_of_date, account_id FROM h UNION SELECT as_of_date, account_id FROM c)
SELECT d.account_id, d.as_of_date, COALESCE(h.holdings, 0), COALESCE(c.cash, 0)
FROM d
LEFT JOIN h ON h.as_of_date = d.as_of_date AND h.account_id = d.account_id
LEFT JOIN c ON c.as_of_date = d.as_of_date AND c.account_id = d.account_id
ORDER BY d.account_id, d.as_of_date
"""
FLOWS = """
SELECT account_id, trade_date, type, amount FROM transactions
WHERE type IN ('contribution', 'withdrawal', 'transfer') AND amount IS NOT NULL
"""


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


def _flow(kind: str, amount: float) -> float:
    """A withdrawal is money out whatever its sign; a contribution or a transfer keeps its own (a negative
    contribution is a reversal)."""
    return -abs(amount) if kind == "withdrawal" else amount


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _day(text: str) -> str:
    """An ISO day as "24 Sep"."""
    day = date.fromisoformat(text)
    return f"{day.day} {day:%b}"


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


def history(conn: sqlite3.Connection) -> dict[int, list[tuple[str, float, float]]]:
    """Per account (the warehouse's own id): (day, value, cash), days ascending."""
    out: dict[int, list[tuple[str, float, float]]] = defaultdict(list)
    for account, day, holdings, cash in conn.execute(HISTORY):
        out[account].append((day, holdings + cash, cash))
    return out


def flows(conn: sqlite3.Connection, days: dict[int, list[str]]) -> dict[int, dict[str, float]]:
    """Per account, the money moved in or out, filed under a history day: a flow on a day without a point goes to
    the next one (a Saturday deposit is Monday's), and one after the last point is dropped."""
    out: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for account, when, kind, amount in conn.execute(FLOWS):
        known = days.get(account, [])
        i = bisect_left(known, when[:10])
        if i < len(known):
            out[account][known[i]] += _flow(kind, amount)
    return out


class FdcConnector:
    """Reads one warehouse. `categories` maps an account id or exact label to a category; `benchmark` is looked up
    in the warehouse's prices."""

    def __init__(self, source_id: str, label: str, path: Path, categories: dict[str, str] | None = None,
                 benchmark: BenchmarkCfg | None = None, timeout: float = TIMEOUT) -> None:
        self.source_id = source_id
        self.label = label
        self.path = path
        self.categories = dict(categories or {})
        self.benchmark = benchmark
        self.timeout = timeout

    def snapshot(self, now: datetime) -> Snapshot:
        try:
            with connect(self.path, self.timeout) as conn:
                check_schema(conn, self.path)
                return self._read(conn, now)
        except sqlite3.Error as exc:
            raise ConnectorError(f"the warehouse couldn't be read: {exc}") from None

    def _category(self, account_id: str, label: str, account_type: str) -> Category:
        chosen = self.categories.get(account_id) or self.categories.get(label)
        return cast(Category, chosen) if chosen else category_of(account_type)

    def _read(self, conn: sqlite3.Connection, now: datetime) -> Snapshot:
        rows = conn.execute("SELECT id, label, institution, account_type FROM accounts ORDER BY id").fetchall()
        ids = dict(zip((r[0] for r in rows), account_ids([r[1] for r in rows])))
        by_label = {r[1]: ids[r[0]] for r in rows}
        # the latest daily value of each account; SQLite takes the bare columns from the row MAX() picked
        latest = {label: (day, total, cash) for label, day, total, cash in conn.execute(
            "SELECT account, MAX(as_of_date), total, cash FROM account_values_daily GROUP BY account")}
        days = history(conn)
        moved = flows(conn, {account: [day for day, _, _ in points] for account, points in days.items()})

        accounts: list[Account] = []
        series: list[Series] = []
        for warehouse_id, label, institution, kind in rows:
            points = days.get(warehouse_id, [])
            if points:
                series.append(Series(id=ids[warehouse_id], points=[
                    ValuePoint(date=date.fromisoformat(day), value=round(value, 2),
                               net_flow=round(moved[warehouse_id].get(day, 0.0), 2))
                    for day, value, _ in points]))
            # the newer of the broker's last snapshot and the last replayed day; on the same day the snapshot wins
            snapped = latest.get(label)
            if snapped and (not points or snapped[0] >= points[-1][0]):
                day, value, cash = snapped
            elif points:
                day, value, cash = points[-1]
            else:
                day, value, cash = None, 0.0, 0.0
            accounts.append(Account(
                id=ids[warehouse_id], name=label, institution=institution_text(institution),
                account_type=type_text(kind), category=self._category(ids[warehouse_id], label, kind),
                value=round(value, 2), cash=round(cash, 2), as_of=_close(day) if day else now,
            ))

        holdings, left_out = self._holdings(conn, by_label)
        first = min((s.points[0].date for s in series), default=None)
        benchmark = self._benchmark(conn, first)
        # each security's last price through the prices index: MAX(date) over the whole table is a full scan
        priced = conn.execute("SELECT MAX((SELECT MAX(date) FROM prices WHERE symbol = s.symbol)) "
                              "FROM securities s").fetchone()[0]
        notes = [_plural(len(accounts), "account"), _plural(len(holdings), "holding"),
                 f"prices to {_day(priced)}" if priced else "no prices yet"]
        if left_out:
            notes.append(f"{_plural(left_out, 'holding')} left out (no market value)")
        if self.benchmark and benchmark is None:
            notes.append(f"no {self.benchmark.symbol} prices in the warehouse")
        unmatched = sorted(set(self.categories) - {a.id for a in accounts} - {a.name for a in accounts})
        if unmatched:
            notes.append(f"no account matches categories {', '.join(repr(k) for k in unmatched)}")
        synced = last_success(conn)
        source = Source(id=self.source_id, label=self.label, kind="fdc", last_success=synced,
                        status="ok" if synced else "stale", detail=" · ".join(notes))
        return Snapshot(generated_at=now, sources=[source], accounts=accounts, holdings=holdings,
                        account_history=series, benchmark=benchmark)

    def _holdings(self, conn: sqlite3.Connection, by_label: dict[str, str]) -> tuple[list[Holding], int]:
        """The latest snapshot's positions, largest first in each account, and how many had no market value (they
        are left out: there is nothing to add up)."""
        holdings: list[Holding] = []
        left_out = 0
        for label, symbol, name, quantity, price, value, cost in conn.execute(
                "SELECT account, symbol, description, quantity, price, market_value, cost_basis_total "
                "FROM positions_latest"):
            if value is None:
                left_out += 1
                continue
            if price is None:
                price = value / quantity if quantity else 0.0
            holdings.append(Holding(account_id=by_label[label], symbol=symbol, name=name or "", quantity=quantity,
                                    price=price, value=round(value, 2),
                                    cost_basis=round(cost, 2) if cost is not None else None))
        rank = {account_id: i for i, account_id in enumerate(by_label.values())}
        holdings.sort(key=lambda h: (rank[h.account_id], -h.value))
        return holdings, left_out

    def _benchmark(self, conn: sqlite3.Connection, first: date | None) -> Benchmark | None:
        """The profile's benchmark from the warehouse's prices (adjusted, so dividends count, as they do in the
        accounts), from the last close on or before the first day of account history."""
        if self.benchmark is None:
            return None
        rows = conn.execute("SELECT date, adj_close FROM prices WHERE symbol = ? ORDER BY date",
                            (self.benchmark.symbol,)).fetchall()
        if first is not None:
            rows = rows[max((i for i, (day, _) in enumerate(rows) if day <= first.isoformat()), default=0):]
        if not rows:
            return None
        return Benchmark(symbol=self.benchmark.symbol, label=self.benchmark.label,
                         points=[ValuePoint(date=date.fromisoformat(day), value=value) for day, value in rows])
````


`src/kestrel/connectors/__init__.py`:

````python
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
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `168 passed` (`test_fdc_connector.py` 23); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/connectors/fdc.py src/kestrel/connectors/__init__.py tests/test_fdc_connector.py
git commit -m "feat(fdc): history with the money moved in and out, holdings, the benchmark and the source's detail" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 5: The accounts views, and Home's trading line from the trading accounts

**Files:**
- Create: `src/kestrel/views/accounts.py`
- Modify (replace the whole file): `src/kestrel/views/home.py`
- Test (create or replace): `tests/test_accounts_view.py`, `tests/test_home_view.py`

**Interfaces:**
- Consumes: `View`, `_day_pct` (views/home.py); `sum_series` (metrics).
- Produces (`views/accounts.py`, pure functions of one Snapshot):
  - `Window = Literal["ytd", "1y", "all"]`, `WINDOWS`; `window_start(window, today, points)` (1 January of the profile-timezone year; today − 365 days; the first point); `growth(points, start) -> Growth | None` (from the last point on or before `start`, or the first point when history begins later; `deposits` = Σ `net_flow` after that point; `market = end − start − deposits`; cents; fewer than 2 points is `None`); `growths(points, today) -> dict[Window, Growth | None]`; `combined_holdings(snapshot)`.
  - `Growth {start_date, start, deposits, market, end}`, `AccountLine {id, name, institution, account_type, category, value, share, day_change, day_pct, year_market}`, `CombinedHolding {symbol, name, cash, value, share, accounts}` (the cash row: `symbol ""`, `name "Cash"`, `cash true`, when any account has cash), `AccountsView {as_of, count, total, growth, accounts, holdings}`.
  - `Flow {date, amount}`, `HoldingRow {symbol, name, quantity, price, value, weight, cost_basis, gain, gain_pct}`, `Totals {value, cost_basis, gain, gain_pct, unknown_cost}`, `AccountView {id, name, institution, account_type, category, value, as_of (a date), points, growth, flows (the last 8 non-zero, newest first), holdings (largest first), cash, cash_weight, totals}`.
  - `accounts_view(snapshot, profile, now)`; `account_view(snapshot, profile, now, account_id) -> AccountView | None`. A share or weight of a whole that is zero or less is `None`.
- `views/home.py` `_comparison`: when no real book has two or more points, the trading line is the sum of the `trading`-category accounts' history (still labelled "Trading").

- [ ] **Step 1: Write the failing tests**

`tests/test_accounts_view.py`:

````python
import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Holding, Series, Snapshot, ValuePoint
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.accounts import account_view, accounts_view, growth, window_start

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
d = dt.date


@pytest.fixture(scope="module")
def demo():
    return collect(DEMO_PROFILE, NOW)


def points(*rows):
    return [ValuePoint(date=day, value=value, net_flow=flow) for day, value, flow in rows]


def account(id_, value, cash=0.0, name=None):
    return Account(id=id_, name=name or id_.title(), category="long_term", value=value, cash=cash, as_of=NOW)


def test_windows_start_on_1_january_a_year_ago_and_at_the_first_point():
    history = points((d(2024, 3, 4), 10, 0), (d(2026, 9, 25), 12, 0))
    today = d(2026, 9, 25)
    assert [window_start(w, today, history) for w in ("ytd", "1y", "all")] == [
        d(2026, 1, 1), d(2025, 9, 25), d(2024, 3, 4)]


def test_growth_splits_the_change_into_what_you_put_in_and_what_the_market_added():
    history = points((d(2025, 12, 31), 1000, 0), (d(2026, 1, 5), 1600, 500), (d(2026, 3, 2), 1700, 0),
                     (d(2026, 9, 25), 1900, 100))
    g = growth(history, d(2026, 1, 1))  # starts from the value held on 1 January: 31 December's
    assert g is not None
    assert (g.start_date, g.start, g.deposits, g.market, g.end) == (d(2025, 12, 31), 1000, 600, 300, 1900)


def test_history_that_begins_after_the_window_starts_at_its_first_point_and_one_point_is_no_growth():
    history = points((d(2026, 3, 2), 500, 0), (d(2026, 6, 1), 700, 150), (d(2026, 9, 25), 640, -50))
    g = growth(history, d(2026, 1, 1))
    assert g is not None and (g.start_date, g.start, g.deposits, g.market) == (d(2026, 3, 2), 500, 100, 40)
    assert growth(history[:1], d(2026, 1, 1)) is None
    assert growth([], d(2026, 1, 1)) is None
    assert growth(history[:2], d(2026, 9, 1)) is None  # history that ended before the window holds one point of it


def test_the_list_puts_the_largest_account_first_with_its_share_its_day_and_its_year(demo):
    view = accounts_view(demo, DEMO_PROFILE, NOW)
    assert (view.count, view.total) == (4, round(sum(a.value for a in demo.accounts), 2))
    assert [a.id for a in view.accounts] == ["roth", "brokerage", "savings", "trading"]
    assert sum(a.share or 0 for a in view.accounts) == pytest.approx(100, abs=0.02)
    roth = view.accounts[0]
    assert (roth.institution, roth.account_type, roth.category) == ("Brokerage A", "Roth IRA", "long_term")
    history = list(next(s.points for s in demo.account_history if s.id == "roth"))
    assert roth.day_change == round(history[-1].value - history[-2].value - history[-1].net_flow, 2)
    assert roth.year_market == growth(history, d(2026, 1, 1)).market
    ytd = view.growth["ytd"]
    assert ytd is not None and ytd.end == view.total and ytd.start_date == d(2026, 1, 1)
    assert ytd.market == pytest.approx(sum(a.year_market or 0 for a in view.accounts), abs=0.05)


def test_holdings_add_up_by_symbol_with_one_row_for_all_the_cash(demo):
    rows = accounts_view(demo, DEMO_PROFILE, NOW).holdings
    assert len(rows) == 14  # 13 symbols and the cash
    assert [r.value for r in rows] == sorted((r.value for r in rows), reverse=True)
    spy = next(r for r in rows if r.symbol == "SPY")
    assert spy.accounts == ["Brokerage", "Roth IRA"] and spy.name == "S&P 500 index fund"
    assert spy.value == round(sum(h.value for h in demo.holdings if h.symbol == "SPY"), 2)
    cash = next(r for r in rows if r.cash)
    assert (cash.symbol, cash.name) == ("", "Cash")
    assert cash.value == round(sum(a.cash for a in demo.accounts), 2)
    assert cash.accounts == ["Brokerage", "High-yield savings", "Roth IRA", "Trading account"]
    assert sum(r.share or 0 for r in rows) == pytest.approx(100, abs=0.05)


def test_one_account_weighs_each_holding_and_leaves_an_unknown_cost_out_of_the_gain(demo):
    view = account_view(demo, DEMO_PROFILE, NOW, "brokerage")
    assert view is not None and (view.name, view.as_of) == ("Brokerage", d(2026, 9, 25))
    assert [h.symbol for h in view.holdings] == ["SPY", "XLK", "COST", "HD", "XLE", "KO", "XLI"]
    assert sum(h.weight or 0 for h in view.holdings) + (view.cash_weight or 0) == pytest.approx(100, abs=0.05)
    ko = next(h for h in view.holdings if h.symbol == "KO")
    assert (ko.cost_basis, ko.gain, ko.gain_pct) == (None, None, None)
    xle = next(h for h in view.holdings if h.symbol == "XLE")
    assert xle.gain is not None and xle.gain < 0 and xle.gain_pct == round(xle.gain / xle.cost_basis * 100, 2)
    known = [h for h in view.holdings if h.cost_basis is not None]
    assert view.totals.unknown_cost == 1
    assert view.totals.gain == round(sum(h.value - h.cost_basis for h in known), 2)
    assert view.totals.value == round(sum(h.value for h in view.holdings) + view.cash, 2) == view.value


def test_the_last_eight_days_money_moved_newest_first():
    history = points(*[(d(2026, month, 1), 1000 + month, 50 if month % 2 else -25) for month in range(1, 10)],
                     (d(2026, 9, 25), 1100, 0))
    snap = Snapshot(generated_at=NOW, accounts=[account("roth", 1100)], account_history=[Series(id="roth",
                                                                                               points=history)])
    flows = account_view(snap, Profile(), NOW, "roth").flows
    assert [(f.date.month, f.amount) for f in flows] == [
        (9, 50), (8, -25), (7, 50), (6, -25), (5, 50), (4, -25), (3, 50), (2, -25)]


def test_a_margin_debit_weighs_against_the_holdings_and_a_debit_bigger_than_the_holdings_has_no_weights():
    held = [Holding(account_id="margin", symbol="AAPL", quantity=4, price=250, value=1000, cost_basis=900)]
    snap = Snapshot(generated_at=NOW, accounts=[account("margin", 800, cash=-200)], holdings=held)
    view = account_view(snap, Profile(), NOW, "margin")
    assert (view.holdings[0].weight, view.cash, view.cash_weight) == (125.0, -200.0, -25.0)
    listed = accounts_view(snap, Profile(), NOW).holdings
    assert [(r.name, r.value, r.share) for r in listed] == [("", 1000.0, 125.0), ("Cash", -200.0, -25.0)]
    deep = snap.model_copy(update={"accounts": [account("margin", -100, cash=-1100)]})
    view = account_view(deep, Profile(), NOW, "margin")
    assert (view.holdings[0].weight, view.cash_weight) == (None, None)


def test_a_closed_account_at_zero_sits_last_and_a_household_of_zeros_has_no_shares():
    snap = Snapshot(generated_at=NOW, accounts=[account("old-401k", 0.0, name="Old 401(k)"), account("roth", 500)])
    view = accounts_view(snap, Profile(), NOW)
    assert [(a.id, a.share, a.day_change, a.year_market) for a in view.accounts] == [
        ("roth", 100.0, None, None), ("old-401k", 0.0, None, None)]
    closed = account_view(snap, Profile(), NOW, "old-401k")
    assert closed is not None and (closed.holdings, closed.cash_weight, closed.flows) == ([], None, [])
    assert closed.totals.model_dump() == {"value": 0.0, "cost_basis": None, "gain": None, "gain_pct": None,
                                          "unknown_cost": 0}
    zeros = accounts_view(Snapshot(generated_at=NOW, accounts=[account("old-401k", 0.0)]), Profile(), NOW)
    assert [a.share for a in zeros.accounts] == [None] and zeros.holdings == []


def test_no_accounts_is_an_empty_page_and_an_unknown_account_is_none():
    view = accounts_view(Snapshot(generated_at=NOW), Profile(), NOW)
    assert (view.count, view.total, view.accounts, view.holdings) == (0, 0, [], [])
    assert view.growth == {"ytd": None, "1y": None, "all": None}
    assert account_view(Snapshot(generated_at=NOW), Profile(), NOW, "roth") is None
````


`tests/test_home_view.py`:

````python
import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import (
    Account,
    Benchmark,
    Book,
    Position,
    Series,
    Snapshot,
    Source,
    Strategy,
    Trade,
    ValuePoint,
)
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.home import home_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def demo_home():
    return home_view(collect(DEMO_PROFILE, NOW), DEMO_PROFILE, NOW)


def test_net_worth_is_the_sum_of_accounts(demo_home):
    assert demo_home.net_worth.total == pytest.approx(sum(a.value for a in demo_home.accounts))
    assert demo_home.net_worth.points[-1].value == pytest.approx(demo_home.net_worth.total)


def test_allocation_fills_exactly_one_hundred_cells(demo_home):
    assert sum(s.cells for s in demo_home.allocation) == 100
    assert [s.category for s in demo_home.allocation] == ["long_term", "trading", "cash"]


def test_the_comparison_is_year_to_date_with_three_aligned_lines(demo_home):
    c = demo_home.comparison
    assert c.window == "ytd" and c.dates[0] >= dt.date(2026, 1, 1)
    assert [line.key for line in c.lines] == ["trading", "long_term", "benchmark"]
    assert all(len(line.values) == len(c.dates) for line in c.lines)
    assert c.lines[0].values[0] == 0.0
    assert c.gap_pts == pytest.approx(c.lines[0].return_pct - c.lines[1].return_pct, abs=0.01)
    assert c.real_trades == 34 and c.review_at == 50


def test_attention_is_ordered_serious_warning_note(demo_home):
    levels = [a.level for a in demo_home.attention]
    assert levels == sorted(levels, key=["serious", "warning", "note"].index)
    titles = [a.title for a in demo_home.attention]
    assert "MSFT has no resting stop" in titles
    assert any("Savings" in t for t in titles)
    assert demo_home.summary.needs_you == 2


def test_book_verdicts(demo_home):
    verdicts = {b.id: b.verdict for b in demo_home.books}
    assert verdicts["rsi2-real"] == "in_band"
    assert verdicts["ibs-paper"] == "early"  # 7 trades is too few to judge
    assert verdicts["leader-paper"] == "below"


def test_positions_list_real_money_first_and_an_unprotected_one_first_of_all(demo_home):
    first = demo_home.positions[0]
    assert (first.symbol, first.money, first.room_pct) == ("MSFT", "real", None)
    assert all(p.money == "real" for p in demo_home.positions[:4])


def test_today_holds_only_today(demo_home):
    assert [r.label for r in demo_home.today][:2] == ["Opening leader · paper", "Morning run"]


def _tiny(accounts, history, books=(), book_history=(), trades=(), positions=(), strategies=(), sources=()):
    return Snapshot(generated_at=NOW, accounts=list(accounts), account_history=list(history), books=list(books),
                    book_history=list(book_history), trades=list(trades), positions=list(positions),
                    strategies=list(strategies), sources=list(sources))


def test_an_empty_snapshot_still_renders():
    home = home_view(_tiny([], []), Profile(), NOW)
    assert home.net_worth.total == 0 and home.allocation == [] and home.comparison.lines == []
    assert home.comparison.gap_pts is None and home.books == [] and home.attention == []


def test_early_january_falls_back_to_twelve_months():
    days = [dt.date(2025, 12, 30) - dt.timedelta(days=i) for i in range(30)][::-1] + [dt.date(2026, 1, 2)]
    points = [ValuePoint(date=d, value=100 + i) for i, d in enumerate(days)]
    acct = Account(id="a", name="A", category="long_term", value=points[-1].value, as_of=NOW)
    home = home_view(_tiny([acct], [Series(id="a", points=points)]), Profile(), NOW.replace(month=1, day=2))
    assert home.comparison.window == "12m"
    assert len(home.comparison.dates) == len(days)


def test_every_comparison_line_starts_on_the_same_day():
    """A long-term account held all year (+10%) and a real book opened on 1 July (+4%) are compared from 1 July."""
    d = dt.date
    lt = [ValuePoint(date=day, value=v) for day, v in [
        (d(2026, 1, 1), 100), (d(2026, 4, 1), 102), (d(2026, 7, 1), 105), (d(2026, 8, 3), 106), (d(2026, 9, 1), 108),
        (d(2026, 9, 25), 110)]]
    book = [ValuePoint(date=day, value=v) for day, v in [
        (d(2026, 7, 1), 1000), (d(2026, 7, 15), 1010), (d(2026, 8, 3), 1020), (d(2026, 9, 1), 1030),
        (d(2026, 9, 25), 1040)]]
    # the benchmark has no close on 1 July itself: it starts from the last close before it
    spx = [ValuePoint(date=day, value=v) for day, v in [
        (d(2026, 1, 2), 500), (d(2026, 6, 30), 525), (d(2026, 7, 2), 530), (d(2026, 9, 25), 550)]]
    snapshot = Snapshot(
        generated_at=NOW,
        accounts=[Account(id="lt", name="Index fund", category="long_term", value=110, as_of=NOW)],
        account_history=[Series(id="lt", points=lt)],
        books=[Book(id="real", name="Real", money="real", strategy_id="s", status="running", started=d(2026, 7, 1),
                    value=1040)],
        book_history=[Series(id="real", points=book)],
        benchmark=Benchmark(symbol="SPY", label="S&P 500", points=spx),
    )
    c = home_view(snapshot, Profile(), NOW).comparison
    assert c.window == "ytd" and c.start == d(2026, 7, 1) and c.dates[0] == d(2026, 7, 1)
    assert [line.key for line in c.lines] == ["trading", "long_term", "benchmark"]
    assert [line.values[0] for line in c.lines] == [0.0, 0.0, 0.0]
    returns = {line.key: line.return_pct for line in c.lines}
    assert returns == {"trading": 4.0, "long_term": pytest.approx(4.76), "benchmark": pytest.approx(4.76)}
    assert c.gap_pts == pytest.approx(-0.76)  # 4.0 - 4.76 over the shared period, not 4.0 - 10.0


def test_a_paper_position_without_a_stop_is_not_an_alarm():
    book = Book(id="p", name="Paper", money="paper", strategy_id="s", status="running", started=dt.date(2026, 1, 1),
                value=1000)
    pos = Position(book_id="p", symbol="XLF", quantity=1, entry_price=50, last_price=51, opened=dt.date(2026, 9, 25))
    home = home_view(_tiny([], [], books=[book], positions=[pos]), Profile(), NOW)
    assert home.attention == []


def test_an_error_source_becomes_a_warning():
    src = Source(id="desk", label="Trading desk", kind="feed", status="error", detail="timed out")
    home = home_view(_tiny([], [], sources=[src]), Profile(), NOW)
    assert [(a.level, a.title) for a in home.attention] == [("warning", "Trading desk couldn't be read")]


def test_a_book_without_history_or_trades_has_no_numbers_but_still_shows():
    book = Book(id="b", name="New", money="real", strategy_id="s", status="running", started=dt.date(2026, 9, 25),
                value=500, slots_total=3)
    strat = Strategy(id="s", name="New strategy")
    trade = Trade(book_id="b", symbol="HD", opened=dt.date(2026, 9, 24), closed=dt.date(2026, 9, 25),
                  entry_price=10, exit_price=11, quantity=1, pnl=1, return_pct=10)
    home = home_view(_tiny([], [], books=[book], strategies=[strat], trades=[trade]), Profile(), NOW)
    row = home.books[0]
    assert row.day_change is None and row.since_pct is None
    assert row.verdict == "none"  # no expectation to compare with
    assert row.slots_used == 0 and row.slots_total == 3


def test_a_real_book_on_its_first_day_does_not_empty_the_comparison():
    """A book with a single point can't be drawn yet; it must not move the shared start or the window."""
    d = dt.date
    lt = [ValuePoint(date=d(2026, 1, 2) + dt.timedelta(days=i), value=100 + i) for i in range(260)]
    spx = [ValuePoint(date=p.date, value=500 + p.value) for p in lt]
    first_day = [ValuePoint(date=d(2026, 9, 25), value=2000)]
    snapshot = Snapshot(
        generated_at=NOW,
        accounts=[Account(id="lt", name="Index fund", category="long_term", value=lt[-1].value, as_of=NOW)],
        account_history=[Series(id="lt", points=lt)],
        books=[Book(id="new", name="New", money="real", strategy_id="s", status="running", started=d(2026, 9, 25),
                    value=2000)],
        book_history=[Series(id="new", points=first_day)],
        benchmark=Benchmark(symbol="SPY", label="S&P 500", points=spx),
    )
    c = home_view(snapshot, Profile(), NOW).comparison
    assert c.window == "ytd" and c.start == d(2026, 1, 2) and len(c.dates) > 200
    assert [line.key for line in c.lines] == ["long_term", "benchmark"]
    assert c.gap_pts is None


def test_a_book_below_its_band_links_to_its_strategy(demo_home):
    below = next(a for a in demo_home.attention if a.title == "Opening leader is below its expected band")
    assert below.link == "/strategies/leader"


def test_until_a_real_book_has_a_history_the_trading_accounts_are_the_trading_line():
    d = dt.date
    days = [d(2026, 1, 2), d(2026, 3, 2), d(2026, 5, 1), d(2026, 7, 1), d(2026, 9, 1), d(2026, 9, 25)]
    trading = [ValuePoint(date=day, value=1000 + 20 * i) for i, day in enumerate(days)]  # +10%
    lt = [ValuePoint(date=day, value=100 + i) for i, day in enumerate(days)]  # +5%
    accounts = [Account(id="desk", name="Trading", category="trading", value=1100, as_of=NOW),
                Account(id="lt", name="Index fund", category="long_term", value=105, as_of=NOW)]
    history = [Series(id="desk", points=trading), Series(id="lt", points=lt)]
    book = Book(id="real", name="Real", money="real", strategy_id="s", status="running", started=d(2026, 9, 24),
                value=2100)

    def lines(book_points):
        snapshot = Snapshot(generated_at=NOW, accounts=accounts, account_history=history,
                            books=[book] if book_points else [], book_history=[Series(id="real", points=book_points)])
        comparison = home_view(snapshot, Profile(), NOW).comparison
        return {line.key: (line.label, line.return_pct) for line in comparison.lines}

    assert lines([]) == {"trading": ("Trading", 10.0), "long_term": ("Long-term", 5.0)}
    first_day = [ValuePoint(date=d(2026, 9, 25), value=2000)]
    assert lines(first_day)["trading"] == ("Trading", 10.0)  # one point is not a history yet
    two_days = [ValuePoint(date=d(2026, 9, 24), value=2000), ValuePoint(date=d(2026, 9, 25), value=2100)]
    assert lines(two_days)["trading"] == ("Trading", 5.0)
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_accounts_view.py tests/test_home_view.py`
Expected: a collection error, `ModuleNotFoundError: No module named 'kestrel.views.accounts'` (`1 error`). The new Home test needs the implementation too (on the old `home.py` the comparison has no trading line); Step 4 runs it.

- [ ] **Step 3: Implement**

`src/kestrel/views/accounts.py`:

````python
"""The Accounts pages, computed from one Snapshot: what does each account hold, and how much of its growth was my
deposits vs the market?"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from ..contract import Category, Holding, Snapshot, ValuePoint
from ..metrics import sum_series
from ..profile import Profile
from .home import View, _day_pct

Window = Literal["ytd", "1y", "all"]
WINDOWS: tuple[Window, ...] = ("ytd", "1y", "all")
FLOWS = 8  # "Money in and out" lists the last eight


class Growth(View):
    start_date: dt.date  # the day the starting value is from
    start: float
    deposits: float  # deposits minus withdrawals after the start, up to the end
    market: float  # the rest of the change: end - start - deposits
    end: float


class AccountLine(View):
    id: str
    name: str
    institution: str
    account_type: str
    category: Category
    value: float
    share: float | None  # percent of all accounts
    day_change: float | None  # the last day's change, net of that day's deposits
    day_pct: float | None
    year_market: float | None  # this year's market growth


class CombinedHolding(View):
    symbol: str  # empty on the cash row
    name: str
    cash: bool
    value: float
    share: float | None  # percent of everything held, cash included
    accounts: list[str]  # the names of the accounts that hold it, alphabetical


class AccountsView(View):
    as_of: dt.datetime
    count: int
    total: float
    growth: dict[Window, Growth | None]  # all accounts together
    accounts: list[AccountLine]  # largest first
    holdings: list[CombinedHolding]  # largest first


class Flow(View):
    date: dt.date
    amount: float  # positive in, negative out


class HoldingRow(View):
    symbol: str
    name: str
    quantity: float
    price: float
    value: float
    weight: float | None  # percent of the account: its holdings plus its cash
    cost_basis: float | None
    gain: float | None
    gain_pct: float | None


class Totals(View):
    value: float  # the holdings plus the cash
    cost_basis: float | None  # of the holdings whose cost is known
    gain: float | None
    gain_pct: float | None
    unknown_cost: int  # holdings left out of the cost and gain totals


class AccountView(View):
    id: str
    name: str
    institution: str
    account_type: str
    category: Category
    value: float
    as_of: dt.date  # the day the value is from
    points: list[ValuePoint]
    growth: dict[Window, Growth | None]
    flows: list[Flow]  # the last eight days money moved, newest first
    holdings: list[HoldingRow]  # largest first
    cash: float
    cash_weight: float | None
    totals: Totals


def window_start(window: Window, today: dt.date, points: list[ValuePoint]) -> dt.date:
    """This year: 1 January; 1 year: a year ago today; all: the first point."""
    if window == "ytd":
        return dt.date(today.year, 1, 1)
    if window == "1y":
        return today - dt.timedelta(days=365)
    return points[0].date if points else today


def growth(points: list[ValuePoint], start: dt.date) -> Growth | None:
    """From the value held on `start` (the last point on or before it, or the first point when history begins
    later) to the last point. Fewer than two points is no growth."""
    first = max((i for i, p in enumerate(points) if p.date <= start), default=0)
    window = points[first:]
    if len(window) < 2:
        return None
    begin, end = window[0].value, window[-1].value
    deposits = sum(p.net_flow for p in window[1:])
    return Growth(start_date=window[0].date, start=round(begin, 2), deposits=round(deposits, 2),
                  market=round(end - begin - deposits, 2), end=round(end, 2))


def growths(points: list[ValuePoint], today: dt.date) -> dict[Window, Growth | None]:
    return {w: growth(points, window_start(w, today, points)) for w in WINDOWS}


def _share(value: float, whole: float) -> float | None:
    """A percent of a positive whole; none of a whole that is zero or less (every account closed, or a debit bigger
    than what is held)."""
    return round(value / whole * 100, 2) if whole > 0 else None


def _history(snapshot: Snapshot) -> dict[str, list[ValuePoint]]:
    return {s.id: list(s.points) for s in snapshot.account_history}


def combined_holdings(snapshot: Snapshot) -> list[CombinedHolding]:
    """Every holding added up by symbol across accounts, and one row for all the cash; largest first."""
    names = {a.id: a.name for a in snapshot.accounts}
    by_symbol: dict[str, list[Holding]] = {}
    for h in snapshot.holdings:
        by_symbol.setdefault(h.symbol, []).append(h)
    cash = sum(a.cash for a in snapshot.accounts)
    whole = sum(h.value for h in snapshot.holdings) + cash
    rows = [
        CombinedHolding(symbol=symbol, name=next((h.name for h in held if h.name), ""), cash=False,
                        value=round(sum(h.value for h in held), 2), share=_share(sum(h.value for h in held), whole),
                        accounts=sorted({names.get(h.account_id, h.account_id) for h in held}))
        for symbol, held in by_symbol.items()
    ]
    holders = sorted(a.name for a in snapshot.accounts if round(a.cash, 2) != 0)
    if holders:
        rows.append(CombinedHolding(symbol="", name="Cash", cash=True, value=round(cash, 2), share=_share(cash, whole),
                                    accounts=holders))
    return sorted(rows, key=lambda r: (-r.value, r.symbol))


def accounts_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> AccountsView:
    today = now.astimezone(profile.tz).date()
    history = _history(snapshot)
    total = sum(a.value for a in snapshot.accounts)
    rows = []
    for a in snapshot.accounts:
        points = history.get(a.id, [])
        year = growth(points, window_start("ytd", today, points))
        rows.append(AccountLine(
            id=a.id, name=a.name, institution=a.institution, account_type=a.account_type, category=a.category,
            value=a.value, share=_share(a.value, total),
            day_change=round(points[-1].value - points[-2].value - points[-1].net_flow, 2) if len(points) > 1 else None,
            day_pct=_day_pct(points), year_market=year.market if year else None,
        ))
    rows.sort(key=lambda r: (-r.value, r.name))
    everything = sum_series([history[a.id] for a in snapshot.accounts if a.id in history])
    return AccountsView(as_of=now, count=len(rows), total=round(total, 2), growth=growths(everything, today),
                        accounts=rows, holdings=combined_holdings(snapshot))


def _row(h: Holding, whole: float) -> HoldingRow:
    gain = round(h.value - h.cost_basis, 2) if h.cost_basis is not None else None
    return HoldingRow(symbol=h.symbol, name=h.name, quantity=h.quantity, price=h.price, value=h.value,
                      weight=_share(h.value, whole), cost_basis=h.cost_basis, gain=gain,
                      gain_pct=round((h.value - h.cost_basis) / h.cost_basis * 100, 2) if h.cost_basis else None)


def account_view(snapshot: Snapshot, profile: Profile, now: dt.datetime, account_id: str) -> AccountView | None:
    """One account, or None when there is no account with that id."""
    account = next((a for a in snapshot.accounts if a.id == account_id), None)
    if account is None:
        return None
    today = now.astimezone(profile.tz).date()
    points = _history(snapshot).get(account.id, [])
    held = sorted((h for h in snapshot.holdings if h.account_id == account.id), key=lambda h: (-h.value, h.symbol))
    whole = sum(h.value for h in held) + account.cash
    known = [(h.value, h.cost_basis) for h in held if h.cost_basis is not None]
    cost = sum(c for _, c in known) if known else None
    gain = sum(v - c for v, c in known) if known else None
    return AccountView(
        id=account.id, name=account.name, institution=account.institution, account_type=account.account_type,
        category=account.category, value=account.value, as_of=account.as_of.date(), points=points,
        growth=growths(points, today),
        flows=[Flow(date=p.date, amount=p.net_flow) for p in reversed(points) if round(p.net_flow, 2) != 0][:FLOWS],
        holdings=[_row(h, whole) for h in held], cash=account.cash, cash_weight=_share(account.cash, whole),
        totals=Totals(value=round(whole, 2), cost_basis=round(cost, 2) if cost is not None else None,
                      gain=round(gain, 2) if gain is not None else None,
                      gain_pct=round(gain / cost * 100, 2) if cost and gain is not None else None,
                      unknown_cost=len(held) - len(known)),  # the gain totals leave these out
    )
````


`src/kestrel/views/home.py`:

````python
"""The Home page, computed from one Snapshot: how is all my money doing, and does anything need me?"""

from __future__ import annotations

import datetime as dt
from statistics import fmean
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel

from ..contract import Book, Snapshot, Source, ValuePoint
from ..metrics import expected_band, growth_index, largest_remainder, max_drawdown_pct, sum_series
from ..profile import Profile

CATEGORY_LABELS = {"long_term": "Long-term", "trading": "Trading", "cash": "Cash", "other": "Other"}
MIN_TRADES_FOR_VERDICT = 10  # fewer closed trades than this is "too early" to judge a book
MIN_YTD_POINTS = 5  # early January falls back to the past twelve months


class View(BaseModel):
    pass


class Delta(View):
    amount: float
    pct: float | None


class NetWorth(View):
    total: float
    today: Delta
    month: Delta
    year: Delta
    year_flows: float
    points: list[ValuePoint]  # the client draws the "starting value + deposits" line from net_flow


class Slice(View):
    category: str
    label: str
    value: float
    share: float
    cells: int  # of 100, for the waffle


class AccountRow(View):
    id: str
    name: str
    category: str
    value: float
    day_pct: float | None


class Line(View):
    key: Literal["trading", "long_term", "benchmark"]
    label: str
    return_pct: float
    max_drop_pct: float
    values: list[float | None]  # percent change since the window start, aligned with Comparison.dates


class Comparison(View):
    window: Literal["ytd", "12m"]
    start: dt.date  # the shared first day: later than the window's start when a line's history begins later
    dates: list[dt.date]
    lines: list[Line]
    gap_pts: float | None  # trading minus long-term, in percentage points
    shallower: bool | None  # trading's worst drop was smaller than long-term's
    real_trades: int
    review_at: int | None


class Attention(View):
    level: Literal["serious", "warning", "note"]
    title: str
    detail: str
    link: str


class BookRow(View):
    id: str
    name: str
    strategy: str
    money: Literal["real", "paper"]
    status: str
    value: float
    day_change: float | None
    since_pct: float | None
    started: dt.date
    trades: int
    per_trade_pct: float | None
    band_lo: float | None
    band_hi: float | None
    verdict: Literal["in_band", "below", "above", "early", "none"]
    slots_used: int
    slots_total: int | None
    next_run: dt.datetime | None


class TodayRun(View):
    time: dt.datetime
    label: str
    status: str
    detail: str


class PositionRow(View):
    book_id: str
    book: str
    symbol: str
    money: Literal["real", "paper"]
    quantity: float
    entry_price: float
    last_price: float
    stop_price: float | None
    room_pct: float | None  # distance from the last price down to the stop
    pnl: float
    note: str


class Summary(View):
    day_change: float
    gap_pts: float | None
    needs_you: int  # serious + warning items


class HomeView(View):
    as_of: dt.datetime
    summary: Summary
    net_worth: NetWorth
    allocation: list[Slice]
    accounts: list[AccountRow]
    comparison: Comparison
    attention: list[Attention]
    books: list[BookRow]
    today: list[TodayRun]
    positions: list[PositionRow]


def _delta(points: list[ValuePoint], since: dt.date) -> Delta:
    """Money change from the last point before `since` to the latest point (deposits included)."""
    if not points:
        return Delta(amount=0.0, pct=None)
    base = next((p.value for p in reversed(points) if p.date < since), points[0].value)
    amount = points[-1].value - base
    return Delta(amount=round(amount, 2), pct=round(amount / base * 100, 2) if base else None)


def _day_pct(points: list[ValuePoint]) -> float | None:
    if len(points) < 2 or points[-2].value <= 0:
        return None
    return round(((points[-1].value - points[-1].net_flow) / points[-2].value - 1) * 100, 2)


def age_text(delta: dt.timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{hours // 24} days"


def _window(points: list[ValuePoint], start: dt.date) -> list[ValuePoint]:
    return [p for p in points if p.date >= start]


def _from(points: list[ValuePoint], start: dt.date) -> list[ValuePoint]:
    """The points after `start`, opening on `start` with the value held then (the last point on or before it)."""
    before = [p for p in points if p.date <= start]
    after = [p for p in points if p.date > start]
    return [ValuePoint(date=start, value=before[-1].value), *after] if before else after


def _line(key, label, points: list[ValuePoint], dates: list[dt.date]) -> Line | None:
    if len(points) < 2:
        return None
    index = growth_index(points)
    by_date = {p.date: i for p, i in zip(points, index)}
    values: list[float | None] = []
    last: float | None = None
    for day in dates:
        last = by_date.get(day, last)
        values.append(None if last is None else round((last - 1) * 100, 3))
    return Line(key=key, label=label, return_pct=round((index[-1] - 1) * 100, 2),
                max_drop_pct=round(max_drawdown_pct(index), 2), values=values)


def _comparison(snapshot: Snapshot, profile: Profile, today: dt.date, real_books: list[Book]) -> Comparison:
    history = {s.id: s.points for s in snapshot.account_history}
    book_history = {s.id: s.points for s in snapshot.book_history}
    real = [book_history[b.id] for b in real_books if b.id in book_history]
    if not any(len(points) >= 2 for points in real):
        # until a real book has a history of its own, the trading accounts are the trading money
        real = [history[a.id] for a in snapshot.accounts if a.category == "trading" and a.id in history]
    trading = sum_series(real)
    long_term = sum_series([history[a.id] for a in snapshot.accounts if a.category == "long_term" and a.id in history])
    bench = list(snapshot.benchmark.points) if snapshot.benchmark else []
    start, window = dt.date(today.year, 1, 1), "ytd"
    # a series needs two points to be a line: a real book on its first day must not move the window or the start
    drawable = lambda points: len(points) >= 2  # noqa: E731
    if len(_window(trading if drawable(trading) else long_term, start)) < MIN_YTD_POINTS:
        start, window = today - dt.timedelta(days=365), "12m"
    trading, long_term, bench = _window(trading, start), _window(long_term, start), _window(bench, start)
    firsts = [s[0].date for s in (trading, long_term, bench) if drawable(s)]
    if firsts:
        # every line is measured from the same day: the latest first date, so a book opened in July is not
        # set against an index fund's whole year
        start = max(firsts)
        trading, long_term, bench = _from(trading, start), _from(long_term, start), _from(bench, start)
    dates = sorted({p.date for p in next((s for s in (trading, long_term, bench) if drawable(s)), [])})
    lines = [
        line for line in (
            _line("trading", "Trading", trading, dates),
            _line("long_term", "Long-term", long_term, dates),
            _line("benchmark", snapshot.benchmark.label if snapshot.benchmark else profile.benchmark.label, bench,
                  dates),
        ) if line is not None
    ]
    by_key = {line.key: line for line in lines}
    t, lt = by_key.get("trading"), by_key.get("long_term")
    real_ids = {b.id for b in real_books}
    review = [s.review_at_trades for s in snapshot.strategies
              if s.review_at_trades and s.id in {b.strategy_id for b in real_books}]
    return Comparison(
        window=window, start=start, dates=dates, lines=lines,
        gap_pts=round(t.return_pct - lt.return_pct, 2) if t and lt else None,
        shallower=(t.max_drop_pct > lt.max_drop_pct) if t and lt else None,
        real_trades=sum(1 for tr in snapshot.trades if tr.book_id in real_ids),
        review_at=min(review) if review else None,
    )


def _book_rows(snapshot: Snapshot) -> list[BookRow]:
    history = {s.id: s.points for s in snapshot.book_history}
    strategies = {s.id: s for s in snapshot.strategies}
    rows = []
    for book in snapshot.books:
        points = list(history.get(book.id, []))
        returns = [t.return_pct for t in snapshot.trades if t.book_id == book.id]
        strategy = strategies.get(book.strategy_id)
        expected = strategy.expected if strategy else None
        per_trade_raw = fmean(returns) if returns else None
        per_trade = round(per_trade_raw, 3) if per_trade_raw is not None else None
        lo = hi = None
        if not returns or expected is None:
            verdict = "none"
        elif len(returns) < MIN_TRADES_FOR_VERDICT:
            verdict = "early"
        else:
            lo, hi = expected_band(expected.avg_trade_pct, expected.sd_trade_pct, len(returns))
            # compare the unrounded mean: a mean that rounds to the band edge must not read as "in_band" (the
            # scorecard on the strategy page compares the same unrounded mean, so the two never disagree)
            verdict = "below" if per_trade_raw < lo else "above" if per_trade_raw > hi else "in_band"
        rows.append(BookRow(
            id=book.id, name=book.name, strategy=strategy.name if strategy else book.strategy_id, money=book.money,
            status=book.status, value=book.value,
            day_change=round(points[-1].value - points[-2].value - points[-1].net_flow, 2) if len(points) > 1 else None,
            since_pct=round((growth_index(points)[-1] - 1) * 100, 2) if len(points) > 1 else None,
            started=book.started, trades=len(returns), per_trade_pct=per_trade,
            band_lo=round(lo, 3) if lo is not None else None, band_hi=round(hi, 3) if hi is not None else None,
            verdict=verdict, slots_used=sum(1 for p in snapshot.positions if p.book_id == book.id),
            slots_total=book.slots_total, next_run=book.next_run,
        ))
    return rows


def _source_attention(source: Source, now: dt.datetime, tz: dt.tzinfo) -> Attention | None:
    if source.status == "error":
        return Attention(level="warning", title=f"{source.label} couldn't be read", detail=source.detail,
                         link="/settings")
    if source.status == "stale" and source.last_success is not None:
        when = source.last_success.astimezone(tz).strftime("%a %H:%M")
        age = age_text(now - source.last_success)
        return Attention(level="warning", title=f"{source.label} hasn't synced in {age}",
                         detail=f"{source.kind} · last success {when}", link="/settings")
    return None


def _attention(snapshot: Snapshot, rows: list[BookRow], strategies_review: dict[str, int | None],
               now: dt.datetime, tz: dt.tzinfo) -> list[Attention]:
    books = {b.id: b for b in snapshot.books}
    items: list[Attention] = []
    for p in snapshot.positions:
        book = books.get(p.book_id)
        if book is not None and book.money == "real" and p.stop_price is None:
            items.append(Attention(level="serious", title=f"{p.symbol} has no resting stop",
                                   detail=f"{book.name} · real — no protective stop on record", link="/books"))
    for source in snapshot.sources:
        item = _source_attention(source, now, tz)
        if item:
            items.append(item)
    for row in rows:
        if row.verdict == "below":
            review = strategies_review.get(row.id)
            detail = f"{row.trades} of {review} {row.money} trades · reviewed at {review}" if review else \
                f"{row.trades} {row.money} trades"
            # the strategy's own page; its id is escaped so an odd id can't bend the link into another path
            items.append(Attention(level="note", title=f"{row.name} is below its expected band", detail=detail,
                                   link=f"/strategies/{quote(books[row.id].strategy_id, safe='')}"))
    items.extend(Attention(level=a.level, title=a.title, detail=a.detail, link=a.link) for a in snapshot.alerts)
    order = {"serious": 0, "warning": 1, "note": 2}
    return sorted(items, key=lambda a: order[a.level])


def home_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> HomeView:
    tz = profile.tz
    today = now.astimezone(tz).date()
    history = {s.id: s.points for s in snapshot.account_history}
    net = sum_series([history[a.id] for a in snapshot.accounts if a.id in history])
    total = round(sum(a.value for a in snapshot.accounts), 2)
    net_worth = NetWorth(
        total=total,
        today=_delta(net, today), month=_delta(net, today.replace(day=1)), year=_delta(net, dt.date(today.year, 1, 1)),
        year_flows=round(sum(p.net_flow for p in net[1:] if p.date >= dt.date(today.year, 1, 1)), 2),
        points=net,
    )
    order = ["long_term", "trading", "cash", "other"]
    values = {c: sum(a.value for a in snapshot.accounts if a.category == c) for c in order}
    present = [c for c in order if values[c] > 0]
    cells = largest_remainder([values[c] for c in present])
    allocation = [
        Slice(category=c, label=CATEGORY_LABELS[c], value=round(values[c], 2),
              share=round(values[c] / total * 100, 2) if total else 0.0, cells=n)
        for c, n in zip(present, cells)
    ]
    accounts = [AccountRow(id=a.id, name=a.name, category=a.category, value=a.value,
                           day_pct=_day_pct(list(history.get(a.id, [])))) for a in snapshot.accounts]
    real_books = [b for b in snapshot.books if b.money == "real"]
    comparison = _comparison(snapshot, profile, today, real_books)
    rows = _book_rows(snapshot)
    review_by_book = {b.id: next((s.review_at_trades for s in snapshot.strategies if s.id == b.strategy_id), None)
                      for b in snapshot.books}
    attention = _attention(snapshot, rows, review_by_book, now, tz)
    books = {b.id: b for b in snapshot.books}
    positions = [
        PositionRow(
            book_id=p.book_id, book=books[p.book_id].name if p.book_id in books else p.book_id, symbol=p.symbol,
            money=books[p.book_id].money if p.book_id in books else "paper", quantity=p.quantity,
            entry_price=p.entry_price, last_price=p.last_price, stop_price=p.stop_price,
            room_pct=round((p.last_price - p.stop_price) / p.last_price * 100, 2)
            if p.stop_price is not None and p.last_price > 0 else None,
            pnl=round((p.last_price - p.entry_price) * p.quantity, 2), note=p.note,
        )
        for p in snapshot.positions
    ]
    positions.sort(key=lambda r: (r.money != "real", r.room_pct is not None, r.symbol))
    runs = sorted((r for r in snapshot.runs if r.time.astimezone(tz).date() == today), key=lambda r: r.time)
    return HomeView(
        as_of=now,
        summary=Summary(day_change=net_worth.today.amount, gap_pts=comparison.gap_pts,
                        needs_you=sum(1 for a in attention if a.level in ("serious", "warning"))),
        net_worth=net_worth, allocation=allocation, accounts=accounts, comparison=comparison, attention=attention,
        books=rows, today=[TodayRun(time=r.time, label=r.label, status=r.status, detail=r.detail) for r in runs],
        positions=positions,
    )
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `179 passed` (`test_accounts_view.py` 10, `test_home_view.py` 16); `All checks passed!`. `home.json` doesn't change: the demo's real book has a year of history.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/views/accounts.py src/kestrel/views/home.py tests/test_accounts_view.py tests/test_home_view.py
git commit -m "feat(views): the account list and one account; Home's trading line falls back to the trading accounts" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 6: Routes, CLI views and the generated fixtures

**Files:**
- Modify (replace the whole file): `src/kestrel/server.py`, `src/kestrel/cli.py`
- Generate: `web/src/test/fixtures/accounts.json`, `web/src/test/fixtures/account-roth.json`
- Test (replace the whole file): `tests/test_server.py`, `tests/test_cli.py`, `tests/test_generated_files.py`

**Interfaces:**
- Consumes: `accounts_view`, `account_view`, `AccountsView`, `AccountView` (Task 5).
- Produces:
  - `GET /api/accounts` → `AccountsView`; `GET /api/accounts/{account_id}` → `AccountView`, or a JSON 404 `{"detail": "no such account: <id>"}`. Both are registered before the `/api/{rest:path}` catch-all and are GET-only.
  - `kestrel demo --view accounts` and `kestrel demo --view account --id ID`; without `--id`, or with an unknown one, a line to stderr and exit 2 (the same handling as `--view strategy`).
  - `tests/test_generated_files.py` `GENERATED` gains the two fixtures.

- [ ] **Step 1: Write the failing tests**

`tests/test_server.py`:

````python
import datetime as dt
import pathlib

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from kestrel.profile import DEMO_PROFILE
from kestrel.server import create_app

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
BASE_URL = "http://127.0.0.1"  # the Host the server allows; TestClient's default "testserver" is refused


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>kestrel</title>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(dist):
    return TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist), base_url=BASE_URL)


def test_every_route_is_read_only(dist):
    app = create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist)
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    assert routes, "expected API routes"
    for route in routes:
        assert route.methods <= {"GET", "HEAD"}, f"{route.path} allows {route.methods}"


def test_writes_are_refused(client):
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/home").status_code == 405


def test_health_shell_and_home(client):
    assert client.get("/api/health").json()["ok"] is True
    shell = client.get("/api/shell").json()
    assert shell["name"] == "Alex" and shell["app"]["accent"] == "rufous"
    assert shell["counts"] == {"accounts": 4, "books": 5, "strategies": 4}
    home = client.get("/api/home").json()
    assert home["summary"]["needs_you"] == 2
    assert home["net_worth"]["total"] > 0


def test_the_shell_never_exposes_source_settings(client, tmp_path):
    body = client.get("/api/shell").text
    assert "stale_after" not in body and "token_env" not in body


def test_an_unknown_api_path_is_a_json_404(client):
    response = client.get("/api/nope")
    assert response.status_code == 404 and "no such endpoint" in response.json()["detail"]


def test_pages_fall_back_to_the_app_and_files_are_served(client):
    assert "<title>kestrel</title>" in client.get("/strategies").text
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/favicon.svg").text == "<svg></svg>"


def test_a_path_outside_the_build_is_never_served(tmp_path):
    base = tmp_path / "base"
    dist = base / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>kestrel</title>", encoding="utf-8")
    (base / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    client = TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist), base_url=BASE_URL)
    for path in ("/../../pyproject.toml", "/..%2F..%2Fpyproject.toml", "/assets/../../../pyproject.toml"):
        response = client.get(path)
        assert "[project]" not in response.text, path


def test_a_windows_network_path_is_refused_before_touching_the_filesystem(client, monkeypatch):
    touched: list[str] = []
    real_resolve, real_is_file = pathlib.Path.resolve, pathlib.Path.is_file

    def unc(path: pathlib.Path) -> bool:
        return str(path).startswith(("\\\\", "//"))

    # record, then delegate, except for a network path: even a regressed build must not reach the network here
    def resolve(self, *args, **kwargs):
        touched.append(str(self))
        return self if unc(self) else real_resolve(self, *args, **kwargs)

    def is_file(self, *args, **kwargs):
        touched.append(str(self))
        return False if unc(self) else real_is_file(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "resolve", resolve)
    monkeypatch.setattr(pathlib.Path, "is_file", is_file)
    response = client.get("/%5C%5Chost%5Cshare%5Cx.txt")
    assert response.status_code == 200 and "<title>kestrel</title>" in response.text
    assert not [t for t in touched if t.startswith(("\\\\", "//"))], touched


def test_a_request_for_another_host_is_refused(client):
    """DNS rebinding: a page on another site that resolves its name to 127.0.0.1 still sends its own Host."""
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/api/health", headers={"Host": "localhost:8030"}).status_code == 200


def test_the_api_works_without_a_built_front_end():
    client = TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=None), base_url=BASE_URL)
    assert client.get("/api/health").status_code == 200
    assert client.get("/").status_code == 404


def test_a_nul_character_in_a_path_gets_the_app_not_an_error(client):
    response = client.get("/strategies%00x")
    assert response.status_code == 200 and "<title>kestrel</title>" in response.text


def test_the_strategy_list_and_one_strategy(client):
    cards = client.get("/api/strategies").json()["strategies"]
    assert [c["id"] for c in cards] == ["rsi2", "ibs", "leader", "verticals"]
    real = client.get("/api/strategies/rsi2").json()
    assert (real["book"], real["primary"], real["toggle"]) == ("real", "rsi2-real", True)
    assert client.get("/api/strategies/rsi2?book=paper").json()["primary"] == "rsi2-paper"


def test_an_unknown_strategy_is_a_json_404(client):
    response = client.get("/api/strategies/nope")
    assert response.status_code == 404 and response.json()["detail"] == "no such strategy: nope"


def test_a_book_other_than_real_or_paper_is_refused(client):
    assert client.get("/api/strategies/rsi2?book=both").status_code == 422


def test_writes_to_the_strategy_routes_are_refused(client):
    for path in ("/api/strategies", "/api/strategies/rsi2"):
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(path).status_code == 405, (method, path)


def test_the_account_list_and_one_account(client):
    listed = client.get("/api/accounts").json()
    assert [a["id"] for a in listed["accounts"]] == ["roth", "brokerage", "savings", "trading"]
    assert list(listed["growth"]) == ["ytd", "1y", "all"]
    roth = client.get("/api/accounts/roth").json()
    assert (roth["name"], roth["holdings"][0]["symbol"]) == ("Roth IRA", "SPY")


def test_an_unknown_account_is_a_json_404(client):
    response = client.get("/api/accounts/nope")
    assert response.status_code == 404 and response.json() == {"detail": "no such account: nope"}


def test_writes_to_the_account_routes_are_refused(client):
    for path in ("/api/accounts", "/api/accounts/roth"):
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(path).status_code == 405, (method, path)
````


`tests/test_cli.py`:

````python
import json
import re

import pytest
from fdc_fixture import Warehouse

import kestrel.cli
import kestrel.server
from kestrel.cli import main
from kestrel.profile import DEMO_PROFILE

NOW = "2026-09-25T21:08:00+00:00"


def run(capsysbinary, *argv):
    code = main(list(argv))
    out, err = capsysbinary.readouterr()
    return code, out.decode("utf-8"), err.decode("utf-8")


def test_demo_prints_a_valid_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--now", NOW)
    data = json.loads(out)
    assert code == 0 and data["contract_version"] == "1" and len(data["accounts"]) == 4


def test_demo_home_is_reproducible(capsysbinary):
    first = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    second = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    assert first == second and json.loads(first)["summary"]["needs_you"] == 2


def test_schema_describes_the_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "schema")
    schema = json.loads(out)
    assert code == 0 and schema["title"] == "Snapshot" and "accounts" in schema["properties"]


def test_check_passes_on_the_demo_and_fails_on_a_bad_profile(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsysbinary, "check")
    assert code == 0 and "hello, Alex" in out and "stale" in out
    bad = tmp_path / "bad.toml"
    bad.write_text('[app]\ntheme = "neon"\n', encoding="utf-8")
    code, _, err = run(capsysbinary, "check", "--profile", str(bad))
    assert code == 2 and "app.theme" in err


def test_serve_only_ever_listens_on_this_computer(capsys):
    assert kestrel.cli.HOST == "127.0.0.1"
    with pytest.raises(SystemExit) as done:
        main(["serve", "--help"])
    out = capsys.readouterr().out
    assert done.value.code == 0 and "--port" in out and "--host" not in out


def test_check_fails_when_a_source_cannot_be_read(capsysbinary, tmp_path):
    profile = tmp_path / "p.toml"
    profile.write_text('[[sources]]\nid = "desk"\nkind = "feed"\n', encoding="utf-8")
    code, out, _ = run(capsysbinary, "check", "--profile", str(profile))
    assert code == 1 and "error" in out


def test_demo_prints_the_strategy_views(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--view", "strategies", "--now", NOW)
    assert code == 0 and [c["id"] for c in json.loads(out)["strategies"]] == ["rsi2", "ibs", "leader", "verticals"]
    code, out, _ = run(capsysbinary, "demo", "--view", "strategy", "--id", "rsi2", "--now", NOW)
    assert code == 0 and json.loads(out)["book"] == "real"
    code, out, _ = run(capsysbinary, "demo", "--view", "strategy", "--id", "rsi2", "--book", "paper", "--now", NOW)
    assert code == 0 and json.loads(out)["primary"] == "rsi2-paper"


def test_demo_strategy_needs_a_known_id(capsysbinary):
    code, _, err = run(capsysbinary, "demo", "--view", "strategy", "--now", NOW)
    assert code == 2 and "--view strategy needs --id" in err
    code, _, err = run(capsysbinary, "demo", "--view", "strategy", "--id", "nope", "--now", NOW)
    assert code == 2 and "no strategy 'nope' in the demo data" in err


def test_check_lists_each_sources_accounts_but_never_a_balance(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsysbinary, "check")
    assert code == 0
    assert [line for line in out.splitlines() if line.startswith(" " * 9)] == [
        "         roth             long_term        Roth IRA",
        "         brokerage        long_term        Brokerage",
        "         trading          trading          Trading account",
        "         savings          cash             High-yield savings",
    ]
    assert "$" not in out and not re.search(r"\d{4}", out)  # no balances, no amounts


def test_the_demo_flag_shows_the_demo_whatever_profile_toml_says(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profile.toml").write_text('[you]\nname = "Sam"\n[[sources]]\nid = "desk"\nkind = "feed"\n',
                                           encoding="utf-8")
    code, out, _ = run(capsysbinary, "check")
    assert code == 1 and "hello, Sam" in out
    code, out, _ = run(capsysbinary, "check", "--demo")
    assert code == 0 and out.startswith("profile: built-in demo profile - hello, Alex")
    served = []
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: None)
    monkeypatch.setattr(kestrel.server, "create_app", lambda profile, **kwargs: served.append(profile))
    code, out, _ = run(capsysbinary, "serve", "--demo", "--no-open")
    assert code == 0 and served == [DEMO_PROFILE] and "profile: built-in demo profile" in out
    with pytest.raises(SystemExit) as refused:
        main(["check", "--demo", "--profile", "profile.toml"])
    assert refused.value.code == 2


def test_demo_prints_the_account_views(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--view", "accounts", "--now", NOW)
    assert code == 0 and json.loads(out)["count"] == 4
    code, out, _ = run(capsysbinary, "demo", "--view", "account", "--id", "savings", "--now", NOW)
    savings = json.loads(out)
    assert code == 0 and savings["holdings"] == [] and savings["cash"] == savings["value"]
    code, _, err = run(capsysbinary, "demo", "--view", "account", "--now", NOW)
    assert code == 2 and "--view account needs --id, e.g. --id roth" in err
    code, _, err = run(capsysbinary, "demo", "--view", "account", "--id", "nope", "--now", NOW)
    assert code == 2 and "no account 'nope' in the demo data" in err


def test_check_prints_a_warehouses_accounts_whatever_their_labels(capsysbinary, tmp_path):
    w = Warehouse(tmp_path / "warehouse.db")
    w.account("Épargne · Alex", "unknown", "savings")
    w.account("★ ★ ★", "webull", "brokerage")
    w.close()
    profile = tmp_path / "profile.toml"
    profile.write_text('[[sources]]\nid = "portfolio"\nkind = "fdc"\nlabel = "Portfolio"\npath = "warehouse.db"\n'
                       '[sources.categories]\n"account" = "trading"\n', encoding="utf-8")
    code, out, _ = run(capsysbinary, "check", "--profile", str(profile))
    assert code == 0 and "Portfolio        fdc              never  2 accounts · 0 holdings · no prices yet" in out
    assert [line for line in out.splitlines() if line.startswith(" " * 9)] == [
        "         epargne-alex     cash             Épargne · Alex",
        "         account          trading          ★ ★ ★",
    ]
````


`tests/test_generated_files.py`:

````python
"""Files generated from the code must match the code. Regenerate with the command in each failure message."""

import json
from pathlib import Path

import pytest

from kestrel.cli import main

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-09-25T21:08:00+00:00"

GENERATED = [
    (ROOT / "docs" / "contract" / "snapshot.schema.json", ["schema"]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "home.json", ["demo", "--view", "home", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "shell.json", ["demo", "--view", "shell", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "strategies.json", ["demo", "--view", "strategies", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "strategy-rsi2.json",
     ["demo", "--view", "strategy", "--id", "rsi2", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "accounts.json", ["demo", "--view", "accounts", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "account-roth.json",
     ["demo", "--view", "account", "--id", "roth", "--now", NOW]),
]


@pytest.mark.parametrize("path,argv", GENERATED, ids=[p.name for p, _ in GENERATED])
def test_generated_file_is_current(path, argv, capsysbinary):
    main(argv)
    current = json.loads(capsysbinary.readouterr().out.decode("utf-8"))
    command = "kestrel " + " ".join(argv) + f" > {path.relative_to(ROOT).as_posix()}"
    assert path.is_file(), f"missing: run `{command}`"
    assert json.loads(path.read_text(encoding="utf-8")) == current, f"out of date: run `{command}`"
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_server.py tests/test_cli.py tests/test_generated_files.py`
Expected: `5 failed, 32 passed`: the two account routes (the catch-all answers: `KeyError: 'accounts'` and `{'detail': 'no such endpoint: /api/accounts/nope'}`), the CLI views and the two new drift entries (`SystemExit: 2`: `--view accounts` is not a choice yet). `test_writes_to_the_account_routes_are_refused` and `test_check_prints_a_warehouses_accounts_whatever_their_labels` pass already (the catch-all is GET-only; Tasks 2 and 4 print the lines); they pin that.

- [ ] **Step 3: Implement, then generate the fixtures**

`src/kestrel/server.py`:

````python
"""The read-only web server. GET routes only, bound to this computer (127.0.0.1)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .connectors import collect
from .contract import Money
from .profile import Profile
from .views.accounts import AccountsView, AccountView, account_view, accounts_view
from .views.home import HomeView, home_view
from .views.shell import ShellView, shell_view
from .views.strategy import StrategiesView, StrategyView, strategies_view, strategy_view

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
LOCAL_HOSTS = ("127.0.0.1", "localhost")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _plain_parts(rest: str) -> tuple[str, ...] | None:
    """The path's parts when it is a plain relative path, else None.

    Decided on the text alone, before any filesystem call: on Windows a backslash or a drive colon could turn the
    path into a network (UNC) or absolute path, and merely resolving one of those reaches out over the network.
    A NUL character is refused too: the filesystem calls would raise on it.
    """
    if not rest or "\\" in rest or ":" in rest or chr(0) in rest or rest.startswith("/"):
        return None
    parts = PurePosixPath(rest).parts
    return None if ".." in parts else parts


def create_app(profile: Profile, *, clock: Callable[[], datetime] = _utcnow,
               web_dist: Path | None = WEB_DIST, allowed_hosts: Sequence[str] = LOCAL_HOSTS) -> FastAPI:
    app = FastAPI(title="kestrel", version=__version__, docs_url=None, redoc_url=None,
                  openapi_url="/api/openapi.json")
    # DNS-rebinding guard: a page elsewhere whose name resolves to 127.0.0.1 still sends its own Host header
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"ok": True, "version": __version__}

    @app.get("/api/shell", response_model=ShellView)
    def shell() -> ShellView:
        now = clock()
        return shell_view(collect(profile, now), profile, now)

    @app.get("/api/home", response_model=HomeView)
    def home() -> HomeView:
        now = clock()
        return home_view(collect(profile, now), profile, now)

    @app.get("/api/accounts", response_model=AccountsView)
    def accounts() -> AccountsView:
        now = clock()
        return accounts_view(collect(profile, now), profile, now)

    @app.get("/api/accounts/{account_id}", response_model=AccountView)
    def account(account_id: str) -> AccountView:
        now = clock()
        view = account_view(collect(profile, now), profile, now, account_id)
        if view is None:
            raise HTTPException(status_code=404, detail=f"no such account: {account_id}")
        return view

    @app.get("/api/strategies", response_model=StrategiesView)
    def strategies() -> StrategiesView:
        now = clock()
        return strategies_view(collect(profile, now), profile, now)

    @app.get("/api/strategies/{strategy_id}", response_model=StrategyView)
    def strategy(strategy_id: str, book: Money = "real") -> StrategyView:
        now = clock()
        view = strategy_view(collect(profile, now), profile, now, strategy_id, book)
        if view is None:
            raise HTTPException(status_code=404, detail=f"no such strategy: {strategy_id}")
        return view

    @app.get("/api/{rest:path}", include_in_schema=False)
    def unknown_api(rest: str) -> None:
        raise HTTPException(status_code=404, detail=f"no such endpoint: /api/{rest}")

    if web_dist is not None and (web_dist / "index.html").is_file():
        root = web_dist.resolve()
        if (root / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @app.get("/{rest:path}", include_in_schema=False)
        def page(rest: str) -> FileResponse:
            parts = _plain_parts(rest)
            if parts:
                candidate = root.joinpath(*parts).resolve()
                if candidate.is_file() and root in candidate.parents:
                    return FileResponse(candidate)
            return FileResponse(root / "index.html")  # the app's router handles every other path

    return app
````


`src/kestrel/cli.py`:

````python
"""kestrel's command line: serve, check, demo, schema."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from .contract import Snapshot
from .profile import DEMO_PROFILE, Profile, ProfileError, load_profile

HOST = "127.0.0.1"  # never listen beyond this computer


def _emit(text: str) -> None:
    """Write UTF-8 whatever the console's code page is (redirected output on Windows is cp1252 otherwise)."""
    sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
    sys.stdout.flush()


def _now(text: str | None) -> datetime:
    if not text:
        return datetime.now(timezone.utc)
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise SystemExit("--now needs a time zone offset, e.g. 2026-09-25T21:08:00+00:00")
    return value


def _profile(args: argparse.Namespace) -> tuple[Profile, str]:
    """--demo shows the demo whatever profile.toml says; otherwise --profile, else ./profile.toml, else the demo."""
    if args.demo:
        return DEMO_PROFILE, "built-in demo profile"
    return load_profile(args.profile)


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .server import WEB_DIST, create_app

    try:
        profile, origin = _profile(args)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    url = f"http://{HOST}:{args.port}"
    print(f"kestrel {url} - profile: {origin} - read-only - Ctrl+C to stop")
    if not (WEB_DIST / "index.html").is_file():
        print("web/dist is not built yet: run `npm ci && npm run build` in web/ (the API works without it)")
    if not args.no_open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(profile), host=HOST, port=args.port, log_level="warning")
    return 0


def _check(args: argparse.Namespace) -> int:
    from .connectors import collect
    from .views.home import age_text

    try:
        profile, origin = _profile(args)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc)
    # UTF-8 out: a source's detail or an account's name can carry any character
    _emit(f"profile: {origin} - hello, {profile.you.name}")
    failed = False
    for cfg in profile.sources:
        # one source at a time, so each source's accounts print under it; never a balance
        part = collect(profile.model_copy(update={"sources": [cfg]}), now)
        for s in part.sources:
            age = f"{age_text(now - s.last_success)} ago" if s.last_success else "never"
            _emit(f"  {s.status:<5}  {s.label:<16} {s.kind:<16} {age}  {s.detail}".rstrip())
            failed = failed or s.status == "error"
        for a in part.accounts:
            _emit(f"{'':9}{a.id:<16} {a.category:<16} {a.name}")
    return 1 if failed else 0


def _demo(args: argparse.Namespace) -> int:
    from .connectors import collect
    from .views.accounts import account_view, accounts_view
    from .views.home import home_view
    from .views.shell import shell_view
    from .views.strategy import strategies_view, strategy_view

    now = _now(args.now)
    snapshot = collect(DEMO_PROFILE, now)
    if args.view == "home":
        _emit(home_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "shell":
        _emit(shell_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "strategies":
        _emit(strategies_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "accounts":
        _emit(accounts_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view in ("strategy", "account"):
        if not args.id:
            example = "rsi2" if args.view == "strategy" else "roth"
            print(f"--view {args.view} needs --id, e.g. --id {example}", file=sys.stderr)
            return 2
        view = (strategy_view(snapshot, DEMO_PROFILE, now, args.id, args.book) if args.view == "strategy"
                else account_view(snapshot, DEMO_PROFILE, now, args.id))
        if view is None:
            print(f"no {args.view} {args.id!r} in the demo data", file=sys.stderr)
            return 2
        _emit(view.model_dump_json(indent=2))
    else:
        _emit(snapshot.model_dump_json(indent=2))
    return 0


def _schema(args: argparse.Namespace) -> int:
    _emit(json.dumps(Snapshot.model_json_schema(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kestrel", description="A calm, read-only home for all your money.")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the dashboard on this computer")
    serve.add_argument("--port", type=int, default=8030)
    serve.add_argument("--no-open", action="store_true", help="don't open a browser")
    serve.set_defaults(run=_serve)
    check = sub.add_parser("check", help="validate the profile and try every source")
    check.set_defaults(run=_check)
    for command in (serve, check):
        which = command.add_mutually_exclusive_group()
        which.add_argument("--profile", type=Path, help="profile file (default: ./profile.toml, else demo data)")
        which.add_argument("--demo", action="store_true", help="show the demo data, whatever profile.toml says")
    demo = sub.add_parser("demo", help="print the demo data as JSON (an example feed payload)")
    demo.add_argument("--view", choices=["snapshot", "home", "shell", "strategies", "strategy", "accounts", "account"],
                      default="snapshot")
    demo.add_argument("--id", help="the strategy or account the view shows, e.g. rsi2 or roth")
    demo.add_argument("--book", choices=["real", "paper"], default="real", help="the money --view strategy shows")
    demo.add_argument("--now", help="ISO time with offset, for reproducible output")
    demo.set_defaults(run=_demo)
    schema = sub.add_parser("schema", help="print the data contract as JSON Schema")
    schema.set_defaults(run=_schema)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
````


```bash
.venv/Scripts/kestrel demo --view accounts --now 2026-09-25T21:08:00+00:00 > web/src/test/fixtures/accounts.json
.venv/Scripts/kestrel demo --view account --id roth --now 2026-09-25T21:08:00+00:00 > web/src/test/fixtures/account-roth.json
```

(These are the commands the failing drift test prints. `account-roth.json` is about 1,400 lines, mostly the year of value points.)

- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `186 passed` (`test_server.py` 18, `test_cli.py` 12, `test_generated_files.py` 7); `All checks passed!`. Until the fixtures are generated, the two drift entries fail with ``missing: run `kestrel demo --view accounts --now 2026-09-25T21:08:00+00:00 > web/src/test/fixtures/accounts.json` `` and the same for `account-roth.json`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/server.py src/kestrel/cli.py tests/test_server.py tests/test_cli.py tests/test_generated_files.py web/src/test/fixtures/accounts.json web/src/test/fixtures/account-roth.json
git commit -m "feat(server,cli): GET /api/accounts and /api/accounts/{id}; demo views; generated fixtures" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 7: Shared pieces and the growth bar

**Files:**
- Modify (replace the whole file): `web/src/components/bits.tsx`, `web/src/pages/home/NetWorthPanel.tsx`, `web/src/pages/strategy/TradesPanel.tsx`
- Create: `web/src/charts/GrowthBar.tsx`
- Test (create or replace): `web/src/charts/GrowthBar.test.tsx`, `web/src/components/bits.test.tsx`

**Interfaces:**
- Produces:
  - `bits.tsx`, added to the Phase 2–3a pieces: `Stat({ label, sub?, children })` (moved out of `NetWorthPanel`, unchanged); `Sort<K>`, `toggleSort(sort, key)` and `SortHeader<K>({ label, k, sort, onSort, right? })` (moved out of `TradesPanel`, now generic); `CATEGORY_COLOR`, `CATEGORY_WORD` and `CategoryChip({ category })` (the word beside a dot in the category's colour).
  - `GrowthBar.tsx`: `GrowthSteps { start, deposits, market, end }`, `GrowthPart`, `PART_LABEL` ("Started at", "You put in", "The market added"), `segments(g)`; `GrowthBar({ growth, height?, ariaLabel })`: the start (solid `--s3`), what you put in (the dotted reference outline with a wash, like the "Start + deposits" line), the market (solid `--up`, or `--down` for a loss, running back over what came before), a tick at now; a per-part tooltip by pointer or keys; `Nothing to show yet.` when everything is zero. `GrowthTable({ growth })`: Started at · You put in · The market added · Now.
  - `NetWorthPanel` and `TradesPanel` import `Stat` and `SortHeader` / `toggleSort` instead of their own copies; nothing they show changes.

- [ ] **Step 1: Write the failing tests**

`web/src/charts/GrowthBar.test.tsx`:

````tsx
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GrowthBar, GrowthTable, segments } from './GrowthBar'

const growth = { start: 1000, deposits: 500, market: 250, end: 1750 }
const width = (el: Element | null) => Number(el?.getAttribute('width'))
const left = (el: Element | null) => Number(el?.getAttribute('x'))

describe('GrowthBar', () => {
  it('puts the start, what you put in and the market end to end, with a tick at now', () => {
    const { container } = render(<GrowthBar growth={growth} ariaLabel="Growth" />)
    const [start, put, gain] = ['start', 'deposits', 'gain'].map((m) => container.querySelector(`[data-mark="${m}"]`))
    expect(width(start)).toBeCloseTo((1000 / 1750) * 640, 1) // jsdom charts are 640 wide
    expect(left(put)).toBeCloseTo(left(start) + width(start), 1)
    expect(left(gain) + width(gain)).toBeCloseTo(640, 1)
    expect(put?.getAttribute('stroke-dasharray')).toBe('1.5 2.5') // the reference money is dotted
    expect(container.querySelector('line')?.getAttribute('x1')).toBe('640')
  })

  it('runs a loss or a withdrawal back over the part before it', () => {
    expect(segments({ start: 1000, deposits: -200, market: -300, end: 500 })).toEqual([
      { key: 'start', from: 0, to: 1000 }, { key: 'deposits', from: 1000, to: 800 },
      { key: 'market', from: 800, to: 500 },
    ])
    const { container } = render(<GrowthBar growth={{ start: 1000, deposits: 500, market: -300, end: 1200 }}
      ariaLabel="Growth" />)
    const loss = container.querySelector('[data-mark="loss"]')
    expect(loss?.getAttribute('fill')).toBe('var(--down)')
    expect([left(loss), width(loss)].map((v) => Math.round(v))).toEqual([512, 128]) // 1200 to 1500 of 1500
  })

  it('reads out each part from the keyboard', () => {
    render(<GrowthBar growth={growth} ariaLabel="Growth" />)
    const chart = screen.getByRole('img', { name: 'Growth' })
    fireEvent.keyDown(chart, { key: 'Home' })
    expect(screen.getByRole('status').textContent).toBe('Started atAmount$1,000.00')
    fireEvent.keyDown(chart, { key: 'ArrowRight' })
    expect(screen.getByRole('status').textContent).toBe('You put inAmount$500.00')
    fireEvent.keyDown(chart, { key: 'End' })
    expect(screen.getByRole('status').textContent).toBe('The market addedAmount+$250.00')
    fireEvent.keyDown(chart, { key: 'Escape' })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('has a table view', () => {
    render(<GrowthTable growth={{ ...growth, market: -250, end: 1250 }} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row').map((r) => r.textContent)
    expect(rows).toEqual(['PartAmount', 'Started at$1,000.00', 'You put in$500.00',
      'The market added▼ down −$250.00', 'Now$1,250.00'])
  })

  it('says so when there is nothing to show', () => {
    render(<GrowthBar growth={{ start: 0, deposits: 0, market: 0, end: 0 }} ariaLabel="Growth" />)
    expect(screen.getByText('Nothing to show yet.')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })
})
````


`web/src/components/bits.test.tsx`:

````tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { pct } from '../lib/format'
import { CategoryChip, Delta, type Sort, SortHeader, Stat, toggleSort } from './bits'

describe('Delta', () => {
  it('treats a value that rounds to zero at its shown precision as no change', () => {
    const { container } = render(<Delta value={0.03} digits={1}>{pct(0.03)}</Delta>)
    expect(container.textContent).toBe('0.0%')
    expect(container.textContent).not.toContain('▲')
  })

  it('still marks a change that shows', () => {
    const { container } = render(<Delta value={0.06} digits={1}>{pct(0.06)}</Delta>)
    expect(container.textContent).toContain('▲')
    expect(container.textContent).toContain('+0.1%')
  })
})

describe('shared pieces', () => {
  it('writes a stat block as a label, the value and a second line', () => {
    const { container } = render(<Stat label="Started at" sub="1 Jan">$1,000.00</Stat>)
    expect(container.textContent).toBe('Started at$1,000.001 Jan')
    expect(container.querySelector('.label')?.textContent).toBe('Started at')
  })

  it('sorts by a column heading, and flips the order when it is clicked again', () => {
    const sorted: Sort<'value' | 'gain'>[] = []
    const sort: Sort<'value' | 'gain'> = { key: 'value', dir: 'desc' }
    render(
      <table><thead><tr>
        <SortHeader label="Value" k="value" sort={sort} onSort={(k) => sorted.push(toggleSort(sort, k))} right />
        <SortHeader label="Gain" k="gain" sort={sort} onSort={(k) => sorted.push(toggleSort(sort, k))} right />
      </tr></thead></table>,
    )
    const [value, gain] = screen.getAllByRole('columnheader')
    expect([value.getAttribute('aria-sort'), gain.getAttribute('aria-sort')]).toEqual(['descending', 'none'])
    fireEvent.click(screen.getByRole('button', { name: 'Value' }))
    fireEvent.click(screen.getByRole('button', { name: 'Gain' }))
    expect(sorted).toEqual([{ key: 'value', dir: 'asc' }, { key: 'gain', dir: 'desc' }])
  })

  it('names a category in words beside its dot', () => {
    const { container } = render(<><CategoryChip category="long_term" /><CategoryChip category="cash" /></>)
    expect([...container.querySelectorAll('.chip')].map((c) => c.textContent)).toEqual(['Long-term', 'Cash'])
    expect(container.querySelector('.chip span')?.getAttribute('style')).toContain('var(--s1)')
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/charts/GrowthBar.test.tsx src/components/bits.test.tsx`
Expected: `Test Files  2 failed (2)` and `Tests  3 failed | 2 passed (5)`: `Failed to resolve import "./GrowthBar"`, and the three new shared-piece tests (`Element type is invalid: expected a string … but got: undefined`: `Stat`, `SortHeader` and `CategoryChip` aren't in `bits.tsx` yet).

- [ ] **Step 3: Implement**

`web/src/components/bits.tsx`:

````tsx
// Small shared pieces: the money-state mark and badge, deltas, panels, segmented controls, stat blocks, sortable
// column headings and the category chip.
import type { CSSProperties, ReactNode } from 'react'
import type { Money } from '../lib/api'

/** Real = solid, paper = hatched, expected = dotted. The one convention every page shares. */
export function BookMark({ kind, color, size = 12 }: { kind: Money | 'expected'; color?: string; size?: number }) {
  return (
    <span className={`mark ${kind}`} aria-hidden="true"
      style={{ width: size, height: size, ...(color ? ({ '--mc': color } as CSSProperties) : {}) }} />
  )
}

export function MoneyBadge({ money }: { money: Money }) {
  return <span className="badge"><BookMark kind={money} size={9} />{money === 'real' ? 'REAL' : 'PAPER'}</span>
}

/** A signed value with ▲/▼ so a gain or loss never rests on colour alone. `digits` is the precision the value is
 *  shown at (pct() shows 1, money 2): what rounds to zero there is no change — muted, no arrow. */
export function Delta({ value, digits = 2, children }: { value: number; digits?: number; children: ReactNode }) {
  if (Math.abs(value) < 0.5 * 10 ** -digits) {
    return <span className="num" style={{ color: 'var(--ink3)' }}>{children}</span>
  }
  const up = value > 0
  return (
    <span className={`num ${up ? 'up' : 'down'}`}>
      <span aria-hidden="true">{up ? '▲' : '▼'} </span>
      <span className="sr-only">{up ? 'up ' : 'down '}</span>
      {children}
    </span>
  )
}

export function Panel({ id, title, subtitle, actions, span, height, children }: {
  id: string; title: string; subtitle?: string; actions?: ReactNode; span: 4 | 5 | 6 | 7 | 8 | 12; height?: number
  children: ReactNode
}) {
  return (
    <section className={`panel span-${span}`} aria-labelledby={`${id}-title`}
      style={height ? ({ '--h': `${height}px` } as CSSProperties) : undefined}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={`${id}-title`} className="panel-title">{title}</h2>
          {subtitle && <div className="panel-sub">{subtitle}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
      {children}
    </section>
  )
}

export function Seg<T extends string>({ label, options, value, onChange }: {
  label: string; options: readonly T[]; value: T; onChange: (value: T) => void
}) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((option) => (
        <button key={option} type="button" aria-pressed={option === value} onClick={() => onChange(option)}>
          {option}
        </button>
      ))}
    </div>
  )
}

/** "—" for a missing value (design-system rule), in muted ink */
export function Missing() {
  return <span style={{ color: 'var(--ink3)' }}>—</span>
}

/** The stat block: a caps label, the value, and a muted second line. */
export function Stat({ label, children, sub }: { label: string; children: ReactNode; sub?: ReactNode }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="text-[13px] mt-1.5">{children}</div>
      {sub && <div className="text-xs text-ink3 mt-1">{sub}</div>}
    </div>
  )
}

export interface Sort<K extends string> { key: K; dir: 'desc' | 'asc' }

/** A column clicked again flips its order; another column starts largest first. */
export function toggleSort<K extends string>(sort: Sort<K>, key: K): Sort<K> {
  return sort.key === key ? { key, dir: sort.dir === 'desc' ? 'asc' : 'desc' } : { key, dir: 'desc' }
}

/** A sortable column heading: a real button, with the order announced on the heading cell. */
export function SortHeader<K extends string>({ label, k, sort, onSort, right = false }: {
  label: string; k: K; sort: Sort<K>; onSort: (key: K) => void; right?: boolean
}) {
  const active = sort.key === k
  return (
    <th className={right ? 'r' : undefined} aria-sort={active ? (sort.dir === 'desc' ? 'descending' : 'ascending') : 'none'}>
      <button type="button" onClick={() => onSort(k)} className="uppercase tracking-[0.08em] font-medium"
        style={{ color: active ? 'var(--ink1)' : 'inherit', background: 'none', border: 0, padding: 0, cursor: 'pointer',
          font: 'inherit' }}>
        {label}
      </button>
      {active && <span aria-hidden="true"> {sort.dir === 'desc' ? '↓' : '↑'}</span>}
    </th>
  )
}

/** Where an account's money is filed: long-term money is slate, trading rufous, cash neutral. */
export const CATEGORY_COLOR: Record<string, string> = {
  long_term: 'var(--s1)', trading: 'var(--s2)', cash: 'var(--s3)', other: 'var(--ink3)',
}
export const CATEGORY_WORD: Record<string, string> = {
  long_term: 'Long-term', trading: 'Trading', cash: 'Cash', other: 'Other',
}

/** The category as a word beside its dot, so the colour is never the only cue. */
export function CategoryChip({ category }: { category: string }) {
  return (
    <span className="chip">
      <span aria-hidden="true" className="w-2 h-2 rounded-full flex-none"
        style={{ background: CATEGORY_COLOR[category] ?? 'var(--ink3)' }} />
      {CATEGORY_WORD[category] ?? category}
    </span>
  )
}
````


`web/src/charts/GrowthBar.tsx`:

````tsx
// Where the money came from, as one bar: what you started with, what you put in since, and what the market added.
import { scaleLinear } from 'd3-scale'
import type { CSSProperties, PointerEvent } from 'react'
import { Delta } from '../components/bits'
import { money, signedMoney } from '../lib/format'
import { clampTip } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Tip } from './marks'

export interface GrowthSteps {
  start: number
  deposits: number // deposits minus withdrawals
  market: number
  end: number
}

export type GrowthPart = 'start' | 'deposits' | 'market'
export const PART_LABEL: Record<GrowthPart, string> = {
  start: 'Started at', deposits: 'You put in', market: 'The market added',
}

interface Segment { key: GrowthPart; from: number; to: number }

/** The parts end to end: the start from zero, then what you put in, then the market up to the end. A negative part
 *  runs back over the one before it (money taken out, or lost). */
export function segments(g: GrowthSteps): Segment[] {
  const put = g.start + g.deposits
  return [
    { key: 'start', from: 0, to: g.start }, { key: 'deposits', from: g.start, to: put },
    { key: 'market', from: put, to: g.end },
  ]
}

const amount = (key: GrowthPart, value: number) => (key === 'market' ? signedMoney(value) : money(value))

/** The part under a position: the last one drawn there, as a later part draws over an earlier one. */
function partAt(parts: Segment[], value: number): number | null {
  for (let i = parts.length - 1; i >= 0; i -= 1) {
    const { from, to } = parts[i]
    if (from !== to && value >= Math.min(from, to) && value <= Math.max(from, to)) return i
  }
  return null
}

export function GrowthBar({ growth, height = 40, ariaLabel }: { growth: GrowthSteps; height?: number; ariaLabel: string }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const parts = segments(growth)
  const { index: hover, set: setHover, onKey } = useIndex(parts.length)
  const ends = parts.flatMap((p) => [p.from, p.to])
  const lo = Math.min(0, ...ends)
  const hi = Math.max(0, ...ends)
  if (hi === lo) return <Empty>Nothing to show yet.</Empty>

  const x = scaleLinear().domain([lo, hi]).range([0, width])
  const top = 6
  const barH = height - 2 * top
  const box = (p: Segment) => ({ x: x(Math.min(p.from, p.to)), width: Math.abs(x(p.to) - x(p.from)) })
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    setHover(partAt(parts, x.invert(event.clientX - rect.left)))
  }
  const [start, deposits, market] = parts
  const shown = hover == null ? null : parts[hover]

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        <rect data-mark="start" {...box(start)} y={top} height={barH} rx={3} fill="var(--s3)" />
        {/* what you put in is the reference money, drawn like the "Start + deposits" line: dotted, with a wash */}
        <rect data-mark="deposits" {...box(deposits)} y={top + 0.75} height={barH - 1.5} rx={3} fill="var(--ink1)"
          fillOpacity={0.05} stroke="var(--ref)" strokeWidth={1.5} strokeDasharray="1.5 2.5" />
        <rect data-mark={growth.market >= 0 ? 'gain' : 'loss'} {...box(market)} y={top} height={barH} rx={3}
          fill={growth.market >= 0 ? 'var(--up)' : 'var(--down)'} />
        <line x1={x(growth.end)} x2={x(growth.end)} y1={1} y2={height - 1} stroke="var(--ink1)" strokeWidth={2} />
        {shown && (
          <rect {...box(shown)} y={top - 3} height={barH + 6} rx={4} fill="none" stroke="var(--ink1)" strokeWidth={1.5} />
        )}
      </svg>
      {shown && hover != null && (
        <Tip left={clampTip(x((shown.from + shown.to) / 2), width)} top={height + 4} title={PART_LABEL[shown.key]}
          rows={[['Amount', amount(shown.key, shown.to - shown.from)]]} />
      )}
    </div>
  )
}

export function GrowthTable({ growth }: { growth: GrowthSteps }) {
  return (
    <table className="tbl" style={{ '--row': '36px' } as CSSProperties}>
      <thead><tr><th>Part</th><th className="r">Amount</th></tr></thead>
      <tbody>
        <tr><td>{PART_LABEL.start}</td><td className="r num">{money(growth.start)}</td></tr>
        <tr><td>{PART_LABEL.deposits}</td><td className="r num">{money(growth.deposits)}</td></tr>
        <tr>
          <td>{PART_LABEL.market}</td>
          <td className="r"><Delta value={growth.market}>{signedMoney(growth.market)}</Delta></td>
        </tr>
        <tr><td>Now</td><td className="r num">{money(growth.end)}</td></tr>
      </tbody>
    </table>
  )
}
````


`web/src/pages/home/NetWorthPanel.tsx`:

````tsx
import { useState } from 'react'
import { baseline, RANGES, type Range, windowPoints } from '../../charts/geometry'
import { LineChart, LineKey } from '../../charts/LineChart'
import { Delta, Panel, Seg, Stat } from '../../components/bits'
import type { NetWorth } from '../../lib/api'
import { compactMoney, monthLabel, money, pct, shortDate, signedMoney, splitCents } from '../../lib/format'

export function NetWorthPanel({ nw }: { nw: NetWorth }) {
  const [range, setRange] = useState<Range>('1Y')
  const [view, setView] = useState<'Chart' | 'Table'>('Chart')
  const points = windowPoints(nw.points, range)
  const base = baseline(points)
  const growth = points.length ? points[points.length - 1].value - base[base.length - 1] : 0
  const [whole, cents] = splitCents(nw.total)
  return (
    <Panel id="net-worth" title="Net worth" span={8} height={372}
      actions={<>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ink1)" style="solid" />Net worth
        </span>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ref)" style="dotted" />Start + deposits
        </span>
        <Seg label="Range" options={RANGES} value={range} onChange={setRange} />
        <Seg label="View" options={['Chart', 'Table'] as const} value={view} onChange={setView} />
      </>}>
      <div className="flex flex-wrap items-end gap-x-9 gap-y-3 mt-3.5">
        <div className="text-[38px] sm:text-5xl font-semibold tracking-[-0.035em] leading-none">
          {whole}<span className="text-ink3">.{cents}</span>
        </div>
        <div className="flex flex-wrap gap-x-7 gap-y-3 pb-1">
          <Stat label="Today" sub={nw.today.pct != null && pct(nw.today.pct, 2)}>
            <Delta value={nw.today.amount}>{signedMoney(nw.today.amount)}</Delta>
          </Stat>
          <Stat label="Month" sub={nw.month.pct != null && pct(nw.month.pct, 2)}>
            <Delta value={nw.month.amount}>{signedMoney(nw.month.amount)}</Delta>
          </Stat>
          <Stat label="Year" sub={<>incl. <span className="num">{money(nw.year_flows, false)}</span> deposited</>}>
            <Delta value={nw.year.amount}>{signedMoney(nw.year.amount)}</Delta>
          </Stat>
          <Stat label="Market" sub={`over ${range}`}>
            <Delta value={growth} digits={0}>{signedMoney(growth, false)}</Delta>
          </Stat>
        </div>
      </div>
      <div className="mt-auto pt-3">
        {points.length === 0 ? (
          <p className="text-ink3">No history yet. The chart appears once your accounts have a few days of data.</p>
        ) : view === 'Chart' ? (
          <LineChart dates={points.map((p) => p.date)} height={196}
            ariaLabel="Net worth against your starting value plus deposits"
            series={[
              { key: 'nw', label: 'Net worth', values: points.map((p) => p.value), color: 'var(--ink1)', style: 'solid',
                area: true },
              { key: 'base', label: 'Start + deposits', values: base, color: 'var(--ref)', style: 'dotted', step: true },
            ]}
            yFormat={compactMoney} valueFormat={(v) => money(v, false)}
            xLabel={(d) => monthLabel(d, range === '1M' || range === '3M')} tipTitle={(d) => shortDate(d)} />
        ) : (
          <div className="overflow-y-auto" style={{ maxHeight: 196 }}>
            <table className="tbl">
              <thead><tr><th>Date</th><th className="r">Net worth</th><th className="r">Start + deposits</th></tr></thead>
              <tbody>
                {points.map((p, i) => (
                  <tr key={p.date}>
                    <td>{shortDate(p.date)}</td>
                    <td className="r num">{money(p.value)}</td>
                    <td className="r num">{money(base[i])}</td>
                  </tr>
                )).reverse()}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Panel>
  )
}
````


`web/src/pages/strategy/TradesPanel.tsx`:

````tsx
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Missing, Panel, type Sort, SortHeader, toggleSort } from '../../components/bits'
import { type StrategyView, type TradeRow, useShell } from '../../lib/api'
import { monthLabel, num, pct, signedMoney } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'
import { reasonWord } from './Anatomy'

type SortKey = 'closed' | 'return' | 'pnl'

const VALUE: Record<SortKey, (t: TradeRow) => string | number> = {
  closed: (t) => `${t.closed}|${t.opened}|${t.symbol}`,
  return: (t) => t.return_pct,
  pnl: (t) => t.pnl,
}

/** "18 Sep" this year, "26 Nov 2025" before it */
function day(iso: string, year: number): string {
  return Number(iso.slice(0, 4)) === year ? monthLabel(iso, true) : `${monthLabel(iso, true)} ${iso.slice(0, 4)}`
}

/** Every closed trade in the primary book, newest first; sortable by closed date, return and P/L. */
export function TradesPanel({ v }: { v: StrategyView }) {
  const [sort, setSort] = useState<Sort<SortKey>>({ key: 'closed', dir: 'desc' })
  const shell = useShell()
  const year = new Date(shell.data?.now ?? Date.now()).getUTCFullYear()
  const word = MONEY_WORD[v.book ?? 'real']
  const onSort = (key: SortKey) => setSort((s) => toggleSort(s, key))
  const sorted = [...v.trades].sort((a, b) => {
    const [x, y] = [VALUE[sort.key](a), VALUE[sort.key](b)]
    const order = x < y ? -1 : x > y ? 1 : 0
    return sort.dir === 'desc' ? -order : order
  })
  return (
    <Panel id="trades" title="All trades" span={12} subtitle={`${word} book · ${v.trades.length} closed trades`}>
      {v.trades.length === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : (
        <div className="table-scroll overflow-y-auto mt-3.5" style={{ maxHeight: 560 }}>
          <table className="tbl" style={{ minWidth: 760, '--row': '44px' } as CSSProperties}>
            <thead>
              <tr>
                <th>Symbol</th><th>Opened</th>
                <SortHeader label="Closed" k="closed" sort={sort} onSort={onSort} />
                <th className="r">Days held</th>
                <SortHeader label="Return" k="return" sort={sort} onSort={onSort} right />
                <th className="r">R</th>
                <SortHeader label="P/L" k="pnl" sort={sort} onSort={onSort} right />
                <th style={{ paddingLeft: 16 }}>Why it closed</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((t, i) => (
                <tr key={`${t.symbol}-${t.opened}-${t.closed}-${i}`}>
                  <td>
                    <div className="flex items-center gap-2.5">
                      <BookMark kind={t.money} color="var(--s2)" />
                      <span className="num font-semibold">{t.symbol}</span>
                      <span className="sr-only">{t.money}</span>
                    </div>
                  </td>
                  <td className="num text-ink2">{day(t.opened, year)}</td>
                  <td className="num text-ink2">{day(t.closed, year)}</td>
                  <td className="r num">{t.days_held}</td>
                  <td className="r"><Delta value={t.return_pct}>{pct(t.return_pct, 2)}</Delta></td>
                  <td className="r num">{t.r_multiple == null ? <Missing /> : num(t.r_multiple, 2)}</td>
                  <td className="r"><Delta value={t.pnl}>{signedMoney(t.pnl)}</Delta></td>
                  <td style={{ paddingLeft: 16 }}>{reasonWord(t.exit_reason)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
````


- [ ] **Step 4: Run everything and watch it pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit && npm run build`
Expected: `Tests  127 passed (127)` (`GrowthBar.test.tsx` 5, `bits.test.tsx` 5); tsc prints nothing; `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/bits.tsx web/src/components/bits.test.tsx web/src/charts/GrowthBar.tsx web/src/charts/GrowthBar.test.tsx web/src/pages/home/NetWorthPanel.tsx web/src/pages/strategy/TradesPanel.tsx
git commit -m "feat(charts): the growth bar; Stat, SortHeader and the category chip join the shared pieces" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 8: API types and hooks, the account list, and Home's rows as links

**Files:**
- Modify (replace the whole file): `web/src/lib/api.ts`, `web/src/test/renderApp.tsx`, `web/src/router.tsx`, `web/src/pages/home/AllocationPanel.tsx`
- Create: `web/src/pages/accounts/GrowthPanel.tsx`, `web/src/pages/accounts/Accounts.tsx`
- Test (create or replace): `web/src/pages/accounts/Accounts.test.tsx`, `web/src/pages/home/Home.test.tsx`

**Interfaces:**
- Consumes: the generated `accounts.json` and `account-roth.json` (Task 6); Task 7's pieces.
- Produces:
  - `api.ts`: `Window`, `Category`, `Growth`, `AccountLine`, `CombinedHolding`, `AccountsView`, `Flow`, `HoldingRow`, `Totals`, `AccountView` (the Python field names), `useAccounts()` (`['accounts']`), `useAccount(id)` (`['account', id]`).
  - `renderApp.tsx`: `accountsFixture`, `accountFixture` (checked with `satisfies Widen<…>`); `Data.accounts?: AccountsView | null`, `Data.account?: { id, view }[]` (by default `roth` answers).
  - `GrowthPanel.tsx`: `WINDOWS`, `WINDOW_WORD` (This year · 1 year · All), `WindowSeg({ value, onChange })`, `GrowthTiles({ g, asOf, className? })` (Started at, with the day it is from · You put in · The market added · Now; dashes without growth), `GrowthPanel({ growth, asOf })` (span 12: window, Chart | Table, the tiles, the growth bar with its key).
  - `Accounts.tsx`: `headline(v) -> { lead, moved }` ("4 accounts, $162,265.11 in all." · "you deposited …" / "you withdrew …"), `kindText(a)` ("Brokerage A · Roth IRA"), `Accounts()`: the header sentence, Growth, the Accounts table (largest first; each name links to `/accounts/<id>`), and Everything you hold (the first 12, then "Show all N"). No accounts: `No accounts yet. Add a source in profile.toml (see docs/connectors.md).`
  - `router.tsx`: `/accounts` is the real page (the Phase 2 placeholder goes). `AllocationPanel`: each account row is a link to its page.

- [ ] **Step 1: Write the failing tests**

`web/src/pages/accounts/Accounts.test.tsx`:

````tsx
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AccountsView } from '../../lib/api'
import { accountsFixture, renderApp } from '../../test/renderApp'
import { headline, kindText } from './Accounts'

// a title lookup, not a role query over the whole app: role queries dominate these tests' time
const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const rows = (region: HTMLElement) => [...region.querySelectorAll('tbody tr')].map((r) => r.textContent)
const ytd = accountsFixture.growth.ytd!

describe('Accounts', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with how many accounts, how much, and this year in two figures', async () => {
    renderApp('/accounts')
    const title = await screen.findByRole('heading', { level: 1, name: 'Accounts' })
    expect(title.closest('header')?.textContent).toBe('MoneyAccounts4 accounts, $162,265.11 in all. This year the '
      + 'market added ▲ up +$11,511.65 and you deposited $11,100.00.')
  })

  it('words the sentence for one account, a withdrawal, and a year without history', () => {
    expect(headline(accountsFixture)).toEqual({ lead: '4 accounts, $162,265.11 in all.', moved: 'you deposited $11,100.00' })
    const one: AccountsView = { ...accountsFixture, count: 1, total: 500, growth: {
      ...accountsFixture.growth, ytd: { ...ytd, deposits: -250 } } }
    expect(headline(one)).toEqual({ lead: '1 account, $500.00 in all.', moved: 'you withdrew $250.00' })
    expect(headline({ ...accountsFixture, growth: { ...accountsFixture.growth, ytd: null } }).moved).toBeNull()
    expect([kindText({ institution: 'Bank C', account_type: '' }), kindText({ institution: '', account_type: '' })])
      .toEqual(['Bank C', ''])
  })

  it('splits the growth into what you put in and what the market added, for each window', async () => {
    renderApp('/accounts')
    const growth = await findPanel('Growth')
    expect(growth.textContent).toContain('Started at$139,653.461 Jan')
    expect(growth.textContent).toContain('You put in$11,100.00The market added▲ up +$11,511.65Now$162,265.11')
    fireEvent.click(within(growth).getByRole('button', { name: '1 year' }))
    expect(growth.textContent).toContain('Started at$123,300.00Sep 2025')
    expect(within(growth).getByRole('img', { name: '1 year: started at, you put in, the market added' })).toBeTruthy()
    fireEvent.click(within(growth).getByRole('button', { name: 'Table' }))
    expect(rows(growth)).toEqual(['Started at$123,300.00', 'You put in$15,900.00',
      'The market added▲ up +$23,065.11', 'Now$162,265.11'])
  })

  it('shows dashes for a window without enough history', async () => {
    renderApp('/accounts', { accounts: { ...accountsFixture, growth: { ...accountsFixture.growth, ytd: null } } })
    const growth = await findPanel('Growth')
    expect(within(growth).getAllByText('—')).toHaveLength(4)
    expect(within(growth).getByText('Not enough history for this window yet.')).toBeTruthy()
  })

  it('lists every account, largest first, each opening its own page', async () => {
    renderApp('/accounts')
    const accounts = await findPanel('Accounts')
    expect(rows(accounts)).toEqual([
      'Roth IRABrokerage A · Roth IRALong-term$67,890.8141.8%▼ down −$49.79−0.07%▲ up +$5,603.44',
      'BrokerageBrokerage A · BrokerageLong-term$51,663.7431.8%▲ up +$146.99+0.29%▲ up +$3,362.77',
      'High-yield savingsBank C · SavingsCash$24,242.8514.9%▲ up +$3.82+0.02%▲ up +$701.08',
      'Trading accountBrokerage B · IndividualTrading$18,467.7111.4%▼ down −$94.32−0.51%▲ up +$1,844.36',
    ])
    expect(within(accounts).getByRole('link', { name: 'Roth IRA' }).getAttribute('href')).toBe('/accounts/roth')
  })

  it('adds up everything held across accounts: the first twelve, then all of it', async () => {
    renderApp('/accounts')
    const held = await findPanel('Everything you hold')
    expect(rows(held)).toHaveLength(12)
    expect(rows(held).slice(0, 2)).toEqual([
      'SPYS&P 500 index fund$61,723.6838.0%Brokerage, Roth IRA',
      'Cash—$31,904.0719.7%Brokerage, High-yield savings, Roth IRA, Trading account',
    ])
    fireEvent.click(within(held).getByRole('button', { name: 'Show all 14' }))
    expect(rows(held)).toHaveLength(14)
    expect(within(held).getByRole('button', { name: 'Show the first 12' })).toBeTruthy()
  })

  it('says so when there are no accounts yet', async () => {
    const none: AccountsView = { ...accountsFixture, count: 0, total: 0, accounts: [], holdings: [],
      growth: { ytd: null, '1y': null, all: null } }
    renderApp('/accounts', { accounts: none })
    expect(await screen.findByText('No accounts yet. Add a source in profile.toml (see docs/connectors.md).'))
      .toBeTruthy()
    expect(document.querySelector('.panel-title')).toBeNull()
  })

  it('says it is loading, and says so plainly when the accounts could not load', async () => {
    const { unmount } = renderApp('/accounts', { accounts: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading your accounts…')).toBeTruthy()
    unmount()
    renderApp('/accounts', { accounts: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Accounts couldn’t load: network is off in tests')
  })
})
````


`web/src/pages/home/Home.test.tsx`:

````tsx
import { act, fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { HomeView } from '../../lib/api'
import { setCurrency } from '../../lib/format'
import { homeFixture, renderApp, shellFixture } from '../../test/renderApp'
import { period, verdict } from './ComparisonPanel'
import { summaryParts } from './Home'

const panel = (name: string) => screen.getByRole('region', { name })

const empty: HomeView = {
  ...homeFixture, allocation: [], accounts: [], attention: [], books: [], today: [], positions: [],
  comparison: { ...homeFixture.comparison, lines: [], dates: [], gap_pts: null, shallower: null },
  net_worth: { ...homeFixture.net_worth, total: 0, points: [] },
  summary: { day_change: 0, gap_pts: null, needs_you: 0 },
}

describe('Home', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with net worth, cents dimmed', async () => {
    renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    const [whole, cents] = homeFixture.net_worth.total.toFixed(2).split('.')
    expect(within(nw).getByText(`$${Number(whole).toLocaleString('en-US')}`)).toBeTruthy()
    expect(within(nw).getByText(`.${cents}`)).toBeTruthy()
  })

  it('opens an account from Where it sits', async () => {
    renderApp('/')
    const where = await screen.findByRole('region', { name: 'Where it sits' })
    const roth = within(where).getByRole('link', { name: /^Roth IRA/ })
    expect(roth.getAttribute('href')).toBe('/accounts/roth')
    expect(within(where).getAllByRole('link')).toHaveLength(homeFixture.accounts.length + 1) // and "4 accounts"
  })

  it('switches a chart to its table', async () => {
    renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    fireEvent.click(within(nw).getByRole('button', { name: 'Table' }))
    expect(within(nw).getByRole('table')).toBeTruthy()
    expect(within(nw).getAllByRole('row').length).toBeGreaterThan(200) // a year of weekdays
  })

  it('shows what needs you, most serious first', async () => {
    renderApp('/')
    const items = within(await screen.findByRole('region', { name: 'Needs you' })).getAllByRole('listitem')
    expect(items[0].textContent).toContain('MSFT has no resting stop')
    expect(items[0].textContent).toContain('Serious')
  })

  it('lists every book with its real/paper badge', async () => {
    renderApp('/')
    await screen.findByRole('region', { name: 'Books' })
    const rows = within(panel('Books')).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(homeFixture.books.length)
    expect(rows[0].textContent).toContain('REAL')
    expect(within(panel('Books')).getByText('Below band')).toBeTruthy()
  })

  it('puts the now line between done and due runs', async () => {
    renderApp('/')
    const today = await screen.findByRole('region', { name: 'Today' })
    const labels = within(today).getAllByRole('listitem').map((li) => li.getAttribute('aria-label') ?? li.textContent)
    const nowAt = labels.findIndex((l) => l?.startsWith('Now'))
    expect(labels[nowAt - 1]).toContain('ETF close entries')
    expect(labels[nowAt + 1]).toContain('Nightly suite')
  })

  it('caps the positions table and links to the rest', async () => {
    renderApp('/')
    const positions = await screen.findByRole('region', { name: 'Open positions' })
    expect(within(positions).getAllByRole('row')).toHaveLength(6) // header + 5
    expect(within(positions).getByText(`${homeFixture.positions.length - 5} more in Books`)).toBeTruthy()
  })

  it('handles a person with no data yet', async () => {
    renderApp('/', { home: empty })
    expect(await screen.findByText('Nothing needs you right now.')).toBeTruthy()
    expect(screen.getByText('No open positions.')).toBeTruthy()
    expect(within(panel('Trading vs your index money')).getByText(/No history yet/)).toBeTruthy()
    expect(within(panel('Net worth')).getByText(/No history yet/)).toBeTruthy()
  })

  it('survives a pointer or key on an empty chart', async () => {
    renderApp('/', { home: empty })
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    const chart = within(nw).queryByRole('img') ?? nw
    fireEvent.pointerMove(chart, { clientX: 40 })
    fireEvent.keyDown(chart, { key: 'ArrowRight' })
    expect(screen.getByRole('region', { name: 'Net worth' })).toBeTruthy()
    expect(screen.queryByText(/Something went wrong/)).toBeNull()
  })

  it('keeps what it showed when a refresh fails', async () => {
    const { client } = renderApp('/')
    await screen.findByRole('region', { name: 'Net worth' })
    act(() => client.getQueryCache().find({ queryKey: ['home'] })?.setState({
      status: 'error', error: new Error('/api/home answered 502'), fetchStatus: 'idle',
    }))
    expect((await screen.findByRole('alert')).textContent).toMatch(/refresh.*502/)
    expect(screen.getByRole('region', { name: 'Net worth' })).toBeTruthy()
  })

  it('prints a stop above the last price with a true minus sign', async () => {
    const positions = homeFixture.positions.map((p, i) => (i === 1 ? { ...p, room_pct: -2.5 } : p))
    renderApp('/', { home: { ...homeFixture, positions } })
    const table = await screen.findByRole('region', { name: 'Open positions' })
    expect(within(table).getByText('−2.5%')).toBeTruthy()
  })

  describe('in another currency', () => {
    afterEach(() => setCurrency('USD'))

    it('shows every amount in the profile currency from the first render', async () => {
      renderApp('/', { shell: { ...shellFixture, app: { ...shellFixture.app, currency: 'EUR' } } })
      const nw = await screen.findByRole('region', { name: 'Net worth' })
      const [whole] = homeFixture.net_worth.total.toFixed(2).split('.')
      expect(within(nw).getByText(`€${Number(whole).toLocaleString('en-US')}`)).toBeTruthy()
      expect(nw.textContent).not.toContain('$')
    })
  })

  it('marks returns as gains or losses, never by colour alone', async () => {
    renderApp('/')
    const cmp = await screen.findByRole('region', { name: 'Trading vs your index money' })
    expect(within(cmp).getAllByText('up')).toHaveLength(3)
  })
})

describe('words from the data', () => {
  it('writes the summary sentence', async () => {
    const base = homeFixture
    expect(summaryParts(base).needs).toBe('2 items need you.')
    expect(summaryParts(base).trading).toBe('Trading is ahead of your index money by 2.9 pts this year.')
    const behind = { ...base, summary: { ...base.summary, gap_pts: -1.26, needs_you: 1 } }
    expect(summaryParts(behind)).toEqual({
      trading: 'Trading is behind your index money by 1.3 pts this year.', needs: 'One item needs you.',
    })
    expect(summaryParts({ ...base, summary: { ...base.summary, gap_pts: null, needs_you: 0 } }))
      .toEqual({ trading: null, needs: 'Nothing needs you.' })
    // a weekend or a flat day: no "$0.00", no arrow
    renderApp('/', { home: { ...base, summary: { ...base.summary, day_change: 0.004 } } })
    expect(await screen.findByText(/^All your money is unchanged today\. Trading is ahead/)).toBeTruthy()
  })

  it('writes the verdict with its sample-size caveat', () => {
    const v = verdict(homeFixture.comparison)
    expect(v?.headline).toMatch(/^Trading is ahead by 2\.9 pts this year, with a shallower worst drop/)
    expect(v?.caveat).toBe('34 real trades so far — early evidence. The strategy is reviewed at 50.')
    expect(verdict({ ...homeFixture.comparison, gap_pts: null })).toBeNull()
    const lt = homeFixture.comparison.lines.find((l) => l.key === 'long_term')!
    const level = homeFixture.comparison.lines.map((l) => (l.key === 'trading'
      ? { ...l, max_drop_pct: lt.max_drop_pct + 0.04 } : l))
    expect(verdict({ ...homeFixture.comparison, lines: level })?.headline).toMatch(/, with an equal worst drop \(/)
  })

  it('names no date when there is nothing to compare yet', () => {
    const none = { ...homeFixture.comparison, window: '12m' as const, start: '2025-09-25', dates: [], lines: [] }
    expect(period(none)).toEqual({ phrase: 'over the past 12 months', title: 'Past 12 months' })
  })

  it('names the shared start when a line begins later in the year', async () => {
    const late: HomeView = { ...homeFixture, comparison: { ...homeFixture.comparison, start: '2026-07-01' } }
    expect(summaryParts(late).trading).toBe('Trading is ahead of your index money by 2.9 pts since 1 Jul.')
    expect(verdict(late.comparison)?.headline).toMatch(/^Trading is ahead by 2\.9 pts since 1 Jul, with a/)
    // the year's first close can fall a few days into January: that is still "this year"
    const firstClose: HomeView = { ...homeFixture, comparison: { ...homeFixture.comparison, start: '2026-01-05' } }
    expect(summaryParts(firstClose).trading).toMatch(/this year\.$/)
    renderApp('/', { home: late })
    const cmp = await screen.findByRole('region', { name: 'Trading vs your index money' })
    expect(within(cmp).getByText(/^Since 1 Jul · real money only/)).toBeTruthy()
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/pages/accounts/Accounts.test.tsx src/pages/home/Home.test.tsx`
Expected: `Test Files  2 failed (2)` and `Tests  1 failed | 16 passed (17)`: `Failed to resolve import "./Accounts"`, and `opens an account from Where it sits` (`Unable to find an accessible element with the role "link" and name /^Roth IRA/`).

- [ ] **Step 3: Implement**

`web/src/lib/api.ts`:

````ts
// Types mirror src/kestrel/views/*.py, by hand. What keeps them honest:
// - the fixtures in src/test/fixtures are generated from the Python code, and a Python test fails when they drift;
// - src/test/renderApp.tsx checks the fixtures `satisfies` these types, so `tsc` fails when a field here is renamed,
//   missing from Python's output, or of another JSON type.
// Not checked: a field Python adds that is not declared here, and the members of string-literal unions (both sides
// are plain strings in JSON).
import { useQuery } from '@tanstack/react-query'

export type Money = 'real' | 'paper'
export type Level = 'serious' | 'warning' | 'note'

export interface AppSettings {
  name: string
  accent: 'rufous' | 'slate' | 'mono'
  theme: 'system' | 'dark' | 'light'
  gain_loss: 'green-red' | 'blue-orange'
  density: 'comfortable' | 'compact'
  currency: string
  timezone: string
}

export interface Source {
  id: string
  label: string
  kind: string
  last_success: string | null
  status: 'ok' | 'stale' | 'error'
  detail: string
}

export interface ShellView {
  name: string
  app: AppSettings
  benchmark_label: string
  now: string
  sources: Source[]
  counts: { accounts: number; books: number; strategies: number }
}

export interface Delta {
  amount: number
  pct: number | null
}

export interface ValuePoint {
  date: string
  value: number
  net_flow: number
}

export interface NetWorth {
  total: number
  today: Delta
  month: Delta
  year: Delta
  year_flows: number
  points: ValuePoint[]
}

export interface Slice {
  category: string
  label: string
  value: number
  share: number
  cells: number
}

export interface AccountRow {
  id: string
  name: string
  category: string
  value: number
  day_pct: number | null
}

export interface Line {
  key: 'trading' | 'long_term' | 'benchmark'
  label: string
  return_pct: number
  max_drop_pct: number
  values: (number | null)[]
}

export interface Comparison {
  window: 'ytd' | '12m'
  start: string // the lines' shared first day
  dates: string[]
  lines: Line[]
  gap_pts: number | null
  shallower: boolean | null
  real_trades: number
  review_at: number | null
}

export interface Attention {
  level: Level
  title: string
  detail: string
  link: string
}

export interface BookRow {
  id: string
  name: string
  strategy: string
  money: Money
  status: string
  value: number
  day_change: number | null
  since_pct: number | null
  started: string
  trades: number
  per_trade_pct: number | null
  band_lo: number | null
  band_hi: number | null
  verdict: 'in_band' | 'below' | 'above' | 'early' | 'none'
  slots_used: number
  slots_total: number | null
  next_run: string | null
}

export interface TodayRun {
  time: string
  label: string
  status: 'done' | 'due' | 'late' | 'failed' | 'paused'
  detail: string
}

export interface PositionRow {
  book_id: string
  book: string
  symbol: string
  money: Money
  quantity: number
  entry_price: number
  last_price: number
  stop_price: number | null
  room_pct: number | null
  pnl: number
  note: string
}

export interface HomeView {
  as_of: string
  summary: { day_change: number; gap_pts: number | null; needs_you: number }
  net_worth: NetWorth
  allocation: Slice[]
  accounts: AccountRow[]
  comparison: Comparison
  attention: Attention[]
  books: BookRow[]
  today: TodayRun[]
  positions: PositionRow[]
}

// --- the Strategy pages (src/kestrel/views/strategy.py) ---------------------------------------------------------

export type Verdict = BookRow['verdict']

export interface BookChip {
  id: string
  name: string
  money: Money
  status: string
  open: number
  trades: number
}

export interface StrategyCard {
  id: string
  name: string
  summary: string
  books: BookChip[]
  book: Money | null
  trades: number
  per_trade_pct: number | null
  band_lo: number | null
  band_hi: number | null
  verdict: Verdict
}

export interface StrategiesView {
  strategies: StrategyCard[]
}

export interface Step {
  label: string
  title: string
  text: string
  params: string[]
}

export interface Expected {
  win_rate: number
  avg_trade_pct: number
  avg_win_pct: number
  avg_loss_pct: number
  trades_per_month: number
  sd_trade_pct: number
  distribution: number[]
  source: string
  window: string
  cagr_pct: number | null
  max_drawdown_pct: number | null
}

export interface Bucket {
  low: number
  count: number
  share: number
  expected: number | null
}

export interface ScoreRow {
  key: 'win_rate' | 'avg_trade' | 'avg_win' | 'avg_loss' | 'per_month'
  label: string
  actual: number | null
  expected: number | null
  status: 'ok' | 'above' | 'below' | 'early' | 'none'
}

export interface OtherBook {
  id: string
  money: Money
  trades: number
  per_trade_pct: number | null
  win_rate: number | null
}

export interface Behaving {
  trades: number
  buckets: Bucket[]
  scorecard: ScoreRow[]
  review_at: number | null
  other: OtherBook | null
}

export interface FunnelLine {
  book_id: string
  money: Money
  values: number[]
}

export interface Funnel {
  expected: number | null
  lines: FunnelLine[]
  lo: (number | null)[]
  hi: (number | null)[]
}

export interface WatchItem {
  symbol: string
  label: string
  value: number | null
  note: string
}

export interface Slots {
  book_id: string | null
  total: number | null
  days: string[]
  used: number[]
  avg_used: number | null
  working_pct: number | null
  idle: number
  watch: WatchItem[]
}

export interface RecentTrade {
  key: string
  symbol: string
  money: Money
  opened: string
  closed: string
  return_pct: number
  r_multiple: number | null
  exit_reason: string
  sessions: number
  chart: boolean
}

export interface Bar {
  date: string
  open: number
  high: number
  low: number
  close: number
}

export interface Indicator {
  label: string
  values: (number | null)[]
  lines: { value: number; label: string }[]
}

export interface AnatomyChart {
  key: string
  bars: Bar[]
  indicator: Indicator | null
  stop: number | null
  entry: number
  exit: number
  entry_price: number
  exit_price: number
}

export interface Anatomy {
  recent: RecentTrade[]
  charts: AnatomyChart[]
  selected: string | null
}

export interface WorthPoint {
  key: 'backtest' | 'book' | 'long_term' | 'benchmark'
  label: string
  period: string
  early: boolean
  return_pct: number
  drop_pct: number
}

export interface Month {
  month: string
  book: number | null
  long_term: number | null
  ahead: boolean | null
}

export interface Monthly {
  months: Month[]
  ahead: number
  compared: number
  best: { month: string; value: number } | null
  worst: { month: string; value: number } | null
}

export interface TradeRow {
  symbol: string
  money: Money
  opened: string
  closed: string
  days_held: number
  return_pct: number
  r_multiple: number | null
  pnl: number
  exit_reason: string
}

export interface StrategyView {
  id: string
  name: string
  summary: string
  books: BookChip[]
  book: Money | null
  primary: string | null
  toggle: boolean
  expected: Expected | null
  steps: Step[]
  sizing: string
  behaving: Behaving
  funnel: Funnel
  slots: Slots
  anatomy: Anatomy
  worth: { points: WorthPoint[] }
  monthly: Monthly
  trades: TradeRow[]
}

// --- the Accounts pages (src/kestrel/views/accounts.py) ---------------------------------------------------------

export type Window = 'ytd' | '1y' | 'all'
export type Category = 'long_term' | 'trading' | 'cash' | 'other'

export interface Growth {
  start_date: string // the day the starting value is from
  start: number
  deposits: number // deposits minus withdrawals
  market: number
  end: number
}

export interface AccountLine {
  id: string
  name: string
  institution: string
  account_type: string
  category: Category
  value: number
  share: number | null
  day_change: number | null
  day_pct: number | null
  year_market: number | null
}

export interface CombinedHolding {
  symbol: string // empty on the cash row
  name: string
  cash: boolean
  value: number
  share: number | null
  accounts: string[]
}

export interface AccountsView {
  as_of: string
  count: number
  total: number
  growth: Record<Window, Growth | null>
  accounts: AccountLine[]
  holdings: CombinedHolding[]
}

export interface Flow {
  date: string
  amount: number // positive in, negative out
}

export interface HoldingRow {
  symbol: string
  name: string
  quantity: number
  price: number
  value: number
  weight: number | null
  cost_basis: number | null
  gain: number | null
  gain_pct: number | null
}

export interface Totals {
  value: number
  cost_basis: number | null
  gain: number | null
  gain_pct: number | null
  unknown_cost: number
}

export interface AccountView {
  id: string
  name: string
  institution: string
  account_type: string
  category: Category
  value: number
  as_of: string
  points: ValuePoint[]
  growth: Record<Window, Growth | null>
  flows: Flow[]
  holdings: HoldingRow[]
  cash: number
  cash_weight: number | null
  totals: Totals
}

/** A non-2xx answer, with its status, so a page can tell "not found" from "the server is down". */
export class HttpError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new HttpError(response.status, `${path} answered ${response.status}`)
  return (await response.json()) as T
}

const MINUTE = 60_000

export function useShell() {
  return useQuery({ queryKey: ['shell'], queryFn: () => getJson<ShellView>('/api/shell'), refetchInterval: MINUTE })
}

export function useHome() {
  return useQuery({ queryKey: ['home'], queryFn: () => getJson<HomeView>('/api/home'), refetchInterval: MINUTE })
}

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'], queryFn: () => getJson<AccountsView>('/api/accounts'), refetchInterval: MINUTE,
  })
}

export function useAccount(id: string) {
  return useQuery({
    queryKey: ['account', id],
    queryFn: () => getJson<AccountView>(`/api/accounts/${encodeURIComponent(id)}`),
    refetchInterval: MINUTE,
  })
}

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'], queryFn: () => getJson<StrategiesView>('/api/strategies'), refetchInterval: MINUTE,
  })
}

export function useStrategy(id: string, book: Money) {
  return useQuery({
    queryKey: ['strategy', id, book],
    queryFn: () => getJson<StrategyView>(`/api/strategies/${encodeURIComponent(id)}?book=${book}`),
    refetchInterval: MINUTE,
    // switching Real | Paper keeps the page up until the other book arrives; another strategy starts clean
    placeholderData: (previous, query) => (query?.queryKey[1] === id ? previous : undefined),
  })
}
````


`web/src/test/renderApp.tsx`:

````tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, RouterProvider } from '@tanstack/react-router'
import { render } from '@testing-library/react'
import { vi } from 'vitest'
import type { AccountsView, AccountView, HomeView, Money, ShellView, StrategiesView, StrategyView } from '../lib/api'
import { createAppRouter } from '../router'
import accountJson from './fixtures/account-roth.json'
import accountsJson from './fixtures/accounts.json'
import homeJson from './fixtures/home.json'
import shellJson from './fixtures/shell.json'
import strategiesJson from './fixtures/strategies.json'
import strategyJson from './fixtures/strategy-rsi2.json'

/** The API types with every string-literal union widened to `string`, the way TypeScript types a JSON import. */
type Widen<T> = T extends string ? string
  : T extends (infer U)[] ? Widen<U>[]
  : T extends object ? { [K in keyof T]: Widen<T[K]> }
  : T

// Generated by `kestrel demo --view ...`; tests/test_generated_files.py keeps them in step with the Python code, and
// `satisfies` makes `tsc` fail when a field in lib/api.ts is renamed or missing from what Python emits.
export const homeFixture = (homeJson satisfies Widen<HomeView>) as unknown as HomeView
export const shellFixture = (shellJson satisfies Widen<ShellView>) as unknown as ShellView
export const strategiesFixture = (strategiesJson satisfies Widen<StrategiesView>) as unknown as StrategiesView
export const strategyFixture = (strategyJson satisfies Widen<StrategyView>) as unknown as StrategyView
export const accountsFixture = (accountsJson satisfies Widen<AccountsView>) as unknown as AccountsView
export const accountFixture = (accountJson satisfies Widen<AccountView>) as unknown as AccountView

interface Data {
  home?: HomeView
  shell?: ShellView
  strategies?: StrategiesView | null // null: leave it unanswered, so the page fetches (and the fetch fails)
  strategy?: { id: string; book: Money; view: StrategyView }[] // answers for GET /api/strategies/{id}?book=
  accounts?: AccountsView | null
  account?: { id: string; view: AccountView }[] // answers for GET /api/accounts/{id}
}

/** The whole app at `path`, with the API answered from fixtures. Any other network call goes to `fetchImpl`, which
 *  fails by default. */
export function renderApp(path = '/', data: Data = {}, fetchImpl?: (url: string) => Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn(fetchImpl ?? (() => Promise.reject(new Error('network is off in tests')))))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } })
  client.setQueryData(['home'], data.home ?? homeFixture)
  client.setQueryData(['shell'], data.shell ?? shellFixture)
  if (data.strategies !== null) client.setQueryData(['strategies'], data.strategies ?? strategiesFixture)
  for (const { id, book, view } of data.strategy ?? [{ id: 'rsi2', book: 'real', view: strategyFixture }]) {
    client.setQueryData(['strategy', id, book], view)
  }
  if (data.accounts !== null) client.setQueryData(['accounts'], data.accounts ?? accountsFixture)
  for (const { id, view } of data.account ?? [{ id: 'roth', view: accountFixture }]) {
    client.setQueryData(['account', id], view)
  }
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }))
  const view = render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...view, router, client }
}
````


`web/src/pages/accounts/GrowthPanel.tsx`:

````tsx
// How the money grew over a window: what it started at, what you put in, and what the market added.
import { type ReactNode, useState } from 'react'
import { GrowthBar, GrowthTable, PART_LABEL } from '../../charts/GrowthBar'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Missing, Panel, Seg, Stat } from '../../components/bits'
import type { Growth, Window } from '../../lib/api'
import { money, signedMoney, sinceLabel } from '../../lib/format'

export const WINDOWS: readonly Window[] = ['ytd', '1y', 'all']
export const WINDOW_WORD: Record<Window, string> = { ytd: 'This year', '1y': '1 year', all: 'All' }
const WORDS = WINDOWS.map((w) => WINDOW_WORD[w])
const VIEWS = ['Chart', 'Table'] as const

/** This year · 1 year · All */
export function WindowSeg({ value, onChange }: { value: Window; onChange: (window: Window) => void }) {
  return (
    <Seg label="Window" options={WORDS} value={WINDOW_WORD[value]}
      onChange={(word) => onChange(WINDOWS.find((w) => WINDOW_WORD[w] === word) ?? value)} />
  )
}

function Tile({ label, sub, children }: { label: string; sub?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-line px-3 py-2.5 min-w-0 [overflow-wrap:anywhere]">
      <Stat label={label} sub={sub}>{children}</Stat>
    </div>
  )
}

/** The four figures. A window with fewer than two days of history has no growth: dashes. */
export function GrowthTiles({ g, asOf, className = 'grid-cols-2' }: { g: Growth | null; asOf: string; className?: string }) {
  const figure = (text: string) => <span className="num text-lg">{text}</span>
  return (
    <div className={`grid gap-3 ${className}`}>
      <Tile label={PART_LABEL.start} sub={g ? sinceLabel(g.start_date, asOf) : undefined}>
        {g ? figure(money(g.start)) : <Missing />}
      </Tile>
      <Tile label={PART_LABEL.deposits}>{g ? figure(money(g.deposits)) : <Missing />}</Tile>
      <Tile label={PART_LABEL.market}>
        {g ? <span className="text-lg"><Delta value={g.market}>{signedMoney(g.market)}</Delta></span> : <Missing />}
      </Tile>
      <Tile label="Now">{g ? figure(money(g.end)) : <Missing />}</Tile>
    </div>
  )
}

/** Every account together: the four figures for the window, then the same split as one bar. */
export function GrowthPanel({ growth, asOf }: { growth: Record<Window, Growth | null>; asOf: string }) {
  const [period, setPeriod] = useState<Window>('ytd')
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const g = growth[period]
  return (
    <Panel id="growth" title="Growth" subtitle="How much of the change was what you put in, and how much the market"
      span={12} actions={<>
        <WindowSeg value={period} onChange={setPeriod} />
        {g && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}
      </>}>
      <div className="mt-4"><GrowthTiles g={g} asOf={asOf} className="grid-cols-2 lg:grid-cols-4" /></div>
      {g == null ? (
        <Empty>Not enough history for this window yet.</Empty>
      ) : view === 'Chart' ? (
        <div className="mt-5">
          <GrowthBar growth={g} ariaLabel={`${WINDOW_WORD[period]}: started at, you put in, the market added`} />
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 text-xs text-ink2">
            <span className="inline-flex items-center gap-1.5"><BookMark kind="real" color="var(--s3)" />{PART_LABEL.start}</span>
            <span className="inline-flex items-center gap-1.5"><BookMark kind="expected" />{PART_LABEL.deposits}</span>
            <span className="inline-flex items-center gap-1.5">
              <BookMark kind="real" color={g.market >= 0 ? 'var(--up)' : 'var(--down)'} />{PART_LABEL.market}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className="inline-block w-0.5 h-3 bg-ink1" />Now
            </span>
          </div>
        </div>
      ) : (
        <div className="mt-4"><GrowthTable growth={g} /></div>
      )}
    </Panel>
  )
}
````


`web/src/pages/accounts/Accounts.tsx`:

````tsx
// Every account: what each holds, and how much of the growth was your deposits vs the market.
import { Link } from '@tanstack/react-router'
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { CategoryChip, Delta, Missing, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type AccountLine, type AccountsView, type CombinedHolding, useAccounts } from '../../lib/api'
import { money, num, pct, signedMoney } from '../../lib/format'
import { GrowthPanel } from './GrowthPanel'

const SHOWN = 12

/** The sentence under the title, from the data: how many accounts, how much, and this year in two figures. */
export function headline(v: AccountsView): { lead: string; moved: string | null } {
  const lead = `${v.count} account${v.count === 1 ? '' : 's'}, ${money(v.total)} in all.`
  const year = v.growth.ytd
  if (!year) return { lead, moved: null }
  const moved = year.deposits >= 0 ? `you deposited ${money(year.deposits)}` : `you withdrew ${money(-year.deposits)}`
  return { lead, moved }
}

/** "Brokerage A · Roth IRA", leaving out whichever is unknown */
export function kindText(a: { institution: string; account_type: string }): string {
  return [a.institution, a.account_type].filter(Boolean).join(' · ')
}

/** A share of a whole, in percent: no sign, since it is not a change. */
const shareCell = (value: number | null) => (value == null ? <Missing /> : `${num(value, 1)}%`)

function AccountsPanel({ accounts }: { accounts: AccountLine[] }) {
  return (
    <Panel id="accounts" title="Accounts" subtitle="Largest first · open one to see what it holds" span={12}>
      <div className="table-scroll mt-3.5">
        <table className="tbl" style={{ minWidth: 820 }}>
          <thead>
            <tr>
              <th>Account</th><th>Category</th><th className="r">Value</th><th className="r">Share</th>
              <th className="r">Today</th><th className="r">Market this year</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id}>
                <td>
                  <Link to="/accounts/$accountId" params={{ accountId: a.id }}
                    className="inline-flex items-center gap-1 font-medium">
                    <span className="text-ink1">{a.name}</span><Icon name="chevron" size={13} />
                  </Link>
                  {kindText(a) && <div className="text-xs text-ink3 mt-0.5">{kindText(a)}</div>}
                </td>
                <td><CategoryChip category={a.category} /></td>
                <td className="r num">{money(a.value)}</td>
                <td className="r num">{shareCell(a.share)}</td>
                <td className="r">
                  {a.day_change == null ? <Missing /> : <Delta value={a.day_change}>{signedMoney(a.day_change)}</Delta>}
                  {a.day_pct != null && <div className="num text-[11px] text-ink3 mt-0.5">{pct(a.day_pct, 2)}</div>}
                </td>
                <td className="r">
                  {a.year_market == null ? <Missing /> : <Delta value={a.year_market}>{signedMoney(a.year_market)}</Delta>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

/** Every holding added up by symbol across accounts, with all the cash as one row; the first twelve, then the rest. */
function EverythingPanel({ rows }: { rows: CombinedHolding[] }) {
  const [all, setAll] = useState(false)
  const shown = all ? rows : rows.slice(0, SHOWN)
  return (
    <Panel id="everything" title="Everything you hold" subtitle="Across every account, largest first" span={12}>
      {rows.length === 0 ? (
        <Empty>Nothing held yet.</Empty>
      ) : (
        <>
          <div className="table-scroll mt-3.5">
            <table className="tbl" style={{ minWidth: 640, '--row': '48px' } as CSSProperties}>
              <thead>
                <tr>
                  <th>Symbol</th><th>Name</th><th className="r">Value</th><th className="r">Share</th>
                  <th style={{ paddingLeft: 16 }}>Held in</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r, i) => (
                  <tr key={`${r.symbol}-${i}`}>
                    <td>
                      {r.cash ? <span className="font-medium">Cash</span> : <span className="num font-semibold">{r.symbol}</span>}
                    </td>
                    <td className="text-ink2">{r.cash || !r.name ? <Missing /> : r.name}</td>
                    <td className="r num">{money(r.value)}</td>
                    <td className="r num">{shareCell(r.share)}</td>
                    <td className="text-sm text-ink2" style={{ paddingLeft: 16 }}>{r.accounts.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length > SHOWN && (
            <button type="button" onClick={() => setAll(!all)} className="self-start mt-3 text-xs"
              style={{ color: 'var(--acc-ink)', background: 'none', border: 0, padding: 0, cursor: 'pointer' }}>
              {all ? `Show the first ${SHOWN}` : `Show all ${rows.length}`}
            </button>
          )}
        </>
      )}
    </Panel>
  )
}

export function Accounts() {
  const list = useAccounts()
  if (list.isPending) return <p className="text-ink3" role="status">Loading your accounts…</p>
  if (!list.data) {
    return <div role="alert" className="panel">Accounts couldn&rsquo;t load: {list.error.message}</div>
  }
  const v = list.data
  const { lead, moved } = headline(v)
  const year = v.growth.ytd
  return (
    <>
      <header className="mb-5">
        <div className="label">Money</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Accounts</h1>
        {v.count > 0 && (
          <p className="text-ink2 mt-1.5">
            {lead}
            {year && moved && (
              <> This year the market added <Delta value={year.market}>{signedMoney(year.market)}</Delta> and {moved}.</>
            )}
          </p>
        )}
      </header>
      {v.count === 0 ? (
        <div className="panel text-ink2">No accounts yet. Add a source in profile.toml (see docs/connectors.md).</div>
      ) : (
        <div className="grid12">
          <GrowthPanel growth={v.growth} asOf={v.as_of} />
          <AccountsPanel accounts={v.accounts} />
          <EverythingPanel rows={v.holdings} />
        </div>
      )}
    </>
  )
}
````


`web/src/pages/home/AllocationPanel.tsx`:

````tsx
import { Link } from '@tanstack/react-router'
import { CATEGORY_COLOR, CATEGORY_WORD, Delta, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { AccountRow, Slice } from '../../lib/api'
import { money, pct } from '../../lib/format'

/** 100 cells, filled column by column, so the waffle reads like one proportional bar. */
export function Waffle({ slices }: { slices: Slice[] }) {
  const cells = slices.flatMap((s) => Array.from({ length: s.cells }, () => s.category))
  return (
    <div role="img" aria-label={slices.map((s) => `${s.label} ${s.share.toFixed(1)} percent`).join(', ')}
      style={{ display: 'grid', gridTemplateColumns: 'repeat(20, minmax(0, 1fr))',
        gridTemplateRows: 'repeat(5, auto)', gridAutoFlow: 'column', gap: 4 }}>
      {cells.map((category, i) => (
        <span key={i} style={{ aspectRatio: '1', borderRadius: 2, background: CATEGORY_COLOR[category] }} />
      ))}
    </div>
  )
}

export function AllocationPanel({ slices, accounts }: { slices: Slice[]; accounts: AccountRow[] }) {
  return (
    <Panel id="allocation" title="Where it sits" span={4} height={372}
      actions={<Link to="/accounts" className="text-xs inline-flex items-center gap-1">
        {accounts.length} accounts<Icon name="chevron" size={13} />
      </Link>}>
      <div className="mt-4"><Waffle slices={slices} /></div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-3">
        {slices.map((s) => (
          <span key={s.category} className="inline-flex items-center gap-1.5 text-[11.5px] text-ink2 whitespace-nowrap">
            <span className="mark real" style={{ '--mc': CATEGORY_COLOR[s.category], width: 10, height: 10 } as React.CSSProperties} />
            {s.label} <span className="num text-ink1">{s.share.toFixed(1)}%</span>
          </span>
        ))}
      </div>
      <div className="mt-3.5 overflow-y-auto">
        {accounts.map((a) => (
          // each row opens the account; the text keeps its own ink, not the link colour
          <Link key={a.id} to="/accounts/$accountId" params={{ accountId: a.id }}
            className="flex items-center gap-2.5 h-[42px] border-t border-line">
            <span className="w-2 h-2 rounded-full flex-none" style={{ background: CATEGORY_COLOR[a.category] }} />
            <span className="text-[13px] font-medium truncate text-ink1">{a.name}</span>
            <span className="text-[11px] text-ink3 hidden sm:inline">{CATEGORY_WORD[a.category]}</span>
            <div className="ml-auto text-right">
              <div className="num text-[13px] text-ink1">{money(a.value)}</div>
              <div className="text-[11px]">
                {a.day_pct == null ? <span className="text-ink3">—</span> : <Delta value={a.day_pct}>{pct(a.day_pct, 2)}</Delta>}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </Panel>
  )
}
````


`web/src/router.tsx`:

````tsx
import { createRootRoute, createRoute, createRouter, type RouterHistory, useNavigate } from '@tanstack/react-router'
import type { Money } from './lib/api'
import { Accounts } from './pages/accounts/Accounts'
import { Home } from './pages/home/Home'
import { Soon } from './pages/Soon'
import { Strategies } from './pages/strategies/Strategies'
import { Strategy } from './pages/strategy/Strategy'
import { Shell } from './shell/Shell'

const root = createRootRoute({
  component: Shell,
  notFoundComponent: () => <Soon title="Not found" text="There is no page here. Pick one from the menu." />,
})

const later = (path: string, title: string, text: string) =>
  createRoute({ getParentRoute: () => root, path, component: () => <Soon title={title} text={text} /> })

/** `?book=real|paper` picks the money the page focuses on; anything else is dropped (the page defaults to real). */
function bookSearch(search: Record<string, unknown>): { book?: Money } {
  return search.book === 'real' || search.book === 'paper' ? { book: search.book } : {}
}

const strategyRoute = createRoute({
  getParentRoute: () => root,
  path: '/strategies/$strategyId',
  validateSearch: bookSearch,
  component: StrategyRoute,
})

function StrategyRoute() {
  const { strategyId } = strategyRoute.useParams()
  const { book } = strategyRoute.useSearch()
  const navigate = useNavigate()
  return (
    <Strategy id={strategyId} book={book ?? 'real'}
      onBook={(next) => navigate({ to: '/strategies/$strategyId', params: { strategyId }, search: { book: next } })} />
  )
}

const routeTree = root.addChildren([
  createRoute({ getParentRoute: () => root, path: '/', component: Home }),
  createRoute({ getParentRoute: () => root, path: '/accounts', component: Accounts }),
  later('/books', 'Books', 'Each book, real or paper: equity against its benchmark, drawdown, trades — Phase 3.'),
  createRoute({ getParentRoute: () => root, path: '/strategies', component: Strategies }),
  strategyRoute,
  later('/backtests', 'Backtests', 'What has been tested and what passed — Phase 5.'),
  later('/activity', 'Activity', 'What ran, what is due, what failed — Phase 5.'),
  later('/settings', 'Settings', 'Your profile and the status of every source — Phase 5.'),
])

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, history, defaultPreload: 'intent' })
}
````


- [ ] **Step 4: Run everything and watch it pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit && npm run build`
Expected: `Tests  136 passed (136)` (`Accounts.test.tsx` 8, `Home.test.tsx` 17); tsc prints nothing; `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/test/renderApp.tsx web/src/router.tsx web/src/pages/home/AllocationPanel.tsx web/src/pages/home/Home.test.tsx web/src/pages/accounts
git commit -m "feat(web): the account list: growth, every account, everything you hold; Home's accounts open their page" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 9: One account's page

**Files:**
- Create: `web/src/pages/account/ValuePanel.tsx`, `web/src/pages/account/AccountGrowth.tsx`, `web/src/pages/account/HoldingsPanel.tsx`, `web/src/pages/account/Account.tsx`
- Modify (replace the whole file): `web/src/router.tsx`
- Test (create): `web/src/pages/account/Account.test.tsx`

**Interfaces:**
- Consumes: `useAccount`, `AccountView` (Task 8); `WINDOW_WORD`, `WindowSeg`, `GrowthTiles`, `kindText` (Task 8); `Stat`, `SortHeader`, `toggleSort`, `CategoryChip`, `CATEGORY_COLOR` (Task 7); `LineChart`, `baseline` (Phase 2–3a).
- Produces:
  - `ValuePanel.tsx` `pointsIn(points, growth)`; `ValuePanel({ v, period, onPeriod })` (span 8: the value, the chart in the category's colour with the dotted "Start + deposits" step line, This year · 1 year · All, Chart | Table; the table's "In or out" column).
  - `AccountGrowth.tsx` `flowDay(iso, year)`; `AccountGrowthPanel({ v, period })` (span 4: the four tiles for the Value panel's window, then "Money in and out": date, ▲ in / ▼ out, amount).
  - `HoldingsPanel.tsx` `sortHoldings(rows, sort)` (a holding with no gain goes last either way), `quantityText(value)`; `HoldingsPanel({ v })` (span 12: symbol, name, quantity, price, value, weight as a thin bar and a percent, cost basis, gain with its percent; sortable by value (default) or gain; a Cash row; a totals row; a note when the totals leave out holdings of unknown cost; `This account holds nothing right now.`).
  - `Account.tsx` `Account({ id })`: the header ("Account", the name, "Institution · type", the category chip, "as of Fri 25 Sep"), the window state (default 1 year) shared by Value and Growth; a 404 is the in-shell "Not found" page (the breadcrumb already reads Money › Accounts).
  - `router.tsx`: `/accounts/$accountId`, keyed by the id so another account starts on its own default window.

- [ ] **Step 1: Write the failing tests**

`web/src/pages/account/Account.test.tsx`:

````tsx
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AccountView } from '../../lib/api'
import { accountFixture, renderApp } from '../../test/renderApp'
import { flowDay } from './AccountGrowth'
import { quantityText } from './HoldingsPanel'

// a title lookup, not a role query over the whole app: role queries dominate these tests' time
const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const rows = (region: HTMLElement, part = 'tbody') => [...region.querySelectorAll(`${part} tr`)].map((r) => r.textContent)
const withView = (view: AccountView) => ({ account: [{ id: view.id, view }] })

describe('Account page', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with the account, where it is, what kind it is and when', async () => {
    renderApp('/accounts/roth')
    const title = await screen.findByRole('heading', { level: 1, name: 'Roth IRA' })
    expect(title.closest('header')?.textContent).toBe('AccountRoth IRABrokerage A · Roth IRALong-termas of Fri 25 Sep')
  })

  it('draws a year of value against the start plus deposits, as a chart or a table', async () => {
    renderApp('/accounts/roth')
    const value = await findPanel('Value')
    expect(value.textContent).toContain('$67,890.81')
    expect(within(value).getByText('1 year · the gap between the lines is the market')).toBeTruthy()
    const chart = within(value).getByRole('img', { name: 'The account’s value against its starting value plus deposits' })
    expect(chart.querySelectorAll('path[stroke-dasharray="1.5 3.5"]')).toHaveLength(1) // the dotted start + deposits
    fireEvent.click(within(value).getByRole('button', { name: 'Table' }))
    const table = rows(value)
    expect(table).toHaveLength(262)
    expect(table[0]).toBe('Fri 25 Sep$67,890.81$56,200.00—') // newest first; the deposits line ends at start + deposits
  })

  it('moves the value and the growth to another window together', async () => {
    renderApp('/accounts/roth')
    const value = await findPanel('Value')
    const growth = panel('Growth')
    expect(growth.textContent).toContain('Started at$50,200.00Sep 2025')
    fireEvent.click(within(value).getByRole('button', { name: 'This year' }))
    expect(within(growth).getByText('This year')).toBeTruthy()
    expect(growth.textContent).toContain('Started at$58,287.371 JanYou put in$4,000.00The market added▲ up +$5,603.44')
    fireEvent.click(within(value).getByRole('button', { name: 'Table' }))
    expect(rows(value)).toHaveLength(192)
  })

  it('lists the last eight times money moved in or out', async () => {
    const flows = [{ date: '2026-09-18', amount: -200 }, ...accountFixture.flows.slice(0, 7)]
    renderApp('/accounts/roth', withView({ ...accountFixture, flows }))
    const growth = await findPanel('Growth')
    const items = within(growth).getAllByRole('listitem').map((li) => li.textContent)
    expect(items).toHaveLength(8)
    expect(items.slice(0, 2)).toEqual(['Fri 18 Sep▼ out$200.00', 'Tue 1 Sep▲ in$500.00'])
    expect(flowDay('2025-11-03', '2026')).toBe('3 Nov 2025')
  })

  it('weighs each holding with its gain, then the cash and the totals', async () => {
    renderApp('/accounts/roth')
    const holdings = await findPanel('Holdings')
    expect(rows(holdings)).toEqual([
      'SPYS&P 500 index fund63.66661.20$42,091.9962.0%$32,831.75▲ up +$9,260.24▲ up +28.21%',
      'XLVHealth care sector fund100.155142.35$14,257.0621.0%$13,259.07▲ up +$997.99▲ up +7.53%',
      'XLPConsumer staples sector fund137.32679.10$10,862.4916.0%$11,296.99▼ down −$434.50▼ down −3.85%',
      'Cash———$679.271.0%——',
    ])
    expect(rows(holdings, 'tfoot')).toEqual(['Total$67,890.81100.0%$57,387.81▲ up +$9,823.73▲ up +17.12%'])
    expect(within(holdings).getByRole('columnheader', { name: 'Value' }).getAttribute('aria-sort')).toBe('descending')
  })

  it('sorts by gain, with a holding of unknown cost last and the totals saying they leave it out', async () => {
    const holdings = accountFixture.holdings.map((h) => (h.symbol === 'XLV'
      ? { ...h, cost_basis: null, gain: null, gain_pct: null } : h))
    const totals = { ...accountFixture.totals, unknown_cost: 1 }
    renderApp('/accounts/roth', withView({ ...accountFixture, holdings, totals }))
    const panelEl = await findPanel('Holdings')
    fireEvent.click(within(panelEl).getByRole('button', { name: 'Gain' }))
    expect(rows(panelEl).map((r) => r?.slice(0, 3))).toEqual(['SPY', 'XLP', 'XLV', 'Cas'])
    fireEvent.click(within(panelEl).getByRole('button', { name: 'Gain' }))
    expect(rows(panelEl).map((r) => r?.slice(0, 3))).toEqual(['XLP', 'SPY', 'XLV', 'Cas'])
    expect(within(panelEl).getByText('The cost and gain totals leave out 1 holding with no cost basis.')).toBeTruthy()
    expect([quantityText(1200), quantityText(0.000123), quantityText(-2.5)]).toEqual(['1,200', '0.000123', '−2.5'])
  })

  it('prints a margin debit with a true minus, and a closed account plainly', async () => {
    const margin = { ...accountFixture, cash: -200, cash_weight: -25 }
    const { unmount } = renderApp('/accounts/roth', withView(margin))
    const holdings = await findPanel('Holdings')
    expect(rows(holdings).at(-1)).toBe('Cash———−$200.00−25.0%——')
    unmount()
    const closed: AccountView = { ...accountFixture, value: 0, points: [], flows: [], holdings: [], cash: 0,
      cash_weight: null, growth: { ytd: null, '1y': null, all: null },
      totals: { value: 0, cost_basis: null, gain: null, gain_pct: null, unknown_cost: 0 } }
    renderApp('/accounts/roth', withView(closed))
    expect(within(await findPanel('Holdings')).getByText('This account holds nothing right now.')).toBeTruthy()
    expect(within(panel('Value')).getByText(/^No history yet/)).toBeTruthy()
    expect(within(panel('Growth')).getAllByText('—')).toHaveLength(4)
    expect(within(panel('Growth')).getByText('No money has moved in or out yet.')).toBeTruthy()
  })

  it('shows an unknown account as not found, inside the shell', async () => {
    const answer = () => Promise.resolve(new Response('{"detail":"no such account: nope"}', { status: 404 }))
    renderApp('/accounts/nope', {}, answer)
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
    const crumbs = screen.getByRole('navigation', { name: 'Breadcrumb' })
    expect(crumbs.textContent).toBe('MoneyAccounts')
    expect(within(crumbs).getByRole('link', { name: 'Accounts' }).getAttribute('href')).toBe('/accounts')
  })

  it('says it is loading, and says so plainly when the account could not load', async () => {
    const { unmount } = renderApp('/accounts/roth', { account: [] }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading the account…')).toBeTruthy()
    unmount()
    renderApp('/accounts/roth', { account: [] })
    expect((await screen.findByRole('alert')).textContent).toBe('This account couldn’t load: network is off in tests')
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/pages/account/Account.test.tsx`
Expected: `Test Files  1 failed (1)`, no tests run: `Failed to resolve import "./AccountGrowth"` or `"./HoldingsPanel"` (the test imports both; Vite names whichever it tries first).

- [ ] **Step 3: Implement**

`web/src/pages/account/ValuePanel.tsx`:

````tsx
import { type CSSProperties, useState } from 'react'
import { baseline } from '../../charts/geometry'
import { LineChart, LineKey } from '../../charts/LineChart'
import { Empty } from '../../charts/marks'
import { CATEGORY_COLOR, Missing, Panel, Seg } from '../../components/bits'
import type { AccountView, Growth, ValuePoint, Window } from '../../lib/api'
import { compactMoney, money, monthLabel, shortDate, signedMoney, splitCents } from '../../lib/format'
import { WINDOW_WORD, WindowSeg } from '../accounts/GrowthPanel'

const VIEWS = ['Chart', 'Table'] as const
const DAY_MS = 86_400_000

/** The window's points: from the day its starting value is from (all of them when it has no growth yet). */
export function pointsIn(points: ValuePoint[], growth: Growth | null): ValuePoint[] {
  return growth ? points.filter((p) => p.date >= growth.start_date) : points
}

/** The account's value over the window, with the dotted "start + deposits" line: the gap between them is what the
 *  market added. */
export function ValuePanel({ v, period, onPeriod }: { v: AccountView; period: Window; onPeriod: (w: Window) => void }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const points = pointsIn(v.points, v.growth[period])
  const base = baseline(points)
  const [whole, cents] = splitCents(v.value)
  const color = CATEGORY_COLOR[v.category] ?? 'var(--ink1)'
  // a window under about three months labels its days, not just its months
  const short = points.length > 1 && Date.parse(points[points.length - 1].date) - Date.parse(points[0].date) < 100 * DAY_MS
  return (
    <Panel id="value" title="Value" subtitle={`${WINDOW_WORD[period]} · the gap between the lines is the market`}
      span={8} height={372} actions={<>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color={color} style="solid" />Value
        </span>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ref)" style="dotted" />Start + deposits
        </span>
        <WindowSeg value={period} onChange={onPeriod} />
        <Seg label="View" options={VIEWS} value={view} onChange={setView} />
      </>}>
      <div className="text-[38px] sm:text-5xl font-semibold tracking-[-0.035em] leading-none mt-3.5">
        {whole}<span className="text-ink3">.{cents}</span>
      </div>
      <div className="mt-auto pt-3">
        {points.length < 2 ? (
          <Empty>No history yet. The chart appears once this account has a few days of data.</Empty>
        ) : view === 'Chart' ? (
          <LineChart dates={points.map((p) => p.date)} height={196}
            ariaLabel="The account’s value against its starting value plus deposits"
            series={[
              { key: 'value', label: 'Value', values: points.map((p) => p.value), color, style: 'solid', area: true },
              { key: 'base', label: 'Start + deposits', values: base, color: 'var(--ref)', style: 'dotted', step: true },
            ]}
            yFormat={compactMoney} valueFormat={(n) => money(n, false)} xLabel={(d) => monthLabel(d, short)}
            tipTitle={(d) => shortDate(d)} />
        ) : (
          <div className="table-scroll overflow-y-auto" style={{ maxHeight: 196 }}>
            <table className="tbl" style={{ minWidth: 480, '--row': '36px' } as CSSProperties}>
              <thead>
                <tr>
                  <th>Date</th><th className="r">Value</th><th className="r">Start + deposits</th>
                  <th className="r">In or out</th>
                </tr>
              </thead>
              <tbody>
                {points.map((p, i) => (
                  <tr key={p.date}>
                    <td>{shortDate(p.date)}</td>
                    <td className="r num">{money(p.value)}</td>
                    <td className="r num">{money(base[i])}</td>
                    <td className="r num">{i > 0 && p.net_flow !== 0 ? signedMoney(p.net_flow) : <Missing />}</td>
                  </tr>
                )).reverse()}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Panel>
  )
}
````


`web/src/pages/account/AccountGrowth.tsx`:

````tsx
import { Panel } from '../../components/bits'
import type { AccountView, Window } from '../../lib/api'
import { money, monthLabel, shortDate } from '../../lib/format'
import { GrowthTiles, WINDOW_WORD } from '../accounts/GrowthPanel'

/** "Tue 1 Sep" this year, "1 Sep 2025" before it */
export function flowDay(iso: string, year: string): string {
  return iso.slice(0, 4) === year ? shortDate(iso) : `${monthLabel(iso, true)} ${iso.slice(0, 4)}`
}

/** The window's four figures, then the last eight times money moved in or out. */
export function AccountGrowthPanel({ v, period }: { v: AccountView; period: Window }) {
  const year = v.as_of.slice(0, 4)
  return (
    <Panel id="growth" title="Growth" subtitle={WINDOW_WORD[period]} span={4} height={372}>
      <div className="mt-3.5"><GrowthTiles g={v.growth[period]} asOf={v.as_of} /></div>
      <div className="label mt-4">Money in and out</div>
      {v.flows.length === 0 ? (
        <p className="text-xs text-ink3 mt-2">No money has moved in or out yet.</p>
      ) : (
        <ul className="mt-1">
          {v.flows.map((f, i) => (
            <li key={`${f.date}-${i}`} className="flex items-center gap-3 h-7 text-[13px]">
              <span className="num text-xs text-ink2 min-w-[92px]">{flowDay(f.date, year)}</span>
              <span className="text-xs text-ink2">
                <span aria-hidden="true">{f.amount > 0 ? '▲' : '▼'} </span>{f.amount > 0 ? 'in' : 'out'}
              </span>
              <span className="num ml-auto">{money(Math.abs(f.amount))}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
````


`web/src/pages/account/HoldingsPanel.tsx`:

````tsx
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { CATEGORY_COLOR, Delta, Missing, Panel, type Sort, SortHeader, toggleSort } from '../../components/bits'
import type { AccountView, HoldingRow } from '../../lib/api'
import { MINUS, money, num, pct, signedMoney } from '../../lib/format'

type SortKey = 'value' | 'gain'
const SORT_VALUE: Record<SortKey, (h: HoldingRow) => number | null> = { value: (h) => h.value, gain: (h) => h.gain }

/** Sorted by value or gain; a holding with no gain (its cost is unknown) goes last either way. */
export function sortHoldings(rows: HoldingRow[], sort: Sort<SortKey>): HoldingRow[] {
  return [...rows].sort((a, b) => {
    const [x, y] = [SORT_VALUE[sort.key](a), SORT_VALUE[sort.key](b)]
    if (x == null || y == null) return x == null && y == null ? 0 : x == null ? 1 : -1
    return sort.dir === 'desc' ? y - x : x - y
  })
}

/** 63.66 · 1,200 · 0.000123: whole shares plainly, fractions to four places (six under one) */
export function quantityText(value: number): string {
  const text = Math.abs(value).toLocaleString('en-US', { maximumFractionDigits: Math.abs(value) >= 1 ? 4 : 6 })
  return value < 0 && text !== '0' ? MINUS + text : text
}

/** A thin bar and the percent; the bar stays inside its track for a weight over 100% or under zero. */
function Weight({ value, color }: { value: number | null; color: string }) {
  if (value == null) return <Missing />
  return (
    <div className="flex items-center justify-end gap-2">
      <span className="relative w-14 h-1.5 rounded-full overflow-hidden bg-panel2"
        style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
        <span className="absolute inset-y-0 left-0"
          style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }} />
      </span>
      <span className="num text-xs min-w-[46px] text-right">{num(value, 1)}%</span>
    </div>
  )
}

function Gain({ gain, pctValue }: { gain: number | null; pctValue: number | null }) {
  if (gain == null) return <Missing />
  return (
    <>
      <Delta value={gain}>{signedMoney(gain)}</Delta>
      {pctValue != null && <div className="text-[11px] mt-0.5"><Delta value={pctValue}>{pct(pctValue, 2)}</Delta></div>}
    </>
  )
}

/** What the account holds, then its cash and the totals. */
export function HoldingsPanel({ v }: { v: AccountView }) {
  const [sort, setSort] = useState<Sort<SortKey>>({ key: 'value', dir: 'desc' })
  const onSort = (key: SortKey) => setSort((s) => toggleSort(s, key))
  const color = CATEGORY_COLOR[v.category] ?? 'var(--ink3)'
  const t = v.totals
  const n = v.holdings.length
  return (
    <Panel id="holdings" title="Holdings" span={12}
      subtitle={`${n} holding${n === 1 ? '' : 's'} and cash · weights are shares of the account`}>
      {n === 0 && v.cash === 0 ? (
        <Empty>This account holds nothing right now.</Empty>
      ) : (
        <>
          <div className="table-scroll mt-3.5">
            <table className="tbl" style={{ minWidth: 900, '--row': '52px' } as CSSProperties}>
              <thead>
                <tr>
                  <th>Symbol</th><th>Name</th><th className="r">Quantity</th><th className="r">Price</th>
                  <SortHeader label="Value" k="value" sort={sort} onSort={onSort} right />
                  <th className="r">Weight</th><th className="r">Cost basis</th>
                  <SortHeader label="Gain" k="gain" sort={sort} onSort={onSort} right />
                </tr>
              </thead>
              <tbody>
                {sortHoldings(v.holdings, sort).map((h, i) => (
                  <tr key={`${h.symbol}-${i}`}>
                    <td><span className="num font-semibold">{h.symbol}</span></td>
                    <td className="text-ink2">{h.name || <Missing />}</td>
                    <td className="r num">{quantityText(h.quantity)}</td>
                    <td className="r num">{num(h.price, Math.abs(h.price) < 1 ? 4 : 2)}</td>
                    <td className="r num">{money(h.value)}</td>
                    <td className="r"><Weight value={h.weight} color={color} /></td>
                    <td className="r num">{h.cost_basis == null ? <Missing /> : money(h.cost_basis)}</td>
                    <td className="r"><Gain gain={h.gain} pctValue={h.gain_pct} /></td>
                  </tr>
                ))}
                <tr>
                  <td><span className="font-medium">Cash</span></td>
                  <td><Missing /></td><td className="r"><Missing /></td><td className="r"><Missing /></td>
                  <td className="r num">{money(v.cash)}</td>
                  <td className="r"><Weight value={v.cash_weight} color="var(--s3)" /></td>
                  <td className="r"><Missing /></td><td className="r"><Missing /></td>
                </tr>
              </tbody>
              <tfoot>
                <tr style={{ borderTop: '1px solid var(--line2)' }}>
                  <td className="font-medium">Total</td><td /><td /><td />
                  <td className="r num font-medium">{money(t.value)}</td>
                  <td className="r num text-xs">{t.value > 0 ? '100.0%' : <Missing />}</td>
                  <td className="r num">{t.cost_basis == null ? <Missing /> : money(t.cost_basis)}</td>
                  <td className="r"><Gain gain={t.gain} pctValue={t.gain_pct} /></td>
                </tr>
              </tfoot>
            </table>
          </div>
          {t.unknown_cost > 0 && (
            <p className="text-xs text-ink3 mt-2">
              The cost and gain totals leave out {t.unknown_cost} holding{t.unknown_cost === 1 ? '' : 's'} with no cost
              basis.
            </p>
          )}
        </>
      )}
    </Panel>
  )
}
````


`web/src/pages/account/Account.tsx`:

````tsx
// One account: its value over time against what went in, how it grew, and what it holds.
import { useState } from 'react'
import { CategoryChip } from '../../components/bits'
import { HttpError, useAccount, type Window } from '../../lib/api'
import { shortDate } from '../../lib/format'
import { kindText } from '../accounts/Accounts'
import { Soon } from '../Soon'
import { AccountGrowthPanel } from './AccountGrowth'
import { HoldingsPanel } from './HoldingsPanel'
import { ValuePanel } from './ValuePanel'

export function Account({ id }: { id: string }) {
  const account = useAccount(id)
  const [period, setPeriod] = useState<Window>('1y') // the Value panel's window, which the Growth panel follows
  if (account.isPending) return <p className="text-ink3" role="status">Loading the account…</p>
  if (!account.data) {
    if (account.error instanceof HttpError && account.error.status === 404) {
      return <Soon title="Not found" text="There is no page here. Pick one from the menu." />
    }
    return <div role="alert" className="panel">This account couldn&rsquo;t load: {account.error.message}</div>
  }
  const v = account.data
  return (
    <>
      <header className="mb-5">
        <div className="label">Account</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">{v.name}</h1>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mt-2">
          {kindText(v) && <span className="text-ink2">{kindText(v)}</span>}
          <CategoryChip category={v.category} />
          <span className="text-xs text-ink3">as of {shortDate(v.as_of)}</span>
        </div>
      </header>
      <div className="grid12">
        <ValuePanel v={v} period={period} onPeriod={setPeriod} />
        <AccountGrowthPanel v={v} period={period} />
        <HoldingsPanel v={v} />
      </div>
    </>
  )
}
````


`web/src/router.tsx`:

````tsx
import { createRootRoute, createRoute, createRouter, type RouterHistory, useNavigate } from '@tanstack/react-router'
import type { Money } from './lib/api'
import { Account } from './pages/account/Account'
import { Accounts } from './pages/accounts/Accounts'
import { Home } from './pages/home/Home'
import { Soon } from './pages/Soon'
import { Strategies } from './pages/strategies/Strategies'
import { Strategy } from './pages/strategy/Strategy'
import { Shell } from './shell/Shell'

const root = createRootRoute({
  component: Shell,
  notFoundComponent: () => <Soon title="Not found" text="There is no page here. Pick one from the menu." />,
})

const later = (path: string, title: string, text: string) =>
  createRoute({ getParentRoute: () => root, path, component: () => <Soon title={title} text={text} /> })

/** `?book=real|paper` picks the money the page focuses on; anything else is dropped (the page defaults to real). */
function bookSearch(search: Record<string, unknown>): { book?: Money } {
  return search.book === 'real' || search.book === 'paper' ? { book: search.book } : {}
}

const accountRoute = createRoute({
  getParentRoute: () => root,
  path: '/accounts/$accountId',
  component: AccountRoute,
})

function AccountRoute() {
  const { accountId } = accountRoute.useParams()
  return <Account key={accountId} id={accountId} /> // another account starts on its own default window
}

const strategyRoute = createRoute({
  getParentRoute: () => root,
  path: '/strategies/$strategyId',
  validateSearch: bookSearch,
  component: StrategyRoute,
})

function StrategyRoute() {
  const { strategyId } = strategyRoute.useParams()
  const { book } = strategyRoute.useSearch()
  const navigate = useNavigate()
  return (
    <Strategy id={strategyId} book={book ?? 'real'}
      onBook={(next) => navigate({ to: '/strategies/$strategyId', params: { strategyId }, search: { book: next } })} />
  )
}

const routeTree = root.addChildren([
  createRoute({ getParentRoute: () => root, path: '/', component: Home }),
  createRoute({ getParentRoute: () => root, path: '/accounts', component: Accounts }),
  accountRoute,
  later('/books', 'Books', 'Each book, real or paper: equity against its benchmark, drawdown, trades — Phase 3.'),
  createRoute({ getParentRoute: () => root, path: '/strategies', component: Strategies }),
  strategyRoute,
  later('/backtests', 'Backtests', 'What has been tested and what passed — Phase 5.'),
  later('/activity', 'Activity', 'What ran, what is due, what failed — Phase 5.'),
  later('/settings', 'Settings', 'Your profile and the status of every source — Phase 5.'),
])

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, history, defaultPreload: 'intent' })
}
````


- [ ] **Step 4: Run everything and watch it pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit && npm run build`
Expected: `Tests  145 passed (145)` (`Account.test.tsx` 9); tsc prints nothing; `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/account web/src/router.tsx
git commit -m "feat(web): one account: value against what went in, growth and money moved, holdings with weights and gains" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 10: The docs, and the screenshot pass

**Files:**
- Create: `docs/connectors.md`
- Modify (replace the whole file): `profile.example.toml`
- Modify (exact lines below): `README.md`, `AGENTS.md`, `docs/specs/2026-09-25-kestrel-design.md`, `docs/specs/2026-09-26-phase-4a-accounts-design.md`

**Interfaces:** none (documentation). `tests/test_profile.py::test_the_committed_example_profile_loads` keeps passing: the new `fdc` block is commented out.

- [ ] **Step 1: Write the connector guide and the example profile**

`docs/connectors.md`:

````markdown
# Connectors

A connector reads one source and returns a Snapshot, the format in [`data-contract.md`](data-contract.md). kestrel
asks every source in your `profile.toml` each time a page loads. A source that can't be read shows as an error in the
sidebar's Sources block, and the rest of the page still works. Every connector only reads: none of them writes to its
source.

| `kind` | Reads | Since |
|---|---|---|
| `demo` | nothing: a fictional year for "Alex" | Phase 2; the default when there is no `profile.toml` |
| `fdc` | [financial-data-collector](https://github.com/Dimas-100/financial-data-collector)'s SQLite warehouse | Phase 4a |
| `feed` | any system that serves the contract as JSON (your trading desk) | Phase 4b |
| `rails` | a trading-rails install: paper books, the run log, backtests | Phase 4b |

`kestrel check` tries every source and prints what it found; `kestrel serve --demo` and `kestrel check --demo` show
the demo whatever `profile.toml` says.

## `demo`

```toml
[[sources]]
id = "demo"
kind = "demo"
label = "Demo data"
```

Accounts, holdings, books, trades and runs for a believable year, with the dates moving so the last day is today.

## `fdc`: financial-data-collector

```toml
[[sources]]
id = "portfolio"
kind = "fdc"
label = "Portfolio"
path = "../financial-data-collector/data/warehouse.db"   # relative to this profile's folder
stale_after = "36h"

[sources.categories]          # optional: account id or exact label = long_term | trading | cash | other
"brokerage-2" = "trading"
```

- **`path`** is the warehouse file. A relative path is relative to the folder `profile.toml` is in, not to wherever
  you start kestrel.
- **Read-only.** The file is opened with `mode=ro` and `query_only` on top, once per page load, and closed straight
  after. A sync running at the same time is fine: kestrel reads what the collector last committed.
- **Needs** schema version 3 or later: the tables `accounts`, `transactions`, `prices`, `sync_runs`, `holdings_daily`
  and `cash_daily`, and the views `positions_latest` and `account_values_daily`.

### Accounts

| kestrel shows | from the warehouse |
|---|---|
| id | the account's label as a slug: `Alex Roth IRA` is `alex-roth-ira`, `Épargne` is `epargne`; a label with no letters or digits is `account`. Two labels that make the same slug get `-2`, `-3` in the order the collector first saw them. The id is the account's address: `/accounts/alex-roth-ira`. |
| name | the label |
| institution | `fidelity` is Fidelity, `webull` Webull, anything else title-cased; `unknown` is left out |
| type | `roth_ira` is Roth IRA, `traditional_ira` Traditional IRA, `401k` 401(k), `brokerage` Brokerage, `crypto` Crypto (and the other retirement types the same way); anything else title-cased |
| category | set in `[sources.categories]` by id or label (an id wins over a label), else from the type: retirement accounts, an HSA, a pension and `brokerage` are long-term; `checking`, `savings`, `cash` and `money_market` are cash; anything else, crypto included, is other |

Trading money is whatever you file under `trading`. Until a real trading book has a history of its own, Home's
"Trading vs your index money" draws the trading accounts.

`kestrel check` refuses a category that isn't one of the four, and notes a `categories` entry that matches no
account on the source's line.

### Values, history and money moved

- **Value and cash:** the newer of the broker's last snapshot (`account_values_daily`) and the last replayed day
  (`holdings_daily` plus `cash_daily`). When both are from the same day, the snapshot wins. A value is as of that
  day's US close.
- **History:** each account's holdings plus its cash, per day.
- **Money moved in and out,** from `transactions`, so deposits never count as growth:
  - a `contribution` counts as its signed amount (a negative one is a reversal),
  - a `withdrawal` is always money out,
  - a `transfer` keeps its sign; a transfer of shares with no cash amount moves no money,
  - money moved on a day without history (a Saturday deposit) counts on the next day that has one; money moved
    after the last day is left for the next sync.
- **Holdings:** the positions in each account's latest snapshot (`positions_latest`). A position with no market
  value is left out and counted in the source's detail; one with no price is priced at its value over its quantity.
  When the replayed history is newer than the last snapshot, the holdings are a day or two older than the value.

### Benchmark

When the warehouse has prices for your profile's `[benchmark]` symbol, kestrel draws it from their adjusted closes
(dividends included, as they are in the accounts), over the same days as your accounts' history. Pick a symbol the
collector already prices, such as an index fund you hold. Otherwise there is no benchmark line, and the source's
detail says `no SPY prices in the warehouse`.

### Freshness

The source's last success is when the collector last finished its `derive` step without an error (the step that
rebuilds the daily history), else any step that finished without one. After `stale_after` it turns amber. A
warehouse that has never finished a step shows as stale.

### Troubleshooting

Run `kestrel check`. Under the source's line it lists each account as `id  category  name`, never a balance.

| `kestrel check` says | What to do |
|---|---|
| `no warehouse at …` | Check `path`: it is relative to the folder `profile.toml` is in. |
| `… is not a financial-data-collector warehouse` | The file isn't a collector warehouse (or is empty): check `path`. |
| `this warehouse is at schema version 2 …` or `this warehouse is missing holdings_daily …` | Update financial-data-collector and run `fdc sync`. |
| `the warehouse couldn't be read: database is locked` | Another program held the file for more than five seconds. Refresh once it is done. |
| `unknown category 'trade' for 'Brokerage'` | Use `long_term`, `trading`, `cash` or `other` in `[sources.categories]`. |
| `no account matches categories 'brokerage-9'` | Use an id from the account lines, or the exact label. |
| `no SPY prices in the warehouse` | Set `[benchmark] symbol` to something the collector prices, or add it to the collector. |

## `feed` and `rails`

Phase 4b. Until then a source of either kind shows as an error that says it isn't available in this version.
````


`profile.example.toml`:

````toml
# kestrel profile. Copy this file to profile.toml (gitignored) and make it yours.
# Never put a key or password in here: a source names the environment variable that holds it.

[you]
name = "Alex"

[app]
name = "kestrel"
accent = "rufous"          # rufous | slate | mono
theme = "system"           # system | dark | light
gain_loss = "green-red"    # green-red | blue-orange
density = "comfortable"    # comfortable | compact
currency = "USD"
timezone = "America/New_York"

[benchmark]                # the index your money is compared with; an fdc source draws it from its own prices
symbol = "SPY"
label = "S&P 500"

# Where your data comes from. The demo source works out of the box; see docs/connectors.md for every kind.
[[sources]]
id = "demo"
kind = "demo"
label = "Demo data"

# Your accounts, from financial-data-collector's warehouse (read-only). Replace the demo source above with this one:
#
# [[sources]]
# id = "portfolio"
# kind = "fdc"
# label = "Portfolio"
# path = "../financial-data-collector/data/warehouse.db"   # relative to this file's folder
# stale_after = "36h"
#
# [sources.categories]               # optional: account id or exact label = long_term | trading | cash | other
# "brokerage-2" = "trading"
#
# Coming in Phase 4b:
#
# [[sources]]
# id = "paper"
# kind = "rails"                     # a trading-rails install: paper state, run log, backtests
# path = "../trading-rails/data"
#
# [[sources]]
# id = "desk"
# kind = "feed"                      # any system that serves the kestrel contract as JSON
# url = "http://127.0.0.1:8000/api/feed"
# token_env = "KESTREL_DESK_TOKEN"
# stale_after = "15m"
````


- [ ] **Step 2: Update the docs**

In `README.md`, replace:

````text
> **Status: Phase 3a of 5 — Home and the Strategies pages run.** Both work end to end on demo data; Books,
> Accounts, Backtests, Activity and Settings arrive in later phases.
````

with:

````text
> **Status: Phase 4a of 5 — Home, Accounts and the Strategies pages run.** Accounts read your own data from
> financial-data-collector, or the demo; Books, Backtests, Activity and Settings arrive in later phases.
````

In `README.md`, replace:

````text
- **Books, Accounts, Backtests, Activity and Settings** are built from the same components.
````

with:

````text
- **Accounts:**
  - every account's value, and how much of its growth was your deposits versus the market,
  - what each account holds, its weight and its gain,
  - everything you hold, added up across accounts.
- **Books, Backtests, Activity and Settings** are built from the same components.
````

In `README.md`, replace:

````text
Make it yours: copy `profile.example.toml` to `profile.toml` (gitignored) and set your name, look and sources.
`kestrel check` validates the profile and tries every source; `kestrel demo` prints the demo data as an example feed;
`kestrel schema` prints the [data contract](docs/data-contract.md).
````

with:

````text
Make it yours: copy `profile.example.toml` to `profile.toml` (gitignored) and set your name, look and sources.
`kestrel check` validates the profile and tries every source; `kestrel demo` prints the demo data as an example feed;
`kestrel schema` prints the [data contract](docs/data-contract.md).

### Point it at your own data

1. Fill a warehouse with [financial-data-collector](https://github.com/Dimas-100/financial-data-collector)
   (`fdc sync`).
2. In `profile.toml`, swap the demo source for the commented `fdc` block: `path` is the warehouse, relative to
   `profile.toml`, and `[sources.categories]` files your trading accounts under `trading`.
3. Run `kestrel check`: the source should read `ok`, with every account and its category listed under it (never a
   balance). Then `kestrel serve`; `kestrel serve --demo` still shows the demo.

Every source and what it reads: [docs/connectors.md](docs/connectors.md).
````

In `AGENTS.md`, replace:

````text
**Status:** Phase 3a of 5 — the skeleton plus the Strategies pages (the list, one strategy, the chart kit). Books is Phase 3b.
````

with:

````text
**Status:** Phase 4a of 5 — the skeleton, the Strategies pages and the Accounts pages, with the `fdc` connector reading
financial-data-collector's warehouse. The trading desk's `feed` and `rails` are Phase 4b; Books is Phase 3b.
````

In `AGENTS.md`, replace:

````text
| `docs/data-contract.md` | The Snapshot format any source speaks; schema in `docs/contract/` |
````

with:

````text
| `docs/data-contract.md` | The Snapshot format any source speaks; schema in `docs/contract/` |
| `docs/connectors.md` | Every connector, what it reads, and how to point kestrel at your own data |
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
- **Status:** design approved. Phases 0 (mockups), 1 (this repo, spec, design system, hygiene test), 2 (the skeleton) and 3a (the Strategies pages) are done; Phase 3b (Books) is next.
````

with:

````text
- **Status:** design approved. Phases 0 (mockups), 1 (this repo, spec, design system, hygiene test), 2 (the skeleton), 3a (the Strategies pages) and 4a (Accounts and the `fdc` connector) are done; Phase 4b (the trading desk's `feed` and `rails`) is next, then 3b (Books).
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
    connectors/             base protocol · demo (Phase 2) · fdc · rails · feed (Phase 4)   (§8)
````

with:

````text
    connectors/             base protocol · demo (Phase 2) · fdc (Phase 4a) · rails · feed (Phase 4b)   (§8)
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
                            strategy.py (the strategy list and one strategy's eight sections)
````

with:

````text
                            strategy.py (the strategy list and one strategy's eight sections),
                            accounts.py (the account list and one account)
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
    src/pages/              one folder per page: home/ (Phase 2); strategies/ and strategy/ (Phase 3a); books, accounts, … later
````

with:

````text
    src/pages/              one folder per page: home/ (Phase 2); strategies/ and strategy/ (Phase 3a); accounts/ and
                            account/ (Phase 4a); books, … later
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
| `Account` | `id`, `name`, `institution`, `category` (long_term · trading · cash · other), `value`, `cash`, `as_of` |
````

with:

````text
| `Account` | `id`, `name`, `institution`, `account_type`, `category` (long_term · trading · cash · other), `value`, `cash`, `as_of` |
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
| 4 | Accounts; `fdc`, `rails`, `feed` connectors | |
````

with:

````text
| 4 | Accounts; `fdc`, `rails`, `feed` connectors | 4a done (Accounts, `fdc`); 4b (`feed`, `rails`) next |
````

In `docs/specs/2026-09-26-phase-4a-accounts-design.md`, replace:

````text
- **Status:** design decided autonomously (owner: "Go ahead proceed autonomously"); plan next.
````

with:

````text
- **Status:** built (plan: [`../plans/2026-09-26-phase-4a-accounts.md`](../plans/2026-09-26-phase-4a-accounts.md)).
````


- [ ] **Step 3: Run everything from a clean start**

```bash
.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .
(cd web && npm ci && npx vitest run && npx tsc --noEmit && npm run build)
```
Expected: `186 passed`; `All checks passed!`; `Tests  145 passed (145)`; tsc prints nothing; `✓ built`.

- [ ] **Step 4: The screenshot pass (the check jsdom can't do)**

Run `.venv/Scripts/kestrel serve --demo --no-open` and open `http://127.0.0.1:8030`. At 1440 × 1000, 1280, 1024, 768 and 390 × 844, in both themes (the theme button, or `localStorage.setItem('kestrel.theme', 'light'|'dark')` and reload), open `/`, `/accounts`, `/accounts/roth`, `/accounts/brokerage`, `/accounts/trading`, `/accounts/savings` and `/accounts/nope`, and paste this into the browser console on each:

```js
(() => {
  const over = [...document.querySelectorAll('section.panel, article.panel')]
    .filter((s) => s.scrollHeight > s.clientHeight + 1).map((s) => s.getAttribute('aria-labelledby'))
  return { sidewaysScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth, over }
})()
```
Expected everywhere: `{ sidewaysScroll: 0, over: [] }`.

Then look:
- **`/accounts`, dark, 1440:** the sentence reads "4 accounts, $… in all. This year the market added ▲ +$… and you deposited $…"; the growth bar's grey start, dotted "You put in" and green market sit end to end with a tick at now; Tab to the bar and press End for "The market added".
- **`/accounts/brokerage`:** "This year" moves both the Value and the Growth panels; Gain sorts the holdings with KO (no cost basis) last, and the note under the table says so.
- **390 px:** the tiles go two by two, and the Accounts, Everything you hold and Holdings tables scroll sideways inside their panels.
- **`/accounts/nope`:** the in-shell "Not found" page, with Money › Accounts in the breadcrumb.
- **Home:** each row of "Where it sits" opens its account.

- [ ] **Step 5: Commit, push, and watch CI**

```bash
git add docs/connectors.md profile.example.toml README.md AGENTS.md docs/specs/2026-09-25-kestrel-design.md docs/specs/2026-09-26-phase-4a-accounts-design.md
git commit -m "docs: the connector guide, the fdc profile block, pointing kestrel at your own data; Phase 4a is done" -m "$(cat <temp>/trailer.txt)"
git push
gh run watch --exit-status
```
Expected: all three CI jobs green (`python` 3.11 and 3.12, `python-windows`, `web`).

---

## Done when

- `/accounts` shows the growth split into what went in and what the market added, every account with its share, day and year, and everything held; `/accounts/<id>` shows one account's value against what went in, its growth and money moved, and its holdings with weights and gains, on demo data in both themes.
- A `profile.toml` with one `fdc` source reads a collector warehouse read-only; `kestrel check` lists its accounts and categories, never a balance; `kestrel serve --demo` still shows the demo.
- 186 Python tests and 145 web tests pass locally and in CI (including Windows); ruff and tsc are clean.
- The screenshot pass shows no overflow and no sideways scroll at 390 to 1440 px.
- The parent spec's Phase 4 row reads "4a done"; the feed and rails are Phase 4b.

## After the build: the owner's setup (local only, never committed)

On the owner's machine, spec §6: copy `profile.example.toml` to `kestrel/profile.toml` (gitignored); set `you.name`; set `[benchmark]` to an index fund the warehouse already prices; replace the demo source with the `fdc` block pointing at `../financial-data-collector/data/warehouse.db`, with the trading-desk accounts mapped to `trading` in `[sources.categories]`; run `kestrel check` and confirm the source reads `ok` and every account has the intended category. Nothing changes in financial-data-collector.

## Self-review

- **Spec coverage:** §1 decisions → Tasks 1–9 (ids and clashes, categories and overrides: Task 3; benchmark: Task 4; the Home trading line: Task 5; `--demo`: Task 2); §2.1 profile → Task 2 (relative paths, the category check) and Task 3 (the unmatched-categories note); §2.2 opening → Task 3; §2.3 mapping → Task 3 (ids, name, institution, type, category, the snapshot's value) and Task 4 (the newer history point, holdings, history, flows, benchmark, source); §2.4 performance → measured in the prototype (57 ms, no cache), recorded in Provenance; §3 contract and demo → Task 1; §4.1 → Tasks 7–8; §4.2 → Task 9; §4.3 links → Task 8 (Home's rows, the sidebar item opens the real page); §5.1 derived figures → Task 5; §5.2 view models and routes → Tasks 5–6 (mirrored in `api.ts`, Task 8); §5.3 CLI → Tasks 2 and 6; §5.4 Home → Tasks 5 and 8; §6 owner's setup → "After the build"; §7 safety → Tasks 3–4 (read-only proof, fictional fixture) and the hygiene test on every commit; §8 docs → Task 10 (and `docs/data-contract.md`, Task 1); §9 testing → every task, the browser pass in Task 10; §10 out of scope → nothing here reads books or strategies from the warehouse, writes, or places.
- **Interpretations** (decided in the prototype, listed for the reviewer):
  - **Ids fold accents first.** The spec's slug rule would turn "Épargne" into `pargne`; accents are folded to their letter (Unicode NFKD) before the rule runs, so it is `epargne`. A label with nothing left is still `account`.
  - **Display text:** the collector's default institution `unknown` shows as nothing (the header reads just the type), and the type table also names the other retirement types the category table lists (`ira` IRA, `rollover_ira` Rollover IRA, `sep_ira` SEP IRA, `simple_ira` SIMPLE IRA, `403b` 403(b), `457b` 457(b), `hsa` HSA) instead of title-casing them into "Sep Ira".
  - **Freshness:** a warehouse that has never finished a step has no `last_success` and shows as `stale`, not `ok`.
  - **Benchmark span:** the benchmark starts at the last close on or before the first day of account history, so "Is it worth it?" and the comparison measure the index over the same years as the accounts (a collector with 30 years of prices would otherwise dominate).
  - **"Prices to":** the latest price date among the warehouse's securities, read per security through the prices index; on a household warehouse it gives the same date as a scan of the whole table (checked) at a fraction of the time.
  - **Holdings can lag the value.** Holdings are the latest broker snapshot (spec §2.3), while the value may come from a newer replayed day; `docs/connectors.md` says so. The holdings table's totals add up its own rows.
  - **`kestrel check`** collects one configured source at a time, so each source's accounts print under its own lines (the demo prints its four source rows, then its four accounts); `--profile` and `--demo` together are refused; its lines are written as UTF-8 so an accented or symbol-only name never crashes a redirected console.
  - **The growth bar's colours:** start is neutral (`--s3`), what you put in is the dotted reference (the "Start + deposits" line's encoding), the market is the gain or loss colour. What you put in can't take a data hue: in blue-orange mode the gain and loss colours are the two series hues.
  - **The account page's Growth panel has no bar:** the spec gives it the tiles and "Money in and out"; the Value chart already shows the gap. Money moved reads ▲ in / ▼ out in ink, not in gain and loss colours: a deposit is not a gain.
  - **Totals** sum the holdings whose cost is known, and a note counts the ones left out. With negative cash the holdings weigh over 100% and the cash row is negative; when holdings plus cash is zero or less there are no weights.
  - **Windows:** the list page opens on This year (the header sentence's window), the account page on 1 year (spec §4.2). "Today" on the list is the money change net of that day's deposits, with its percent under it.
- **Placeholders:** none; every step has its file blocks or its exact command and output.
- **Names and types:** the Python view models (Task 5) and `web/src/lib/api.ts` (Task 8) share field names, pinned by the generated fixtures and `satisfies Widen<…>`; the shared pieces (Task 7) are consumed with the same names in Tasks 8–9.
