# Phase 3a — Strategies — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `kestrel serve` shows a Strategies list and one page per strategy that answers "how does it trade?" and "is it behaving the way its backtest said it would?": the rule in steps, trades against the backtest's spread, the running average inside its expected funnel, the money at work, one trade bar by bar, return against worst drop, month by month, and every trade. The Phase 2 follow-ups land first.

**Architecture:**
- **Contract (additive, still version `"1"`):** daily bars around a trade (`TradeChart`, with an optional indicator and stop), backtest yearly return and worst drop on `Expected`, and names close to a signal (`Strategy.watch`).
- **Demo:** 8 charts per book with bars that agree with each trade's prices, RSI(2) and an 8% stop for Mean reversion, backtest figures and a watch list. Existing demo numbers do not move.
- **Server:** one pure module, `views/strategy.py`, builds `StrategiesView` and `StrategyView` from a Snapshot; two GET routes and two `kestrel demo` views expose them; two new generated fixtures pin the web types.
- **Web:** six charts on d3's math modules, each with a hover and keyboard tooltip, a table view and an empty state; pure geometry in `charts/geometry.ts`; `/strategies` and `/strategies/$strategyId?book=real|paper`.

**Tech Stack:** unchanged from Phase 2: Python ≥ 3.11 (FastAPI 0.141, pydantic 2.13), pytest, ruff; Node 24, React 19.2, Vite 8, Tailwind 4.3, TanStack Router 1.170 / Query 5, d3-scale 4 / d3-shape 3 / d3-array 3, Vitest 4.1 + Testing Library 16 + jsdom 27, TypeScript ~6.0. No new dependencies.

**Spec:** `docs/specs/2026-09-26-phase-3a-strategies-design.md` (binding), with `docs/specs/2026-09-25-kestrel-design.md`, `docs/design-system.md` and `docs/design/mockups/strategy.html`.

**Provenance:** every code block below was run in a scratch clone of this repo, task by task, before this plan was written, and the plan itself was then replayed into a second fresh clone, task by task, taking every block out with the same extraction as the helper below; the counts in each task come from that replay.
- End state: `pytest` 136 passed, `ruff check .` clean; `vitest` 115 passed, `tsc --noEmit` clean, `npm run build` succeeded.
- `kestrel serve` was checked at 390, 768, 1024 and 1440 px in both themes on `/`, `/strategies`, `/strategies/rsi2`, `/strategies/rsi2?book=paper`, `/strategies/ibs`, `/strategies/leader` and `/strategies/nope`: no sideways scroll and no panel overflow anywhere (56 combinations).

### How to use this plan (read before Task 1)

- **Copy file blocks with a script, never by hand.** Earlier plans lost typographic apostrophes, minus signs and non-breaking characters to retyping. Save this helper **outside the repo** (for example in your temp folder) and use it for every file block:

````python
"""Copy file blocks out of the plan exactly as written.

python copy_blocks.py PLAN.md TASK_NUMBER            lists the task's file blocks
python copy_blocks.py PLAN.md TASK_NUMBER PATH ...   writes those files, relative to the current directory
"""
import re
import sys
from pathlib import Path

plan, task, *paths = sys.argv[1:]
parts = re.split(r"^### Task (\d+):", Path(plan).read_text(encoding="utf-8"), flags=re.M)
body = dict(zip(parts[1::2], parts[2::2]))[task]
blocks = dict(re.findall(r"^`([^`\n]+)`:\n\n````[a-z]*\n(.*?)\n````\n", body, flags=re.M | re.S))
if not paths:
    print("\n".join(blocks))
for path in paths:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(blocks[path] + "\n", encoding="utf-8", newline="\n")
    print("wrote", path)
````

  Run it from the repo root, for example `python <temp>/copy_blocks.py docs/plans/2026-09-26-phase-3a-strategies.md 4 tests/test_strategy_view.py`. Write the test files first (Step 1), run them, then write the code files (Step 3).
- **Every file block is the complete file.** "Replace the whole file" means overwrite it with the block. There are no partial edits except the documentation lines in Task 13, which are given as exact old and new text.
- **Non-ASCII characters are exact:** − (minus), — (em dash), · (middle dot), ▲ ▼, … (ellipsis), ’ (apostrophe in copy), → ↖ ↓ ↑, ÷, and – (the en dash in 2006–2020). The tests pin every sentence the pages show; if one fails on a character, the copy drifted.
- **Paste raw output.** When you report a step, paste the tool's own summary lines (for example `136 passed in 1.9s`, `Tests  115 passed (115)`), not a paraphrase.
- **Commands:** Python runs as `.venv/Scripts/python -m pytest` (on macOS and Linux, `.venv/bin/python`). `pyproject.toml` already adds `-q`; don't add another, or the summary line disappears. Web commands run in `web/`: `npx vitest run [files]`, `npx tsc --noEmit`, `npm run build`.
- If anything doesn't match what a step says, stop and report it rather than improvising.

## Global Constraints

- **Read-only, always:** GET routes only; the server binds `127.0.0.1`; no broker or trading import and no call named `place`, `place_order`, `submit_order`, `cancel`, `cancel_order`, `replace_order`, `modify_order`, `post`, `put`, `patch`, `delete`, `api_route`, `add_api_route` or `websocket` anywhere in `src/kestrel` (`tests/test_read_only_guard.py`).
- **The contract only grows:** `contract_version` stays `"1"`; every new field is optional with a default; old payloads keep loading.
- **Nothing private in git:** demo data stays fictional ("Alex"; ordinary large caps and sector funds); `tests/test_hygiene.py` passes on every commit.
- **Money state encoding everywhere:** real = solid; paper = hatched fills and dashed lines (`5 3.5`); expected, backtest and benchmark = dotted (outline `1.5 2.5`, lines `1.5 3.5`) with a 4–6 % ink wash. Colour never carries meaning alone.
- **Numbers and copy:** a sign and ▲/▼ on every gain or loss; the true minus sign (−); an em dash (—) for a missing value; sentence case; dates like `Fri 25 Sep`.
- **Tokens only:** no raw hex in `.ts`/`.tsx` (`web/src/styles/design.test.ts`); the type scale is px: 11, 12, 13, 14, 15, 20, 24, 28, 38, 48 (`text-2xs` … `text-5xl`).
- **Every chart:** a Chart | Table switch, a hover and keyboard tooltip (←/→, Home/End, Escape), a table view, and a plain-English empty state.
- **No overflow:** panel content never overflows its panel and the page never scrolls sideways at 390, 768, 1024 or 1440 px, in either theme.
- **Generated files** (`docs/contract/snapshot.schema.json`, `web/src/test/fixtures/*.json`) are only ever regenerated with the command a failing `tests/test_generated_files.py` prints, never edited.
- **CLI output:** ASCII human lines; JSON as UTF-8 bytes whatever the console code page.
- **Commits:** `feat(scope): …` / `fix(scope): …` / `ci: …` / `docs: …`, each ending with the `Co-Authored-By` trailer given in the session.

## Review Focus

These are the inputs most likely to bite a real person that the happy path never meets. Each has a test in the task named after it.

- **A new real book on its first day.** A book with one history point can't be drawn; it must not drag the comparison window to 12 months or shift every line's shared start (the spec says this lands before any real feed). Test: `test_a_real_book_on_its_first_day_does_not_empty_the_comparison` (Task 1).
- **Whatever arrives in the address bar.** An unknown strategy is a JSON 404 and an in-shell "Not found"; `?book=both` is a 422; a NUL character in a page path serves the app instead of a 500; a strategy id is escaped in Home's link. Tests: `test_a_nul_character_in_a_path_gets_the_app_not_an_error` (Task 1), `test_an_unknown_strategy_is_a_json_404` and `test_a_book_other_than_real_or_paper_is_refused` (Task 6), `shows an unknown strategy as not found, inside the shell` (Task 11).
- **Sparse strategies.** No books, paper only, no trades, fewer than 10 trades, no backtest, trades without charts, a chart that misses its open day, a book under 90 days, no slots, an empty watch list. Tests: `test_a_strategy_with_no_books_still_describes_itself`, `test_fewer_than_ten_closed_trades_is_too_early_to_judge`, `test_without_a_backtest_the_actual_figures_stand_alone` (Task 4); `test_a_chart_that_matches_no_trade_or_misses_the_open_day_is_ignored`, `test_worth_annualizes_a_year_or_more_marks_a_shorter_history_early_and_skips_under_ninety_days`, `test_a_book_without_slots_says_so_and_still_lists_the_watch`, `test_a_book_with_no_trades_leaves_those_sections_empty` (Task 5); `handles a strategy with no books yet` (Task 11); `lists a trade without a chart plainly, and says so when none has one` (Task 12).
- **Crowded and narrow charts.** Scatter labels that would collide or run off the chart, tooltips near an edge, a phone-width panel. Tests: `places labels beside their points, clear of each other, the markers and the edges` and `keeps a tooltip beside its anchor and inside the chart` (Task 7), `moves the labels into a key under the chart when they would collide on it` (Task 9), plus the screenshot pass (Task 13).
- **Ties, edges and calendars in the money math.** Trades closing the same day, two books with the same number of trades, returns of exactly 0, −10 or +10, a trade held over a weekend. Tests: `test_the_running_mean_follows_close_order_and_the_band_narrows_from_trade_three`, `test_the_book_with_most_closed_trades_wins_and_a_tie_goes_to_the_first_listed`, `test_buckets_are_one_point_wide_and_fold_the_ends` (Task 4); `test_sessions_held_count_weekdays_after_the_open_and_days_held_count_the_calendar` (Task 5).

## File map

```
src/kestrel/contract.py                  + Bar, IndicatorLine, Indicator, TradeChart, WatchItem; Expected.cagr_pct /
                                           max_drawdown_pct; Strategy.watch; Snapshot.trade_charts   (Task 2)
src/kestrel/metrics.py                   + rsi()                                                     (Task 3)
src/kestrel/connectors/demo.py           + trade charts, backtest figures, watch list               (Task 3)
src/kestrel/views/strategy.py            new: StrategiesView, StrategyView and their builders       (Tasks 4, 5)
src/kestrel/views/home.py                comparison start (Task 1); the attention link (Task 12)
src/kestrel/server.py                    NUL refused (Task 1); /api/strategies, /api/strategies/{id} (Task 6)
src/kestrel/cli.py                       demo --view strategies | strategy --id [--book]             (Task 6)
docs/data-contract.md · docs/contract/snapshot.schema.json (generated)                               (Task 2)
tests/test_{home_view,server,contract,metrics,demo_connector,cli,generated_files}.py (extended)
tests/test_strategy_view.py · tests/test_strategy_sections.py (new)                                 (Tasks 4, 5)
web/src/styles/tokens.css                px type scale, expected wash (Task 1); span-6 (Task 11)
web/src/charts/geometry.ts · hooks.ts · marks.tsx · LineChart.tsx · Histogram.tsx                   (Task 7)
web/src/charts/SlotsStrip.tsx · CandleChart.tsx                                                      (Task 8)
web/src/charts/Scatter.tsx · MonthGrid.tsx                                                           (Task 9)
web/src/lib/api.ts · main.tsx · test/renderApp.tsx · shell/Shell.tsx · router.tsx                    (Tasks 10, 11)
web/src/pages/strategies/Strategies.tsx                                                              (Task 10)
web/src/pages/strategy/{Strategy,HowItTrades,Behaving,FunnelPanel,SlotsPanel}.tsx                    (Task 11)
web/src/pages/strategy/{Anatomy,WorthPanel,MonthlyPanel,TradesPanel}.tsx                             (Task 12)
web/src/test/fixtures/{strategies,strategy-rsi2}.json (generated, Task 6); home.json (regenerated, Task 12)
.github/workflows/ci.yml · README.md · AGENTS.md · docs/specs/*                                      (Task 13)
```

---

### Task 1: Phase 2 follow-ups

**Files:**
- Modify (replace the whole file): `src/kestrel/views/home.py`, `src/kestrel/server.py`, `web/src/styles/tokens.css`, `web/src/pages/home/ComparisonPanel.tsx`
- Test (replace the whole file): `tests/test_home_view.py`, `tests/test_server.py`, `web/src/pages/home/Home.test.tsx`, `web/src/styles/design.test.ts`, `web/src/lib/format.test.ts`

**Interfaces:**
- Produces:
  - `views/home.py` `_comparison`: a series with fewer than 2 points is ignored when choosing the window (year to date vs 12 months), the shared start and the dates. It still draws no line.
  - `server.py` `_plain_parts(rest)`: `None` when `rest` contains a NUL (`chr(0)`), so the page route serves `index.html` instead of raising.
  - `ComparisonPanel.tsx` `period(c)`: with no `dates`, it names the window only ("Past 12 months" / "Year to date"), never a "since" date.
  - `tokens.css`: an `@theme` block with `--text-2xs: 11px` … `--text-5xl: 48px` (so the Home hero, `sm:text-5xl`, is 48 px); `.mark.expected` gains `background: color-mix(in srgb, var(--ink1) 5%, transparent)`.
  - `num()` already drops the minus on a value that shows as zero (Phase 2, bfc93f6); this task only pins one more case.

- [ ] **Step 1: Write the failing tests**

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
````

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

`web/src/styles/design.test.ts`:

````ts
// @vitest-environment node
// Design-system rules that code review keeps missing, pinned as tests (docs/design-system.md).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const SRC = fileURLToPath(new URL('..', import.meta.url))
const css = () => readFileSync(join(SRC, 'styles', 'tokens.css'), 'utf8')

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? files(path) : [path]
  })
}

describe('design rules', () => {
  it('components use tokens, never raw hex colours', () => {
    const offenders = files(SRC)
      .filter((f) => /\.tsx?$/.test(f) && !f.endsWith('.test.ts') && !f.endsWith('.test.tsx'))
      .filter((f) => /#[0-9a-fA-F]{3,8}\b/.test(readFileSync(f, 'utf8')))
    expect(offenders).toEqual([])
  })

  it('keeps screen-reader labels inside scrolling tables (no sideways page scroll on phones)', () => {
    expect(css()).toMatch(/\.table-scroll \{ position: relative;/)
    expect(css()).toMatch(/\.panel \{ position: relative;/)
  })

  it('sets the type scale in px, so the 14 px root never shrinks it', () => {
    const sizes = Object.fromEntries([...css().matchAll(/--text-(\w+): (\d+)px;/g)].map((m) => [m[1], Number(m[2])]))
    expect(sizes).toEqual({
      '2xs': 11, xs: 12, sm: 13, base: 14, lg: 15, xl: 20, '2xl': 24, '3xl': 28, '4xl': 38, '5xl': 48,
    })
  })

  it('gives the expected mark its dotted outline and a faint ink wash', () => {
    expect(css()).toContain('.mark.expected { border: 1.5px dotted var(--mc, var(--ref));'
      + ' background: color-mix(in srgb, var(--ink1) 5%, transparent); }')
  })
})
````

`web/src/lib/format.test.ts`:

````ts
import { afterEach, describe, expect, it } from 'vitest'
import {
  ago, compactMoney, money, monthLabel, num, pct, setCurrency, shortDate, signedMoney, sinceLabel, splitCents, timeHM,
} from './format'

describe('money', () => {
  it('uses a true minus sign and cents', () => {
    expect(money(148392.18)).toBe('$148,392.18')
    expect(money(-12.3)).toBe('−$12.30')
    expect(money(118200, false)).toBe('$118,200')
  })
  it('signs deltas but never zero', () => {
    expect(signedMoney(412.3)).toBe('+$412.30')
    expect(signedMoney(-32.5)).toBe('−$32.50')
    expect(signedMoney(0)).toBe('$0.00')
    expect(signedMoney(-0.001)).toBe('$0.00')
  })
  it('splits the hero figure', () => {
    expect(splitCents(148392.18)).toEqual(['$148,392', '18'])
  })
  describe('in another currency', () => {
    afterEach(() => setCurrency('USD'))
    it('follows the profile', () => {
      setCurrency('EUR')
      expect(money(1234.5)).toBe('€1,234.50')
      expect(signedMoney(-2)).toBe('−€2.00')
      expect(splitCents(1234.5)).toEqual(['€1,234', '50'])
      expect(compactMoney(118200)).toBe('€118.2K')
      expect(compactMoney(-950)).toBe('−€950')
    })
    it('falls back to the code itself when Intl does not know it', () => {
      setCurrency('EURO')
      expect(money(1234.5)).toBe('EURO 1,234.50')
      expect(signedMoney(-2)).toBe('−EURO 2.00')
      expect(compactMoney(118200)).toBe('EURO 118.2K')
    })
  })
})

describe('numbers', () => {
  it('formats percents with a sign', () => {
    expect(pct(14.2)).toBe('+14.2%')
    expect(pct(-5.12)).toBe('−5.1%')
    expect(pct(0.04)).toBe('0.0%')
    expect(pct(0.279, 2)).toBe('+0.28%')
  })
  it('compacts chart labels', () => {
    expect(compactMoney(118200)).toBe('$118.2K')
    expect(compactMoney(1_250_000)).toBe('$1.3M')
    expect(compactMoney(-950)).toBe('−$950')
    expect(compactMoney(-0.04)).toBe('$0') // no sign on what shows as zero
  })
  it('formats prices', () => {
    expect(num(508.2)).toBe('508.20')
    expect(num(-3)).toBe('−3.00')
    expect(num(-2.46, 1)).toBe('−2.5')
    expect(num(-0.004)).toBe('0.00') // no sign on what shows as zero
    expect(num(-0.4, 0)).toBe('0')
  })
})

describe('dates', () => {
  it('formats short dates and axis labels', () => {
    expect(shortDate('2026-09-25')).toBe('Fri 25 Sep')
    expect(monthLabel('2026-09-25')).toBe('Sep')
    expect(monthLabel('2026-09-25', true)).toBe('25 Sep')
    expect(sinceLabel('2026-09-10', '2026-09-25T21:08:00Z')).toBe('10 Sep')
    expect(sinceLabel('2025-07-27', '2026-09-25T21:08:00Z')).toBe('Jul 2025')
  })
  it('formats times in the profile zone', () => {
    expect(timeHM('2026-09-25T21:08:00Z', 'America/New_York')).toBe('17:08')
  })
  it('says how long ago', () => {
    const now = new Date('2026-09-25T21:08:00Z')
    expect(ago('2026-09-25T21:06:00Z', now)).toBe('2m')
    expect(ago('2026-09-24T19:08:00Z', now)).toBe('26h')
    expect(ago('2026-09-20T21:08:00Z', now)).toBe('5d')
    expect(ago(null, now)).toBe('never')
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_home_view.py tests/test_server.py` and, in `web/`, `npx vitest run src/pages/home/Home.test.tsx src/styles/design.test.ts src/lib/format.test.ts`
Expected: pytest `2 failed, 23 passed`: `test_a_real_book_on_its_first_day_does_not_empty_the_comparison` (`AssertionError: assert ('12m' == 'ytd'`) and `test_a_nul_character_in_a_path_gets_the_app_not_an_error` (`ValueError: stat: embedded null character in path`). vitest `Tests  3 failed | 28 passed (31)`: the type scale (`expected {} to deeply equal { '2xs': 11, …`), the expected wash, and `names no date when there is nothing to compare yet` (`expected { phrase: 'since 25 Sep', …`).

- [ ] **Step 3: Implement**

`src/kestrel/views/home.py`:

````python
"""The Home page, computed from one Snapshot: how is all my money doing, and does anything need me?"""

from __future__ import annotations

import datetime as dt
from statistics import fmean
from typing import Literal

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
    trading = sum_series([book_history[b.id] for b in real_books if b.id in book_history])
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
        per_trade = round(fmean(returns), 3) if returns else None
        lo = hi = None
        if not returns or expected is None:
            verdict = "none"
        elif len(returns) < MIN_TRADES_FOR_VERDICT:
            verdict = "early"
        else:
            lo, hi = expected_band(expected.avg_trade_pct, expected.sd_trade_pct, len(returns))
            verdict = "below" if per_trade < lo else "above" if per_trade > hi else "in_band"
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
            items.append(Attention(level="note", title=f"{row.name} is below its expected band", detail=detail,
                                   link="/strategies"))
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
from .profile import Profile
from .views.home import HomeView, home_view
from .views.shell import ShellView, shell_view

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

`web/src/styles/tokens.css`:

````css
/* kestrel — Graphite design tokens. Source of truth: docs/design-system.md. Never use raw hex in components. */
@import "tailwindcss";

@theme inline {
  --color-bg: var(--bg);
  --color-side: var(--side);
  --color-panel: var(--panel);
  --color-panel2: var(--panel2);
  --color-line: var(--line);
  --color-line2: var(--line2);
  --color-ink1: var(--ink1);
  --color-ink2: var(--ink2);
  --color-ink3: var(--ink3);
  --color-acc: var(--acc);
  --color-acc-ink: var(--acc-ink);
  --color-up: var(--up);
  --color-down: var(--down);
  --color-warn: var(--warn);
  --color-serious: var(--serious);
  --color-good: var(--good);
  --font-sans: var(--k-sans);
  --font-mono: var(--k-mono);
}

/* the design-system type scale, in px: the app's root is 14 px, so rem-based sizes would come out smaller */
@theme {
  --text-2xs: 11px; --text-2xs--line-height: 1.4;
  --text-xs: 12px;
  --text-sm: 13px;
  --text-base: 14px;
  --text-lg: 15px;
  --text-xl: 20px;
  --text-2xl: 24px;
  --text-3xl: 28px;
  --text-4xl: 38px;
  --text-5xl: 48px;
}

.k {
  --bg: #0b0c0e; --side: #0e0f12; --panel: #121418; --panel2: #181b20; --line: #22262c; --line2: #2e333a;
  --ink1: #eceef1; --ink2: #a7adb6; --ink3: #7d848e;
  --s1: #5b93db; --s2: #d46c38; --s3: #8a9099; --ref: #7d848e;
  --warn: #e8b84b; --serious: #ec835a; --good: #4cc38f; --up: #4cc38f; --down: #ea5b60;
  --acc: #d46c38; --acc-ink: #e3875a; --on-acc: #0b0c0e;
  --pad: 20px; --row: 56px;
  --k-sans: "Geist", ui-sans-serif, system-ui, sans-serif;
  --k-mono: "Geist Mono", ui-monospace, monospace;
  color-scheme: dark;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink1);
  font-family: var(--k-sans);
  font-size: 14px;
  line-height: 1.4;
  -webkit-font-smoothing: antialiased;
}
.k[data-theme="light"] {
  --bg: #f2f3f5; --side: #f8f9fa; --panel: #ffffff; --panel2: #f5f6f8; --line: #e3e5e9; --line2: #d3d7dd;
  --ink1: #0f1114; --ink2: #4a5059; --ink3: #666d77;
  --s1: #2f6db5; --s2: #c45a24; --s3: #9aa0a8; --ref: #666d77;
  --warn: #9a6700; --serious: #c2562a; --good: #11845a; --up: #11845a; --down: #d1363b;
  color-scheme: light;
}
.k[data-accent="rufous"] { --acc: #d46c38; --acc-ink: #e3875a; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="rufous"] { --acc: #c45a24; --acc-ink: #a9481a; --on-acc: #ffffff; }
.k[data-accent="slate"] { --acc: #5b93db; --acc-ink: #7faae3; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="slate"] { --acc: #2f6db5; --acc-ink: #255a97; --on-acc: #ffffff; }
.k[data-accent="mono"] { --acc: #eceef1; --acc-ink: #eceef1; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="mono"] { --acc: #0f1114; --acc-ink: #0f1114; --on-acc: #ffffff; }
.k[data-gl="blue-orange"] { --up: #5b93db; --down: #d46c38; }
.k[data-theme="light"][data-gl="blue-orange"] { --up: #2f6db5; --down: #c45a24; }
.k[data-density="compact"] { --pad: 14px; --row: 44px; }

.k :focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
.k a { color: var(--ink2); text-decoration: none; }
.k a:hover { color: var(--ink1); }
@media (prefers-reduced-motion: no-preference) {
  .k .ease { transition: background-color 150ms ease-out, color 150ms ease-out, transform 150ms ease-out; }
}

/* --- building blocks ------------------------------------------------------------------------------------- */
.panel { position: relative; background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: var(--pad); display: flex; flex-direction: column; min-width: 0; height: var(--h, auto); }
.panel-title { font-size: 14px; font-weight: 600; letter-spacing: -0.005em; }
.panel-sub { font-size: 12px; color: var(--ink3); margin-top: 2px; }
.label { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink3); font-weight: 500; }
.num { font-family: var(--k-mono); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 7px; padding: 2px; gap: 2px;
  background: var(--panel); }
.seg button { font: 500 12px/1 var(--k-sans); padding: 6px 10px; border-radius: 5px; color: var(--ink3);
  cursor: pointer; background: none; border: 0; }
.seg button[aria-pressed="true"] { background: var(--panel2); color: var(--ink1); box-shadow: inset 0 0 0 1px var(--line2); }
.icon-btn { width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center;
  border-radius: 7px; border: 1px solid var(--line); color: var(--ink2); background: var(--panel); cursor: pointer; }
.chip { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--ink2); padding: 5px 10px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--panel); white-space: nowrap; }
.mark { width: 12px; height: 12px; border-radius: 3px; display: inline-block; flex: none; }
.mark.real { background: var(--mc, var(--ink2)); }
.mark.paper { background-image: repeating-linear-gradient(45deg, var(--mc, var(--ink2)) 0 1.5px, transparent 1.5px 4px);
  box-shadow: inset 0 0 0 1.25px var(--mc, var(--ink2)); }
.mark.expected { border: 1.5px dotted var(--mc, var(--ref)); background: color-mix(in srgb, var(--ink1) 5%, transparent); }
.badge { display: inline-flex; align-items: center; gap: 6px; font: 600 10px/1 var(--k-mono); letter-spacing: 0.08em;
  color: var(--ink2); padding: 5px 7px; border: 1px solid var(--line2); border-radius: 5px; }
.up { color: var(--up); }
.down { color: var(--down); }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink3); font-weight: 500;
  text-align: left; padding: 0 12px 10px 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
.tbl td { height: var(--row); border-bottom: 1px solid var(--line); vertical-align: middle; padding: 0 12px 0 0; }
.tbl tr:last-child td { border-bottom: 0; }
.tbl .r { text-align: right; }
.tip { position: absolute; z-index: 10; pointer-events: none; background: var(--panel2); border: 1px solid var(--line2);
  border-radius: 7px; padding: 8px 10px; font-size: 12px; box-shadow: 0 8px 24px rgb(0 0 0 / 0.28); min-width: 170px; }
.sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; border: 0; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; }

/* --- layout ------------------------------------------------------------------------------------------------ */
.shell { display: flex; min-height: 100vh; }
.sidebar { width: 256px; flex: none; height: 100vh; position: sticky; top: 0; background: var(--side);
  border-right: 1px solid var(--line); display: flex; flex-direction: column; padding: 18px 14px; overflow-y: auto; }
.nav-item { display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 10px; border-radius: 7px;
  font-size: 14px; font-weight: 500; color: var(--ink2); }
.nav-item[aria-current="page"] { background: var(--panel2); color: var(--ink1); box-shadow: inset 0 0 0 1px var(--line); }
.nav-item[aria-current="page"] svg { color: var(--acc); }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.topbar { height: 64px; flex: none; display: flex; align-items: center; gap: 10px; padding: 0 32px;
  border-bottom: 1px solid var(--line); }
.content { padding: 28px 32px 32px; }
.grid12 { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; align-content: start; }
.span-4 { grid-column: span 4; } .span-5 { grid-column: span 5; } .span-7 { grid-column: span 7; }
.span-8 { grid-column: span 8; } .span-12 { grid-column: span 12; }
.menu-btn, .tabbar, .scrim { display: none; }
/* position: relative keeps absolutely positioned children (sr-only labels) inside the scroll box */
.table-scroll { position: relative; overflow-x: auto; }

@media (max-width: 1180px) {
  .span-4, .span-5, .span-7, .span-8 { grid-column: span 12; }
  .panel { height: auto; }
}
@media (max-width: 900px) {
  /* closed: off screen AND hidden, so its links leave the tab order and screen readers skip it */
  .sidebar { position: fixed; left: 0; top: 0; z-index: 30; transform: translateX(-100%); visibility: hidden; }
  .shell[data-drawer="open"] .sidebar { transform: none; visibility: visible; }
  .shell[data-drawer="open"] .scrim { display: block; position: fixed; inset: 0; z-index: 20; background: rgb(0 0 0 / 0.45); }
  .menu-btn { display: inline-flex; }
  .topbar { padding: 0 16px; }
  .content { padding: 20px 16px 24px; }
  .hide-narrow { display: none; }
}
@media (max-width: 640px) {
  .tabbar { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); position: fixed; left: 0; right: 0;
    bottom: 0; z-index: 25; height: 72px; padding: 6px 4px 14px; background: var(--side); border-top: 1px solid var(--line); }
  .content { padding-bottom: 96px; }
  .icon-btn { width: 44px; height: 44px; } /* touch targets */
  .seg button { min-height: 36px; }
}
````

`web/src/pages/home/ComparisonPanel.tsx`:

````tsx
import { useState } from 'react'
import { type ChartSeries, LineChart, LineKey } from '../../charts/LineChart'
import { Delta, Panel, Seg } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Comparison, Line } from '../../lib/api'
import { monthLabel, pct, shortDate } from '../../lib/format'

const STYLE: Record<Line['key'], Pick<ChartSeries, 'color' | 'style'>> = {
  trading: { color: 'var(--s2)', style: 'solid' },
  long_term: { color: 'var(--s1)', style: 'solid' },
  benchmark: { color: 'var(--ref)', style: 'dotted' },
}

const DAY_MS = 86_400_000
const GRACE_DAYS = 7 // a year's first close can fall as late as 4 January (New Year's Day, then a weekend)

/** The comparison's period in words. Every line starts on the same day; when that day is later than the window's
 *  own start (say a book opened in July), the words name it: "since 1 Jul". With no dates yet, it names none. */
export function period(c: Comparison): { phrase: string; title: string } {
  const last = c.dates[c.dates.length - 1]
  const opens = c.window === 'ytd' ? Date.parse(`${c.start.slice(0, 4)}-01-01`) : Date.parse(last) - 365 * DAY_MS
  // with no dates there is no shared start to name (the empty 12-month case): say the window alone
  if (last != null && Date.parse(c.start) - opens > GRACE_DAYS * DAY_MS) {
    const day = monthLabel(c.start, true)
    return { phrase: `since ${day}`, title: `Since ${day}` }
  }
  return c.window === 'ytd'
    ? { phrase: 'this year', title: 'Year to date' }
    : { phrase: 'over the past 12 months', title: 'Past 12 months' }
}

export function verdict(c: Comparison): { headline: string; caveat: string } | null {
  if (c.gap_pts == null) return null
  const { phrase } = period(c)
  const gap = Math.abs(c.gap_pts).toFixed(1)
  const trading = c.lines.find((l) => l.key === 'trading')
  const longTerm = c.lines.find((l) => l.key === 'long_term')
  const drops = trading && longTerm ? ` (${pct(trading.max_drop_pct)} vs ${pct(longTerm.max_drop_pct)})` : ''
  const equalDrop = trading && longTerm && Math.abs(trading.max_drop_pct - longTerm.max_drop_pct) < 0.05
  const drop = equalDrop ? 'an equal' : c.shallower ? 'a shallower' : 'a deeper'
  const headline = Math.abs(c.gap_pts) < 0.05
    ? `Trading is level with your index money ${phrase}.`
    : `Trading is ${c.gap_pts > 0 ? 'ahead' : 'behind'} by ${gap} pts ${phrase}, with ${drop} worst drop${drops}.`
  const early = c.review_at != null && c.real_trades < c.review_at
  const caveat = early
    ? `${c.real_trades} real trades so far — early evidence. The strategy is reviewed at ${c.review_at}.`
    : `${c.real_trades} real trades so far.`
  return { headline, caveat }
}

export function ComparisonPanel({ c }: { c: Comparison }) {
  const [view, setView] = useState<'Chart' | 'Table'>('Chart')
  const v = verdict(c)
  const series: ChartSeries[] = c.lines.map((l) => ({ key: l.key, label: l.label, values: l.values, ...STYLE[l.key] }))
  return (
    <Panel id="comparison" title="Trading vs your index money" span={7} height={372}
      subtitle={`${period(c).title} · real money only · all start at 0%`}
      actions={<Seg label="View" options={['Chart', 'Table'] as const} value={view} onChange={setView} />}>
      {c.lines.length === 0 ? (
        <p className="text-ink3 mt-6">No history yet. The comparison appears once your accounts have a few days of data.</p>
      ) : (
        <div className="flex flex-col sm:flex-row gap-4 sm:gap-6 mt-3.5 min-h-0">
          <div className="flex-1 min-w-0">
            {view === 'Chart' ? (
              <LineChart dates={c.dates} series={series} height={190} zeroLine
                ariaLabel="Return since the start of the window: trading, long-term and the benchmark"
                yFormat={(n) => pct(n, 0)} valueFormat={(n) => pct(n)} xLabel={(d) => monthLabel(d)}
                tipTitle={(d) => shortDate(d)} />
            ) : (
              <table className="tbl">
                <thead><tr><th>Line</th><th className="r">Return</th><th className="r">Worst drop</th></tr></thead>
                <tbody>
                  {c.lines.map((l) => (
                    <tr key={l.key}><td>{l.label}</td><td className="r"><Delta value={l.return_pct} digits={1}>{pct(l.return_pct)}</Delta></td>
                      <td className="r num">{pct(l.max_drop_pct)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="grid grid-cols-3 gap-2.5 sm:flex sm:flex-col sm:w-[150px] flex-none">
            {c.lines.map((l) => (
              <div key={l.key}>
                <div className="flex items-center gap-2 text-xs text-ink2">
                  <LineKey {...STYLE[l.key]} />{l.label}
                </div>
                <div className="num text-xl font-medium mt-1"><Delta value={l.return_pct} digits={1}>{pct(l.return_pct)}</Delta></div>
                <div className="num text-[11px] text-ink3">max drop {pct(l.max_drop_pct)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {v && (
        <div className="mt-auto flex gap-3 items-start rounded-lg border border-line bg-panel2 px-3.5 py-3">
          <Icon name="scale" size={18} style={{ color: 'var(--ink2)', marginTop: 1 }} />
          <div>
            <div className="text-[13px] font-medium">{v.headline}</div>
            <div className="text-xs text-ink3 mt-0.5">{v.caveat}</div>
          </div>
        </div>
      )}
    </Panel>
  )
}
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .` and, in `web/`, `npx vitest run && npx tsc --noEmit && npm run build`
Expected: `90 passed` (`test_home_view.py` 14, `test_server.py` 11); `All checks passed!`; `Tests  51 passed (51)` (`Home.test.tsx` 16, `design.test.ts` 4, `format.test.ts` 11); tsc prints nothing; `✓ built`. `home.json` doesn't change: the demo's real book has a full year of history.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/views/home.py src/kestrel/server.py tests/test_home_view.py tests/test_server.py web/src/styles/tokens.css web/src/styles/design.test.ts web/src/pages/home/ComparisonPanel.tsx web/src/pages/home/Home.test.tsx web/src/lib/format.test.ts
git commit -m "fix: phase 2 follow-ups: a first-day book keeps the comparison, NUL paths, px type scale, expected wash"
```

---

### Task 2: The contract grows: trade charts, backtest figures, a watch list

**Files:**
- Modify (replace the whole file): `src/kestrel/contract.py`, `docs/data-contract.md`
- Regenerate: `docs/contract/snapshot.schema.json`
- Test (replace the whole file): `tests/test_contract.py`

**Interfaces:**
- Produces (all frozen pydantic models on `Model`, `extra="ignore"`):
  - `Bar(date: date, open: float, high: float, low: float, close: float)`
  - `IndicatorLine(value: float, label: str)`; `Indicator(label: str, values: list[float | None], lines: list[IndicatorLine] = [])` with `values` aligned with the bars.
  - `TradeChart(book_id: str, symbol: str, opened: date, bars: list[Bar], indicator: Indicator | None = None, stop: float | None = None)`, matched to a `Trade` by `(book_id, symbol, opened)`.
  - `WatchItem(symbol: str, label: str, value: float | None = None, note: str = "")`
  - `Expected.cagr_pct: float | None = None`, `Expected.max_drawdown_pct: float | None = None` (negative); `Strategy.watch: list[WatchItem] = []`; `Snapshot.trade_charts: list[TradeChart] = []`.
  - `merge()` concatenates `trade_charts` like the other lists.
- A chart that matches no trade, or whose bars miss the open day, still loads; the Strategy view ignores it (Task 5).

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


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_contract.py`
Expected: `4 failed, 15 passed`, each `AttributeError: 'Snapshot' object has no attribute 'trade_charts'` (the unknown field was ignored on the way in).

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

## Optional extras

The Strategy page draws more when a source sends these. Each is optional; without it, the page shows a plain
"not reported" state for that part and everything else still works.

- `trade_charts`: daily bars around a closed trade (`date`, `open`, `high`, `low`, `close`). A chart matches its
  trade by `book_id`, `symbol` and `opened`. It may carry an `indicator` drawn in its own panel under the candles
  (`label`, `values` aligned with the bars, threshold `lines`) and the trade's `stop`. A chart whose bars don't
  include the open date, or that matches no trade, is ignored.
- `Expected.cagr_pct` and `Expected.max_drawdown_pct`: the backtest's yearly return and its worst drop (a negative
  percent), plotted on "Is it worth it?".
- `Strategy.watch`: names close to a signal (`symbol`, `label`, `value`, `note`), listed under "Where the money
  works".
````


Then regenerate the schema (the drift test prints this exact command):

```bash
.venv/Scripts/kestrel schema > docs/contract/snapshot.schema.json
```

- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `94 passed` (`test_contract.py` 19); `All checks passed!`. Before the schema is regenerated, `test_generated_file_is_current[snapshot.schema.json]` fails with ``out of date: run `kestrel schema > docs/contract/snapshot.schema.json` ``.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/contract.py tests/test_contract.py docs/data-contract.md docs/contract/snapshot.schema.json
git commit -m "feat(contract): trade charts, backtest yearly return and worst drop, and a watch list (additive)"
```

---

### Task 3: Demo trade charts, RSI(2), backtest figures and a watch list

**Files:**
- Modify (replace the whole file): `src/kestrel/metrics.py`, `src/kestrel/connectors/demo.py`
- Test (replace the whole file): `tests/test_metrics.py`, `tests/test_demo_connector.py`

**Interfaces:**
- Consumes: `Bar`, `Indicator`, `IndicatorLine`, `TradeChart`, `WatchItem` (Task 2).
- Produces:
  - `metrics.rsi(closes: Sequence[float], period: int = 2) -> list[float | None]`: Wilder's RSI aligned with `closes`, `None` for the first `period` values, 50 when nothing moved.
  - `demo.py`: `CHARTED = 8`, `CHART_BARS = 30`, `RSI2_LINES`, `_chart(trade, days, seed: str, rsi2: bool) -> TradeChart`, `_charts(book, trades, days, seed: int) -> list[TradeChart]`; `DemoConnector.snapshot()` fills `trade_charts` (8 per book); `rsi2`'s `Expected` gains `cagr_pct=23.4, max_drawdown_pct=-11.7`; `rsi2.watch` = KO 12.4, ABT 16.8, UNP 19.1 (label `RSI(2)`).
  - The entry bar opens at the entry price; the exit bar opens at the exit price (a same-day trade closes at it). Mean reversion charts carry RSI(2) with lines at 10 ("buy under 10") and 70 ("sell over 70") and a stop 8% under the entry.
  - Charts use their own random generator, seeded per trade, so every existing demo number (and `home.json`, `shell.json`) stays the same.

- [ ] **Step 1: Write the failing tests**

`tests/test_metrics.py`:

````python
import datetime as dt

import pytest

from kestrel.contract import ValuePoint
from kestrel.metrics import expected_band, growth_index, largest_remainder, max_drawdown_pct, rsi, sum_series


def vp(day, value, flow=0.0):
    return ValuePoint(date=dt.date(2026, 9, day), value=value, net_flow=flow)


def test_growth_index_ignores_deposits():
    # 100 -> 110 of which 10 was a deposit: no performance at all
    assert growth_index([vp(1, 100), vp(2, 110, 10)]) == [1.0, 1.0]


def test_growth_index_chains_daily_returns():
    index = growth_index([vp(1, 100), vp(2, 110), vp(3, 99)])
    assert index == pytest.approx([1.0, 1.1, 0.99])


def test_growth_index_survives_a_zero_balance_and_empty_input():
    assert growth_index([]) == []
    assert growth_index([vp(1, 0), vp(2, 50, 50)]) == [1.0, 1.0]


def test_max_drawdown_is_the_worst_fall_from_a_peak():
    assert max_drawdown_pct([1.0, 1.2, 0.9, 1.3, 1.17]) == pytest.approx(-25.0)
    assert max_drawdown_pct([1.0, 1.1, 1.2]) == 0.0


def test_expected_band_narrows_with_more_trades():
    lo4, hi4 = expected_band(0.84, 3.0, 4)
    lo100, hi100 = expected_band(0.84, 3.0, 100)
    assert (lo4, hi4) == pytest.approx((0.84 - 2.94, 0.84 + 2.94))
    assert hi100 - lo100 < hi4 - lo4
    with pytest.raises(ValueError):
        expected_band(0.84, 3.0, 0)


def test_largest_remainder_always_totals_exactly():
    assert largest_remainder([71.53, 12.40, 16.07]) == [72, 12, 16]
    assert sum(largest_remainder([1, 1, 1])) == 100
    assert largest_remainder([0, 0]) == [0, 0]


def test_sum_series_carries_forward_a_missing_day():
    a = [vp(1, 100), vp(2, 101), vp(3, 102)]
    b = [vp(1, 50), vp(3, 55)]  # no point on the 2nd
    assert [p.value for p in sum_series([a, b])] == [150, 151, 157]


def test_sum_series_counts_a_late_account_as_a_deposit_not_growth():
    a = [vp(1, 100), vp(2, 100)]
    late = [vp(2, 40)]
    total = sum_series([a, late])
    assert total[1].value == 140 and total[1].net_flow == 40
    assert growth_index(total) == [1.0, 1.0]


def test_rsi_is_wilders_and_aligned_with_the_closes():
    assert rsi([10, 11, 10, 12]) == pytest.approx([None, None, 50.0, 83.333], abs=0.001)
    assert rsi([1, 2, 3]) == [None, None, 100.0]  # no losses at all
    assert rsi([3, 2, 1]) == [None, None, 0.0]
    assert rsi([5, 5, 5]) == [None, None, 50.0]  # no movement is neither overbought nor oversold
    assert rsi([1, 2]) == [None, None]
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
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_metrics.py tests/test_demo_connector.py`
Expected: a collection error, `ImportError: cannot import name 'rsi' from 'kestrel.metrics'` (`1 error`). The four new demo tests need the implementation too; Step 4 runs them.

- [ ] **Step 3: Implement**

`src/kestrel/metrics.py`:

````python
"""Pure money math shared by every view. No I/O, no clock."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .contract import ValuePoint


def growth_index(points: Sequence[ValuePoint]) -> list[float]:
    """Time-weighted growth index starting at 1.0.

    Each step is the day's change net of that day's deposits and withdrawals, so adding money never
    looks like performance.
    """
    if not points:
        return []
    index = [1.0]
    for prev, cur in zip(points, points[1:]):
        step = (cur.value - cur.net_flow) / prev.value if prev.value > 0 else 1.0
        index.append(index[-1] * step)
    return index


def max_drawdown_pct(index: Sequence[float]) -> float:
    """Worst fall from a running peak, as a negative percent (0.0 when it never fell)."""
    peak = -math.inf
    worst = 0.0
    for value in index:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return worst * 100.0


def expected_band(avg: float, sd: float, n: int) -> tuple[float, float]:
    """95% range for the average of n trades: avg ± 1.96·sd/√n."""
    if n <= 0:
        raise ValueError("n must be positive")
    half = 1.96 * sd / math.sqrt(n)
    return avg - half, avg + half


def largest_remainder(shares: Sequence[float], total: int = 100) -> list[int]:
    """Round shares to whole units that add up to exactly `total` (for the 100-cell waffle)."""
    whole = sum(shares)
    if whole <= 0:
        return [0] * len(shares)
    raw = [s / whole * total for s in shares]
    floors = [math.floor(r) for r in raw]
    left = total - sum(floors)
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in by_remainder[:left]:
        floors[i] += 1
    return floors


def sum_series(series: Sequence[Sequence[ValuePoint]]) -> list[ValuePoint]:
    """Add value series by date.

    A series with no point on a date contributes its last known value. A series that appears after the
    first date brings its opening value in as a flow, so a newly linked account is not counted as growth.
    """
    dates = sorted({p.date for s in series for p in s})
    by_date = [{p.date: p for p in s} for s in series]
    last: list[float | None] = [None] * len(series)
    out: list[ValuePoint] = []
    for n, day in enumerate(dates):
        total = 0.0
        flow = 0.0
        for i, points in enumerate(by_date):
            point = points.get(day)
            if point is not None:
                if last[i] is None and n > 0:
                    flow += point.value
                else:
                    flow += point.net_flow
                last[i] = point.value
            if last[i] is not None:
                total += last[i]
        out.append(ValuePoint(date=day, value=round(total, 2), net_flow=round(flow, 2)))
    return out


def rsi(closes: Sequence[float], period: int = 2) -> list[float | None]:
    """Wilder's relative strength index, aligned with `closes`: None until `period` changes have been seen."""
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    changes = [b - a for a, b in zip(closes, closes[1:])]
    gain = sum(max(c, 0.0) for c in changes[:period]) / period
    loss = sum(max(-c, 0.0) for c in changes[:period]) / period

    def value() -> float:
        if gain == 0 and loss == 0:
            return 50.0
        return 100.0 if loss == 0 else 100.0 - 100.0 / (1.0 + gain / loss)

    out[period] = value()
    for i in range(period, len(changes)):
        gain = (gain * (period - 1) + max(changes[i], 0.0)) / period
        loss = (loss * (period - 1) + max(-changes[i], 0.0)) / period
        out[i + 1] = value()
    return out
````

`src/kestrel/connectors/demo.py`:

````python
"""Fictional demo data: a believable year for "Alex".

Deterministic for a seed: the numbers never change, only the dates move so the last point is today.
Nothing here is anyone's real account; the tickers are ordinary large caps and sector funds.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..contract import (
    Account,
    Bar,
    Benchmark,
    Book,
    Expected,
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

        as_of = datetime.combine(days[-1], time(16, 0), tzinfo=self.tz)
        accounts = [
            Account(id="roth", name="Roth IRA", institution="Brokerage A", category="long_term", value=roth[-1],
                    as_of=as_of),
            Account(id="brokerage", name="Brokerage", institution="Brokerage A", category="long_term",
                    value=brokerage[-1], as_of=as_of),
            Account(id="trading", name="Trading account", institution="Brokerage B", category="trading",
                    value=trading[-1], as_of=as_of),
            Account(id="savings", name="High-yield savings", institution="Bank C", category="cash", value=savings[-1],
                    as_of=as_of),
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
            generated_at=now, sources=sources, accounts=accounts, account_history=account_history, books=books,
            book_history=book_history, positions=positions, trades=trades,
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


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `99 passed` (`test_metrics.py` 9, `test_demo_connector.py` 13); `All checks passed!`. `tests/test_generated_files.py` still passes: no existing demo number moved.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/metrics.py src/kestrel/connectors/demo.py tests/test_metrics.py tests/test_demo_connector.py
git commit -m "feat(demo): trade charts with RSI(2) and stops, backtest yearly return and worst drop, a watch list"
```

---

### Task 4: The strategy views, part 1: the list, the primary book, how it trades, is it behaving, the funnel

**Files:**
- Create: `src/kestrel/views/strategy.py`
- Test: `tests/test_strategy_view.py`

**Interfaces:**
- Consumes: `View`, `MIN_TRADES_FOR_VERDICT` (10) and `_book_rows` from `views/home.py` (the card's band is exactly Home's Books-table band); `expected_band` from `metrics`.
- Produces (`views/strategy.py`, pydantic `View` models):
  - `BookChip(id, name, money, status, open: int, trades: int)`
  - `StrategyCard(id, name, summary, books: list[BookChip], book: Money | None, trades: int, per_trade_pct, band_lo, band_hi: float | None, verdict: "in_band" | "below" | "above" | "early" | "none")`; `StrategiesView(strategies: list[StrategyCard])`
  - `Bucket(low: int, count: int, share: float, expected: float | None)`; `ScoreRow(key: "win_rate" | "avg_trade" | "avg_win" | "avg_loss" | "per_month", label, actual: float | None, expected: float | None, status: "ok" | "above" | "below" | "early" | "none")`; `OtherBook(id, money, trades, per_trade_pct, win_rate)`; `Behaving(trades, buckets, scorecard, review_at, other)`
  - `FunnelLine(book_id, money, values: list[float])`; `Funnel(expected: float | None, lines, lo: list[float | None], hi: list[float | None])`
  - `StrategyView(id, name, summary, books, book: Money | None, primary: str | None, toggle: bool, expected: Expected | None, steps: list[Step], sizing, behaving, funnel)`
  - `closed_trades(snapshot, book_id) -> list[Trade]` (close order; ties by opened, then symbol); `buckets(returns, distribution) -> list[Bucket]`; `running_mean(trades) -> list[float]`
  - `strategies_view(snapshot, profile, now) -> StrategiesView`; `strategy_view(snapshot, profile, now, strategy_id, book: Money = "real") -> StrategyView | None` (`None` for an unknown id).
- Rules (spec §2.3, §3.2): the primary book is the requested money's book with the most closed trades (a tie goes to the first listed), else the other money's; `toggle` only when the strategy has both a real and a paper book. Scorecard bands: win rate ±1.96·√(p(1−p)/n) points; average trade `expected_band`; average win, average loss and trades per month ±50%; under 10 closed trades → `early`; no backtest → `none`. Trades per month = closed trades ÷ max(1, months since the book started). The funnel band starts at trade 3.

- [ ] **Step 1: Write the failing tests**

`tests/test_strategy_view.py`:

````python
import datetime as dt
from statistics import fmean

import pytest

from kestrel.connectors import collect
from kestrel.contract import Book, Expected, Position, Snapshot, Step, Strategy, Trade
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.strategy import buckets, strategies_view, strategy_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
D = dt.date
EXPECTED = Expected(win_rate=66, avg_trade_pct=0.84, avg_win_pct=2.45, avg_loss_pct=-2.28, trades_per_month=3.1,
                    sd_trade_pct=3.0)


@pytest.fixture(scope="module")
def demo():
    return collect(DEMO_PROFILE, NOW)


def book(id_, money="real", strategy="s", started=D(2026, 7, 27), slots=None):
    return Book(id=id_, name="Test", money=money, strategy_id=strategy, status="running", started=started, value=1000,
                slots_total=slots)


def trade(book_id, ret, opened, closed=None, symbol="HD"):
    return Trade(book_id=book_id, symbol=symbol, opened=opened, closed=closed or opened, entry_price=100,
                 exit_price=100 * (1 + ret / 100), quantity=1, pnl=ret, return_pct=ret)


def snap(books=(), trades=(), expected=EXPECTED, steps=(), positions=()):
    return Snapshot(generated_at=NOW, books=list(books), trades=list(trades), positions=list(positions),
                    strategies=[Strategy(id="s", name="Test strategy", steps=list(steps), sizing="One lot each.",
                                         expected=expected, review_at_trades=30)])


def test_the_list_has_a_card_per_strategy_with_its_books(demo):
    cards = {c.id: c for c in strategies_view(demo, DEMO_PROFILE, NOW).strategies}
    assert list(cards) == ["rsi2", "ibs", "leader", "verticals"]
    rsi2 = cards["rsi2"]
    assert [(b.money, b.status, b.open) for b in rsi2.books] == [("real", "running", 4), ("paper", "running", 5)]
    assert (rsi2.book, rsi2.trades, rsi2.verdict) == ("real", 34, "in_band")
    assert rsi2.band_lo is not None and rsi2.band_lo < rsi2.per_trade_pct < rsi2.band_hi
    assert (cards["leader"].book, cards["leader"].verdict) == ("paper", "below")
    assert (cards["ibs"].trades, cards["ibs"].verdict) == (7, "early")


def test_the_primary_book_follows_the_requested_money(demo):
    real = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real")
    paper = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "paper")
    assert (real.primary, real.book, real.toggle) == ("rsi2-real", "real", True)
    assert (paper.primary, paper.book, paper.toggle) == ("rsi2-paper", "paper", True)
    ibs = strategy_view(demo, DEMO_PROFILE, NOW, "ibs", "real")  # no real book: the paper one, and no toggle
    assert (ibs.primary, ibs.book, ibs.toggle) == ("ibs-paper", "paper", False)


def test_an_unknown_strategy_has_no_view(demo):
    assert strategy_view(demo, DEMO_PROFILE, NOW, "nope", "real") is None


def test_the_book_with_most_closed_trades_wins_and_a_tie_goes_to_the_first_listed():
    two = [trade("b", 1, D(2026, 9, 1)), trade("b", 2, D(2026, 9, 2))]
    view = strategy_view(snap([book("a"), book("b")], [trade("a", 1, D(2026, 9, 1)), *two]), Profile(), NOW, "s")
    assert view.primary == "b"
    tie = strategy_view(snap([book("a"), book("b")], [trade("a", 1, D(2026, 9, 1)), two[0]]), Profile(), NOW, "s")
    assert tie.primary == "a"


def test_how_it_trades_passes_the_steps_and_sizing_through(demo):
    view = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real")
    assert [s.label for s in view.steps] == ["Universe", "Entry", "Protect", "Exit"]
    assert view.steps[2].params == ["−8% stop", "GTC"]
    assert view.sizing == "Each position is the account value ÷ 6, at most 5 open."
    assert view.expected is not None and view.expected.cagr_pct == 23.4


def test_buckets_are_one_point_wide_and_fold_the_ends():
    distribution = [float(i) for i in range(20)]
    out = buckets([-12, -9.5, -0.2, 0, 2.5, 9.99, 10, 15], distribution)
    assert [b.low for b in out] == list(range(-10, 10))
    counts = {b.low: b.count for b in out if b.count}
    assert counts == {-10: 2, -1: 1, 0: 1, 2: 1, 9: 3}
    assert out[0].share == 25.0 and out[19].expected == 19.0
    assert all(b.expected is None for b in buckets([1.0], [1.0, 2.0]))  # a distribution that isn't 20 buckets


def test_the_scorecard_and_the_other_book_on_demo_data(demo):
    view = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real")
    b = view.behaving
    real = [t.return_pct for t in demo.trades if t.book_id == "rsi2-real"]
    assert b.trades == 34 and sum(x.count for x in b.buckets) == 34 and b.review_at == 50
    rows = {r.key: r for r in b.scorecard}
    assert list(rows) == ["win_rate", "avg_trade", "avg_win", "avg_loss", "per_month"]
    assert [r.label for r in b.scorecard] == ["Win rate", "Average per trade", "Average win", "Average loss",
                                              "Trades per month"]
    assert rows["win_rate"].actual == round(sum(r > 0 for r in real) / 34 * 100, 1)
    assert rows["avg_trade"].actual == pytest.approx(fmean(real), abs=0.005)
    assert rows["avg_trade"].expected == 0.84 and rows["avg_trade"].status == "ok"
    assert all(r.status in {"ok", "above", "below"} for r in b.scorecard)
    paper = [t.return_pct for t in demo.trades if t.book_id == "rsi2-paper"]
    assert (b.other.money, b.other.trades) == ("paper", 71)
    assert b.other.per_trade_pct == pytest.approx(fmean(paper), abs=0.005)


def test_a_measure_outside_its_band_is_flagged_in_the_direction_it_is_off():
    trades = [trade("a", 1.0, D(2026, 8, 3) + dt.timedelta(days=i)) for i in range(20)]
    rows = {r.key: r for r in strategy_view(snap([book("a")], trades), Profile(), NOW, "s").behaving.scorecard}
    assert rows["win_rate"].status == "above"  # 100% against 66% ± 20.8 pts
    assert rows["avg_trade"].status == "ok"  # +1.0% inside 0.84 ± 1.31
    assert rows["avg_win"].status == "below"  # +1.0% under half of +2.45%
    assert (rows["avg_loss"].actual, rows["avg_loss"].status) == (None, "none")  # no losses to average
    assert rows["per_month"].status == "above"  # 20 trades in two months against 3.1 a month


def test_fewer_than_ten_closed_trades_is_too_early_to_judge():
    trades = [trade("a", -9.0, D(2026, 9, i)) for i in range(1, 6)]
    rows = strategy_view(snap([book("a")], trades), Profile(), NOW, "s").behaving.scorecard
    assert {r.status for r in rows} == {"early"}


def test_without_a_backtest_the_actual_figures_stand_alone():
    trades = [trade("a", 1.0 + i, D(2026, 9, 1) + dt.timedelta(days=i)) for i in range(12)]
    view = strategy_view(snap([book("a")], trades, expected=None), Profile(), NOW, "s")
    assert {r.status for r in view.behaving.scorecard} == {"none"}
    assert all(r.expected is None for r in view.behaving.scorecard)
    assert view.behaving.scorecard[0].actual == 100.0
    assert all(b.expected is None for b in view.behaving.buckets)
    assert view.funnel.expected is None and set(view.funnel.lo) == {None}


def test_the_running_mean_follows_close_order_and_the_band_narrows_from_trade_three():
    trades = [
        trade("a", 4.0, D(2026, 9, 1), D(2026, 9, 4), "LOW"),
        trade("a", 2.0, D(2026, 9, 1), D(2026, 9, 2), "HD"),
        trade("a", -3.0, D(2026, 8, 31), D(2026, 9, 4), "KO"),  # same close as LOW, opened earlier: first
        trade("a", 1.0, D(2026, 9, 7), D(2026, 9, 8), "HD"),
    ]
    funnel = strategy_view(snap([book("a")], trades), Profile(), NOW, "s").funnel
    assert funnel.lines[0].values == pytest.approx([2.0, -0.5, 1.0, 1.0])
    assert funnel.lo[:2] == [None, None] and funnel.hi[:2] == [None, None]
    assert funnel.lo[2] == pytest.approx(0.84 - 1.96 * 3 / 3 ** 0.5, abs=0.001)
    assert funnel.hi[3] - funnel.lo[3] < funnel.hi[2] - funnel.lo[2]


def test_the_demo_funnel_has_the_primary_book_first(demo):
    funnel = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "paper").funnel
    assert [(line.money, len(line.values)) for line in funnel.lines] == [("paper", 71), ("real", 34)]
    assert len(funnel.lo) == len(funnel.hi) == 71 and funnel.expected == 0.84


def test_a_strategy_with_no_books_still_describes_itself():
    view = strategy_view(snap(steps=[Step(label="Entry", title="Buy", text="On a signal")]), Profile(), NOW, "s")
    assert (view.primary, view.book, view.toggle, view.books) == (None, None, False, [])
    assert [s.title for s in view.steps] == ["Buy"] and view.sizing == "One lot each."
    assert view.behaving.trades == 0 and view.behaving.other is None
    assert view.funnel.lines == [] and view.funnel.lo == []


def test_open_positions_are_counted_on_the_chips():
    pos = Position(book_id="a", symbol="HD", quantity=1, entry_price=10, last_price=11, opened=D(2026, 9, 24))
    view = strategy_view(snap([book("a")], positions=[pos]), Profile(), NOW, "s")
    assert [(b.id, b.open, b.trades) for b in view.books] == [("a", 1, 0)]
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_strategy_view.py`
Expected: `ModuleNotFoundError: No module named 'kestrel.views.strategy'` (`1 error`).

- [ ] **Step 3: Implement**

`src/kestrel/views/strategy.py`:

````python
"""The Strategy pages, computed from one Snapshot: how does a strategy trade, and is it behaving the way its
backtest said it would?"""

from __future__ import annotations

import datetime as dt
import math
from statistics import fmean
from typing import Literal

from ..contract import Book, Expected, Money, Snapshot, Step, Trade
from ..metrics import expected_band
from ..profile import Profile
from .home import MIN_TRADES_FOR_VERDICT, View, _book_rows

BUCKET_LOW, BUCKETS = -10, 20  # 1-point buckets from -10% to +10%; returns beyond fold into the end buckets
FUNNEL_FROM = 3  # the expected band starts at the third trade
MONTH_DAYS = 365.25 / 12

Verdict = Literal["in_band", "below", "above", "early", "none"]
Status = Literal["ok", "above", "below", "early", "none"]


class BookChip(View):
    id: str
    name: str
    money: Money
    status: str
    open: int  # open positions
    trades: int  # closed trades


class StrategyCard(View):
    id: str
    name: str
    summary: str
    books: list[BookChip]
    book: Money | None  # the money of the book the band describes: real when there is one
    trades: int
    per_trade_pct: float | None
    band_lo: float | None
    band_hi: float | None
    verdict: Verdict


class StrategiesView(View):
    strategies: list[StrategyCard]


class Bucket(View):
    low: int  # returns from `low` up to low + 1 percent; the end buckets also hold everything beyond them
    count: int
    share: float  # percent of the book's closed trades
    expected: float | None  # the backtest's share, when it reports a 20-bucket distribution


class ScoreRow(View):
    key: Literal["win_rate", "avg_trade", "avg_win", "avg_loss", "per_month"]
    label: str
    actual: float | None
    expected: float | None
    status: Status  # "above" / "below": outside the band for that measure; "early": under 10 closed trades


class OtherBook(View):
    id: str
    money: Money
    trades: int
    per_trade_pct: float | None
    win_rate: float | None


class Behaving(View):
    trades: int
    buckets: list[Bucket]
    scorecard: list[ScoreRow]
    review_at: int | None
    other: OtherBook | None


class FunnelLine(View):
    book_id: str
    money: Money
    values: list[float]  # the running mean after each closed trade, in close order


class Funnel(View):
    expected: float | None
    lines: list[FunnelLine]  # the primary book first
    lo: list[float | None]  # the expected 95% band after trade n (index n - 1); None before trade 3
    hi: list[float | None]


class StrategyView(View):
    id: str
    name: str
    summary: str
    books: list[BookChip]
    book: Money | None  # the primary book's money
    primary: str | None  # the primary book's id
    toggle: bool  # a real and a paper book: the page offers Real | Paper
    expected: Expected | None
    steps: list[Step]
    sizing: str
    behaving: Behaving
    funnel: Funnel


def closed_trades(snapshot: Snapshot, book_id: str) -> list[Trade]:
    """A book's closed trades in close order; ties by opened date, then symbol."""
    return sorted((t for t in snapshot.trades if t.book_id == book_id), key=lambda t: (t.closed, t.opened, t.symbol))


def _pick(books: list[Book], money: Money, counts: dict[str, int]) -> Book | None:
    """The book of that money with the most closed trades; a tie goes to the first listed."""
    return max((b for b in books if b.money == money), key=lambda b: counts[b.id], default=None)


def _primary(books: list[Book], want: Money, counts: dict[str, int]) -> tuple[Book | None, Book | None]:
    """The book the page focuses on (the other money's book when there is none of the one asked for), and the best
    book of the other money."""
    primary = _pick(books, want, counts) or _pick(books, "paper" if want == "real" else "real", counts)
    if primary is None:
        return None, None
    return primary, _pick(books, "paper" if primary.money == "real" else "real", counts)


def _chips(snapshot: Snapshot, books: list[Book], counts: dict[str, int]) -> list[BookChip]:
    return [BookChip(id=b.id, name=b.name, money=b.money, status=b.status, trades=counts[b.id],
                     open=sum(1 for p in snapshot.positions if p.book_id == b.id)) for b in books]


def buckets(returns: list[float], distribution: list[float]) -> list[Bucket]:
    counts = [0] * BUCKETS
    for r in returns:
        counts[min(BUCKETS - 1, max(0, math.floor(r) - BUCKET_LOW))] += 1
    n = len(returns)
    expected = distribution if len(distribution) == BUCKETS else None
    return [Bucket(low=BUCKET_LOW + i, count=c, share=round(c / n * 100, 2) if n else 0.0,
                   expected=expected[i] if expected else None) for i, c in enumerate(counts)]


def _within_half(expected: float) -> tuple[float, float]:
    """The ±50% range around an expected value, low end first (for a negative value too)."""
    a, b = expected * 0.5, expected * 1.5
    return min(a, b), max(a, b)


def _row(key, label, actual: float | None, expected: float | None, band: tuple[float, float] | None,
         n: int) -> ScoreRow:
    if expected is None:
        status: Status = "none"
    elif n < MIN_TRADES_FOR_VERDICT:
        status = "early"
    elif actual is None or band is None:
        status = "none"
    else:
        status = "below" if actual < band[0] else "above" if actual > band[1] else "ok"
    return ScoreRow(key=key, label=label, actual=actual, expected=expected, status=status)


def _scorecard(trades: list[Trade], expected: Expected | None, book: Book | None, today: dt.date) -> list[ScoreRow]:
    returns = [t.return_pct for t in trades]
    n = len(returns)
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    months = max(1.0, (today - book.started).days / MONTH_DAYS) if book else 1.0
    win_rate = round(len(wins) / n * 100, 1) if n else None
    avg_trade = round(fmean(returns), 2) if n else None
    avg_win = round(fmean(wins), 2) if wins else None
    avg_loss = round(fmean(losses), 2) if losses else None
    per_month = round(n / months, 1) if n else None
    e = expected
    win_band = avg_band = None
    if e is not None and n:
        p = e.win_rate / 100
        half = 1.96 * math.sqrt(p * (1 - p) / n) * 100
        win_band = (e.win_rate - half, e.win_rate + half)
        avg_band = expected_band(e.avg_trade_pct, e.sd_trade_pct, n)
    return [
        _row("win_rate", "Win rate", win_rate, e.win_rate if e else None, win_band, n),
        _row("avg_trade", "Average per trade", avg_trade, e.avg_trade_pct if e else None, avg_band, n),
        _row("avg_win", "Average win", avg_win, e.avg_win_pct if e else None,
             _within_half(e.avg_win_pct) if e else None, n),
        _row("avg_loss", "Average loss", avg_loss, e.avg_loss_pct if e else None,
             _within_half(e.avg_loss_pct) if e else None, n),
        _row("per_month", "Trades per month", per_month, e.trades_per_month if e else None,
             _within_half(e.trades_per_month) if e else None, n),
    ]


def _other_book(book: Book | None, trades: list[Trade]) -> OtherBook | None:
    if book is None:
        return None
    returns = [t.return_pct for t in trades]
    return OtherBook(id=book.id, money=book.money, trades=len(returns),
                     per_trade_pct=round(fmean(returns), 2) if returns else None,
                     win_rate=round(sum(r > 0 for r in returns) / len(returns) * 100, 1) if returns else None)


def running_mean(trades: list[Trade]) -> list[float]:
    out: list[float] = []
    total = 0.0
    for n, t in enumerate(trades, 1):
        total += t.return_pct
        out.append(round(total / n, 3))
    return out


def _funnel(lines: list[FunnelLine], expected: Expected | None) -> Funnel:
    n = max((len(line.values) for line in lines), default=0)
    lo: list[float | None] = []
    hi: list[float | None] = []
    for k in range(1, n + 1):
        if expected is None or k < FUNNEL_FROM:
            lo.append(None)
            hi.append(None)
        else:
            low, high = expected_band(expected.avg_trade_pct, expected.sd_trade_pct, k)
            lo.append(round(low, 3))
            hi.append(round(high, 3))
    return Funnel(expected=expected.avg_trade_pct if expected else None, lines=lines, lo=lo, hi=hi)


def strategies_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> StrategiesView:
    rows = {r.id: r for r in _book_rows(snapshot)}
    counts = {b.id: rows[b.id].trades for b in snapshot.books}
    cards = []
    for s in snapshot.strategies:
        books = [b for b in snapshot.books if b.strategy_id == s.id]
        primary, _ = _primary(books, "real", counts)
        row = rows[primary.id] if primary else None
        cards.append(StrategyCard(
            id=s.id, name=s.name, summary=s.summary, books=_chips(snapshot, books, counts),
            book=primary.money if primary else None, trades=row.trades if row else 0,
            per_trade_pct=row.per_trade_pct if row else None, band_lo=row.band_lo if row else None,
            band_hi=row.band_hi if row else None, verdict=row.verdict if row else "none",
        ))
    return StrategiesView(strategies=cards)


def strategy_view(snapshot: Snapshot, profile: Profile, now: dt.datetime, strategy_id: str,
                  book: Money = "real") -> StrategyView | None:
    """One strategy, focused on its `book` money (the other money's book when it has none). None when unknown."""
    strategy = next((s for s in snapshot.strategies if s.id == strategy_id), None)
    if strategy is None:
        return None
    today = now.astimezone(profile.tz).date()
    books = [b for b in snapshot.books if b.strategy_id == strategy.id]
    closed = {b.id: closed_trades(snapshot, b.id) for b in books}
    counts = {b_id: len(trades) for b_id, trades in closed.items()}
    primary, other = _primary(books, book, counts)
    mine = closed[primary.id] if primary else []
    expected = strategy.expected
    lines = [FunnelLine(book_id=b.id, money=b.money, values=running_mean(closed[b.id]))
             for b in (primary, other) if b is not None and closed[b.id]]
    return StrategyView(
        id=strategy.id, name=strategy.name, summary=strategy.summary, books=_chips(snapshot, books, counts),
        book=primary.money if primary else None, primary=primary.id if primary else None,
        toggle={b.money for b in books} == {"real", "paper"}, expected=expected, steps=list(strategy.steps),
        sizing=strategy.sizing,
        behaving=Behaving(
            trades=len(mine), buckets=buckets([t.return_pct for t in mine], expected.distribution if expected else []),
            scorecard=_scorecard(mine, expected, primary, today), review_at=strategy.review_at_trades,
            other=_other_book(other, closed[other.id] if other else []),
        ),
        funnel=_funnel(lines, expected),
    )
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `113 passed` (`test_strategy_view.py` 14); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/views/strategy.py tests/test_strategy_view.py
git commit -m "feat(views): strategy list and page, part 1: primary book, steps, scorecard, buckets and funnel"
```

---

### Task 5: The strategy views, part 2: the money at work, trade anatomy, worth, month by month, all trades

**Files:**
- Modify (replace the whole file): `src/kestrel/views/strategy.py`
- Test: `tests/test_strategy_sections.py`

**Interfaces:**
- Consumes: Task 4's module; `growth_index`, `max_drawdown_pct`, `sum_series` from `metrics`; `Bar`, `Indicator`, `TradeChart`, `WatchItem` (Task 2).
- Produces (added to `views/strategy.py`; `StrategyView` gains `slots`, `anatomy`, `worth`, `monthly`, `trades`):
  - `Slots(book_id, total: int | None, days: list[date], used: list[int], avg_used: float | None, working_pct: float | None, idle: int, watch: list[WatchItem])`
  - `RecentTrade(key: "book_id|symbol|opened", symbol, money, opened, closed, return_pct, r_multiple, exit_reason, sessions: int, chart: bool)`; `AnatomyChart(key, bars, indicator, stop, entry: int, exit: int, entry_price, exit_price)`; `Anatomy(recent, charts, selected: str | None)`
  - `WorthPoint(key: "backtest" | "book" | "long_term" | "benchmark", label, period, early: bool, return_pct, drop_pct)` (drop is a positive magnitude); `Worth(points)`
  - `Month(month: "YYYY-MM", book, long_term: float | None, ahead: bool | None)`; `MonthFigure(month, value)`; `Monthly(months, ahead, compared, best, worst)`
  - `TradeRow(symbol, money, opened, closed, days_held: int, return_pct, r_multiple, pnl, exit_reason)`
  - `yearly(points) -> tuple[float, float, int] | None` (yearly return %, worst drop %, days; `None` under 90 days); `monthly_returns(points) -> dict[str, float]`
- Rules (spec §2.2, §3.2): slots over the last 40 sessions of the book's history (weekdays when it has none); a trade holds a slot from its open date through its close date, an open position from its open date on. Recent trades are the last 8, newest first; a chart counts only when its bars include the open date. Yearly figures annualize as index^(365/days) − 1; 90–364 days is "early"; under 90 days is omitted. Monthly returns chain month-end growth-index values over the last 12 calendar months.

- [ ] **Step 1: Write the failing tests**

`tests/test_strategy_sections.py`:

````python
"""The Strategy page's later sections: where the money works, trade anatomy, is it worth it, month by month and
all trades."""

import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import (
    Account,
    Bar,
    Benchmark,
    Book,
    Expected,
    Position,
    Series,
    Snapshot,
    Strategy,
    Trade,
    TradeChart,
    ValuePoint,
    WatchItem,
)
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.strategy import strategy_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)  # a Friday
D = dt.date


@pytest.fixture(scope="module")
def demo():
    return collect(DEMO_PROFILE, NOW)


def book(slots=3, started=D(2025, 9, 1)):
    return Book(id="a", name="Test", money="real", strategy_id="s", status="running", started=started, value=1000,
                slots_total=slots)


def trade(opened, closed, ret=1.0, symbol="HD"):
    return Trade(book_id="a", symbol=symbol, opened=opened, closed=closed, entry_price=100,
                 exit_price=100 * (1 + ret / 100), quantity=1, pnl=ret, return_pct=ret)


def bars(days, price=100.0):
    return [Bar(date=d, open=price, high=price + 1, low=price - 1, close=price) for d in days]


def view(**parts):
    strategy = Strategy(id="s", name="Test", watch=parts.pop("watch", []), expected=parts.pop("expected", None))
    books = parts.pop("books", [book()])
    return strategy_view(Snapshot(generated_at=NOW, books=books, strategies=[strategy], **parts), Profile(), NOW, "s")


def week(start, n):
    return [start + dt.timedelta(days=i) for i in range(n)]


def test_slots_count_a_trade_through_its_close_and_a_position_to_the_last_session():
    days = week(D(2026, 9, 21), 5)  # Monday to Friday
    history = [Series(id="a", points=[ValuePoint(date=d, value=1000) for d in days])]
    trades = [trade(days[0], days[1]), trade(days[1], days[3], symbol="LOW")]
    pos = Position(book_id="a", symbol="KO", quantity=1, entry_price=10, last_price=10, opened=days[3])
    slots = view(book_history=history, trades=trades, positions=[pos]).slots
    assert slots.days == days and slots.used == [1, 2, 1, 2, 1]
    assert (slots.total, slots.avg_used, slots.working_pct, slots.idle) == (3, 1.4, 46.7, 0)


def test_slots_fall_back_to_weekdays_without_history_and_count_idle_sessions():
    slots = view().slots
    assert len(slots.days) == 40 and slots.days[-1] == D(2026, 9, 25)
    assert all(d.weekday() < 5 for d in slots.days)
    assert set(slots.used) == {0} and slots.idle == 40 and slots.working_pct == 0.0


def test_a_book_without_slots_says_so_and_still_lists_the_watch():
    watch = [WatchItem(symbol="KO", label="RSI(2)", value=12.4)]
    slots = view(books=[book(slots=None)], watch=watch).slots
    assert slots.total is None and slots.days == [] and slots.avg_used is None
    assert [w.symbol for w in slots.watch] == ["KO"]


def test_the_demo_slots_and_watch_list(demo):
    rsi2 = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real").slots
    assert (rsi2.book_id, rsi2.total, len(rsi2.days), rsi2.days[-1]) == ("rsi2-real", 5, 40, D(2026, 9, 25))
    assert rsi2.used[-1] == 4  # the four open positions
    assert [w.symbol for w in rsi2.watch] == ["KO", "ABT", "UNP"]
    assert strategy_view(demo, DEMO_PROFILE, NOW, "ibs", "real").slots.watch == []


def test_anatomy_lists_the_last_eight_trades_newest_first_and_selects_the_newest_chart(demo):
    a = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real").anatomy
    assert len(a.recent) == 8 and all(r.chart for r in a.recent)
    closes = [r.closed for r in a.recent]
    assert closes == sorted(closes, reverse=True)
    assert a.selected == a.recent[0].key and len(a.charts) == 8
    chart = next(c for c in a.charts if c.key == a.selected)
    assert chart.bars[chart.entry].open == chart.entry_price and chart.entry < chart.exit
    assert chart.indicator is not None and chart.stop == pytest.approx(chart.entry_price * 0.92, abs=0.01)


def test_a_chart_that_matches_no_trade_misses_the_open_day_or_has_a_backwards_trade_is_ignored():
    days = week(D(2026, 9, 14), 12)
    a = trade(days[1], days[3], symbol="HD")
    b = trade(days[4], days[6], symbol="LOW")
    c = trade(days[7], days[9], symbol="KO")
    d = trade(days[11], days[10], symbol="PG")  # closes before it opens: a source's bug, not a crash
    charts = [
        TradeChart(book_id="a", symbol="HD", opened=days[1], bars=bars(days)),
        TradeChart(book_id="a", symbol="LOW", opened=days[4], bars=bars(days[5:])),  # the open day is missing
        TradeChart(book_id="a", symbol="MRK", opened=days[2], bars=bars(days)),  # no such trade
        TradeChart(book_id="a", symbol="PG", opened=days[11], bars=bars(days[11:])),
    ]
    anatomy = view(trades=[a, b, c, d], trade_charts=charts).anatomy
    assert [(r.symbol, r.chart) for r in anatomy.recent] == [
        ("PG", False), ("KO", False), ("LOW", False), ("HD", True)]
    assert [ch.key for ch in anatomy.charts] == [anatomy.selected] == ["a|HD|2026-09-15"]


def test_sessions_held_count_weekdays_after_the_open_and_days_held_count_the_calendar():
    t = trade(D(2026, 9, 18), D(2026, 9, 22))  # Friday to Tuesday
    same_day = trade(D(2026, 9, 23), D(2026, 9, 23), symbol="KO")
    v = view(trades=[t, same_day])
    assert [(r.symbol, r.sessions) for r in v.anatomy.recent] == [("KO", 0), ("HD", 2)]
    assert [(r.symbol, r.days_held) for r in v.trades] == [("KO", 0), ("HD", 4)]


def line(start, days, end_value, drop_at=None):
    """A value series from 100 to `end_value` over `days` calendar days, with an optional 10% dip."""
    points = [ValuePoint(date=start, value=100.0)]
    for i in range(1, days + 1):
        value = 100 + (end_value - 100) * i / days
        points.append(ValuePoint(date=start + dt.timedelta(days=i), value=value * (0.9 if i == drop_at else 1)))
    return points


def test_worth_annualizes_a_year_or_more_marks_a_shorter_history_early_and_skips_under_ninety_days():
    year = view(book_history=[Series(id="a", points=line(D(2025, 9, 25), 365, 110))]).worth.points
    assert [(p.key, p.label, p.early, p.period) for p in year] == [("book", "Real book", False, "12 months")]
    assert year[0].return_pct == pytest.approx(10.0) and str(year[0].drop_pct) == "0.0"  # never "-0.0"
    half = view(book_history=[Series(id="a", points=line(D(2026, 3, 1), 200, 105, drop_at=50))]).worth.points
    assert half[0].early and half[0].period == "7 months"
    assert half[0].return_pct == pytest.approx((1.05 ** (365 / 200) - 1) * 100, abs=0.01)
    assert half[0].drop_pct == pytest.approx(10.0, abs=0.05)  # the one-day 10% dip, net of that day's drift
    assert view(book_history=[Series(id="a", points=line(D(2026, 8, 1), 60, 104))]).worth.points == []


def test_worth_adds_the_backtest_long_term_accounts_and_benchmark_when_they_exist():
    expected = Expected(win_rate=60, avg_trade_pct=1, avg_win_pct=2, avg_loss_pct=-1, trades_per_month=2,
                        sd_trade_pct=2, window="2006–2020", cagr_pct=23.4, max_drawdown_pct=-11.7)
    lt = line(D(2021, 9, 25), 1826, 160)
    accounts = [Account(id="ira", name="IRA", category="long_term", value=160, as_of=NOW)]
    points = view(books=[], expected=expected, accounts=accounts, account_history=[Series(id="ira", points=lt)],
                  benchmark=Benchmark(symbol="SPY", label="S&P 500", points=lt)).worth.points
    assert [(p.key, p.label, p.period) for p in points] == [
        ("backtest", "Backtest", "2006–2020"), ("long_term", "Long-term accounts", "5 years"),
        ("benchmark", "S&P 500", "5 years")]
    assert (points[0].return_pct, points[0].drop_pct) == (23.4, 11.7)


def test_the_demo_worth_points(demo):
    points = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real").worth.points
    assert [p.key for p in points] == ["backtest", "book", "long_term", "benchmark"]
    assert (points[1].label, points[1].period, points[1].early) == ("Real book", "12 months", False)
    assert all(p.drop_pct >= 0 for p in points)


def test_monthly_returns_chain_month_ends_over_the_last_twelve_months():
    book_points = [ValuePoint(date=d, value=v) for d, v in [
        (D(2026, 7, 15), 100), (D(2026, 7, 31), 110), (D(2026, 8, 31), 121), (D(2026, 9, 25), 108.9)]]
    lt_points = [ValuePoint(date=d, value=v) for d, v in [
        (D(2026, 7, 15), 100), (D(2026, 7, 31), 101), (D(2026, 8, 31), 102.01), (D(2026, 9, 25), 103.03)]]
    accounts = [Account(id="ira", name="IRA", category="long_term", value=103.03, as_of=NOW)]
    m = view(book_history=[Series(id="a", points=book_points)], accounts=accounts,
             account_history=[Series(id="ira", points=lt_points)]).monthly
    assert [x.month for x in m.months] == [f"2025-{k}" for k in ("10", "11", "12")] + [
        f"2026-{k:02d}" for k in range(1, 10)]
    tail = [(x.month, x.book, x.long_term, x.ahead) for x in m.months[-3:]]
    assert tail == [("2026-07", 10.0, 1.0, True), ("2026-08", 10.0, 1.0, True), ("2026-09", -10.0, 1.0, False)]
    assert m.months[0].book is None and m.months[0].ahead is None
    assert (m.ahead, m.compared) == (2, 3)
    assert (m.best.month, m.best.value, m.worst.month, m.worst.value) == ("2026-07", 10.0, "2026-09", -10.0)


def test_the_demo_monthly_grid(demo):
    m = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "real").monthly
    assert (m.months[0].month, m.months[-1].month, m.compared) == ("2025-10", "2026-09", 12)
    assert m.ahead == sum(1 for x in m.months if x.ahead)
    assert m.best.value == max(x.book for x in m.months)


def test_all_trades_are_the_primary_books_newest_first(demo):
    trades = strategy_view(demo, DEMO_PROFILE, NOW, "rsi2", "paper").trades
    assert len(trades) == 71 and {t.money for t in trades} == {"paper"}
    assert trades[0].closed >= trades[-1].closed
    assert trades[0].days_held == (trades[0].closed - trades[0].opened).days


def test_a_book_with_no_trades_leaves_those_sections_empty():
    v = view()
    assert (v.anatomy.recent, v.anatomy.charts, v.anatomy.selected, v.trades) == ([], [], None, [])
    assert v.monthly.compared == 0 and v.monthly.best is None
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_strategy_sections.py`
Expected: `14 failed`, each `AttributeError: 'StrategyView' object has no attribute …` (`slots`, `anatomy`, `worth`, `monthly` or `trades`).

- [ ] **Step 3: Implement (replace the whole file)**

`src/kestrel/views/strategy.py`:

````python
"""The Strategy pages, computed from one Snapshot: how does a strategy trade, and is it behaving the way its
backtest said it would?"""

from __future__ import annotations

import datetime as dt
import math
from statistics import fmean
from typing import Literal

from ..contract import Bar, Book, Expected, Indicator, Money, Snapshot, Step, Trade, TradeChart, ValuePoint, WatchItem
from ..metrics import expected_band, growth_index, max_drawdown_pct, sum_series
from ..profile import Profile
from .home import MIN_TRADES_FOR_VERDICT, View, _book_rows

BUCKET_LOW, BUCKETS = -10, 20  # 1-point buckets from -10% to +10%; returns beyond fold into the end buckets
FUNNEL_FROM = 3  # the expected band starts at the third trade
MONTH_DAYS = 365.25 / 12
SESSIONS = 40  # "Where the money works" looks at the last 40 sessions
RECENT = 8  # trades listed beside the anatomy chart
MONTHS = 12
YEAR_DAYS, EARLY_DAYS = 365, 90  # a yearly figure needs 90 days of history; under a year it is "early"

Verdict = Literal["in_band", "below", "above", "early", "none"]
Status = Literal["ok", "above", "below", "early", "none"]


class BookChip(View):
    id: str
    name: str
    money: Money
    status: str
    open: int  # open positions
    trades: int  # closed trades


class StrategyCard(View):
    id: str
    name: str
    summary: str
    books: list[BookChip]
    book: Money | None  # the money of the book the band describes: real when there is one
    trades: int
    per_trade_pct: float | None
    band_lo: float | None
    band_hi: float | None
    verdict: Verdict


class StrategiesView(View):
    strategies: list[StrategyCard]


class Bucket(View):
    low: int  # returns from `low` up to low + 1 percent; the end buckets also hold everything beyond them
    count: int
    share: float  # percent of the book's closed trades
    expected: float | None  # the backtest's share, when it reports a 20-bucket distribution


class ScoreRow(View):
    key: Literal["win_rate", "avg_trade", "avg_win", "avg_loss", "per_month"]
    label: str
    actual: float | None
    expected: float | None
    status: Status  # "above" / "below": outside the band for that measure; "early": under 10 closed trades


class OtherBook(View):
    id: str
    money: Money
    trades: int
    per_trade_pct: float | None
    win_rate: float | None


class Behaving(View):
    trades: int
    buckets: list[Bucket]
    scorecard: list[ScoreRow]
    review_at: int | None
    other: OtherBook | None


class FunnelLine(View):
    book_id: str
    money: Money
    values: list[float]  # the running mean after each closed trade, in close order


class Funnel(View):
    expected: float | None
    lines: list[FunnelLine]  # the primary book first
    lo: list[float | None]  # the expected 95% band after trade n (index n - 1); None before trade 3
    hi: list[float | None]


class Slots(View):
    book_id: str | None
    total: int | None  # the book's slots; None when it doesn't report them
    days: list[dt.date]  # the last 40 sessions
    used: list[int]  # slots in use each session
    avg_used: float | None
    working_pct: float | None  # the average in use as a share of the slots
    idle: int  # sessions with nothing in use
    watch: list[WatchItem]


class RecentTrade(View):
    key: str  # "book_id|symbol|opened": how the page picks a trade's chart
    symbol: str
    money: Money
    opened: dt.date
    closed: dt.date
    return_pct: float
    r_multiple: float | None
    exit_reason: str
    sessions: int  # sessions held: the weekdays after the open day, up to and including the close
    chart: bool


class AnatomyChart(View):
    key: str
    bars: list[Bar]
    indicator: Indicator | None
    stop: float | None
    entry: int  # index of the entry bar
    exit: int  # index of the exit bar
    entry_price: float
    exit_price: float


class Anatomy(View):
    recent: list[RecentTrade]  # the primary book's last 8 closed trades, newest first
    charts: list[AnatomyChart]  # for the recent trades that have one
    selected: str | None  # the newest charted trade


class WorthPoint(View):
    key: Literal["backtest", "book", "long_term", "benchmark"]
    label: str
    period: str  # "2006–2020" for a backtest, "12 months" or "5 years" for a history
    early: bool  # 90 to 364 days of history: annualized, but early
    return_pct: float  # yearly return
    drop_pct: float  # worst drop, as a positive magnitude


class Worth(View):
    points: list[WorthPoint]


class Month(View):
    month: str  # "2026-09"
    book: float | None  # the primary book's return that month, in percent
    long_term: float | None
    ahead: bool | None  # the book did better than the long-term accounts


class MonthFigure(View):
    month: str
    value: float


class Monthly(View):
    months: list[Month]  # the last 12 calendar months, oldest first
    ahead: int
    compared: int  # months with both figures
    best: MonthFigure | None
    worst: MonthFigure | None


class TradeRow(View):
    symbol: str
    money: Money
    opened: dt.date
    closed: dt.date
    days_held: int  # calendar days
    return_pct: float
    r_multiple: float | None
    pnl: float
    exit_reason: str


class StrategyView(View):
    id: str
    name: str
    summary: str
    books: list[BookChip]
    book: Money | None  # the primary book's money
    primary: str | None  # the primary book's id
    toggle: bool  # a real and a paper book: the page offers Real | Paper
    expected: Expected | None
    steps: list[Step]
    sizing: str
    behaving: Behaving
    funnel: Funnel
    slots: Slots
    anatomy: Anatomy
    worth: Worth
    monthly: Monthly
    trades: list[TradeRow]  # the primary book's closed trades, newest first


def closed_trades(snapshot: Snapshot, book_id: str) -> list[Trade]:
    """A book's closed trades in close order; ties by opened date, then symbol."""
    return sorted((t for t in snapshot.trades if t.book_id == book_id), key=lambda t: (t.closed, t.opened, t.symbol))


def _pick(books: list[Book], money: Money, counts: dict[str, int]) -> Book | None:
    """The book of that money with the most closed trades; a tie goes to the first listed."""
    return max((b for b in books if b.money == money), key=lambda b: counts[b.id], default=None)


def _primary(books: list[Book], want: Money, counts: dict[str, int]) -> tuple[Book | None, Book | None]:
    """The book the page focuses on (the other money's book when there is none of the one asked for), and the best
    book of the other money."""
    primary = _pick(books, want, counts) or _pick(books, "paper" if want == "real" else "real", counts)
    if primary is None:
        return None, None
    return primary, _pick(books, "paper" if primary.money == "real" else "real", counts)


def _chips(snapshot: Snapshot, books: list[Book], counts: dict[str, int]) -> list[BookChip]:
    return [BookChip(id=b.id, name=b.name, money=b.money, status=b.status, trades=counts[b.id],
                     open=sum(1 for p in snapshot.positions if p.book_id == b.id)) for b in books]


def buckets(returns: list[float], distribution: list[float]) -> list[Bucket]:
    counts = [0] * BUCKETS
    for r in returns:
        counts[min(BUCKETS - 1, max(0, math.floor(r) - BUCKET_LOW))] += 1
    n = len(returns)
    expected = distribution if len(distribution) == BUCKETS else None
    return [Bucket(low=BUCKET_LOW + i, count=c, share=round(c / n * 100, 2) if n else 0.0,
                   expected=expected[i] if expected else None) for i, c in enumerate(counts)]


def _within_half(expected: float) -> tuple[float, float]:
    """The ±50% range around an expected value, low end first (for a negative value too)."""
    a, b = expected * 0.5, expected * 1.5
    return min(a, b), max(a, b)


def _row(key, label, actual: float | None, expected: float | None, band: tuple[float, float] | None,
         n: int) -> ScoreRow:
    if expected is None:
        status: Status = "none"
    elif n < MIN_TRADES_FOR_VERDICT:
        status = "early"
    elif actual is None or band is None:
        status = "none"
    else:
        status = "below" if actual < band[0] else "above" if actual > band[1] else "ok"
    return ScoreRow(key=key, label=label, actual=actual, expected=expected, status=status)


def _scorecard(trades: list[Trade], expected: Expected | None, book: Book | None, today: dt.date) -> list[ScoreRow]:
    returns = [t.return_pct for t in trades]
    n = len(returns)
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    months = max(1.0, (today - book.started).days / MONTH_DAYS) if book else 1.0
    win_rate = round(len(wins) / n * 100, 1) if n else None
    avg_trade = round(fmean(returns), 2) if n else None
    avg_win = round(fmean(wins), 2) if wins else None
    avg_loss = round(fmean(losses), 2) if losses else None
    per_month = round(n / months, 1) if n else None
    e = expected
    win_band = avg_band = None
    if e is not None and n:
        p = e.win_rate / 100
        half = 1.96 * math.sqrt(p * (1 - p) / n) * 100
        win_band = (e.win_rate - half, e.win_rate + half)
        avg_band = expected_band(e.avg_trade_pct, e.sd_trade_pct, n)
    return [
        _row("win_rate", "Win rate", win_rate, e.win_rate if e else None, win_band, n),
        _row("avg_trade", "Average per trade", avg_trade, e.avg_trade_pct if e else None, avg_band, n),
        _row("avg_win", "Average win", avg_win, e.avg_win_pct if e else None,
             _within_half(e.avg_win_pct) if e else None, n),
        _row("avg_loss", "Average loss", avg_loss, e.avg_loss_pct if e else None,
             _within_half(e.avg_loss_pct) if e else None, n),
        _row("per_month", "Trades per month", per_month, e.trades_per_month if e else None,
             _within_half(e.trades_per_month) if e else None, n),
    ]


def _other_book(book: Book | None, trades: list[Trade]) -> OtherBook | None:
    if book is None:
        return None
    returns = [t.return_pct for t in trades]
    return OtherBook(id=book.id, money=book.money, trades=len(returns),
                     per_trade_pct=round(fmean(returns), 2) if returns else None,
                     win_rate=round(sum(r > 0 for r in returns) / len(returns) * 100, 1) if returns else None)


def running_mean(trades: list[Trade]) -> list[float]:
    out: list[float] = []
    total = 0.0
    for n, t in enumerate(trades, 1):
        total += t.return_pct
        out.append(round(total / n, 3))
    return out


def _funnel(lines: list[FunnelLine], expected: Expected | None) -> Funnel:
    n = max((len(line.values) for line in lines), default=0)
    lo: list[float | None] = []
    hi: list[float | None] = []
    for k in range(1, n + 1):
        if expected is None or k < FUNNEL_FROM:
            lo.append(None)
            hi.append(None)
        else:
            low, high = expected_band(expected.avg_trade_pct, expected.sd_trade_pct, k)
            lo.append(round(low, 3))
            hi.append(round(high, 3))
    return Funnel(expected=expected.avg_trade_pct if expected else None, lines=lines, lo=lo, hi=hi)


def _weekdays_ending(end: dt.date, count: int) -> list[dt.date]:
    days: list[dt.date] = []
    day = end
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= dt.timedelta(days=1)
    return days[::-1]


def _history(snapshot: Snapshot, book_id: str) -> list[ValuePoint]:
    return list(next((s.points for s in snapshot.book_history if s.id == book_id), []))


def _slots(snapshot: Snapshot, book: Book | None, trades: list[Trade], watch: list[WatchItem],
           today: dt.date) -> Slots:
    if book is None or book.slots_total is None:
        return Slots(book_id=book.id if book else None, total=None, days=[], used=[], avg_used=None,
                     working_pct=None, idle=0, watch=watch)
    days = sorted({p.date for p in _history(snapshot, book.id)})[-SESSIONS:] or _weekdays_ending(today, SESSIONS)
    opened = [p.opened for p in snapshot.positions if p.book_id == book.id]
    used = [sum(1 for t in trades if t.opened <= d <= t.closed) + sum(1 for o in opened if o <= d) for d in days]
    avg = fmean(used)
    return Slots(book_id=book.id, total=book.slots_total, days=days, used=used, avg_used=round(avg, 1),
                 working_pct=round(avg / book.slots_total * 100, 1) if book.slots_total else None,
                 idle=sum(1 for u in used if u == 0), watch=watch)


def _key(book_id: str, symbol: str, opened: dt.date) -> str:
    return f"{book_id}|{symbol}|{opened.isoformat()}"


def _sessions_held(opened: dt.date, closed: dt.date) -> int:
    return sum(1 for i in range(1, (closed - opened).days + 1) if (opened + dt.timedelta(days=i)).weekday() < 5)


def _anatomy_chart(chart: TradeChart, trade: Trade) -> AnatomyChart | None:
    dates = [b.date for b in chart.bars]
    if trade.opened not in dates or trade.closed < trade.opened:
        return None  # a chart that doesn't show the entry, or a trade that closes before it opens, can't be drawn
    entry = dates.index(trade.opened)
    exit_ = max(i for i, d in enumerate(dates) if d <= trade.closed)
    return AnatomyChart(key=_key(trade.book_id, trade.symbol, trade.opened), bars=list(chart.bars),
                        indicator=chart.indicator, stop=chart.stop, entry=entry, exit=exit_,
                        entry_price=trade.entry_price, exit_price=trade.exit_price)


def _anatomy(snapshot: Snapshot, book: Book | None, trades: list[Trade]) -> Anatomy:
    if book is None:
        return Anatomy(recent=[], charts=[], selected=None)
    by_key = {(c.book_id, c.symbol, c.opened): c for c in snapshot.trade_charts}
    recent: list[RecentTrade] = []
    charts: list[AnatomyChart] = []
    for t in trades[-RECENT:][::-1]:
        found = by_key.get((t.book_id, t.symbol, t.opened))
        chart = _anatomy_chart(found, t) if found else None
        if chart:
            charts.append(chart)
        recent.append(RecentTrade(key=_key(t.book_id, t.symbol, t.opened), symbol=t.symbol, money=book.money,
                                  opened=t.opened, closed=t.closed, return_pct=t.return_pct, r_multiple=t.r_multiple,
                                  exit_reason=t.exit_reason, sessions=_sessions_held(t.opened, t.closed),
                                  chart=chart is not None))
    return Anatomy(recent=recent, charts=charts, selected=charts[0].key if charts else None)


def _period(days: int) -> str:
    months = round(days / MONTH_DAYS)
    if months >= 24:
        return f"{round(days / 365.25)} years"
    return f"{months} month" if months == 1 else f"{months} months"


def yearly(points: list[ValuePoint]) -> tuple[float, float, int] | None:
    """(yearly return %, worst drop % as a positive magnitude, days spanned), or None under 90 days of history."""
    if len(points) < 2:
        return None
    days = (points[-1].date - points[0].date).days
    index = growth_index(points)
    if days < EARLY_DAYS or index[-1] <= 0:
        return None
    return (index[-1] ** (365 / days) - 1) * 100, abs(max_drawdown_pct(index)), days


def _long_term(snapshot: Snapshot) -> list[ValuePoint]:
    history = {s.id: s.points for s in snapshot.account_history}
    return sum_series([history[a.id] for a in snapshot.accounts if a.category == "long_term" and a.id in history])


def _worth(snapshot: Snapshot, profile: Profile, book: Book | None, expected: Expected | None) -> Worth:
    points: list[WorthPoint] = []
    if expected is not None and expected.cagr_pct is not None and expected.max_drawdown_pct is not None:
        points.append(WorthPoint(key="backtest", label="Backtest", period=expected.window, early=False,
                                 return_pct=expected.cagr_pct, drop_pct=abs(expected.max_drawdown_pct)))
    bench = snapshot.benchmark
    lines = [
        ("book", f"{book.money.capitalize()} book" if book else "", _history(snapshot, book.id) if book else []),
        ("long_term", "Long-term accounts", _long_term(snapshot)),
        ("benchmark", bench.label if bench else profile.benchmark.label, list(bench.points) if bench else []),
    ]
    for key, label, history in lines:
        figure = yearly(history)
        if figure is not None:
            ret, drop, days = figure
            points.append(WorthPoint(key=key, label=label, period=_period(days), early=days < YEAR_DAYS,
                                     return_pct=round(ret, 2), drop_pct=round(drop, 2)))
    return Worth(points=points)


def monthly_returns(points: list[ValuePoint]) -> dict[str, float]:
    """Each month's return in percent: its last growth-index value over the month before's (the first month runs
    from the first point)."""
    ends: dict[str, float] = {}
    for p, value in zip(points, growth_index(points)):
        ends[p.date.strftime("%Y-%m")] = value
    out: dict[str, float] = {}
    base = 1.0
    for month in sorted(ends):
        out[month] = round((ends[month] / base - 1) * 100, 2) if base > 0 else 0.0
        base = ends[month]
    return out


def _last_months(today: dt.date) -> list[str]:
    year, month = today.year, today.month
    out = []
    for _ in range(MONTHS):
        out.append(f"{year:04d}-{month:02d}")
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return out[::-1]


def _monthly(snapshot: Snapshot, book: Book | None, today: dt.date) -> Monthly:
    mine = monthly_returns(_history(snapshot, book.id)) if book else {}
    theirs = monthly_returns(_long_term(snapshot))
    months = []
    for m in _last_months(today):
        a, b = mine.get(m), theirs.get(m)
        months.append(Month(month=m, book=a, long_term=b, ahead=a > b if a is not None and b is not None else None))
    shown = [MonthFigure(month=m.month, value=m.book) for m in months if m.book is not None]
    return Monthly(months=months, ahead=sum(1 for m in months if m.ahead),
                   compared=sum(1 for m in months if m.ahead is not None),
                   best=max(shown, key=lambda f: f.value, default=None),
                   worst=min(shown, key=lambda f: f.value, default=None))


def strategies_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> StrategiesView:
    rows = {r.id: r for r in _book_rows(snapshot)}
    counts = {b.id: rows[b.id].trades for b in snapshot.books}
    cards = []
    for s in snapshot.strategies:
        books = [b for b in snapshot.books if b.strategy_id == s.id]
        primary, _ = _primary(books, "real", counts)
        row = rows[primary.id] if primary else None
        cards.append(StrategyCard(
            id=s.id, name=s.name, summary=s.summary, books=_chips(snapshot, books, counts),
            book=primary.money if primary else None, trades=row.trades if row else 0,
            per_trade_pct=row.per_trade_pct if row else None, band_lo=row.band_lo if row else None,
            band_hi=row.band_hi if row else None, verdict=row.verdict if row else "none",
        ))
    return StrategiesView(strategies=cards)


def strategy_view(snapshot: Snapshot, profile: Profile, now: dt.datetime, strategy_id: str,
                  book: Money = "real") -> StrategyView | None:
    """One strategy, focused on its `book` money (the other money's book when it has none). None when unknown."""
    strategy = next((s for s in snapshot.strategies if s.id == strategy_id), None)
    if strategy is None:
        return None
    today = now.astimezone(profile.tz).date()
    books = [b for b in snapshot.books if b.strategy_id == strategy.id]
    closed = {b.id: closed_trades(snapshot, b.id) for b in books}
    counts = {b_id: len(trades) for b_id, trades in closed.items()}
    primary, other = _primary(books, book, counts)
    mine = closed[primary.id] if primary else []
    expected = strategy.expected
    lines = [FunnelLine(book_id=b.id, money=b.money, values=running_mean(closed[b.id]))
             for b in (primary, other) if b is not None and closed[b.id]]
    return StrategyView(
        id=strategy.id, name=strategy.name, summary=strategy.summary, books=_chips(snapshot, books, counts),
        book=primary.money if primary else None, primary=primary.id if primary else None,
        toggle={b.money for b in books} == {"real", "paper"}, expected=expected, steps=list(strategy.steps),
        sizing=strategy.sizing,
        behaving=Behaving(
            trades=len(mine), buckets=buckets([t.return_pct for t in mine], expected.distribution if expected else []),
            scorecard=_scorecard(mine, expected, primary, today), review_at=strategy.review_at_trades,
            other=_other_book(other, closed[other.id] if other else []),
        ),
        funnel=_funnel(lines, expected),
        slots=_slots(snapshot, primary, mine, list(strategy.watch), today),
        anatomy=_anatomy(snapshot, primary, mine),
        worth=_worth(snapshot, profile, primary, expected),
        monthly=_monthly(snapshot, primary, today),
        trades=[TradeRow(symbol=t.symbol, money=primary.money, opened=t.opened, closed=t.closed,
                         days_held=(t.closed - t.opened).days, return_pct=t.return_pct, r_multiple=t.r_multiple,
                         pnl=t.pnl, exit_reason=t.exit_reason) for t in mine[::-1]] if primary else [],
    )
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `127 passed` (`test_strategy_view.py` 14, `test_strategy_sections.py` 14); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/views/strategy.py tests/test_strategy_sections.py
git commit -m "feat(views): strategy page, part 2: slots, trade anatomy, worth, month by month, all trades"
```

---

### Task 6: Routes, CLI views and the generated fixtures

**Files:**
- Modify (replace the whole file): `src/kestrel/server.py`, `src/kestrel/cli.py`
- Generate: `web/src/test/fixtures/strategies.json`, `web/src/test/fixtures/strategy-rsi2.json`
- Test (replace the whole file): `tests/test_server.py`, `tests/test_cli.py`, `tests/test_generated_files.py`

**Interfaces:**
- Consumes: `strategies_view`, `strategy_view`, `StrategiesView`, `StrategyView` (Tasks 4–5); `Money` (contract).
- Produces:
  - `GET /api/strategies` → `StrategiesView`.
  - `GET /api/strategies/{strategy_id}?book=real|paper` → `StrategyView`; an unknown id → JSON 404 `{"detail": "no such strategy: <id>"}`; any other `book` → 422 (FastAPI validation). Both are registered before the `/api/{rest:path}` catch-all and are GET-only.
  - `kestrel demo --view strategies` and `kestrel demo --view strategy --id ID [--book real|paper]`; without `--id`, or with an unknown one, it prints a line to stderr and exits 2.
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
````

`tests/test_cli.py`:

````python
import json

import pytest

import kestrel.cli
from kestrel.cli import main

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
Expected: `7 failed, 21 passed`: the three strategy route tests (the catch-all answers 404), the two CLI tests (`kestrel demo: error: argument --view: invalid choice: 'strategy'`) and the two new drift entries (``missing: run `kestrel demo --view strategies …` ``). `test_writes_to_the_strategy_routes_are_refused` passes already (the catch-all is GET-only); it pins that for the new routes.

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
from .profile import DEMO_PROFILE, ProfileError, load_profile

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


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .server import WEB_DIST, create_app

    try:
        profile, origin = load_profile(args.profile)
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
        profile, origin = load_profile(args.profile)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc)
    snapshot = collect(profile, now)
    print(f"profile: {origin} - hello, {profile.you.name}")
    for s in snapshot.sources:
        age = f"{age_text(now - s.last_success)} ago" if s.last_success else "never"
        print(f"  {s.status:<5}  {s.label:<16} {s.kind:<16} {age}  {s.detail}".rstrip())
    return 1 if any(s.status == "error" for s in snapshot.sources) else 0


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
    serve.add_argument("--profile", type=Path, help="profile file (default: ./profile.toml, else demo data)")
    serve.add_argument("--port", type=int, default=8030)
    serve.add_argument("--no-open", action="store_true", help="don't open a browser")
    serve.set_defaults(run=_serve)
    check = sub.add_parser("check", help="validate the profile and try every source")
    check.add_argument("--profile", type=Path)
    check.set_defaults(run=_check)
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


```bash
.venv/Scripts/kestrel demo --view strategies --now 2026-09-25T21:08:00+00:00 > web/src/test/fixtures/strategies.json
.venv/Scripts/kestrel demo --view strategy --id rsi2 --now 2026-09-25T21:08:00+00:00 > web/src/test/fixtures/strategy-rsi2.json
```

(These are the commands the failing drift test prints. `strategy-rsi2.json` is about 3,400 lines, mostly chart bars.)

- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `135 passed` (`test_server.py` 15, `test_cli.py` 8, `test_generated_files.py` 5); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/server.py src/kestrel/cli.py tests/test_server.py tests/test_cli.py tests/test_generated_files.py web/src/test/fixtures/strategies.json web/src/test/fixtures/strategy-rsi2.json
git commit -m "feat(server,cli): GET /api/strategies and /api/strategies/{id}; demo views; generated fixtures"
```

---

### Task 7: The chart kit, part 1: geometry, shared pieces, the funnel band and the histogram

**Files:**
- Modify (replace the whole file): `web/src/charts/geometry.ts`, `web/src/charts/LineChart.tsx`
- Create: `web/src/charts/hooks.ts`, `web/src/charts/marks.tsx`, `web/src/charts/Histogram.tsx`
- Test (replace or create): `web/src/charts/geometry.test.ts`, `web/src/charts/LineChart.test.tsx`, `web/src/charts/Histogram.test.tsx`

**Interfaces:**
- Produces:
  - `geometry.ts` (pure, no DOM), added to the Phase 2 helpers: `TIP_W = 190`; `clampTip(anchor, width, tip = TIP_W) -> number` (beside the anchor, flipped near the right edge, never outside); `bandLayout(n, width, max = 24, fill = 0.76) -> { step, mark, left(i), center(i) }`; `indexAt(x, n, width) -> number` (−1 when empty); `OHLC`, `Candle`, `candleShapes(bars, width, y) -> Candle[]` (a bar that didn't move still gets a 1 px body); `Placed { x, y, anchor: 'start' | 'middle' | 'end', leader, clear }`, `placeLabels(points: {x, y, w}[], width, height, h = 28, gap = 10) -> Placed[]`; `cellWash(value) -> number | null` (10 + 10·|v| %, capped at 60, `null` under 0.5); `yearSpans(months) -> {year, span}[]`.
  - `hooks.ts`: `useWidth<T>(fallback) -> [ref, width]` (moved out of `LineChart`), `useIndex(count) -> { index, set, onKey }` (←/→, Home/End, Escape; an index only counts while it names a real item).
  - `marks.tsx`: `useSvgId(prefix)`, `Hatch({ id, color })` (the paper pattern), `Tip({ left, top?, title, rows })` (the tooltip card, `role="status"`), `Empty({ children })`.
  - `LineChart`: optional `band?: { lo, hi: (number | null)[], label }` drawn as a dotted-edge wash and read out in the tooltip ("Expected range+0.2% to +1.5%"); `ChartSeries.endLabel` draws a direct label at the series' last defined point; it now uses `useWidth`, `useIndex`, `clampTip` and `Tip`.
  - `Histogram({ buckets, money, height?, ariaLabel })`, `HistogramTable({ buckets, money })`, `HistogramBucket`, `bucketLabel(low)` ("under −9%", "+2% to +3%", "+9% or more"), `shareText(value)`.

- [ ] **Step 1: Write the failing tests**

`web/src/charts/geometry.test.ts`:

````ts
import { describe, expect, it } from 'vitest'
import type { ValuePoint } from '../lib/api'
import {
  bandLayout, baseline, candleShapes, cellWash, clampTip, indexAt, nearestIndex, placeLabels, tickIndices, windowPoints,
  yearSpans,
} from './geometry'

const p = (date: string, value: number, net_flow = 0): ValuePoint => ({ date, value, net_flow })

describe('chart geometry', () => {
  it('keeps the points inside a range', () => {
    const pts = [p('2025-12-31', 1), p('2026-01-02', 2), p('2026-08-24', 3), p('2026-09-25', 4)]
    expect(windowPoints(pts, 'YTD').map((x) => x.date)).toEqual(['2026-01-02', '2026-08-24', '2026-09-25'])
    expect(windowPoints(pts, '1M').map((x) => x.date)).toEqual(['2026-08-24', '2026-09-25']) // 25 Aug is outside
    expect(windowPoints([p('2026-09-25', 4)], '1M')).toHaveLength(1)
    expect(windowPoints([], '1Y')).toEqual([])
  })
  it('counts months back from the end of a month without skipping the shorter month', () => {
    const march = [p('2026-02-27', 1), p('2026-02-28', 2), p('2026-03-02', 3), p('2026-03-31', 4)]
    expect(windowPoints(march, '1M').map((x) => x.date)).toEqual(['2026-02-28', '2026-03-02', '2026-03-31'])
    const leap = [p('2027-02-26', 1), p('2027-02-28', 2), p('2027-03-01', 3), p('2028-02-29', 4)]
    expect(windowPoints(leap, '1Y').map((x) => x.date)).toEqual(['2027-02-28', '2027-03-01', '2028-02-29'])
  })
  it('never returns fewer than two points when it has them', () => {
    const pts = [p('2026-01-02', 1), p('2026-09-24', 2), p('2026-09-25', 3)]
    expect(windowPoints(pts, '1M')).toHaveLength(2)
  })
  it('adds deposits onto the starting value', () => {
    expect(baseline([p('a', 100), p('b', 130, 20), p('c', 90, -10)])).toEqual([100, 120, 110])
  })
  it('finds the nearest x', () => {
    expect(nearestIndex([0, 10, 20], 14)).toBe(1)
    expect(nearestIndex([0, 10, 20], 16)).toBe(2)
    expect(nearestIndex([0, 10, 20], -5)).toBe(0)
    expect(nearestIndex([], 3)).toBe(-1)
  })
  it('spreads ticks', () => {
    expect(tickIndices(262, 6)).toEqual([0, 52, 104, 157, 209, 261])
    expect(tickIndices(3, 6)).toEqual([0, 1, 2])
  })
  it('keeps a tooltip beside its anchor and inside the chart', () => {
    expect(clampTip(100, 640)).toBe(112)
    expect(clampTip(600, 640)).toBe(600 - 12 - 190) // flipped to the left near the right edge
    expect(clampTip(150, 200)).toBe(0) // flipped would start off the chart
    expect(clampTip(10, 100)).toBe(0) // a chart narrower than the tooltip
  })
  it('lays out a row of evenly spaced marks and finds the one under the pointer', () => {
    const b = bandLayout(20, 660)
    expect([b.step, b.mark]).toEqual([33, 24]) // bars are at most 24 px wide
    expect(b.left(0)).toBe(4.5)
    expect(b.center(19)).toBe(643.5)
    expect(bandLayout(40, 200, Infinity, 0.8).mark).toBe(4)
    expect([indexAt(-5, 20, 660), indexAt(34, 20, 660), indexAt(9999, 20, 660)]).toEqual([0, 1, 19])
    expect(indexAt(10, 0, 660)).toBe(-1)
  })
  it('shapes candles, with a hairline body for a bar that did not move', () => {
    const y = (v: number) => 100 - v
    const [up, down, flat] = candleShapes([
      { open: 10, high: 20, low: 5, close: 15 },
      { open: 15, high: 16, low: 8, close: 9 },
      { open: 9, high: 9, low: 9, close: 9 },
    ], 30, y)
    expect(up).toMatchObject({ x: 5, up: true, bodyTop: 85, bodyH: 5, wickTop: 80, wickBottom: 95 })
    expect(down).toMatchObject({ up: false, bodyTop: 85, bodyH: 6 })
    expect(flat.bodyH).toBe(1)
  })
  it('places labels beside their points, clear of each other, the markers and the edges', () => {
    const placed = placeLabels([{ x: 100, y: 100, w: 80 }, { x: 100, y: 120, w: 80 }, { x: 290, y: 20, w: 80 }],
      300, 200)
    expect(placed[0]).toEqual({ x: 110, y: 86, anchor: 'start', leader: false, clear: true }) // right of its point
    expect(placed[1]).toEqual({ x: 90, y: 106, anchor: 'end', leader: false, clear: true }) // the right is taken
    expect(placed[2]).toEqual({ x: 280, y: 6, anchor: 'end', leader: false, clear: true }) // no room on the right
    // three points close together near the right edge: the third label slides clear and gets a leader line
    const stack = placeLabels([{ x: 160, y: 100, w: 80 }, { x: 160, y: 110, w: 80 }, { x: 160, y: 120, w: 80 }],
      200, 200)
    expect(stack[2]).toEqual({ x: 150, y: 154, anchor: 'end', leader: true, clear: true })
    // twenty labels on one point can't all be clear (the chart then uses a key), but each one stays inside it
    const crowd = placeLabels(Array.from({ length: 20 }, () => ({ x: 150, y: 100, w: 100 })), 300, 200)
    expect(crowd.some((l) => !l.clear)).toBe(true)
    for (const l of crowd) {
      const left = l.anchor === 'start' ? l.x : l.anchor === 'end' ? l.x - 100 : l.x - 50
      expect(left >= 0 && left + 100 <= 300 && l.y >= 0 && l.y + 28 <= 200).toBe(true)
    }
  })
  it('washes a month cell by the size of its move and leaves a small one neutral', () => {
    expect([cellWash(1.2), cellWash(-0.8), cellWash(9)]).toEqual([22, 18, 60])
    expect([cellWash(0.3), cellWash(null)]).toEqual([null, null])
  })
  it('groups months under their year', () => {
    expect(yearSpans(['2025-10', '2025-11', '2025-12', '2026-01'])).toEqual([
      { year: '2025', span: 3 }, { year: '2026', span: 1 },
    ])
  })
})
````

`web/src/charts/LineChart.test.tsx`:

````tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LineChart } from './LineChart'

const props = (dates: string[], values: number[]) => ({
  dates, height: 120, ariaLabel: 'Test chart', yFormat: String, valueFormat: String, xLabel: (d: string) => d,
  tipTitle: (d: string) => `Day ${d}`,
  series: [{ key: 'a', label: 'A', values, color: 'var(--s1)', style: 'solid' as const }],
})

describe('LineChart', () => {
  afterEach(() => vi.restoreAllMocks())

  it('ignores the pointer and keys when it has no dates', () => {
    render(<LineChart {...props([], [])} />)
    const chart = screen.getByRole('img', { name: 'Test chart' })
    fireEvent.pointerMove(chart, { clientX: 30 })
    for (const key of ['ArrowRight', 'ArrowLeft', 'Home', 'End']) fireEvent.keyDown(chart, { key })
    expect(screen.queryByRole('status')).toBeNull() // no tooltip for a day that doesn't exist
  })

  it('keeps the tooltip inside a narrow chart', () => {
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(200) // a phone-width panel
    render(<LineChart {...props(['2026-09-24', '2026-09-25'], [1, 2])} />)
    const chart = screen.getByRole('img', { name: 'Test chart' })
    for (const key of ['Home', 'End']) {
      fireEvent.keyDown(chart, { key })
      const left = parseFloat(screen.getByRole('status').style.left)
      expect(left).toBeGreaterThanOrEqual(0)
      expect(left).toBeLessThanOrEqual(200 - 190)
    }
  })

  it('draws an expected band and reads it out in the tooltip', () => {
    render(<LineChart {...props(['1', '2', '3'], [1, 2, 3])}
      band={{ lo: [null, 0, 0.5], hi: [null, 2, 1.5], label: 'Expected range' }} />)
    const chart = screen.getByRole('img', { name: 'Test chart' })
    expect(chart.querySelector('[data-band="wash"]')).not.toBeNull()
    fireEvent.keyDown(chart, { key: 'End' })
    expect(screen.getByRole('status').textContent).toContain('Expected range0.5 to 1.5')
    fireEvent.keyDown(chart, { key: 'Home' })
    expect(screen.getByRole('status').textContent).toContain('Expected range—') // no band before trade 3
  })

  it('labels the end of a series that asks for it, where that series ends', () => {
    const series = [{ key: 'a', label: 'A', values: [1, 2, null], color: 'var(--s2)', style: 'solid' as const,
      endLabel: 'Real +2%' }]
    render(<LineChart {...props(['1', '2', '3'], [1, 2, 3])} series={series} />)
    expect(screen.getByText('Real +2%')).toBeTruthy()
  })
})
````

`web/src/charts/Histogram.test.tsx`:

````tsx
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { bucketLabel, Histogram, HistogramTable } from './Histogram'

const buckets = Array.from({ length: 20 }, (_, i) => ({
  low: i - 10, count: i === 12 ? 3 : i === 0 ? 1 : 0, share: i === 12 ? 75 : i === 0 ? 25 : 0, expected: 5,
}))

describe('Histogram', () => {
  it('names its buckets, the end ones holding everything beyond', () => {
    expect([bucketLabel(-10), bucketLabel(-1), bucketLabel(2), bucketLabel(9)])
      .toEqual(['under −9%', '−1% to 0%', '+2% to +3%', '+9% or more'])
  })

  it('draws the backtest behind the trades and reads out a bucket from the keyboard', () => {
    const { container } = render(<Histogram buckets={buckets} money="real" ariaLabel="Trade returns" />)
    expect(container.querySelectorAll('[data-mark="expected"]')).toHaveLength(20)
    expect(container.querySelectorAll('[data-mark="real"]')).toHaveLength(2) // the empty buckets draw nothing
    const chart = screen.getByRole('img', { name: 'Trade returns' })
    fireEvent.keyDown(chart, { key: 'Home' })
    const tip = screen.getByRole('status')
    expect(tip.textContent).toContain('Trades returning under −9%')
    expect(tip.textContent).toContain('Real1 trade · 25%')
    expect(tip.textContent).toContain('Backtest5% of trades')
    fireEvent.keyDown(chart, { key: 'Escape' })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('hatches a paper book', () => {
    const { container } = render(<Histogram buckets={buckets} money="paper" ariaLabel="Trade returns" />)
    expect(container.querySelectorAll('[data-mark="paper"]')).toHaveLength(2)
    expect(container.querySelector('pattern')).not.toBeNull()
  })

  it('has a table view with every bucket', () => {
    render(<HistogramTable buckets={buckets} money="real" />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows).toHaveLength(21)
    expect(rows[13].textContent).toBe('+2% to +3%375%5%')
  })

  it('says so when there is nothing to draw', () => {
    const empty = buckets.map((b) => ({ ...b, count: 0, share: 0, expected: null }))
    render(<Histogram buckets={empty} money="real" ariaLabel="Trade returns" />)
    expect(screen.getByText('No closed trades yet.')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/charts/geometry.test.ts src/charts/LineChart.test.tsx src/charts/Histogram.test.tsx`
Expected: `Test Files  3 failed (3)` and `Tests  8 failed | 8 passed (16)`: the six new geometry tests (`clampTip is not a function`, `bandLayout is not a function`, …), the two new LineChart tests, and `Failed to resolve import "./Histogram"`.

- [ ] **Step 3: Implement**

`web/src/charts/geometry.ts`:

````ts
// Pure chart math, tested without a DOM.
import type { ValuePoint } from '../lib/api'

export type Range = '1M' | '3M' | 'YTD' | '1Y'
export const RANGES: readonly Range[] = ['1M', '3M', 'YTD', '1Y']

/** The UTC date `months` whole months before `date`, its day clamped to that month's last (31 Mar → 28 Feb). */
function monthsBefore(date: Date, months: number): Date {
  const year = date.getUTCFullYear()
  const month = date.getUTCMonth() - months // Date.UTC rolls a negative month back into the year before
  const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate()
  return new Date(Date.UTC(year, month, Math.min(date.getUTCDate(), lastDay), 12))
}

/** Points inside the range, counted back from the last point's date. */
export function windowPoints(points: ValuePoint[], range: Range): ValuePoint[] {
  if (points.length === 0) return points
  const last = new Date(`${points[points.length - 1].date}T12:00:00Z`)
  const start = range === 'YTD'
    ? new Date(Date.UTC(last.getUTCFullYear(), 0, 1, 12))
    : monthsBefore(last, { '1M': 1, '3M': 3, '1Y': 12 }[range])
  const from = start.toISOString().slice(0, 10)
  const inside = points.filter((p) => p.date >= from)
  return inside.length >= 2 ? inside : points.slice(-2)
}

/** The "starting value + deposits" line: what the account would hold if the market had not moved. */
export function baseline(points: ValuePoint[]): number[] {
  const out: number[] = []
  points.forEach((p, i) => out.push(i === 0 ? p.value : out[i - 1] + p.net_flow))
  return out
}

/** Index of the x closest to `x` (xs ascending). */
export function nearestIndex(xs: number[], x: number): number {
  if (xs.length === 0) return -1
  let lo = 0
  let hi = xs.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (xs[mid] <= x) lo = mid
    else hi = mid
  }
  return Math.abs(xs[lo] - x) <= Math.abs(xs[hi] - x) ? lo : hi
}

/** About `count` evenly spaced indices across n points, always including the first. */
export function tickIndices(n: number, count: number): number[] {
  if (n <= 0) return []
  if (n <= count) return Array.from({ length: n }, (_, i) => i)
  const step = (n - 1) / (count - 1)
  return Array.from({ length: count }, (_, i) => Math.round(i * step))
}

export const TIP_W = 190 // the tooltip card's width (.tip min-width 170 + padding)

/** A tooltip's left edge: beside the anchor, flipped to its left near the right edge, and never outside the chart
 *  (phones are narrow). */
export function clampTip(anchor: number, width: number, tip = TIP_W): number {
  const side = anchor + 12 + tip > width ? anchor - 12 - tip : anchor + 12
  return Math.min(Math.max(0, side), Math.max(0, width - tip))
}

/** n equal slots across `width`; each slot's mark is centred and `fill` of the slot wide, at most `max` px. */
export function bandLayout(n: number, width: number, max = 24, fill = 0.76) {
  const step = n > 0 ? width / n : width
  const mark = Math.min(max, step * fill)
  return {
    step,
    mark,
    left: (i: number) => i * step + (step - mark) / 2,
    center: (i: number) => i * step + step / 2,
  }
}

/** The slot under an x position, clamped to the ends; -1 when there are no slots. */
export function indexAt(x: number, n: number, width: number): number {
  if (n <= 0) return -1
  return Math.min(n - 1, Math.max(0, Math.floor(x / (width / n))))
}

export interface OHLC { open: number; high: number; low: number; close: number }
export interface Candle { x: number; w: number; up: boolean; bodyTop: number; bodyH: number; wickTop: number;
  wickBottom: number }

/** Candle bodies and wicks for bars spread across `width`, with `y` mapping a price to a pixel. */
export function candleShapes(bars: OHLC[], width: number, y: (price: number) => number): Candle[] {
  const layout = bandLayout(bars.length, width, 12, 0.6)
  return bars.map((b, i) => {
    const top = y(Math.max(b.open, b.close))
    return {
      x: layout.center(i), w: layout.mark, up: b.close >= b.open,
      bodyTop: top, bodyH: Math.max(1, y(Math.min(b.open, b.close)) - top),
      wickTop: y(b.high), wickBottom: y(b.low),
    }
  })
}

export interface Placed { x: number; y: number; anchor: 'start' | 'middle' | 'end'; leader: boolean; clear: boolean }
interface Box { left: number; top: number; w: number; h: number }

/** How much two boxes overlap, in square pixels (0 when they are apart). */
const overlap = (a: Box, b: Box) =>
  Math.max(0, Math.min(a.left + a.w, b.left + b.w) - Math.max(a.left, b.left))
  * Math.max(0, Math.min(a.top + a.h, b.top + b.h) - Math.max(a.top, b.top))

/** Direct labels for points. Each tries the spots around its point (right, left, above, below), then slides to
 *  the right or left of it, up or down in 8 px steps; it takes the first spot that stays inside the chart and clear
 *  of every marker and of the labels placed before it, or else the inside spot that overlaps least (`clear` is
 *  false). A label slid away from its point gets a leader line. `x` is where the text is anchored, `y` the label
 *  box's top; `h` is its height (a name over a figure). */
export function placeLabels(points: { x: number; y: number; w: number }[], width: number, height: number, h = 28,
  gap = 10): Placed[] {
  const taken: Box[] = points.map((p) => ({ left: p.x - 8, top: p.y - 8, w: 16, h: 16 })) // the markers
  return points.map((p) => {
    const right = { left: p.x + gap, x: p.x + gap, anchor: 'start' as const }
    const left = { left: p.x - gap - p.w, x: p.x - gap, anchor: 'end' as const }
    const middle = { left: p.x - p.w / 2, x: p.x, anchor: 'middle' as const }
    const level = p.y - h / 2
    const spots = [
      { ...right, top: level, dy: 0 }, { ...left, top: level, dy: 0 },
      { ...middle, top: p.y - gap - h, dy: 0 }, { ...middle, top: p.y + gap, dy: 0 },
    ]
    for (let step = 8; step <= 64; step += 8) {
      for (const dy of [step, -step]) spots.push({ ...right, top: level + dy, dy }, { ...left, top: level + dy, dy })
    }
    const boxOf = (s: (typeof spots)[number]): Box => ({ left: s.left, top: s.top, w: p.w, h })
    const inside = spots.filter((s) => {
      const b = boxOf(s)
      return b.left >= 0 && b.left + b.w <= width && b.top >= 0 && b.top + b.h <= height
    })
    const crowding = (s: (typeof spots)[number]) => taken.reduce((sum, t) => sum + overlap(boxOf(s), t), 0)
    const pick = inside.find((s) => crowding(s) === 0)
      ?? [...inside].sort((a, b) => crowding(a) - crowding(b))[0] ?? spots[0]
    const clear = crowding(pick) === 0
    taken.push(boxOf(pick))
    return { x: pick.x, y: pick.top, anchor: pick.anchor, leader: Math.abs(pick.dy) >= h / 2, clear }
  })
}

/** How strongly a month cell is washed in the gain or loss colour, in percent; null for a small or missing move. */
export function cellWash(value: number | null): number | null {
  if (value == null || Math.abs(value) < 0.5) return null
  return Math.min(60, Math.round(10 + Math.abs(value) * 10))
}

/** Consecutive "YYYY-MM" months grouped under their year, for the label row above a month grid. */
export function yearSpans(months: string[]): { year: string; span: number }[] {
  const out: { year: string; span: number }[] = []
  for (const month of months) {
    const year = month.slice(0, 4)
    const last = out[out.length - 1]
    if (last && last.year === year) last.span += 1
    else out.push({ year, span: 1 })
  }
  return out
}
````

`web/src/charts/hooks.ts`:

````ts
// What every chart shares: its measured width, and a hovered index that the pointer and the keys both move.
import { type KeyboardEvent, useLayoutEffect, useRef, useState } from 'react'

/** A ref for the chart's wrapper and its current width (`fallback` until measured, and in jsdom). */
export function useWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(fallback)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth || fallback)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [fallback])
  return [ref, width] as const
}

/** The hovered item among `count`: null when none. ←/→ step, Home/End jump, Escape clears. An index only counts
 *  while it names a real item, so an empty chart has none and a refresh that shortens the data can't break it. */
export function useIndex(count: number) {
  const [hovered, setHovered] = useState<number | null>(null)
  const index = hovered != null && hovered >= 0 && hovered < count ? hovered : null
  const onKey = (event: KeyboardEvent<Element>) => {
    const last = count - 1
    const moves: Record<string, number> = {
      ArrowLeft: Math.max(0, (index ?? last) - 1),
      ArrowRight: Math.min(last, (index ?? last - 1) + 1),
      Home: 0,
      End: last,
    }
    if (event.key in moves) {
      event.preventDefault()
      setHovered(count > 0 ? moves[event.key] : null)
    } else if (event.key === 'Escape') setHovered(null)
  }
  return { index, set: setHovered, onKey }
}
````

`web/src/charts/marks.tsx`:

````tsx
// Small SVG and tooltip pieces the charts share (docs/design-system.md → Charts).
import { type ReactNode, useId } from 'react'

/** A unique id that is safe inside url(#…): React's own ids carry characters a CSS url() would need escaped. */
export function useSvgId(prefix: string): string {
  return prefix + useId().replace(/[^a-zA-Z0-9_-]/g, '')
}

/** The paper hatch as an SVG pattern: 1.5 px of ink every 4 px, at 45°. Give each chart its own id (useSvgId). */
export function Hatch({ id, color }: { id: string; color: string }) {
  return (
    <defs>
      <pattern id={id} width={4} height={4} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width={1.5} height={4} fill={color} />
      </pattern>
    </defs>
  )
}

/** The tooltip card: a heading, then one row per series (label on the left, mono value on the right). */
export function Tip({ left, top = 4, title, rows }: {
  left: number; top?: number; title: string; rows: [label: string, value: ReactNode][]
}) {
  return (
    <div className="tip" style={{ left, top }} role="status">
      <div style={{ color: 'var(--ink3)', fontSize: 11 }}>{title}</div>
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between gap-4" style={{ marginTop: 4 }}>
          <span style={{ color: 'var(--ink2)' }}>{label}</span>
          <span className="num" style={{ fontWeight: 500 }}>{value}</span>
        </div>
      ))}
    </div>
  )
}

/** A chart with nothing to draw says so in plain words. */
export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-ink3 mt-6">{children}</p>
}
````

`web/src/charts/LineChart.tsx`:

````tsx
// One line chart for the whole app: hairline grid, right-hand value axis, crosshair tooltip on hover or keys, and
// an optional expected band (the funnel on the Strategy page).
import { max, min } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import { area, curveLinear, curveStepAfter, line } from 'd3-shape'
import type { PointerEvent } from 'react'
import { clampTip, nearestIndex, tickIndices } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Tip } from './marks'

export interface ChartSeries {
  key: string
  label: string
  values: (number | null)[]
  color: string // a CSS colour token, e.g. 'var(--s2)'
  style: 'solid' | 'dashed' | 'dotted' // real · paper · expected/benchmark
  area?: boolean
  step?: boolean
  endLabel?: string // a direct label at the line's last point
}

/** An expected range drawn as a dotted-edge wash: lo[i] to hi[i], skipped where either is null. */
export interface Band {
  lo: (number | null)[]
  hi: (number | null)[]
  label: string
}

interface Props {
  dates: string[]
  series: ChartSeries[]
  height: number
  ariaLabel: string
  yFormat: (value: number) => string
  valueFormat: (value: number) => string
  xLabel: (iso: string) => string
  tipTitle: (iso: string) => string
  zeroLine?: boolean
  compact?: boolean
  band?: Band
}

const DASH = { solid: undefined, dashed: '5 3.5', dotted: '1.5 3.5' } as const

/** The index of a series' last value (a shorter book's line ends before the chart does); -1 when it has none. */
function lastDefined(values: (number | null)[]): number {
  for (let i = values.length - 1; i >= 0; i -= 1) if (values[i] != null) return i
  return -1
}

export function LineChart(props: Props) {
  const { dates, series, height, compact = false, band } = props
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(dates.length)
  const axisW = compact ? 0 : 56
  const bottom = compact ? 4 : 24
  const plotW = Math.max(40, width - axisW)
  const all = [...series.flatMap((s) => s.values), ...(band ? [...band.lo, ...band.hi] : [])]
    .filter((v): v is number => v != null)
  const y = scaleLinear()
    .domain([min(all) ?? 0, max(all) ?? 1])
    .nice(4)
    .range([height - bottom, 8])
  const x = scaleLinear().domain([0, Math.max(1, dates.length - 1)]).range([0, plotW])
  const xs = dates.map((_, i) => x(i))
  const yTicks = compact ? [] : y.ticks(4)
  const xTicks = compact ? [] : tickIndices(dates.length, width < 480 ? 4 : 6)

  const pathOf = (values: (number | null)[], step = false) =>
    line<number | null>()
      .defined((v) => v != null)
      .x((_, i) => x(i))
      .y((v) => y(v as number))
      .curve(step ? curveStepAfter : curveLinear)(values) ?? ''
  const areaOf = (s: ChartSeries) =>
    area<number | null>()
      .defined((v) => v != null)
      .x((_, i) => x(i))
      .y0(height - bottom)
      .y1((v) => y(v as number))(s.values) ?? ''
  const bandArea = band
    ? area<number>()
      .defined((i) => band.lo[i] != null && band.hi[i] != null)
      .x((i) => x(i))
      .y0((i) => y(band.lo[i] as number))
      .y1((i) => y(band.hi[i] as number))(band.lo.map((_, i) => i)) ?? ''
    : ''

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, event.clientX - box.left))
  }
  const labelled = series.filter((s) => s.endLabel)

  const tipRows: [string, string][] = series.map((s) => [
    s.label, hover == null || s.values[hover] == null ? '—' : props.valueFormat(s.values[hover] as number),
  ])
  if (band && hover != null) {
    const lo = band.lo[hover]
    const hi = band.hi[hover]
    tipRows.push([band.label, lo == null || hi == null ? '—' : `${props.valueFormat(lo)} to ${props.valueFormat(hi)}`])
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={props.ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={0} x2={plotW} y1={y(t)} y2={y(t)}
              stroke={props.zeroLine && t === 0 ? 'var(--line2)' : 'var(--line)'} />
            <text x={plotW + 10} y={y(t) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
              {props.yFormat(t)}
            </text>
          </g>
        ))}
        {xTicks.map((i) => (
          <text key={i} x={xs[i]} y={height - 6} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}
            textAnchor={i === 0 ? 'start' : i === dates.length - 1 ? 'end' : 'middle'}>
            {props.xLabel(dates[i])}
          </text>
        ))}
        {band && (
          <g>
            <path data-band="wash" d={bandArea} fill="var(--ink1)" fillOpacity={0.05} />
            {[band.lo, band.hi].map((edge, k) => (
              <path key={k} d={pathOf(edge)} fill="none" stroke="var(--ref)" strokeWidth={1} strokeDasharray="1.5 3"
                strokeLinecap="round" />
            ))}
          </g>
        )}
        {series.filter((s) => s.area).map((s) => (
          <path key={`${s.key}-area`} d={areaOf(s)} fill={s.color} fillOpacity={0.06} />
        ))}
        {series.map((s) => (
          <path key={s.key} d={pathOf(s.values, s.step)} fill="none" stroke={s.color}
            strokeWidth={s.style === 'dotted' ? 1.5 : 2} strokeDasharray={DASH[s.style]} strokeLinecap="round"
            strokeLinejoin="round" />
        ))}
        {hover == null && series.filter((s) => s.style === 'solid' || s.endLabel).map((s) => {
          const lastI = lastDefined(s.values)
          const v = s.values[lastI]
          return v == null ? null : (
            <circle key={`${s.key}-end`} cx={xs[lastI]} cy={y(v)} r={4} strokeWidth={2}
              fill={s.style === 'solid' ? s.color : 'var(--panel)'} stroke={s.style === 'solid' ? 'var(--panel)' : s.color} />
          )
        })}
        {labelled.map((s, k) => {
          const lastI = lastDefined(s.values)
          const v = s.values[lastI]
          if (v == null) return null
          const cx = xs[lastI]
          const anchor = cx > plotW - 60 ? 'end' : cx < 60 ? 'start' : 'middle'
          return (
            <text key={`${s.key}-label`} x={cx} y={y(v) + (k === 0 ? -10 : 18)} textAnchor={anchor}
              fill={k === 0 ? 'var(--ink1)' : 'var(--ink2)'} style={{ font: '500 11px var(--k-sans)' }}>
              {s.endLabel}
            </text>
          )
        })}
        {hover != null && (
          <g>
            <line x1={xs[hover]} x2={xs[hover]} y1={8} y2={height - bottom} stroke="var(--line2)" />
            {series.map((s) => {
              const v = s.values[hover]
              return v == null ? null : (
                <circle key={`${s.key}-hover`} cx={xs[hover]} cy={y(v)} r={4} fill={s.color} stroke="var(--panel)"
                  strokeWidth={2} />
              )
            })}
          </g>
        )}
      </svg>
      {hover != null && <Tip left={clampTip(xs[hover], width)} title={props.tipTitle(dates[hover])} rows={tipRows} />}
    </div>
  )
}

/** The small legend key drawn beside a series name: the line in its real/paper/expected style. */
export function LineKey({ color, style }: { color: string; style: ChartSeries['style'] }) {
  return (
    <svg width="18" height="10" aria-hidden="true" style={{ flex: 'none' }}>
      <line x1="1" x2="17" y1="5" y2="5" stroke={color} strokeWidth={style === 'dotted' ? 1.5 : 2}
        strokeDasharray={style === 'dotted' ? '1.5 3' : style === 'dashed' ? '5 3' : undefined} strokeLinecap="round" />
    </svg>
  )
}
````

`web/src/charts/Histogram.tsx`:

````tsx
// Where each closed trade landed, in 1-point return buckets, over the backtest's spread of outcomes.
import { max } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import type { CSSProperties, PointerEvent } from 'react'
import type { Money } from '../lib/api'
import { MINUS } from '../lib/format'
import { bandLayout, clampTip, indexAt } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Hatch, Tip, useSvgId } from './marks'

export interface HistogramBucket {
  low: number
  count: number
  share: number
  expected: number | null
}

const whole = (v: number) => (v === 0 ? '0%' : `${v > 0 ? '+' : MINUS}${Math.abs(v)}%`)

/** "+2% to +3%"; the end buckets also hold everything beyond them: "under −9%", "+9% or more". */
export function bucketLabel(low: number): string {
  if (low <= -10) return `under ${whole(-9)}`
  if (low >= 9) return `${whole(9)} or more`
  return `${whole(low)} to ${whole(low + 1)}`
}

/** A share of trades: whole percents, with one decimal under 1%. */
export function shareText(value: number): string {
  return value > 0 && value < 1 ? `${value.toFixed(1)}%` : `${Math.round(value)}%`
}

const tradesText = (n: number) => `${n} trade${n === 1 ? '' : 's'}`
const moneyWord = (money: Money) => (money === 'real' ? 'Real' : 'Paper')

/** A bar with a 4 px rounded data end and a square baseline. */
function barPath(x: number, w: number, top: number, base: number): string {
  const r = Math.min(4, w / 2, base - top)
  return `M${x} ${base}V${top + r}Q${x} ${top} ${x + r} ${top}H${x + w - r}Q${x + w} ${top} ${x + w} ${top + r}V${base}Z`
}

export function Histogram({ buckets, money, height = 236, ariaLabel }: {
  buckets: HistogramBucket[]; money: Money; height?: number; ariaLabel: string
}) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(buckets.length)
  const hatch = useSvgId('hatch')
  if (!buckets.some((b) => b.count > 0 || (b.expected ?? 0) > 0)) return <Empty>No closed trades yet.</Empty>

  const axisW = 40
  const base = height - 20
  const plotW = Math.max(40, width - axisW)
  const layout = bandLayout(buckets.length, plotW)
  const inner = layout.mark * 0.5
  const peak = max(buckets.flatMap((b) => [b.share, b.expected ?? 0])) ?? 1
  const y = scaleLinear().domain([0, Math.max(1, peak)]).nice(4).range([base, 16])
  const every = width < 480 ? 5 : 2
  const edges = Array.from({ length: buckets.length + 1 }, (_, i) => i).filter((i) => i % every === 0)
  const zero = buckets.findIndex((b) => b.low === 0)
  const fill = money === 'real' ? 'var(--s2)' : `url(#${hatch})`

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(indexAt(event.clientX - box.left, buckets.length, plotW))
  }
  const b = hover == null ? null : buckets[hover]

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {money === 'paper' && <Hatch id={hatch} color="var(--s2)" />}
        {y.ticks(4).map((t) => (
          <g key={t}>
            <line x1={0} x2={plotW} y1={y(t)} y2={y(t)} stroke={t === 0 ? 'var(--line2)' : 'var(--line)'} />
            <text x={plotW + 8} y={y(t) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>{t}%</text>
          </g>
        ))}
        {edges.map((i) => (
          <text key={i} x={i * layout.step} y={height - 4} textAnchor="middle" fill="var(--ink3)"
            style={{ font: '11px var(--k-mono)' }}>
            {whole(buckets[0].low + i)}
          </text>
        ))}
        {hover != null && (
          <rect x={hover * layout.step} y={8} width={layout.step} height={base - 8} fill="var(--ink1)" fillOpacity={0.04} />
        )}
        {buckets.map((bucket, i) => bucket.expected == null ? null : (
          <rect key={`e${i}`} data-mark="expected" x={layout.left(i)} y={y(bucket.expected)} width={layout.mark}
            height={Math.max(0, base - y(bucket.expected))} rx={3} fill="var(--ink1)" fillOpacity={0.05}
            stroke="var(--ref)" strokeDasharray="1.5 2.5" />
        ))}
        {buckets.map((bucket, i) => bucket.count === 0 ? null : (
          <path key={`a${i}`} data-mark={money} d={barPath(layout.center(i) - inner / 2, inner, y(bucket.share), base)}
            fill={fill} stroke={money === 'paper' ? 'var(--s2)' : undefined}
            strokeWidth={money === 'paper' ? 1.25 : undefined} />
        ))}
        {zero >= 0 && (
          <g>
            <line x1={zero * layout.step} x2={zero * layout.step} y1={14} y2={base} stroke="var(--ink3)" />
            <text x={zero * layout.step + 6} y={12} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}>
              break-even
            </text>
          </g>
        )}
      </svg>
      {b != null && hover != null && (
        <Tip left={clampTip(layout.center(hover), width)} title={`Trades returning ${bucketLabel(b.low)}`} rows={[
          [moneyWord(money), `${tradesText(b.count)} · ${shareText(b.share)}`],
          ...(b.expected == null ? [] : [['Backtest', `${shareText(b.expected)} of trades`] as [string, string]]),
        ]} />
      )}
    </div>
  )
}

export function HistogramTable({ buckets, money }: { buckets: HistogramBucket[]; money: Money }) {
  const backtest = buckets.some((b) => b.expected != null)
  return (
    <div className="table-scroll overflow-y-auto" style={{ maxHeight: 260 }}>
      <table className="tbl" style={{ '--row': '34px' } as CSSProperties}>
        <thead>
          <tr>
            <th>Return</th><th className="r">{moneyWord(money)} trades</th><th className="r">Share</th>
            {backtest && <th className="r">Backtest</th>}
          </tr>
        </thead>
        <tbody>
          {buckets.map((b) => (
            <tr key={b.low}>
              <td>{bucketLabel(b.low)}</td>
              <td className="r num">{b.count}</td>
              <td className="r num">{shareText(b.share)}</td>
              {backtest && <td className="r num">{b.expected == null ? '—' : shareText(b.expected)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
````


- [ ] **Step 4: Run everything and watch it pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit`
Expected: `Tests  64 passed (64)` (`geometry.test.ts` 12, `LineChart.test.tsx` 4, `Histogram.test.tsx` 5); tsc prints nothing.

- [ ] **Step 5: Commit**

```bash
git add web/src/charts/geometry.ts web/src/charts/geometry.test.ts web/src/charts/hooks.ts web/src/charts/marks.tsx web/src/charts/LineChart.tsx web/src/charts/LineChart.test.tsx web/src/charts/Histogram.tsx web/src/charts/Histogram.test.tsx
git commit -m "feat(charts): geometry helpers, shared hover and tooltip pieces, the funnel band, and the histogram"
```

---

### Task 8: The chart kit, part 2: the slots strip and the candle chart

**Files:**
- Create: `web/src/charts/SlotsStrip.tsx`, `web/src/charts/CandleChart.tsx`
- Test: `web/src/charts/SlotsStrip.test.tsx`, `web/src/charts/CandleChart.test.tsx`

**Interfaces:**
- Consumes: `bandLayout`, `candleShapes`, `clampTip`, `indexAt`, `tickIndices` (geometry); `useIndex`, `useWidth`; `Empty`, `Hatch`, `Tip`, `useSvgId` (Task 7); `num`, `pct`, `shortDate`, `monthLabel` (format).
- Produces:
  - `SlotsStrip({ days, used, total, money, height?, ariaLabel })`: a column of `total` slots per session filled from the bottom (solid real, hatched paper; `data-mark="real" | "paper" | "free"`); the tooltip gives the true count ("In use 7 of 5"). `SlotsTable({ days, used, total })` lists sessions newest first. Empty: "No sessions yet."
  - `CandleChart({ bars, indicator, stop, entry, exit, entryPrice, exitPrice, height?, ariaLabel })`: candles (`data-candle`), the holding window (`data-window`, in each panel), a buy marker and label under the entry bar, a sell marker and label over the exit bar (moved up when the two would print over each other), the stop line across the window with "Stop 92.00 · −8%" when `stop` is given, and the indicator in its own panel with dotted threshold lines. `CandleTable({ bars, indicator, entry, exit })` marks the Buy and Sell rows. `CandleBar`, `CandleIndicator`. Empty: "No chart for this trade."

- [ ] **Step 1: Write the failing tests**

`web/src/charts/SlotsStrip.test.tsx`:

````tsx
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SlotsStrip, SlotsTable } from './SlotsStrip'

const days = ['2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25']
const used = [0, 2, 5, 7, 3] // more in use than there are slots still draws a full column

describe('SlotsStrip', () => {
  it('fills a column of slots per session from the bottom up', () => {
    const { container } = render(<SlotsStrip days={days} used={used} total={5} money="real" ariaLabel="Slots" />)
    expect(container.querySelectorAll('[data-mark="real"]')).toHaveLength(0 + 2 + 5 + 5 + 3)
    expect(container.querySelectorAll('[data-mark="free"]')).toHaveLength(5 + 3 + 0 + 0 + 2)
  })

  it('hatches a paper book', () => {
    const { container } = render(<SlotsStrip days={days} used={used} total={5} money="paper" ariaLabel="Slots" />)
    expect(container.querySelectorAll('[data-mark="paper"]')).toHaveLength(15)
    expect(container.querySelector('pattern')).not.toBeNull()
  })

  it('reads out a session from the keyboard, with the true count', () => {
    render(<SlotsStrip days={days} used={used} total={5} money="real" ariaLabel="Slots" />)
    const chart = screen.getByRole('img', { name: 'Slots' })
    fireEvent.keyDown(chart, { key: 'End' })
    expect(screen.getByRole('status').textContent).toBe('Fri 25 SepIn use3 of 5')
    fireEvent.keyDown(chart, { key: 'ArrowLeft' })
    expect(screen.getByRole('status').textContent).toBe('Thu 24 SepIn use7 of 5')
  })

  it('has a table view', () => {
    render(<SlotsTable days={days} used={used} total={5} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows).toHaveLength(6)
    expect(rows[1].textContent).toBe('Fri 25 Sep3 of 5') // newest first
  })

  it('says so when there are no sessions', () => {
    render(<SlotsStrip days={[]} used={[]} total={5} money="real" ariaLabel="Slots" />)
    expect(screen.getByText('No sessions yet.')).toBeTruthy()
  })
})
````

`web/src/charts/CandleChart.test.tsx`:

````tsx
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CandleChart, CandleTable } from './CandleChart'

const bars = [
  { date: '2026-09-14', open: 101, high: 102, low: 99, close: 100 },
  { date: '2026-09-15', open: 100, high: 101.5, low: 99.2, close: 101 },
  { date: '2026-09-16', open: 101, high: 104, low: 100.5, close: 103.5 },
  { date: '2026-09-17', open: 104, high: 105, low: 103, close: 104.4 },
]
const rsi = { label: 'RSI(2)', values: [null, null, 88.2, 93.1],
  lines: [{ value: 10, label: 'buy under 10' }, { value: 70, label: 'sell over 70' }] }
const trade = { entry: 1, exit: 3, entryPrice: 100, exitPrice: 104 }

describe('CandleChart', () => {
  it('draws the candles, the holding window, both markers and the stop, on the scale and clear of the axis', () => {
    const { container } = render(<CandleChart bars={bars} indicator={rsi} stop={92} {...trade} ariaLabel="HD" />)
    expect(container.querySelectorAll('[data-candle]')).toHaveLength(4)
    expect(container.querySelectorAll('[data-window]')).toHaveLength(2) // price panel and indicator panel
    expect(screen.getByText('Buy 100.00')).toBeTruthy()
    expect(screen.getByText('Sell 104.00')).toBeTruthy()
    expect(screen.getByText('Stop 92.00 · −8%')).toBeTruthy()
    expect(screen.getByText('RSI(2)')).toBeTruthy()
    // the exit is the last bar, so the stop label sits inside the window, clear of the price axis (the plot is 588 wide)
    const label = screen.getByText('Stop 92.00 · −8%')
    expect([label.getAttribute('text-anchor'), Number(label.getAttribute('x')) <= 588]).toEqual(['end', true])
    // a stop above every high still lands on the price panel (210 tall)
    const above = render(<CandleChart bars={bars} indicator={null} stop={110} {...trade} ariaLabel="HD" />)
    const y1 = Number(above.container.querySelector('line[stroke="var(--serious)"]')?.getAttribute('y1'))
    expect(y1 >= 4 && y1 <= 206).toBe(true)
  })

  it('leaves out the stop and the indicator panel when the chart has none', () => {
    const { container } = render(<CandleChart bars={bars} indicator={null} stop={null} {...trade} ariaLabel="HD" />)
    expect(screen.queryByText(/^Stop/)).toBeNull()
    expect(container.querySelectorAll('[data-window]')).toHaveLength(1)
  })

  it('reads out a session from the keyboard', () => {
    render(<CandleChart bars={bars} indicator={rsi} stop={92} {...trade} ariaLabel="HD" />)
    fireEvent.keyDown(screen.getByRole('img', { name: 'HD' }), { key: 'End' })
    expect(screen.getByRole('status').textContent).toBe(
      'Thu 17 SepOpen104.00High105.00Low103.00Close104.40RSI(2)93.1')
  })

  it('has a table view that marks the buy and the sell', () => {
    render(<CandleTable bars={bars} indicator={rsi} entry={1} exit={3} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows).toHaveLength(5)
    expect(rows[0].textContent).toBe('DateOpenHighLowCloseRSI(2)Trade')
    expect(rows[2].textContent).toBe('Tue 15 Sep100.00101.5099.20101.00—Buy')
    expect(rows[4].textContent).toContain('Sell')
  })

  it('says so when there are no bars', () => {
    render(<CandleChart bars={[]} indicator={null} stop={null} {...trade} ariaLabel="HD" />)
    expect(screen.getByText('No chart for this trade.')).toBeTruthy()
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/charts/SlotsStrip.test.tsx src/charts/CandleChart.test.tsx`
Expected: `Test Files  2 failed (2)`, no tests run: `Failed to resolve import "./SlotsStrip"` and `Failed to resolve import "./CandleChart"`.

- [ ] **Step 3: Implement**

`web/src/charts/SlotsStrip.tsx`:

````tsx
// How much of a book's money is working: one column of slots per session, filled from the bottom.
import type { CSSProperties, PointerEvent } from 'react'
import type { Money } from '../lib/api'
import { monthLabel, shortDate } from '../lib/format'
import { bandLayout, clampTip, indexAt } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Hatch, Tip, useSvgId } from './marks'

const GAP = 2
const MAX_CELL = 16

export function SlotsStrip({ days, used, total, money, height = 108, ariaLabel }: {
  days: string[]; used: number[]; total: number; money: Money; height?: number; ariaLabel: string
}) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(days.length)
  const hatch = useSvgId('slots')
  if (days.length === 0 || total <= 0) return <Empty>No sessions yet.</Empty>

  const plotH = height - 20
  const cell = Math.min(MAX_CELL, (plotH - (total - 1) * GAP) / total)
  const layout = bandLayout(days.length, width, Infinity, 0.84)
  const rowY = (r: number) => plotH - (r + 1) * cell - r * GAP // row 0 is the bottom one
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(indexAt(event.clientX - box.left, days.length, width))
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {money === 'paper' && <Hatch id={hatch} color="var(--s2)" />}
        {hover != null && (
          <rect x={hover * layout.step} y={rowY(total - 1) - 3} width={layout.step} height={plotH - rowY(total - 1) + 3}
            fill="var(--ink1)" fillOpacity={0.06} rx={2} />
        )}
        {days.map((day, i) => Array.from({ length: total }, (_, r) => r < used[i]
          ? (
            <rect key={`${day}-${r}`} data-mark={money} x={layout.left(i)} y={rowY(r)} width={layout.mark} height={cell}
              rx={2} fill={money === 'real' ? 'var(--s2)' : `url(#${hatch})`}
              stroke={money === 'paper' ? 'var(--s2)' : undefined} strokeWidth={money === 'paper' ? 1 : undefined} />
          ) : (
            <rect key={`${day}-${r}`} data-mark="free" x={layout.left(i) + 0.5} y={rowY(r) + 0.5}
              width={Math.max(0, layout.mark - 1)} height={Math.max(0, cell - 1)} rx={2} fill="none"
              stroke="var(--line2)" />
          )))}
        <text x={0} y={height - 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
          {monthLabel(days[0], true)}
        </text>
        <text x={width} y={height - 4} textAnchor="end" fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
          {monthLabel(days[days.length - 1], true)}
        </text>
      </svg>
      {hover != null && (
        <Tip left={clampTip(layout.center(hover), width)} title={shortDate(days[hover])}
          rows={[['In use', `${used[hover]} of ${total}`]]} />
      )}
    </div>
  )
}

export function SlotsTable({ days, used, total }: { days: string[]; used: number[]; total: number }) {
  return (
    <div className="table-scroll overflow-y-auto" style={{ maxHeight: 180 }}>
      <table className="tbl" style={{ '--row': '34px' } as CSSProperties}>
        <thead><tr><th>Session</th><th className="r">In use</th></tr></thead>
        <tbody>
          {days.map((day, i) => (
            <tr key={day}><td>{shortDate(day)}</td><td className="r num">{used[i]} of {total}</td></tr>
          )).reverse()}
        </tbody>
      </table>
    </div>
  )
}
````

`web/src/charts/CandleChart.tsx`:

````tsx
// One trade, bar by bar: daily candles with the buy, the sell, the holding window and the stop, and an optional
// indicator panel underneath on the same time axis (a small multiple, never a second y axis).
import { max, min } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import { line } from 'd3-shape'
import type { CSSProperties, PointerEvent } from 'react'
import { monthLabel, num, pct, shortDate } from '../lib/format'
import { bandLayout, candleShapes, clampTip, indexAt, tickIndices } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Tip } from './marks'

export interface CandleBar { date: string; open: number; high: number; low: number; close: number }
export interface CandleIndicator { label: string; values: (number | null)[]; lines: { value: number; label: string }[] }

interface Props {
  bars: CandleBar[]
  indicator: CandleIndicator | null
  stop: number | null
  entry: number // index of the entry bar
  exit: number // index of the exit bar
  entryPrice: number
  exitPrice: number
  height?: number // the price panel
  ariaLabel: string
}

const AXIS_W = 52
const STOP_LABEL_W = 120 // "Stop 1,234.56 · −12%" at 11px
const HALO = { stroke: 'var(--panel)', strokeWidth: 3, paintOrder: 'stroke' } as const // text readable over candles
const IND_H = 76
const IND_GAP = 14
const price = (v: number) => num(v, v < 10 ? 2 : 0)

export function CandleChart(props: Props) {
  const { bars, indicator, stop, entry, exit, height = 210 } = props
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(bars.length)
  if (bars.length === 0) return <Empty>No chart for this trade.</Empty>

  const plotW = Math.max(40, width - AXIS_W)
  const layout = bandLayout(bars.length, plotW, 12, 0.6)
  const low = Math.min(min(bars, (b) => b.low) ?? 0, stop ?? Infinity)
  const high = Math.max(max(bars, (b) => b.high) ?? 1, stop ?? -Infinity)
  const pad = (high - low) * 0.16 || 1 // room for the markers and their labels
  const y = scaleLinear().domain([low - pad, high + pad]).nice(4).range([height - 4, 6])
  const candles = candleShapes(bars, plotW, y)
  const panelTop = height + IND_GAP
  const total = height + (indicator ? IND_GAP + IND_H : 0) + 20
  const x0 = entry * layout.step
  const x1 = (exit + 1) * layout.step
  const at = (i: number) => layout.center(i)
  const anchor = (x: number) => (x < 44 ? 'start' : x > plotW - 44 ? 'end' : 'middle')

  const readings = indicator ? [...indicator.values, ...indicator.lines.map((l) => l.value)] : []
  const iy = scaleLinear()
    .domain([min(readings, (v) => v ?? undefined) ?? 0, max(readings, (v) => v ?? undefined) ?? 100])
    .nice(2)
    .range([panelTop + IND_H - 4, panelTop + 4])
  const indicatorPath = indicator
    ? line<number | null>().defined((v) => v != null).x((_, i) => at(i)).y((v) => iy(v as number))(
      indicator.values) ?? ''
    : ''

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(indexAt(event.clientX - box.left, bars.length, plotW))
  }
  const stopBelow = stop != null ? pct((stop / props.entryPrice - 1) * 100, 0) : ''
  // the buy label sits under its bar and the sell label over its bar; when the two bars are close and the price
  // fell (a stop), the sell label moves up so the two never print over each other
  const buyY = y(bars[entry].low) + 30
  const sellY = Math.min(y(bars[exit].high) - 20, Math.abs(at(exit) - at(entry)) < 96 ? buyY - 18 : Infinity)
  // the stop label goes left of the holding window when there's room, else right of it, else inside it under the
  // line: never into the price axis
  const stopSide = x0 > 150 ? 'left' : plotW - x1 >= STOP_LABEL_W + 8 ? 'right' : 'inside'
  const bar = hover == null ? null : bars[hover]

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={total} role="img" aria-label={props.ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {y.ticks(4).map((t) => (
          <g key={t}>
            <line x1={0} x2={plotW} y1={y(t)} y2={y(t)} stroke="var(--line)" />
            <text x={plotW + 10} y={y(t) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>{price(t)}</text>
          </g>
        ))}
        <rect data-window="price" x={x0} y={4} width={x1 - x0} height={height - 8} fill="var(--ink1)" fillOpacity={0.045} />
        {stop != null && (
          <g>
            <line x1={x0} x2={x1} y1={y(stop)} y2={y(stop)} stroke="var(--serious)" strokeWidth={1.5} />
            <text x={stopSide === 'left' ? x0 - 8 : stopSide === 'right' ? x1 + 8 : x1 - 6}
              y={y(stop) + (stopSide === 'inside' ? 16 : 4)} textAnchor={stopSide === 'right' ? 'start' : 'end'}
              fill="var(--ink2)" {...HALO} style={{ font: '500 11px var(--k-sans)' }}>
              Stop {num(stop)} · {stopBelow}
            </text>
          </g>
        )}
        {candles.map((c, i) => (
          <g key={bars[i].date} data-candle="">
            <line x1={c.x} x2={c.x} y1={c.wickTop} y2={c.wickBottom} stroke={c.up ? 'var(--ink2)' : 'var(--ink3)'} />
            <rect x={c.x - c.w / 2} y={c.bodyTop} width={c.w} height={c.bodyH} rx={1}
              fill={c.up ? 'var(--panel)' : 'var(--ink3)'} stroke={c.up ? 'var(--ink2)' : 'none'}
              strokeWidth={c.up ? 1.25 : 0} />
          </g>
        ))}
        <g>
          <path d={`M${at(entry)} ${y(bars[entry].low) + 6}l6 9h-12z`} fill="var(--acc)" />
          <text x={at(entry)} y={buyY} textAnchor={anchor(at(entry))} fill="var(--ink1)" {...HALO}
            style={{ font: '500 11px var(--k-mono)' }}>
            Buy {num(props.entryPrice)}
          </text>
          <path d={`M${at(exit)} ${y(bars[exit].high) - 6}l6 -9h-12z`} fill="var(--acc)" />
          <text x={at(exit)} y={sellY} textAnchor={anchor(at(exit))} fill="var(--ink1)" {...HALO}
            style={{ font: '500 11px var(--k-mono)' }}>
            Sell {num(props.exitPrice)}
          </text>
        </g>
        {indicator && (
          <g>
            <line x1={0} x2={width} y1={panelTop - IND_GAP / 2} y2={panelTop - IND_GAP / 2} stroke="var(--line)" />
            <rect data-window="indicator" x={x0} y={panelTop} width={x1 - x0} height={IND_H} fill="var(--ink1)"
              fillOpacity={0.045} />
            {indicator.lines.map((l) => (
              <g key={l.label}>
                <line x1={0} x2={plotW} y1={iy(l.value)} y2={iy(l.value)} stroke="var(--ref)"
                  strokeDasharray="1.5 3" strokeLinecap="round" />
                <text x={plotW + 10} y={iy(l.value) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
                  {l.value}
                </text>
              </g>
            ))}
            <path d={indicatorPath} fill="none" stroke="var(--ink1)" strokeWidth={1.5} strokeLinejoin="round" />
            <text x={plotW + 10} y={panelTop + IND_H / 2 + 4} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}>
              {indicator.label}
            </text>
          </g>
        )}
        {tickIndices(bars.length, width < 480 ? 3 : 5).map((i) => (
          <text key={i} x={at(i)} y={total - 4} textAnchor={anchor(at(i))} fill="var(--ink3)"
            style={{ font: '11px var(--k-mono)' }}>
            {monthLabel(bars[i].date, true)}
          </text>
        ))}
        {hover != null && (
          <line x1={at(hover)} x2={at(hover)} y1={4} y2={total - 20} stroke="var(--line2)" />
        )}
      </svg>
      {bar != null && hover != null && (
        <Tip left={clampTip(at(hover), width)} title={shortDate(bar.date)} rows={[
          ['Open', num(bar.open)], ['High', num(bar.high)], ['Low', num(bar.low)], ['Close', num(bar.close)],
          ...(indicator ? [[indicator.label, indicator.values[hover] == null ? '—'
            : num(indicator.values[hover] as number, 1)] as [string, string]] : []),
        ]} />
      )}
    </div>
  )
}

export function CandleTable({ bars, indicator, entry, exit }: {
  bars: CandleBar[]; indicator: CandleIndicator | null; entry: number; exit: number
}) {
  return (
    <div className="table-scroll overflow-y-auto" style={{ maxHeight: 300 }}>
      <table className="tbl" style={{ '--row': '34px', minWidth: 460 } as CSSProperties}>
        <thead>
          <tr>
            <th>Date</th><th className="r">Open</th><th className="r">High</th><th className="r">Low</th>
            <th className="r">Close</th>{indicator && <th className="r">{indicator.label}</th>}<th>Trade</th>
          </tr>
        </thead>
        <tbody>
          {bars.map((b, i) => (
            <tr key={b.date}>
              <td>{shortDate(b.date)}</td>
              <td className="r num">{num(b.open)}</td><td className="r num">{num(b.high)}</td>
              <td className="r num">{num(b.low)}</td><td className="r num">{num(b.close)}</td>
              {indicator && (
                <td className="r num">{indicator.values[i] == null ? '—' : num(indicator.values[i] as number, 1)}</td>
              )}
              <td>{[i === entry && 'Buy', i === exit && 'Sell'].filter(Boolean).join(' · ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
````


- [ ] **Step 4: Run everything and watch it pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit`
Expected: `Tests  74 passed (74)` (`SlotsStrip.test.tsx` 5, `CandleChart.test.tsx` 5); tsc prints nothing.

- [ ] **Step 5: Commit**

```bash
git add web/src/charts/SlotsStrip.tsx web/src/charts/SlotsStrip.test.tsx web/src/charts/CandleChart.tsx web/src/charts/CandleChart.test.tsx
git commit -m "feat(charts): slots strip and candle chart with an indicator panel on the same time axis"
```

---

### Task 9: The chart kit, part 3: the worth scatter and the month grid

**Files:**
- Create: `web/src/charts/Scatter.tsx`, `web/src/charts/MonthGrid.tsx`
- Test: `web/src/charts/Scatter.test.tsx`, `web/src/charts/MonthGrid.test.tsx`

**Interfaces:**
- Consumes: `clampTip`, `placeLabels`, `cellWash`, `yearSpans` (geometry); the Task 7 hooks and marks; `BookMark` (components/bits), `Icon`.
- Produces:
  - `Scatter({ points, height?, ariaLabel })` with `ScatterPoint { key, label, sub, period, x (worst drop, positive), y (yearly return), color, style: 'solid' | 'hatched' | 'dotted' }`: points (`data-point`), labels placed by `placeLabels` with leader lines when slid, a dotted "return = worst drop" guide, "↖ better"; when any label can't be placed clear, every label moves into a key under the chart (`<ul aria-label="Key">`). `ScatterTable({ points })`. Empty: "Not enough history yet. A yearly figure needs at least 90 days."
  - `MonthGrid({ months, bookLabel, money, ariaLabel })` with `MonthCell { month, book, long_term, ahead }`: a year row, a month row, a book row and a long-term row washed with `cellWash` (`data-cell="book" | "long_term"`, value printed in each), and an "Ahead?" row (✓ or −, with hidden "yes"/"no"); keyboard on the `role="group"`; it scrolls sideways inside its panel under 400 px. `MonthTable({ months, bookLabel })`. Empty: "No monthly history yet."

- [ ] **Step 1: Write the failing tests**

`web/src/charts/Scatter.test.tsx`:

````tsx
import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Scatter, type ScatterPoint, ScatterTable } from './Scatter'

const points: ScatterPoint[] = [
  { key: 'backtest', label: 'Backtest', sub: '+23.4%/yr · 2006–2020', period: '2006–2020', x: 11.7, y: 23.4,
    color: 'var(--s2)', style: 'dotted' },
  { key: 'book', label: 'Paper book', sub: '+19.0%/yr · 12 months', period: '12 months', x: 5.6, y: 19,
    color: 'var(--s2)', style: 'hatched' },
  { key: 'long_term', label: 'Long-term accounts', sub: '+21.4%/yr · 12 months', period: '12 months', x: 9, y: 21.4,
    color: 'var(--s1)', style: 'solid' },
]

describe('Scatter', () => {
  afterEach(() => vi.restoreAllMocks())

  it('draws and labels every point in its money style, with the guide line', () => {
    const { container } = render(<Scatter points={points} ariaLabel="Worth" />)
    const marks = [...container.querySelectorAll('[data-point]')].map((m) => m.getAttribute('data-point'))
    expect(marks).toEqual(['dotted', 'hatched', 'solid'])
    for (const p of points) {
      expect(screen.getByText(p.label)).toBeTruthy()
      expect(screen.getByText(p.sub)).toBeTruthy()
    }
    expect(screen.getByText('return = worst drop')).toBeTruthy()
    expect(screen.getByText('↖ better')).toBeTruthy()
  })

  it('moves the labels into a key under the chart when they would collide on it', () => {
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(220) // a narrow phone panel
    render(<Scatter points={points} ariaLabel="Worth" />)
    const key = screen.getByRole('list', { name: 'Key' })
    expect(within(key).getAllByRole('listitem').map((li) => li.textContent)).toEqual(points.map((p) => p.label + p.sub))
  })

  it('reads out a point from the keyboard', () => {
    render(<Scatter points={points} ariaLabel="Worth" />)
    fireEvent.keyDown(screen.getByRole('img', { name: 'Worth' }), { key: 'Home' })
    expect(screen.getByRole('status').textContent).toBe('Backtest · 2006–2020Yearly return+23.4%Worst drop−11.7%')
  })

  it('has a table view', () => {
    render(<ScatterTable points={points} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows.map((r) => r.textContent)).toEqual([
      'LineYearly returnWorst dropOver',
      'Backtest+23.4%−11.7%2006–2020',
      'Paper book+19.0%−5.6%12 months',
      'Long-term accounts+21.4%−9.0%12 months',
    ])
  })

  it('says so when there is nothing to plot', () => {
    render(<Scatter points={[]} ariaLabel="Worth" />)
    expect(screen.getByText('Not enough history yet. A yearly figure needs at least 90 days.')).toBeTruthy()
  })
})
````

`web/src/charts/MonthGrid.test.tsx`:

````tsx
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MonthGrid, MonthTable } from './MonthGrid'

const months = [
  { month: '2025-11', book: null, long_term: null, ahead: null },
  { month: '2025-12', book: 1.2, long_term: -0.8, ahead: true },
  { month: '2026-01', book: 0.3, long_term: 2.9, ahead: false },
]

describe('MonthGrid', () => {
  it('washes each month by the size of its move and prints the value', () => {
    const { container } = render(<MonthGrid months={months} bookLabel="Real" money="real" ariaLabel="Months" />)
    const cells = [...container.querySelectorAll<HTMLElement>('[data-cell="book"]')]
    expect(cells.map((c) => c.textContent)).toEqual(['—', '+1.2', '+0.3'])
    expect(cells[1].style.background).toContain('var(--up) 22%')
    expect(cells[2].style.background).toBe('var(--panel2)') // a small move stays neutral
    const lt = [...container.querySelectorAll<HTMLElement>('[data-cell="long_term"]')]
    expect(lt[1].style.background).toContain('var(--down) 18%')
    expect(screen.getByText('2025')).toBeTruthy()
    expect(screen.getByText('2026')).toBeTruthy()
  })

  it('says whether the book was ahead in words as well as marks', () => {
    const { container } = render(<MonthGrid months={months} bookLabel="Real" money="real" ariaLabel="Months" />)
    const ahead = [...container.querySelectorAll('[data-cell="ahead"]')].map((c) => c.textContent)
    expect(ahead).toEqual(['', 'yes', '−no'])
  })

  it('reads out a month from the keyboard', () => {
    render(<MonthGrid months={months} bookLabel="Real" money="real" ariaLabel="Months" />)
    fireEvent.keyDown(screen.getByRole('group', { name: 'Months' }), { key: 'End' })
    expect(screen.getByRole('status').textContent).toBe('Jan 2026Real+0.3%Long-term+2.9%Ahead?no')
  })

  it('has a table view', () => {
    render(<MonthTable months={months} bookLabel="Real" />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows.map((r) => r.textContent)).toEqual([
      'MonthRealLong-termAhead?', 'Nov 2025———', 'Dec 2025+1.2%−0.8%yes', 'Jan 2026+0.3%+2.9%no',
    ])
  })

  it('says so when there is no monthly history', () => {
    render(<MonthGrid months={[months[0]]} bookLabel="Real" money="real" ariaLabel="Months" />)
    expect(screen.getByText('No monthly history yet.')).toBeTruthy()
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/charts/Scatter.test.tsx src/charts/MonthGrid.test.tsx`
Expected: `Test Files  2 failed (2)`, no tests run: `Failed to resolve import "./Scatter"` and `Failed to resolve import "./MonthGrid"`.

- [ ] **Step 3: Implement**

`web/src/charts/Scatter.tsx`:

````tsx
// Is it worth it? Yearly return (up) against the worst drop along the way (right is worse), one labelled point per
// line of money, with a dotted "return = worst drop" guide.
import { max, min } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import type { CSSProperties, PointerEvent } from 'react'
import { MINUS, pct } from '../lib/format'
import { clampTip, placeLabels } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Hatch, Tip, useSvgId } from './marks'

export interface ScatterPoint {
  key: string
  label: string
  sub: string // the figure and period printed under the label
  period: string
  x: number // worst drop, a positive magnitude
  y: number // yearly return
  color: string
  style: 'solid' | 'hatched' | 'dotted' // real · paper · backtest or benchmark
}

const LEFT = 44
const BOTTOM = 22
const drop = (v: number) => (v === 0 ? '0%' : `${MINUS}${v}%`)

export function Scatter({ points, height = 262, ariaLabel }: { points: ScatterPoint[]; height?: number; ariaLabel: string }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(points.length)
  const hatch = useSvgId('worth')
  if (points.length === 0) return <Empty>Not enough history yet. A yearly figure needs at least 90 days.</Empty>

  const right = width - 8
  // headroom on the right of the points, where their labels go
  const x = scaleLinear().domain([0, Math.max(5, (max(points, (p) => p.x) ?? 0) * 1.4)]).nice(3).range([LEFT, right])
  const y = scaleLinear()
    .domain([Math.min(0, min(points, (p) => p.y) ?? 0), Math.max(5, (max(points, (p) => p.y) ?? 0) * 1.15)])
    .nice(3)
    .range([height - BOTTOM, 10])
  const guide = Math.min(x.domain()[1], y.domain()[1])
  // labels stay inside the plot, clear of the y axis on the left
  const labels = placeLabels(points.map((p) => ({
    x: x(p.x) - LEFT, y: y(p.y), w: Math.max(p.label.length * 6.8, p.sub.length * 6.6),
  })), right - LEFT, height - BOTTOM).map((l) => ({ ...l, x: l.x + LEFT }))
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    const px = event.clientX - box.left
    const py = event.clientY - box.top
    const distances = points.map((p) => Math.hypot(x(p.x) - px, y(p.y) - py))
    setHover(distances.indexOf(Math.min(...distances))) // the closest point
  }
  const p = hover == null ? null : points[hover]
  const direct = labels.every((l) => l.clear) // labels that would collide go in a key under the chart instead

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        <Hatch id={hatch} color="var(--s2)" />
        {y.ticks(3).map((t) => (
          <g key={`y${t}`}>
            <line x1={LEFT} x2={right} y1={y(t)} y2={y(t)} stroke={t === 0 ? 'var(--line2)' : 'var(--line)'} />
            <text x={LEFT - 8} y={y(t) + 4} textAnchor="end" fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
              {pct(t, 0)}
            </text>
          </g>
        ))}
        {x.ticks(3).map((t) => (
          <text key={`x${t}`} x={x(t)} y={height - 4} textAnchor="middle" fill="var(--ink3)"
            style={{ font: '11px var(--k-mono)' }}>
            {drop(t)}
          </text>
        ))}
        <line x1={x(0)} y1={y(0)} x2={x(guide)} y2={y(guide)} stroke="var(--ref)" strokeDasharray="1.5 3"
          strokeLinecap="round" />
        <text x={x(guide) - 4} y={y(guide) + 16} textAnchor="end" fill="var(--ink3)"
          style={{ font: '11px var(--k-sans)' }}>
          return = worst drop
        </text>
        <text x={LEFT + 8} y={22} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}>↖ better</text>
        {points.map((pt, i) => (
          <g key={pt.key}>
            {hover === i && <circle cx={x(pt.x)} cy={y(pt.y)} r={10} fill="none" stroke="var(--ink3)" />}
            {direct && labels[i].leader && (
              <line x1={x(pt.x)} y1={y(pt.y)} x2={labels[i].x + (labels[i].anchor === 'end' ? 3 : -3)}
                y2={labels[i].y + 14} stroke="var(--line2)" />
            )}
            <circle data-point={pt.style} cx={x(pt.x)} cy={y(pt.y)} r={6} strokeWidth={2}
              fill={pt.style === 'solid' ? pt.color : pt.style === 'hatched' ? `url(#${hatch})` : 'var(--panel)'}
              stroke={pt.style === 'solid' ? 'var(--panel)' : pt.color}
              strokeDasharray={pt.style === 'dotted' ? '2 2' : undefined} />
            {direct && (
              <>
                <text x={labels[i].x} y={labels[i].y + 11} textAnchor={labels[i].anchor} fill="var(--ink1)"
                  style={{ font: '500 12px var(--k-sans)' }}>
                  {pt.label}
                </text>
                <text x={labels[i].x} y={labels[i].y + 25} textAnchor={labels[i].anchor} fill="var(--ink3)"
                  style={{ font: '11px var(--k-mono)' }}>
                  {pt.sub}
                </text>
              </>
            )}
          </g>
        ))}
      </svg>
      {!direct && (
        <ul aria-label="Key" className="flex flex-wrap gap-x-4 gap-y-1.5 mt-2 text-xs">
          {points.map((pt) => (
            <li key={pt.key} className="inline-flex items-center gap-1.5">
              <svg width={12} height={12} aria-hidden="true" style={{ flex: 'none' }}>
                <circle cx={6} cy={6} r={4.5} strokeWidth={1.5}
                  fill={pt.style === 'solid' ? pt.color : pt.style === 'hatched' ? `url(#${hatch})` : 'var(--panel)'}
                  stroke={pt.color} strokeDasharray={pt.style === 'dotted' ? '1.5 1.5' : undefined} />
              </svg>
              <span className="font-medium">{pt.label}</span>
              <span className="num text-ink3">{pt.sub}</span>
            </li>
          ))}
        </ul>
      )}
      {p != null && (
        <Tip left={clampTip(x(p.x), width)} title={`${p.label} · ${p.period}`}
          rows={[['Yearly return', pct(p.y, 1)], ['Worst drop', pct(-p.x, 1)]]} />
      )}
    </div>
  )
}

export function ScatterTable({ points }: { points: ScatterPoint[] }) {
  return (
    <div className="table-scroll">
      <table className="tbl" style={{ '--row': '40px' } as CSSProperties}>
        <thead>
          <tr><th>Line</th><th className="r">Yearly return</th><th className="r">Worst drop</th><th>Over</th></tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.key}>
              <td>{p.label}</td><td className="r num">{pct(p.y, 1)}</td><td className="r num">{pct(-p.x, 1)}</td>
              <td>{p.period}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
````

`web/src/charts/MonthGrid.tsx`:

````tsx
// Month by month: the book's monthly returns over the long-term accounts', as a diverging grid with an
// "ahead?" row. Colour is never alone: every cell prints its value and the ahead row says yes or no.
import type { CSSProperties, PointerEvent } from 'react'
import { BookMark } from '../components/bits'
import { Icon } from '../components/Icon'
import type { Money } from '../lib/api'
import { monthLabel, pct } from '../lib/format'
import { cellWash, clampTip, yearSpans } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Tip } from './marks'

export interface MonthCell {
  month: string // "2026-09"
  book: number | null
  long_term: number | null
  ahead: boolean | null
}

const LABEL_W = 76
const MIN_W = 400 // narrower than this, the grid scrolls sideways inside its panel

const monthName = (m: string) => `${monthLabel(`${m}-01`)} ${m.slice(0, 4)}`
const cellText = (v: number) => pct(v, 1).replace('%', '')
const aheadText = (a: boolean | null) => (a == null ? '—' : a ? 'yes' : 'no')

function wash(value: number | null): string {
  const strength = cellWash(value)
  if (value == null) return 'transparent'
  if (strength == null) return 'var(--panel2)'
  return `color-mix(in srgb, var(${value > 0 ? '--up' : '--down'}) ${strength}%, transparent)`
}

function Cell({ kind, value, i }: { kind: 'book' | 'long_term'; value: number | null; i: number }) {
  return (
    <div data-cell={kind} data-i={i} className="num flex items-center justify-center rounded"
      style={{ height: 36, fontSize: 10, background: wash(value), color: value == null ? 'var(--ink3)' : 'var(--ink1)' }}>
      {value == null ? '—' : cellText(value)}
    </div>
  )
}

export function MonthGrid({ months, bookLabel, money, ariaLabel }: {
  months: MonthCell[]; bookLabel: string; money: Money; ariaLabel: string
}) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(480)
  const { index: hover, set: setHover, onKey } = useIndex(months.length)
  if (!months.some((m) => m.book != null || m.long_term != null)) return <Empty>No monthly history yet.</Empty>

  const grid: CSSProperties = {
    display: 'grid', gridTemplateColumns: `${LABEL_W}px repeat(${months.length}, minmax(0, 1fr))`, gap: 3,
    alignItems: 'center', minWidth: MIN_W,
  }
  const inner = Math.max(width, MIN_W)
  const col = (inner - LABEL_W) / months.length
  const onPointer = (event: PointerEvent<HTMLDivElement>) => {
    const cell = (event.target as HTMLElement).closest<HTMLElement>('[data-i]')
    setHover(cell ? Number(cell.dataset.i) : null)
  }
  const m = hover == null ? null : months[hover]

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <div className="table-scroll">
        <div role="group" aria-label={ariaLabel} tabIndex={0} style={grid} onKeyDown={onKey}
          onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onBlur={() => setHover(null)}>
          <div />
          {yearSpans(months.map((x) => x.month)).map((y) => (
            <div key={y.year} className="text-ink3" style={{ gridColumn: `span ${y.span}`, fontSize: 10,
              borderBottom: '1px solid var(--line)', paddingBottom: 3 }}>
              {y.year}
            </div>
          ))}
          <div />
          {months.map((x) => (
            <div key={x.month} className="text-ink3 text-center" style={{ fontSize: 10 }}>{monthLabel(`${x.month}-01`)}</div>
          ))}
          <div className="flex items-center gap-1.5 text-xs text-ink2 whitespace-nowrap">
            <BookMark kind={money} color="var(--s2)" size={9} />{bookLabel}
          </div>
          {months.map((x, i) => <Cell key={x.month} kind="book" value={x.book} i={i} />)}
          <div className="flex items-center gap-1.5 text-xs text-ink2 whitespace-nowrap">
            <BookMark kind="real" color="var(--s1)" size={9} />Long-term
          </div>
          {months.map((x, i) => <Cell key={x.month} kind="long_term" value={x.long_term} i={i} />)}
          <div className="text-xs text-ink3">Ahead?</div>
          {months.map((x, i) => (
            <div key={x.month} data-cell="ahead" data-i={i} className="flex justify-center"
              style={{ color: x.ahead ? 'var(--good)' : 'var(--ink3)' }}>
              {x.ahead === true && <Icon name="check" size={14} />}
              {x.ahead === false && <span aria-hidden="true" className="text-xs">−</span>}
              {x.ahead != null && <span className="sr-only">{aheadText(x.ahead)}</span>}
            </div>
          ))}
        </div>
      </div>
      {m != null && hover != null && (
        <Tip left={clampTip(LABEL_W + (hover + 0.5) * col, width)} top={-8} title={monthName(m.month)} rows={[
          [bookLabel, m.book == null ? '—' : pct(m.book, 1)],
          ['Long-term', m.long_term == null ? '—' : pct(m.long_term, 1)],
          ['Ahead?', aheadText(m.ahead)],
        ]} />
      )}
    </div>
  )
}

export function MonthTable({ months, bookLabel }: { months: MonthCell[]; bookLabel: string }) {
  return (
    <div className="table-scroll overflow-y-auto" style={{ maxHeight: 220 }}>
      <table className="tbl" style={{ '--row': '34px' } as CSSProperties}>
        <thead>
          <tr><th>Month</th><th className="r">{bookLabel}</th><th className="r">Long-term</th><th>Ahead?</th></tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={m.month}>
              <td>{monthName(m.month)}</td>
              <td className="r num">{m.book == null ? '—' : pct(m.book, 1)}</td>
              <td className="r num">{m.long_term == null ? '—' : pct(m.long_term, 1)}</td>
              <td>{aheadText(m.ahead)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
````


- [ ] **Step 4: Run everything and watch it pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit`
Expected: `Tests  84 passed (84)` (`Scatter.test.tsx` 5, `MonthGrid.test.tsx` 5); tsc prints nothing.

- [ ] **Step 5: Commit**

```bash
git add web/src/charts/Scatter.tsx web/src/charts/Scatter.test.tsx web/src/charts/MonthGrid.tsx web/src/charts/MonthGrid.test.tsx
git commit -m "feat(charts): return-against-worst-drop scatter with collision-free labels, and the month grid"
```

---

### Task 10: API types, hooks, the strategy list and the breadcrumb

**Files:**
- Modify (replace the whole file): `web/src/lib/api.ts`, `web/src/main.tsx`, `web/src/test/renderApp.tsx`, `web/src/router.tsx`, `web/src/shell/Shell.tsx`, `web/src/pages/home/BooksPanel.tsx`
- Create: `web/src/pages/strategies/Strategies.tsx`
- Test: `web/src/pages/strategies/Strategies.test.tsx` (new), `web/src/shell/Shell.test.tsx` (replace the whole file)

**Interfaces:**
- Consumes: the generated fixtures `strategies.json` and `strategy-rsi2.json` (Task 6); `BandBar` (Home).
- Produces:
  - `api.ts`: types mirroring `views/strategy.py` by hand (`BookChip`, `StrategyCard`, `StrategiesView`, `Step`, `Expected`, `Bucket`, `ScoreRow`, `OtherBook`, `Behaving`, `FunnelLine`, `Funnel`, `WatchItem`, `Slots`, `RecentTrade`, `Bar`, `Indicator`, `AnatomyChart`, `Anatomy`, `WorthPoint`, `Month`, `Monthly`, `TradeRow`, `StrategyView`, `Verdict`); `HttpError(status, message)` thrown by `getJson`; `useStrategies()` (key `['strategies']`); `useStrategy(id, book)` (key `['strategy', id, book]`, keeps the page up while switching Real | Paper).
  - `main.tsx`: queries retry once, never on a 404.
  - `renderApp(path, data?, fetchImpl?)`: `data.strategies` (`null` leaves it unanswered) and `data.strategy: { id, book, view }[]`; exports `strategiesFixture` and `strategyFixture`, both checked with `satisfies Widen<…>`.
  - `BooksPanel.tsx`: `VERDICT` is exported.
  - `Strategies.tsx`: `MONEY_WORD`, `chipText(book)` ("Real · running · 4 open"), `BookChips({ books })`, `verdictText(card)`, `Strategies()`; cards in 2 columns (1 below 900 px); empty "No strategies yet."
  - `Shell.tsx`: `crumbs(pathname) -> { group, page, parent }`; on `/strategies/rsi2` the breadcrumb reads Trading › Strategies, with Strategies linking back.
  - `router.tsx`: `/strategies` renders `Strategies` (the placeholder goes).

- [ ] **Step 1: Write the failing tests**

`web/src/pages/strategies/Strategies.test.tsx`:

````tsx
import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderApp, strategiesFixture } from '../../test/renderApp'
import { chipText, verdictText } from './Strategies'

describe('Strategies', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows a card per strategy with its books, its band and a way in', async () => {
    renderApp('/strategies')
    expect(await screen.findByRole('heading', { level: 1, name: 'Strategies' })).toBeTruthy()
    expect(screen.getByText('How each strategy trades, and whether it is behaving the way its backtest said it would.'))
      .toBeTruthy()
    const cards = screen.getAllByRole('article')
    expect(cards).toHaveLength(4)
    const rsi2 = within(cards[0])
    expect(rsi2.getByRole('heading', { name: 'Mean reversion' })).toBeTruthy()
    expect(rsi2.getByText('Real · running · 4 open')).toBeTruthy()
    expect(rsi2.getByText('Paper · running · 5 open')).toBeTruthy()
    expect(cards[0].textContent).toContain('In band · ▲ up +0.79%')
    expect(rsi2.getByText('Per trade vs expected · real book')).toBeTruthy()
    expect(rsi2.getByText('34 closed trades')).toBeTruthy()
    expect(rsi2.getByRole('link', { name: 'Open Mean reversion' }).getAttribute('href')).toBe('/strategies/rsi2')
  })

  it('words the verdict the way Home does', () => {
    const [rsi2, ibs, leader] = strategiesFixture.strategies
    expect(verdictText(ibs)).toBe('Too early · 7 trades')
    expect(verdictText(leader)).toBe('Below band')
    expect(verdictText(rsi2)).toBe('In band')
    expect(verdictText({ ...ibs, verdict: 'none', trades: 0 })).toBe('No closed trades yet')
    expect(verdictText({ ...ibs, verdict: 'none', trades: 3 })).toBe('No backtest to compare with')
    expect(chipText(rsi2.books[1])).toBe('Paper · running · 5 open')
  })

  it('says so when there are no strategies yet', async () => {
    renderApp('/strategies', { strategies: { strategies: [] } })
    expect(await screen.findByText('No strategies yet.')).toBeTruthy()
  })

  it('says it is loading while the list is on its way', async () => {
    renderApp('/strategies', { strategies: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading strategies…')).toBeTruthy()
  })

  it('says so when the list could not load', async () => {
    renderApp('/strategies', { strategies: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Strategies couldn’t load: network is off in tests')
  })
})
````

`web/src/shell/Shell.test.tsx`:

````tsx
import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderApp, shellFixture } from '../test/renderApp'
import { crumbs } from './Shell'

describe('shell', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('greets by name in the profile time zone', async () => {
    renderApp('/')
    expect(await screen.findByText('Good evening,')).toBeTruthy() // 17:08 in New York
    expect(screen.getByText('Alex')).toBeTruthy()
  })

  it('lists every source and flags the stale one without relying on colour', async () => {
    renderApp('/')
    const sidebar = await screen.findByRole('complementary', { name: 'Sidebar' })
    expect(within(sidebar).getByText('Savings')).toBeTruthy()
    expect(within(sidebar).getByText('26h')).toBeTruthy()
    expect(within(sidebar).getAllByText('stale')).toHaveLength(1)
  })

  it('marks the current page and navigates', async () => {
    renderApp('/')
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    expect(within(nav).getByRole('link', { name: /Home/ }).getAttribute('aria-current')).toBe('page')
    fireEvent.click(within(nav).getByRole('link', { name: /Strategies/ }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Strategies' })).toBeTruthy()
    expect(within(nav).getByRole('link', { name: /Strategies/ }).getAttribute('aria-current')).toBe('page')
  })

  it('themes the whole document from the profile, and the toggle flips it', async () => {
    renderApp('/', { shell: { ...shellFixture, app: { ...shellFixture.app, theme: 'light', accent: 'slate' } } })
    await screen.findByText('Alex')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(document.documentElement.dataset.accent).toBe('slate')
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    window.localStorage.clear()
  })

  it('opens and closes the phone drawer, keeping keyboard focus in step', async () => {
    const { container } = renderApp('/')
    const menu = await screen.findByRole('button', { name: 'Open menu' })
    const frame = container.querySelector('.shell') as HTMLElement
    const sidebar = screen.getByRole('complementary', { name: 'Sidebar' })
    expect(menu.getAttribute('aria-controls')).toBe(sidebar.id)
    expect(menu.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(menu)
    expect(menu.getAttribute('aria-expanded')).toBe('true')
    expect(frame.dataset.drawer).toBe('open')
    expect(sidebar.contains(document.activeElement)).toBe(true) // focus moved into the drawer
    fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' })
    expect(menu.getAttribute('aria-expanded')).toBe('false')
    expect(frame.dataset.drawer).toBe('closed')
    expect(document.activeElement).toBe(menu)
  })

  it('keeps the section in the breadcrumb on a page inside it', () => {
    expect(crumbs('/strategies')).toEqual({ group: 'Trading', page: 'Strategies', parent: null })
    expect(crumbs('/strategies/rsi2')).toEqual({ group: 'Trading', page: 'Strategies', parent: '/strategies' })
    expect(crumbs('/nowhere')).toEqual({ group: 'kestrel', page: 'Not found', parent: null })
  })

  it('shows an unknown path as not found inside the shell', async () => {
    renderApp('/nowhere')
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeTruthy()
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/pages/strategies/Strategies.test.tsx src/shell/Shell.test.tsx`
Expected: `Failed to resolve import "./Strategies"`, and in `Shell.test.tsx` `Tests  1 failed | 6 passed (7)` with `TypeError: crumbs is not a function`. (`marks the current page and navigates` passes against the Phase 2 placeholder too: its heading is also "Strategies".)

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

`web/src/main.tsx`:

````tsx
import '@fontsource/geist/latin-400.css'
import '@fontsource/geist/latin-500.css'
import '@fontsource/geist/latin-600.css'
import '@fontsource/geist-mono/latin-400.css'
import '@fontsource/geist-mono/latin-500.css'
import '@fontsource/geist-mono/latin-600.css'
import './styles/tokens.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HttpError } from './lib/api'
import { createAppRouter } from './router'

// one retry for a blip; never for a 404 (an unknown strategy won't appear on a second try)
const retry = (failures: number, error: Error) => !(error instanceof HttpError && error.status === 404) && failures < 1
const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry } } })
const router = createAppRouter()

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
````

`web/src/test/renderApp.tsx`:

````tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, RouterProvider } from '@tanstack/react-router'
import { render } from '@testing-library/react'
import { vi } from 'vitest'
import type { HomeView, Money, ShellView, StrategiesView, StrategyView } from '../lib/api'
import { createAppRouter } from '../router'
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

interface Data {
  home?: HomeView
  shell?: ShellView
  strategies?: StrategiesView | null // null: leave it unanswered, so the page fetches (and the fetch fails)
  strategy?: { id: string; book: Money; view: StrategyView }[] // answers for GET /api/strategies/{id}?book=
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
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }))
  const view = render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...view, router, client }
}
````

`web/src/pages/home/BooksPanel.tsx`:

````tsx
import { BookMark, Delta, Missing, MoneyBadge, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { BookRow } from '../../lib/api'
import { money, pct, shortDate, signedMoney, sinceLabel, timeHM } from '../../lib/format'

/** The per-trade result against its expected 95% band: dotted band, zero tick, a dot for the actual. */
export function BandBar({ lo, hi, actual }: { lo: number; hi: number; actual: number }) {
  const W = 110
  const low = Math.min(lo, actual, 0)
  const high = Math.max(hi, actual, 0)
  const pad = (high - low) * 0.15 || 1
  const x = (v: number) => ((v - (low - pad)) / (high + pad - (low - pad))) * W
  return (
    <svg width={W} height={14} aria-hidden="true" style={{ display: 'block', overflow: 'visible' }}>
      <line x1={0} x2={W} y1={7} y2={7} stroke="var(--line2)" />
      <rect x={x(lo)} y={2} width={Math.max(2, x(hi) - x(lo))} height={10} rx={3} fill="var(--ink1)" fillOpacity={0.06}
        stroke="var(--ref)" strokeDasharray="1.5 2.5" />
      <line x1={x(0)} x2={x(0)} y1={0} y2={14} stroke="var(--ink3)" />
      <circle cx={x(actual)} cy={7} r={4} fill="var(--ink1)" stroke="var(--panel)" strokeWidth={2} />
    </svg>
  )
}

function Slots({ used, total, money: kind }: { used: number; total: number; money: BookRow['money'] }) {
  return (
    <div className="flex gap-[3px]" role="img" aria-label={`${used} of ${total} slots in use`}>
      {Array.from({ length: total }, (_, i) => i < used
        ? <BookMark key={i} kind={kind} size={10} />
        : <span key={i} className="w-2.5 h-2.5 rounded-sm" style={{ boxShadow: 'inset 0 0 0 1px var(--line2)' }} />)}
    </div>
  )
}

export const VERDICT: Record<BookRow['verdict'], string> = {
  in_band: 'In band', below: 'Below band', above: 'Above band', early: 'Too early', none: '—',
}

export function BooksPanel({ books, tz, now }: { books: BookRow[]; tz: string; now: string }) {
  return (
    <Panel id="books" title="Books" subtitle="Every strategy, real and paper, side by side" span={12}
      actions={<div className="hidden md:flex items-center gap-4 text-xs text-ink2">
        <span className="inline-flex items-center gap-1.5"><BookMark kind="real" />Real money</span>
        <span className="inline-flex items-center gap-1.5"><BookMark kind="paper" />Paper</span>
        <span className="inline-flex items-center gap-1.5"><BookMark kind="expected" />Expected range</span>
      </div>}>
      <div className="table-scroll mt-4">
        <table className="tbl" style={{ minWidth: 900 }}>
          <thead>
            <tr>
              <th>Book</th><th>Money</th><th className="r">Value</th><th className="r">Today</th>
              <th className="r">Since start</th><th style={{ paddingLeft: 28 }}>Per trade vs expected</th>
              <th>Slots</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {books.map((b) => (
              <tr key={b.id}>
                <td>
                  <div className="flex items-center gap-3">
                    <BookMark kind={b.money} size={14} />
                    <div>
                      <div className="font-medium">{b.name}</div>
                      <div className="text-xs text-ink3 mt-0.5">{b.trades} trades · since {sinceLabel(b.started, now)}</div>
                    </div>
                  </div>
                </td>
                <td><MoneyBadge money={b.money} /></td>
                <td className="r num">{money(b.value)}</td>
                <td className="r">{b.day_change == null ? <Missing /> : <Delta value={b.day_change}>{signedMoney(b.day_change)}</Delta>}</td>
                <td className="r">{b.since_pct == null ? <Missing /> : <Delta value={b.since_pct} digits={1}>{pct(b.since_pct)}</Delta>}</td>
                <td style={{ paddingLeft: 28 }}>
                  {b.band_lo != null && b.band_hi != null && b.per_trade_pct != null && (
                    <BandBar lo={b.band_lo} hi={b.band_hi} actual={b.per_trade_pct} />
                  )}
                  <div className="text-[11px] mt-1.5 flex items-center gap-1.5 whitespace-nowrap"
                    style={{ color: b.verdict === 'below' ? 'var(--ink1)' : 'var(--ink3)' }}>
                    {b.verdict === 'below' && <Icon name="alert" size={12} style={{ color: 'var(--warn)' }} />}
                    {VERDICT[b.verdict]}
                    {b.verdict === 'early' && ` · ${b.trades} trades`}
                    {b.per_trade_pct != null && b.verdict !== 'early' && b.verdict !== 'none' && (
                      <span className="num"> · <Delta value={b.per_trade_pct}>{pct(b.per_trade_pct, 2)}</Delta></span>
                    )}
                  </div>
                </td>
                <td>
                  {b.slots_total ? <><Slots used={b.slots_used} total={b.slots_total} money={b.money} />
                    <div className="num text-[11px] text-ink3 mt-1.5">{b.slots_used} of {b.slots_total}</div></> : <Missing />}
                </td>
                <td>
                  <div className="flex items-center gap-2 text-[13px] capitalize">
                    <span className="w-2 h-2 rounded-full" style={b.status === 'running'
                      ? { background: 'var(--good)' } : { boxShadow: 'inset 0 0 0 1.5px var(--ink3)' }} />
                    {b.status}
                  </div>
                  <div className="num text-[11px] text-ink3 mt-1">
                    {b.next_run ? `${shortDate(b.next_run, tz).slice(0, 3)} ${timeHM(b.next_run, tz)}` : '—'}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
````

`web/src/pages/strategies/Strategies.tsx`:

````tsx
// The strategy list: one card per strategy with its books and how its primary book is doing against the backtest.
import { Link } from '@tanstack/react-router'
import { BookMark, Delta } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type BookChip, type StrategyCard, useStrategies } from '../../lib/api'
import { pct } from '../../lib/format'
import { BandBar, VERDICT } from '../home/BooksPanel'

export const MONEY_WORD = { real: 'Real', paper: 'Paper' } as const

/** "Real · running · 4 open" */
export function chipText(book: BookChip): string {
  return `${MONEY_WORD[book.money]} · ${book.status} · ${book.open} open`
}

export function BookChips({ books }: { books: BookChip[] }) {
  return (
    <>
      {books.map((b) => (
        <span key={b.id} className="chip"><BookMark kind={b.money} color="var(--s2)" />{chipText(b)}</span>
      ))}
    </>
  )
}

/** The verdict in Home's words, with the sample size when it is too early to judge. */
export function verdictText(s: StrategyCard): string {
  if (s.verdict === 'early') return `${VERDICT.early} · ${s.trades} trades`
  if (s.verdict === 'none') return s.trades === 0 ? 'No closed trades yet' : 'No backtest to compare with'
  return VERDICT[s.verdict]
}

function Card({ s }: { s: StrategyCard }) {
  const title = `strategy-${s.id}`
  const band = s.band_lo != null && s.band_hi != null && s.per_trade_pct != null
  return (
    <article className="panel gap-4" aria-labelledby={title}>
      <div>
        <h2 id={title} className="text-lg font-semibold tracking-[-0.01em]">{s.name}</h2>
        {s.summary && <p className="text-sm text-ink2 mt-1">{s.summary}</p>}
      </div>
      {s.books.length > 0 && <div className="flex flex-wrap gap-2"><BookChips books={s.books} /></div>}
      <div>
        <div className="label">Per trade vs expected{s.book ? ` · ${s.book} book` : ''}</div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mt-2">
          {band && <BandBar lo={s.band_lo as number} hi={s.band_hi as number} actual={s.per_trade_pct as number} />}
          <span className="text-xs whitespace-nowrap" style={{ color: s.verdict === 'below' ? 'var(--ink1)' : 'var(--ink2)' }}>
            {s.verdict === 'below' && (
              <Icon name="alert" size={12}
                style={{ color: 'var(--warn)', display: 'inline-block', verticalAlign: '-2px', marginRight: 6 }} />
            )}
            {verdictText(s)}
            {band && <> · <Delta value={s.per_trade_pct as number}>{pct(s.per_trade_pct as number, 2)}</Delta></>}
          </span>
        </div>
      </div>
      <div className="mt-auto flex items-center justify-between border-t border-line pt-3 text-xs">
        <span className="text-ink3">{s.trades} closed trades</span>
        <Link to="/strategies/$strategyId" params={{ strategyId: s.id }} aria-label={`Open ${s.name}`}
          className="inline-flex items-center gap-1" style={{ color: 'var(--acc-ink)' }}>
          Open<Icon name="arrow" size={13} />
        </Link>
      </div>
    </article>
  )
}

export function Strategies() {
  const list = useStrategies()
  if (list.isPending) return <p className="text-ink3" role="status">Loading strategies…</p>
  if (!list.data) {
    return <div role="alert" className="panel">Strategies couldn&rsquo;t load: {list.error.message}</div>
  }
  const cards = list.data.strategies
  return (
    <>
      <header className="mb-5">
        <h1 className="text-3xl font-semibold tracking-[-0.025em]">Strategies</h1>
        <p className="text-ink2 mt-1.5">How each strategy trades, and whether it is behaving the way its backtest said it would.</p>
      </header>
      {cards.length === 0 ? (
        <div className="panel text-ink2">No strategies yet.</div>
      ) : (
        <div className="grid grid-cols-1 min-[900px]:grid-cols-2 gap-4">
          {cards.map((s) => <Card key={s.id} s={s} />)}
        </div>
      )}
    </>
  )
}
````

`web/src/shell/Shell.tsx`:

````tsx
// The frame around every page: sidebar (greeting, navigation, sources), top bar, phone tab bar.
import { useQueryClient } from '@tanstack/react-query'
import { Link, Outlet, useRouterState } from '@tanstack/react-router'
import { type Ref, useEffect, useRef, useState } from 'react'
import { Icon, type IconName, Mark } from '../components/Icon'
import { type ShellView, type Source, useShell } from '../lib/api'
import { ago, setCurrency, timeHM } from '../lib/format'
import { clockLine, greeting } from '../lib/greeting'
import { useTheme } from '../lib/theme'

type CountKey = keyof ShellView['counts']
interface NavItem { to: string; label: string; icon: IconName; count?: CountKey }

export const NAV: { group: string; items: NavItem[] }[] = [
  { group: 'Overview', items: [{ to: '/', label: 'Home', icon: 'home' }] },
  { group: 'Money', items: [{ to: '/accounts', label: 'Accounts', icon: 'accounts', count: 'accounts' }] },
  {
    group: 'Trading',
    items: [
      { to: '/books', label: 'Books', icon: 'books', count: 'books' },
      { to: '/strategies', label: 'Strategies', icon: 'strategy', count: 'strategies' },
    ],
  },
  { group: 'Research', items: [{ to: '/backtests', label: 'Backtests', icon: 'backtests' }] },
  {
    group: 'System',
    items: [
      { to: '/activity', label: 'Activity', icon: 'activity' },
      { to: '/settings', label: 'Settings', icon: 'settings' },
    ],
  },
]

const SIDEBAR_ID = 'sidebar'

const TABS: NavItem[] = [
  { to: '/', label: 'Home', icon: 'home' },
  { to: '/accounts', label: 'Accounts', icon: 'accounts' },
  { to: '/books', label: 'Books', icon: 'books' },
  { to: '/strategies', label: 'Strategies', icon: 'strategy' },
  { to: '/settings', label: 'More', icon: 'more' },
]

/** The breadcrumb for a path: its section and page. A page inside a section (/strategies/rsi2) keeps the section's
 *  crumb, as a link back to the section (`parent`). */
export function crumbs(pathname: string): { group: string; page: string; parent: string | null } {
  for (const { group, items } of NAV) {
    const item = items.find((i) => i.to === pathname || (i.to !== '/' && pathname.startsWith(`${i.to}/`)))
    if (item) return { group, page: item.label, parent: item.to === pathname ? null : item.to }
  }
  return { group: 'kestrel', page: 'Not found', parent: null }
}

const STATUS_ICON: Record<Source['status'], { name: IconName; color: string; text: string }> = {
  ok: { name: 'checkCircle', color: 'var(--good)', text: 'up to date' },
  stale: { name: 'clock', color: 'var(--warn)', text: 'stale' },
  error: { name: 'alert', color: 'var(--serious)', text: 'error' },
}

function SourceRow({ source, now }: { source: Source; now: Date }) {
  const status = STATUS_ICON[source.status]
  return (
    <div className="flex items-center gap-2.5 h-7 text-xs" title={source.detail || undefined}>
      <Icon name={status.name} size={14} style={{ color: status.color }} />
      <span className="text-ink2">{source.label}</span>
      <span className="text-ink3 text-[11px] truncate">{source.kind}</span>
      <span className="sr-only">{status.text}</span>
      <span className="num ml-auto text-[11px]" style={{ color: source.status === 'ok' ? 'var(--ink3)' : status.color }}>
        {ago(source.last_success, now)}
      </span>
    </div>
  )
}

function Sidebar({ shell, ref }: { shell?: ShellView; ref: Ref<HTMLElement> }) {
  const now = shell ? new Date(shell.now) : null
  const tz = shell?.app.timezone ?? 'UTC'
  return (
    <aside className="sidebar" id={SIDEBAR_ID} aria-label="Sidebar" ref={ref}>
      <div className="flex items-center gap-2.5 px-1.5 h-9">
        <Mark />
        <span className="text-base font-semibold tracking-tight">{shell?.app.name ?? 'kestrel'}</span>
      </div>
      <div className="px-2 pt-6 pb-2">
        <div className="text-[13px] text-ink3">{now ? `${greeting(now, tz)},` : ' '}</div>
        <div className="text-[26px] font-semibold tracking-[-0.03em] mt-0.5">{shell?.name ?? ' '}</div>
        <div className="num text-[11px] text-ink3 mt-1.5">{now ? clockLine(now, tz) : ' '}</div>
      </div>
      <nav aria-label="Main" className="flex flex-col gap-0.5">
        {NAV.map(({ group, items }) => (
          <div key={group} className="flex flex-col gap-0.5">
            <div className="label px-2.5 pt-4 pb-1.5">{group}</div>
            {items.map((item) => (
              <Link key={item.to} to={item.to} className="nav-item ease"
                activeOptions={{ exact: item.to === '/' }} activeProps={{ 'aria-current': 'page' }}>
                <Icon name={item.icon} size={17} />
                <span>{item.label}</span>
                {item.count && shell && <span className="num ml-auto text-[11px] text-ink3">{shell.counts[item.count]}</span>}
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div className="mt-auto border-t border-line pt-3.5 px-1.5">
        <div className="label mb-1.5">Sources</div>
        {now && shell?.sources.map((s) => <SourceRow key={s.id} source={s} now={now} />)}
      </div>
    </aside>
  )
}

function TopBar({ pathname, shell, theme, onToggleTheme, onMenu, menuOpen, menuRef }: {
  pathname: string; shell?: ShellView; theme: 'dark' | 'light'; onToggleTheme: () => void; onMenu: () => void
  menuOpen: boolean; menuRef: Ref<HTMLButtonElement>
}) {
  const client = useQueryClient()
  const { group, page, parent } = crumbs(pathname)
  return (
    <header className="topbar">
      <button type="button" className="icon-btn menu-btn" aria-label="Open menu" onClick={onMenu} ref={menuRef}
        aria-expanded={menuOpen} aria-controls={SIDEBAR_ID}>
        <Icon name="menu" size={18} />
      </button>
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-[13px]">
        <span className="text-ink3 hide-narrow">{group}</span>
        <Icon name="chevron" size={14} style={{ color: 'var(--ink3)' }} />
        {parent ? <Link to={parent} className="font-medium">{page}</Link> : <span className="font-medium">{page}</span>}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        {shell && (
          <span className="text-xs text-ink3 hide-narrow">Updated {timeHM(shell.now, shell.app.timezone)}</span>
        )}
        <button type="button" className="icon-btn" aria-label="Refresh data" onClick={() => client.invalidateQueries()}>
          <Icon name="refresh" size={16} />
        </button>
        <button type="button" className="icon-btn" onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={16} />
        </button>
      </div>
    </header>
  )
}

function TabBar() {
  return (
    <nav className="tabbar" aria-label="Tabs">
      {TABS.map((tab) => (
        <Link key={tab.to} to={tab.to} activeOptions={{ exact: tab.to === '/' }} activeProps={{ 'aria-current': 'page' }}
          className="flex flex-col items-center justify-center gap-1 min-h-12 text-[11px] font-medium text-ink3 aria-[current=page]:text-ink1">
          <Icon name={tab.icon} size={20} />
          {tab.label}
        </Link>
      ))}
    </nav>
  )
}

export function Shell() {
  const shell = useShell()
  const app = shell.data?.app
  const [theme, toggleTheme] = useTheme(app?.theme ?? 'system')
  const [drawer, setDrawer] = useState(false)
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const menuRef = useRef<HTMLButtonElement>(null)
  const sidebarRef = useRef<HTMLElement>(null)
  const drawerWasOpen = useRef(false)

  // during render, not in an effect: the page below renders after this line and must format in this currency
  // from its first paint (setCurrency is idempotent)
  if (app) setCurrency(app.currency)

  useEffect(() => setDrawer(false), [pathname]) // navigating closes the phone drawer
  useEffect(() => {
    document.title = app?.name ?? 'kestrel'
  }, [app])
  useEffect(() => {
    // opening the drawer moves focus into it; closing hands focus back to the menu button; Escape closes it
    if (drawer) sidebarRef.current?.querySelector<HTMLElement>('nav a')?.focus()
    else if (drawerWasOpen.current) menuRef.current?.focus()
    drawerWasOpen.current = drawer
    if (!drawer) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDrawer(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [drawer])
  useEffect(() => {
    // theme the whole document so overscroll and scrollbars match
    const root = document.documentElement
    root.classList.add('k')
    root.dataset.theme = theme
    root.dataset.accent = app?.accent ?? 'rufous'
    root.dataset.gl = app?.gain_loss ?? 'green-red'
    root.dataset.density = app?.density ?? 'comfortable'
  }, [theme, app])

  return (
    <div className="shell" data-drawer={drawer ? 'open' : 'closed'}>
      <Sidebar shell={shell.data} ref={sidebarRef} />
      <div className="scrim" aria-hidden="true" onClick={() => setDrawer(false)} />
      <div className="main">
        <TopBar pathname={pathname} shell={shell.data} theme={theme} onToggleTheme={toggleTheme}
          onMenu={() => setDrawer(true)} menuOpen={drawer} menuRef={menuRef} />
        <main className="content" id="main">
          {shell.isError && (
            <div role="alert" className="panel mb-4" style={{ borderColor: 'var(--serious)' }}>
              kestrel&rsquo;s server didn&rsquo;t answer. Is <code>kestrel serve</code> running?
            </div>
          )}
          {/* pages wait for the profile's settings (currency, time zone) so they never paint with the defaults */}
          {shell.data || shell.isError ? <Outlet /> : <p className="text-ink3" role="status">Loading…</p>}
        </main>
      </div>
      <TabBar />
    </div>
  )
}
````

`web/src/router.tsx`:

````tsx
import { createRootRoute, createRoute, createRouter, type RouterHistory } from '@tanstack/react-router'
import { Home } from './pages/home/Home'
import { Soon } from './pages/Soon'
import { Strategies } from './pages/strategies/Strategies'
import { Shell } from './shell/Shell'

const root = createRootRoute({
  component: Shell,
  notFoundComponent: () => <Soon title="Not found" text="There is no page here. Pick one from the menu." />,
})

const later = (path: string, title: string, text: string) =>
  createRoute({ getParentRoute: () => root, path, component: () => <Soon title={title} text={text} /> })

const routeTree = root.addChildren([
  createRoute({ getParentRoute: () => root, path: '/', component: Home }),
  later('/accounts', 'Accounts', 'Every account, what it holds, and how much of its growth was your deposits — Phase 4.'),
  later('/books', 'Books', 'Each book, real or paper: equity against its benchmark, drawdown, trades — Phase 3.'),
  createRoute({ getParentRoute: () => root, path: '/strategies', component: Strategies }),
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
Expected: `Tests  90 passed (90)` (`Strategies.test.tsx` 5, `Shell.test.tsx` 7); tsc prints nothing; `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/main.tsx web/src/test/renderApp.tsx web/src/router.tsx web/src/shell/Shell.tsx web/src/shell/Shell.test.tsx web/src/pages/home/BooksPanel.tsx web/src/pages/strategies/Strategies.tsx web/src/pages/strategies/Strategies.test.tsx
git commit -m "feat(web): strategy list page, API types and hooks, and a breadcrumb for pages inside a section"
```

---

### Task 11: The strategy page, part 1: header, Real | Paper, how it trades, is it behaving, the funnel, the money at work

**Files:**
- Modify (replace the whole file): `web/src/styles/tokens.css`, `web/src/components/bits.tsx`, `web/src/router.tsx`
- Create: `web/src/pages/strategy/Strategy.tsx`, `HowItTrades.tsx`, `Behaving.tsx`, `FunnelPanel.tsx`, `SlotsPanel.tsx` (all in `web/src/pages/strategy/`)
- Test: `web/src/pages/strategy/Strategy.test.tsx`

**Interfaces:**
- Consumes: `useStrategy`, `HttpError` (Task 10); `Histogram`, `HistogramTable`, `LineChart`, `LineKey`, `SlotsStrip`, `SlotsTable`, `Empty` (Tasks 7–8); `BookChips`, `MONEY_WORD` (Task 10); `Soon`.
- Produces:
  - `tokens.css` `.span-6` (full width under 1180 px) and `Panel` `span: 6`.
  - `Strategy({ id, book, onBook })` with `backtestText(expected)` ("Backtest 2006–2020"); header (caps "Strategy", h1, summary, book chips, backtest chip), the `Seg` "Book" (Real | Paper) only when `toggle`; 404 → the in-shell "Not found"; other errors → "This strategy couldn’t load: …".
  - `HowItTrades({ steps, sizing })`, `BehavingPanel({ v })`, `ScorecardPanel({ v })`, `FunnelPanel({ v })`, `SlotsPanel({ v })`.
  - `router.tsx`: `/strategies/$strategyId` with `validateSearch` → `{ book?: 'real' | 'paper' }` (anything else is dropped); the Real | Paper switch navigates to `?book=…`.

- [ ] **Step 1: Write the failing tests**

`web/src/pages/strategy/Strategy.test.tsx`:

````tsx
import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { StrategyView } from '../../lib/api'
import { renderApp, strategyFixture } from '../../test/renderApp'

const panel = (name: string) => screen.getByRole('region', { name })
const paper: StrategyView = { ...strategyFixture, book: 'paper', primary: 'rsi2-paper' }
const withView = (view: StrategyView, book: 'real' | 'paper' = 'real') => ({ strategy: [{ id: view.id, book, view }] })

describe('Strategy page', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with the strategy, its books and its backtest', async () => {
    renderApp('/strategies/rsi2')
    expect(await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })).toBeTruthy()
    expect(screen.getByText('Strategy')).toBeTruthy()
    expect(screen.getByText(strategyFixture.summary)).toBeTruthy()
    expect(screen.getByText('Real · running · 4 open')).toBeTruthy()
    expect(screen.getByText('Paper · running · 5 open')).toBeTruthy()
    expect(screen.getByText('Backtest 2006–2020')).toBeTruthy()
    const toggle = screen.getByRole('group', { name: 'Book' })
    expect(within(toggle).getByRole('button', { name: 'Real' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('switches to the paper book and keeps the choice in the address', async () => {
    const { router } = renderApp('/strategies/rsi2', {
      strategy: [{ id: 'rsi2', book: 'real', view: strategyFixture }, { id: 'rsi2', book: 'paper', view: paper }],
    })
    await screen.findByText('Real book against the backtest')
    fireEvent.click(within(screen.getByRole('group', { name: 'Book' })).getByRole('button', { name: 'Paper' }))
    expect(await screen.findByText('Paper book against the backtest')).toBeTruthy()
    expect(router.state.location.search).toEqual({ book: 'paper' })
  })

  it('opens on the book the address names', async () => {
    renderApp('/strategies/rsi2?book=paper', withView(paper, 'paper'))
    expect(await screen.findByText('Paper book against the backtest')).toBeTruthy()
  })

  it('offers no toggle when the strategy has one kind of money', async () => {
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, toggle: false }))
    await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })
    expect(screen.queryByRole('group', { name: 'Book' })).toBeNull()
  })

  it('shows an unknown strategy as not found, inside the shell', async () => {
    const answer = () => Promise.resolve(new Response('{"detail":"no such strategy: nope"}', { status: 404 }))
    renderApp('/strategies/nope', {}, answer)
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeTruthy()
    const crumb = within(screen.getByRole('navigation', { name: 'Breadcrumb' })).getByRole('link', { name: 'Strategies' })
    expect(crumb.getAttribute('href')).toBe('/strategies')
  })

  it('says it is loading, and says so plainly when the strategy could not load', async () => {
    const { unmount } = renderApp('/strategies/rsi2', { strategy: [] }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading the strategy…')).toBeTruthy()
    unmount()
    renderApp('/strategies/rsi2', { strategy: [] })
    expect((await screen.findByRole('alert')).textContent)
      .toBe('This strategy couldn’t load: network is off in tests')
  })

  it('draws the rule as numbered steps with its parameters and the sizing', async () => {
    renderApp('/strategies/rsi2')
    const how = await screen.findByRole('region', { name: 'How it trades' })
    expect(within(how).getByText('The whole rule, in four steps')).toBeTruthy()
    const steps = within(how).getAllByRole('listitem')
    expect(steps).toHaveLength(4)
    expect(steps[0].textContent).toContain('01')
    expect(steps[2].textContent).toContain('A stop rests at the broker')
    expect(within(how).getByText('−8% stop')).toBeTruthy()
    expect(how.textContent).toContain('SizingEach position is the account value ÷ 6, at most 5 open.')
  })

  it('says so when a strategy has not described its rules', async () => {
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, steps: [], sizing: '' }))
    const how = await screen.findByRole('region', { name: 'How it trades' })
    expect(within(how).getByText('This strategy hasn’t described its rules.')).toBeTruthy()
  })

  it('shows where trades landed, as a chart or a table', async () => {
    renderApp('/strategies/rsi2')
    const behaving = await screen.findByRole('region', { name: 'Is it behaving?' })
    expect(within(behaving).getByText('Where each real trade landed, against the spread of outcomes in the backtest'))
      .toBeTruthy()
    expect(within(behaving).getByText('Real trades (34)')).toBeTruthy()
    expect(within(behaving).getByText(
      'Return per trade, in 1-point buckets. Bars show the share of trades in each bucket.')).toBeTruthy()
    expect(within(behaving).getByRole('img', { name: 'Real trade returns against the backtest' })).toBeTruthy()
    fireEvent.click(within(behaving).getByRole('button', { name: 'Table' }))
    expect(within(behaving).getAllByRole('row')).toHaveLength(21)
  })

  it('scores the book against the backtest, in words as well as marks', async () => {
    renderApp('/strategies/rsi2')
    const card = await screen.findByRole('region', { name: 'Scorecard' })
    const rows = within(card).getAllByRole('row').slice(1)
    expect(rows.map((r) => r.textContent)).toEqual([
      'Win rate64.7%66.0%as expected',
      'Average per trade+0.79%+0.84%as expected',
      'Average win+2.59%+2.45%as expected',
      'Average loss−2.51%−2.28%as expected',
      'Trades per month2.83.1as expected',
    ])
    expect(within(card).getByText('34 / 50 trades')).toBeTruthy()
    expect(within(card).getByRole('progressbar', { name: 'Until the strategy review' })
      .getAttribute('aria-valuenow')).toBe('34')
    expect(card.textContent).toContain('Paper, same rules: 71 trades · +0.83% · 69.0% wins')
  })

  it('flags a measure off its band and waits for enough trades', async () => {
    const scorecard = strategyFixture.behaving.scorecard.map((r, i) => ({
      ...r, status: (['above', 'below', 'early', 'ok', 'ok'] as const)[i],
    }))
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, behaving: { ...strategyFixture.behaving, scorecard } }))
    const card = await screen.findByRole('region', { name: 'Scorecard' })
    expect(within(card).getByText('higher than expected')).toBeTruthy()
    expect(within(card).getByText('lower than expected')).toBeTruthy()
    expect(within(card).getByText('too early')).toBeTruthy()
  })

  it('shows the figures alone when there is no backtest', async () => {
    const scorecard = strategyFixture.behaving.scorecard.map((r) => ({ ...r, expected: null, status: 'none' as const }))
    renderApp('/strategies/rsi2', withView({
      ...strategyFixture, expected: null, behaving: { ...strategyFixture.behaving, scorecard },
      funnel: { ...strategyFixture.funnel, expected: null },
    }))
    const card = await screen.findByRole('region', { name: 'Scorecard' })
    expect(within(card).getByText('No backtest to compare with.')).toBeTruthy()
    expect(within(panel('Average per trade, as trades add up')).getByText('The running average of every closed trade'))
      .toBeTruthy()
    expect(within(card).getByText('Real book')).toBeTruthy()
    expect(screen.queryByText('Backtest 2006–2020')).toBeNull()
  })

  it('draws the running average of both books inside the expected range', async () => {
    renderApp('/strategies/rsi2')
    const funnel = await screen.findByRole('region', { name: 'Average per trade, as trades add up' })
    expect(within(funnel).getByText('If the edge is real, the line settles inside the funnel')).toBeTruthy()
    expect(within(funnel).getByText('Expected range (95%)')).toBeTruthy()
    expect(within(funnel).getByText('Real +0.79%')).toBeTruthy()
    expect(within(funnel).getByText('Paper +0.83%')).toBeTruthy()
    expect(within(funnel).getByText('trade number')).toBeTruthy()
    fireEvent.click(within(funnel).getByRole('button', { name: 'Table' }))
    expect(within(funnel).getAllByRole('row')).toHaveLength(72) // a header and 71 trades
  })

  it('shows the slots in use, the money working and the names close to a signal', async () => {
    renderApp('/strategies/rsi2')
    const slots = await screen.findByRole('region', { name: 'Where the money works' })
    expect(within(slots).getByText('Real book · slots in use, last 40 sessions · 5 slots')).toBeTruthy()
    expect(slots.textContent).toContain('Average in use0.8 of 5')
    expect(slots.textContent).toContain('Money working17%')
    expect(slots.textContent).toContain('Idle sessions12 of 40')
    expect(slots.textContent).toContain('Close to a signalKORSI(2) 12.4ABTRSI(2) 16.8UNPRSI(2) 19.1')
  })

  it('says so when a book does not report slots, and hides an empty watch list', async () => {
    const slots = { ...strategyFixture.slots, total: null, days: [], used: [], watch: [] }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, slots }))
    const panel = await screen.findByRole('region', { name: 'Where the money works' })
    expect(within(panel).getByText('This book doesn’t report slots.')).toBeTruthy()
    expect(within(panel).queryByText('Close to a signal')).toBeNull()
  })

  it('handles a strategy with no books yet', async () => {
    const empty: StrategyView = {
      ...strategyFixture, books: [], book: null, primary: null, toggle: false,
      behaving: { ...strategyFixture.behaving, trades: 0, other: null,
        buckets: strategyFixture.behaving.buckets.map((b) => ({ ...b, count: 0, share: 0 })) },
      funnel: { ...strategyFixture.funnel, lines: [], lo: [], hi: [] },
      slots: { ...strategyFixture.slots, book_id: null, total: null, days: [], used: [] },
    }
    renderApp('/strategies/rsi2', withView(empty))
    await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })
    expect(within(panel('Average per trade, as trades add up')).getByText('No closed trades yet.')).toBeTruthy()
    expect(within(panel('Where the money works')).getByText('No book trades this strategy yet.')).toBeTruthy()
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/pages/strategy/Strategy.test.tsx`
Expected: `Tests  15 failed | 1 passed (16)`. The page tests find the root "Not found" page instead (each takes about a second, the `findBy…` timeout); `shows an unknown strategy as not found, inside the shell` passes already on Task 10's breadcrumb.

- [ ] **Step 3: Implement**

`web/src/styles/tokens.css`:

````css
/* kestrel — Graphite design tokens. Source of truth: docs/design-system.md. Never use raw hex in components. */
@import "tailwindcss";

@theme inline {
  --color-bg: var(--bg);
  --color-side: var(--side);
  --color-panel: var(--panel);
  --color-panel2: var(--panel2);
  --color-line: var(--line);
  --color-line2: var(--line2);
  --color-ink1: var(--ink1);
  --color-ink2: var(--ink2);
  --color-ink3: var(--ink3);
  --color-acc: var(--acc);
  --color-acc-ink: var(--acc-ink);
  --color-up: var(--up);
  --color-down: var(--down);
  --color-warn: var(--warn);
  --color-serious: var(--serious);
  --color-good: var(--good);
  --font-sans: var(--k-sans);
  --font-mono: var(--k-mono);
}

/* the design-system type scale, in px: the app's root is 14 px, so rem-based sizes would come out smaller */
@theme {
  --text-2xs: 11px; --text-2xs--line-height: 1.4;
  --text-xs: 12px;
  --text-sm: 13px;
  --text-base: 14px;
  --text-lg: 15px;
  --text-xl: 20px;
  --text-2xl: 24px;
  --text-3xl: 28px;
  --text-4xl: 38px;
  --text-5xl: 48px;
}

.k {
  --bg: #0b0c0e; --side: #0e0f12; --panel: #121418; --panel2: #181b20; --line: #22262c; --line2: #2e333a;
  --ink1: #eceef1; --ink2: #a7adb6; --ink3: #7d848e;
  --s1: #5b93db; --s2: #d46c38; --s3: #8a9099; --ref: #7d848e;
  --warn: #e8b84b; --serious: #ec835a; --good: #4cc38f; --up: #4cc38f; --down: #ea5b60;
  --acc: #d46c38; --acc-ink: #e3875a; --on-acc: #0b0c0e;
  --pad: 20px; --row: 56px;
  --k-sans: "Geist", ui-sans-serif, system-ui, sans-serif;
  --k-mono: "Geist Mono", ui-monospace, monospace;
  color-scheme: dark;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink1);
  font-family: var(--k-sans);
  font-size: 14px;
  line-height: 1.4;
  -webkit-font-smoothing: antialiased;
}
.k[data-theme="light"] {
  --bg: #f2f3f5; --side: #f8f9fa; --panel: #ffffff; --panel2: #f5f6f8; --line: #e3e5e9; --line2: #d3d7dd;
  --ink1: #0f1114; --ink2: #4a5059; --ink3: #666d77;
  --s1: #2f6db5; --s2: #c45a24; --s3: #9aa0a8; --ref: #666d77;
  --warn: #9a6700; --serious: #c2562a; --good: #11845a; --up: #11845a; --down: #d1363b;
  color-scheme: light;
}
.k[data-accent="rufous"] { --acc: #d46c38; --acc-ink: #e3875a; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="rufous"] { --acc: #c45a24; --acc-ink: #a9481a; --on-acc: #ffffff; }
.k[data-accent="slate"] { --acc: #5b93db; --acc-ink: #7faae3; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="slate"] { --acc: #2f6db5; --acc-ink: #255a97; --on-acc: #ffffff; }
.k[data-accent="mono"] { --acc: #eceef1; --acc-ink: #eceef1; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="mono"] { --acc: #0f1114; --acc-ink: #0f1114; --on-acc: #ffffff; }
.k[data-gl="blue-orange"] { --up: #5b93db; --down: #d46c38; }
.k[data-theme="light"][data-gl="blue-orange"] { --up: #2f6db5; --down: #c45a24; }
.k[data-density="compact"] { --pad: 14px; --row: 44px; }

.k :focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
.k a { color: var(--ink2); text-decoration: none; }
.k a:hover { color: var(--ink1); }
@media (prefers-reduced-motion: no-preference) {
  .k .ease { transition: background-color 150ms ease-out, color 150ms ease-out, transform 150ms ease-out; }
}

/* --- building blocks ------------------------------------------------------------------------------------- */
.panel { position: relative; background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: var(--pad); display: flex; flex-direction: column; min-width: 0; height: var(--h, auto); }
.panel-title { font-size: 14px; font-weight: 600; letter-spacing: -0.005em; }
.panel-sub { font-size: 12px; color: var(--ink3); margin-top: 2px; }
.label { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink3); font-weight: 500; }
.num { font-family: var(--k-mono); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 7px; padding: 2px; gap: 2px;
  background: var(--panel); }
.seg button { font: 500 12px/1 var(--k-sans); padding: 6px 10px; border-radius: 5px; color: var(--ink3);
  cursor: pointer; background: none; border: 0; }
.seg button[aria-pressed="true"] { background: var(--panel2); color: var(--ink1); box-shadow: inset 0 0 0 1px var(--line2); }
.icon-btn { width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center;
  border-radius: 7px; border: 1px solid var(--line); color: var(--ink2); background: var(--panel); cursor: pointer; }
.chip { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--ink2); padding: 5px 10px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--panel); white-space: nowrap; }
.mark { width: 12px; height: 12px; border-radius: 3px; display: inline-block; flex: none; }
.mark.real { background: var(--mc, var(--ink2)); }
.mark.paper { background-image: repeating-linear-gradient(45deg, var(--mc, var(--ink2)) 0 1.5px, transparent 1.5px 4px);
  box-shadow: inset 0 0 0 1.25px var(--mc, var(--ink2)); }
.mark.expected { border: 1.5px dotted var(--mc, var(--ref)); background: color-mix(in srgb, var(--ink1) 5%, transparent); }
.badge { display: inline-flex; align-items: center; gap: 6px; font: 600 10px/1 var(--k-mono); letter-spacing: 0.08em;
  color: var(--ink2); padding: 5px 7px; border: 1px solid var(--line2); border-radius: 5px; }
.up { color: var(--up); }
.down { color: var(--down); }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink3); font-weight: 500;
  text-align: left; padding: 0 12px 10px 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
.tbl td { height: var(--row); border-bottom: 1px solid var(--line); vertical-align: middle; padding: 0 12px 0 0; }
.tbl tr:last-child td { border-bottom: 0; }
.tbl .r { text-align: right; }
.tip { position: absolute; z-index: 10; pointer-events: none; background: var(--panel2); border: 1px solid var(--line2);
  border-radius: 7px; padding: 8px 10px; font-size: 12px; box-shadow: 0 8px 24px rgb(0 0 0 / 0.28); min-width: 170px; }
.sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; border: 0; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; }

/* --- layout ------------------------------------------------------------------------------------------------ */
.shell { display: flex; min-height: 100vh; }
.sidebar { width: 256px; flex: none; height: 100vh; position: sticky; top: 0; background: var(--side);
  border-right: 1px solid var(--line); display: flex; flex-direction: column; padding: 18px 14px; overflow-y: auto; }
.nav-item { display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 10px; border-radius: 7px;
  font-size: 14px; font-weight: 500; color: var(--ink2); }
.nav-item[aria-current="page"] { background: var(--panel2); color: var(--ink1); box-shadow: inset 0 0 0 1px var(--line); }
.nav-item[aria-current="page"] svg { color: var(--acc); }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.topbar { height: 64px; flex: none; display: flex; align-items: center; gap: 10px; padding: 0 32px;
  border-bottom: 1px solid var(--line); }
.content { padding: 28px 32px 32px; }
.grid12 { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; align-content: start; }
.span-4 { grid-column: span 4; } .span-5 { grid-column: span 5; } .span-6 { grid-column: span 6; }
.span-7 { grid-column: span 7; } .span-8 { grid-column: span 8; } .span-12 { grid-column: span 12; }
.menu-btn, .tabbar, .scrim { display: none; }
/* position: relative keeps absolutely positioned children (sr-only labels) inside the scroll box */
.table-scroll { position: relative; overflow-x: auto; }

@media (max-width: 1180px) {
  .span-4, .span-5, .span-6, .span-7, .span-8 { grid-column: span 12; }
  .panel { height: auto; }
}
@media (max-width: 900px) {
  /* closed: off screen AND hidden, so its links leave the tab order and screen readers skip it */
  .sidebar { position: fixed; left: 0; top: 0; z-index: 30; transform: translateX(-100%); visibility: hidden; }
  .shell[data-drawer="open"] .sidebar { transform: none; visibility: visible; }
  .shell[data-drawer="open"] .scrim { display: block; position: fixed; inset: 0; z-index: 20; background: rgb(0 0 0 / 0.45); }
  .menu-btn { display: inline-flex; }
  .topbar { padding: 0 16px; }
  .content { padding: 20px 16px 24px; }
  .hide-narrow { display: none; }
}
@media (max-width: 640px) {
  .tabbar { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); position: fixed; left: 0; right: 0;
    bottom: 0; z-index: 25; height: 72px; padding: 6px 4px 14px; background: var(--side); border-top: 1px solid var(--line); }
  .content { padding-bottom: 96px; }
  .icon-btn { width: 44px; height: 44px; } /* touch targets */
  .seg button { min-height: 36px; }
}
````

`web/src/components/bits.tsx`:

````tsx
// Small shared pieces: the money-state mark and badge, deltas, panels, segmented controls.
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
````

`web/src/pages/strategy/HowItTrades.tsx`:

````tsx
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Step } from '../../lib/api'
import { Empty } from '../../charts/marks'

const COUNT = ['', 'one step', 'two steps', 'three steps', 'four steps']

/** The rule as up to four cards joined by arrows, each with its parameters, then the sizing line. */
export function HowItTrades({ steps, sizing }: { steps: Step[]; sizing: string }) {
  const shown = steps.slice(0, 4)
  return (
    <Panel id="how" title="How it trades" span={12} height={252}
      subtitle={shown.length ? `The whole rule, in ${COUNT[shown.length]}` : undefined}>
      {shown.length === 0 ? (
        <Empty>This strategy hasn&rsquo;t described its rules.</Empty>
      ) : (
        <ol className="grid grid-cols-1 sm:grid-cols-2 min-[1180px]:flex gap-3 min-[1180px]:gap-0 mt-3.5">
          {shown.map((step, i) => (
            <li key={`${i}-${step.label}`} className="flex min-w-0 min-[1180px]:flex-1">
              {i > 0 && (
                <span aria-hidden="true" className="hidden min-[1180px]:flex w-8 flex-none items-center justify-center"
                  style={{ color: 'var(--ink3)' }}>
                  <Icon name="arrow" size={18} />
                </span>
              )}
              <div className="flex-1 min-w-0 rounded-[9px] border border-line bg-panel2 p-4">
                <div className="flex items-center gap-2">
                  <span className="num text-2xs" style={{ color: 'var(--acc-ink)' }}>{String(i + 1).padStart(2, '0')}</span>
                  <span className="label">{step.label}</span>
                </div>
                <div className="text-lg font-medium mt-2.5">{step.title}</div>
                <div className="text-xs text-ink3 mt-1">{step.text}</div>
                {step.params.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {step.params.map((param) => (
                      <span key={param} className="num text-2xs text-ink2 rounded-[5px] border border-line2 px-[7px] py-[3px]">
                        {param}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
      {sizing && (
        <div className="mt-auto pt-3 flex items-start gap-2 text-xs text-ink2">
          <Icon name="scale" size={15} style={{ color: 'var(--ink3)' }} />
          <span><span className="label mr-2">Sizing</span>{sizing}</span>
        </div>
      )}
    </Panel>
  )
}
````

`web/src/pages/strategy/Behaving.tsx`:

````tsx
import { type CSSProperties, useState } from 'react'
import { Histogram, HistogramTable } from '../../charts/Histogram'
import { BookMark, Panel, Seg } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { ScoreRow, StrategyView } from '../../lib/api'
import { num, pct } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'

const VIEWS = ['Chart', 'Table'] as const

export function BehavingPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const money = v.book ?? 'real'
  const word = MONEY_WORD[money]
  const backtest = v.behaving.buckets.some((b) => b.expected != null)
  return (
    <Panel id="behaving" title="Is it behaving?" span={8} height={412}
      subtitle={`Where each ${money} trade landed${backtest ? ', against the spread of outcomes in the backtest' : ''}`}
      actions={<>
        <span className="inline-flex items-center gap-1.5 text-xs text-ink2 whitespace-nowrap">
          <BookMark kind={money} color="var(--s2)" />{word} trades ({v.behaving.trades})
        </span>
        {backtest && (
          <span className="inline-flex items-center gap-1.5 text-xs text-ink2 whitespace-nowrap">
            <BookMark kind="expected" />Backtest
          </span>
        )}
        <Seg label="View" options={VIEWS} value={view} onChange={setView} />
      </>}>
      <div className="mt-auto pt-3">
        {view === 'Chart'
          ? <Histogram buckets={v.behaving.buckets} money={money} ariaLabel={`${word} trade returns against the backtest`} />
          : <HistogramTable buckets={v.behaving.buckets} money={money} />}
      </div>
      <p className="text-xs text-ink3 mt-2">
        Return per trade, in 1-point buckets. Bars show the share of trades in each bucket.
      </p>
    </Panel>
  )
}

function figure(row: ScoreRow, value: number | null): string {
  if (value == null) return '—'
  if (row.key === 'win_rate') return `${num(value, 1)}%`
  if (row.key === 'per_month') return num(value, 1)
  return pct(value, 2)
}

const STATUS: Record<'ok' | 'above' | 'below', { icon: 'check' | 'alert'; color: string; text: string }> = {
  ok: { icon: 'check', color: 'var(--good)', text: 'as expected' },
  above: { icon: 'alert', color: 'var(--warn)', text: 'higher than expected' },
  below: { icon: 'alert', color: 'var(--warn)', text: 'lower than expected' },
}

function Status({ status }: { status: ScoreRow['status'] }) {
  if (status === 'none') return null
  if (status === 'early') return <span className="text-2xs text-ink3 whitespace-nowrap">too early</span>
  const look = STATUS[status]
  return (
    <span className="inline-flex" style={{ color: look.color }}>
      <Icon name={look.icon} size={15} /><span className="sr-only">{look.text}</span>
    </span>
  )
}

export function ScorecardPanel({ v }: { v: StrategyView }) {
  const b = v.behaving
  const word = MONEY_WORD[v.book ?? 'real']
  const early = b.scorecard.some((r) => r.status === 'early')
  const done = b.review_at ? Math.min(100, (b.trades / b.review_at) * 100) : 0
  return (
    <Panel id="scorecard" title="Scorecard" span={4} height={412}
      subtitle={v.expected ? `${word} book against the backtest` : `${word} book`}>
      <table className="tbl mt-3" style={{ '--row': '40px', tableLayout: 'fixed' } as CSSProperties}>
        <colgroup><col /><col style={{ width: 74 }} /><col style={{ width: 74 }} /><col style={{ width: early ? 58 : 28 }} /></colgroup>
        <thead>
          <tr>
            <th>Measure</th><th className="r">{word}</th><th className="r">Expected</th>
            <th className="r"><span className="sr-only">Status</span></th>
          </tr>
        </thead>
        <tbody>
          {b.scorecard.map((row) => (
            <tr key={row.key}>
              <td className="text-sm text-ink2">{row.label}</td>
              <td className="r"><span className="num font-medium">{figure(row, row.actual)}</span></td>
              <td className="r"><span className="num text-ink3">{figure(row, row.expected)}</span></td>
              <td className="r" style={{ paddingRight: 0 }}><Status status={row.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      {!v.expected && <p className="text-xs text-ink3 mt-3">No backtest to compare with.</p>}
      {b.review_at != null && (
        <div className="mt-4">
          <div className="flex justify-between text-xs">
            <span className="text-ink2">Until the strategy review</span>
            <span className="num">{b.trades} / {b.review_at} trades</span>
          </div>
          <div role="progressbar" aria-label="Until the strategy review" aria-valuemin={0} aria-valuemax={b.review_at}
            aria-valuenow={Math.min(b.trades, b.review_at)} className="relative h-2 rounded mt-2 overflow-hidden bg-panel2"
            style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
            <span className="absolute inset-y-0 left-0 rounded" style={{ width: `${done}%`, background: 'var(--acc)' }} />
          </div>
        </div>
      )}
      {b.other && (
        <div className="mt-auto border-t border-line pt-3.5 flex items-center gap-2.5 text-xs text-ink2">
          <BookMark kind={b.other.money} color="var(--s2)" />
          <span>
            {MONEY_WORD[b.other.money]}, same rules: <span className="num text-ink1">{b.other.trades}</span> trades
            {' · '}<span className="num text-ink1">{b.other.per_trade_pct == null ? '—' : pct(b.other.per_trade_pct, 2)}</span>
            {' · '}<span className="num text-ink1">{b.other.win_rate == null ? '—' : `${num(b.other.win_rate, 1)}%`}</span> wins
          </span>
        </div>
      )}
    </Panel>
  )
}
````

`web/src/pages/strategy/FunnelPanel.tsx`:

````tsx
import { type CSSProperties, useState } from 'react'
import { type ChartSeries, LineChart, LineKey } from '../../charts/LineChart'
import { Empty } from '../../charts/marks'
import { Panel, Seg } from '../../components/bits'
import type { StrategyView } from '../../lib/api'
import { pct } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'

const VIEWS = ['Chart', 'Table'] as const

/** The running average per trade for each book (the primary one solid if real, a paper one dashed) inside the
 *  expected 95% range, which narrows as trades add up. */
export function FunnelPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const f = v.funnel
  const n = Math.max(0, ...f.lines.map((l) => l.values.length))
  const trades = Array.from({ length: n }, (_, i) => String(i + 1))
  const series: ChartSeries[] = f.lines.map((l) => ({
    key: l.book_id, label: MONEY_WORD[l.money], color: 'var(--s2)', style: l.money === 'real' ? 'solid' : 'dashed',
    values: trades.map((_, i) => l.values[i] ?? null),
    endLabel: `${MONEY_WORD[l.money]} ${pct(l.values[l.values.length - 1], 2)}`,
  }))
  const band = f.expected != null ? { lo: f.lo, hi: f.hi, label: 'Expected range' } : undefined
  return (
    <Panel id="funnel" title="Average per trade, as trades add up" span={6} height={372}
      subtitle={band ? 'If the edge is real, the line settles inside the funnel' : 'The running average of every closed trade'}
      actions={n > 0 && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      {n === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : (
        <>
          <div className="flex flex-wrap gap-x-3.5 gap-y-1 mt-3 text-xs text-ink2">
            {series.map((s) => (
              <span key={s.key} className="inline-flex items-center gap-1.5"><LineKey color={s.color} style={s.style} />{s.label}</span>
            ))}
            {band && (
              <span className="inline-flex items-center gap-1.5"><LineKey color="var(--ref)" style="dotted" />Expected range (95%)</span>
            )}
          </div>
          <div className="mt-auto pt-2">
            {view === 'Chart' ? (
              <>
                <LineChart dates={trades} series={series} band={band} height={214} zeroLine
                  ariaLabel="Running average return per trade, with the expected range"
                  yFormat={(value) => pct(value, 0)} valueFormat={(value) => pct(value, 2)} xLabel={(t) => t}
                  tipTitle={(t) => `After trade ${t}`} />
                <div className="text-2xs text-ink3 text-center">trade number</div>
              </>
            ) : (
              <div className="table-scroll overflow-y-auto" style={{ maxHeight: 236 }}>
                <table className="tbl" style={{ '--row': '34px' } as CSSProperties}>
                  <thead>
                    <tr>
                      <th>Trade</th>{series.map((s) => <th key={s.key} className="r">{s.label}</th>)}
                      {band && <th className="r">Expected range</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t, i) => (
                      <tr key={t}>
                        <td className="num">{t}</td>
                        {series.map((s) => (
                          <td key={s.key} className="r num">{s.values[i] == null ? '—' : pct(s.values[i] as number, 2)}</td>
                        ))}
                        {band && (
                          <td className="r num">
                            {f.lo[i] == null || f.hi[i] == null ? '—'
                              : `${pct(f.lo[i] as number, 2)} to ${pct(f.hi[i] as number, 2)}`}
                          </td>
                        )}
                      </tr>
                    )).reverse()}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </Panel>
  )
}
````

`web/src/pages/strategy/SlotsPanel.tsx`:

````tsx
import { type ReactNode, useState } from 'react'
import { Empty } from '../../charts/marks'
import { SlotsStrip, SlotsTable } from '../../charts/SlotsStrip'
import { Panel, Seg } from '../../components/bits'
import type { StrategyView } from '../../lib/api'
import { num } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'

const VIEWS = ['Chart', 'Table'] as const

function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-line px-3 py-2.5 min-w-0">
      <div className="label">{label}</div>
      <div className="num text-lg mt-1">{children}</div>
    </div>
  )
}

/** Slots in use over the last sessions, how much of the money that keeps working, and the names close to a signal. */
export function SlotsPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const s = v.slots
  const money = v.book ?? 'real'
  const reported = s.total != null && s.days.length > 0
  return (
    <Panel id="slots" title="Where the money works" span={6} height={372}
      subtitle={reported ? `${MONEY_WORD[money]} book · slots in use, last ${s.days.length} sessions · ${s.total} slots`
        : undefined}
      actions={reported && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      {s.book_id == null ? (
        <Empty>No book trades this strategy yet.</Empty>
      ) : !reported || s.total == null ? (
        <Empty>This book doesn&rsquo;t report slots.</Empty>
      ) : (
        <>
          <div className="mt-4">
            {view === 'Chart'
              ? <SlotsStrip days={s.days} used={s.used} total={s.total} money={money} ariaLabel="Slots in use each session" />
              : <SlotsTable days={s.days} used={s.used} total={s.total} />}
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3.5">
            <Tile label="Average in use">
              {s.avg_used == null ? '—' : num(s.avg_used, 1)} <span className="text-xs text-ink3">of {s.total}</span>
            </Tile>
            <Tile label="Money working">{s.working_pct == null ? '—' : `${Math.round(s.working_pct)}%`}</Tile>
            <Tile label="Idle sessions">
              {s.idle} <span className="text-xs text-ink3">of {s.days.length}</span>
            </Tile>
          </div>
        </>
      )}
      {s.watch.length > 0 && (
        <div className="mt-auto border-t border-line pt-3">
          <div className="label">Close to a signal</div>
          <div className="flex flex-wrap gap-2 mt-2">
            {s.watch.map((w) => (
              <span key={w.symbol} className="chip">
                <span className="num font-semibold text-ink1">{w.symbol}</span>
                <span className="num">{w.label} {w.value == null ? '—' : num(w.value, 1)}</span>
                {w.note && <span className="text-ink3">{w.note}</span>}
              </span>
            ))}
          </div>
        </div>
      )}
    </Panel>
  )
}
````

`web/src/pages/strategy/Strategy.tsx`:

````tsx
// One strategy: how it trades and whether it is behaving the way its backtest said it would.
import { BookMark, Seg } from '../../components/bits'
import { type Expected, HttpError, type Money, type StrategyView, useStrategy } from '../../lib/api'
import { Soon } from '../Soon'
import { BookChips, MONEY_WORD } from '../strategies/Strategies'
import { BehavingPanel, ScorecardPanel } from './Behaving'
import { FunnelPanel } from './FunnelPanel'
import { HowItTrades } from './HowItTrades'
import { SlotsPanel } from './SlotsPanel'

const BOOKS = ['Real', 'Paper'] as const

/** "Backtest 2006–2020" */
export function backtestText(expected: Expected): string {
  const source = expected.source || 'backtest'
  return `${source[0].toUpperCase()}${source.slice(1)}${expected.window ? ` ${expected.window}` : ''}`
}

function Header({ v, onBook }: { v: StrategyView; onBook: (book: Money) => void }) {
  return (
    <header className="mb-5">
      <div className="label">Strategy</div>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">{v.name}</h1>
          {v.summary && <p className="text-ink2 mt-1.5 max-w-[680px]">{v.summary}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <BookChips books={v.books} />
          {v.expected && <span className="chip"><BookMark kind="expected" />{backtestText(v.expected)}</span>}
        </div>
      </div>
      {v.toggle && v.book && (
        <div className="mt-4">
          <Seg label="Book" options={BOOKS} value={MONEY_WORD[v.book]}
            onChange={(word) => onBook(word === 'Real' ? 'real' : 'paper')} />
        </div>
      )}
    </header>
  )
}

export function Strategy({ id, book, onBook }: { id: string; book: Money; onBook: (book: Money) => void }) {
  const strategy = useStrategy(id, book)
  if (strategy.isPending) return <p className="text-ink3" role="status">Loading the strategy…</p>
  if (!strategy.data) {
    if (strategy.error instanceof HttpError && strategy.error.status === 404) {
      return <Soon title="Not found" text="There is no page here. Pick one from the menu." />
    }
    return <div role="alert" className="panel">This strategy couldn&rsquo;t load: {strategy.error.message}</div>
  }
  const v = strategy.data
  return (
    <>
      <Header v={v} onBook={onBook} />
      <div className="grid12">
        <HowItTrades steps={v.steps} sizing={v.sizing} />
        <BehavingPanel v={v} />
        <ScorecardPanel v={v} />
        <FunnelPanel v={v} />
        <SlotsPanel v={v} />
      </div>
    </>
  )
}
````

`web/src/router.tsx`:

````tsx
import { createRootRoute, createRoute, createRouter, type RouterHistory, useNavigate } from '@tanstack/react-router'
import type { Money } from './lib/api'
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
  later('/accounts', 'Accounts', 'Every account, what it holds, and how much of its growth was your deposits — Phase 4.'),
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
Expected: `Tests  106 passed (106)` (`Strategy.test.tsx` 16); tsc prints nothing; `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add web/src/styles/tokens.css web/src/components/bits.tsx web/src/router.tsx web/src/pages/strategy/Strategy.tsx web/src/pages/strategy/HowItTrades.tsx web/src/pages/strategy/Behaving.tsx web/src/pages/strategy/FunnelPanel.tsx web/src/pages/strategy/SlotsPanel.tsx web/src/pages/strategy/Strategy.test.tsx
git commit -m "feat(web): strategy page: header and Real | Paper, how it trades, scorecard, funnel, slots"
```

---

### Task 12: The strategy page, part 2: trade anatomy, is it worth it, month by month, all trades; Home links to the strategy

**Files:**
- Modify (replace the whole file): `src/kestrel/views/home.py`, `web/src/pages/strategy/Strategy.tsx`
- Regenerate: `web/src/test/fixtures/home.json`
- Create: `web/src/pages/strategy/Anatomy.tsx`, `WorthPanel.tsx`, `MonthlyPanel.tsx`, `TradesPanel.tsx`
- Test: `tests/test_home_view.py` (replace the whole file), `web/src/pages/strategy/StrategyTrades.test.tsx` (new)

**Interfaces:**
- Consumes: `CandleChart`, `CandleTable`, `Scatter`, `ScatterTable`, `MonthGrid`, `MonthTable` (Tasks 8–9); `useShell`.
- Produces:
  - `views/home.py`: "… is below its expected band" links to `/strategies/<strategy_id>` (the id URL-escaped).
  - `AnatomySection({ v })` (the anatomy chart and the Recent trades list that picks it; keyed by the primary book so switching Real | Paper starts from that book's newest charted trade), `reasonWord(reason)`, `sessionsText(n)`; `WorthPanel({ v })`; `MonthlyPanel({ v })`; `TradesPanel({ v })` (sortable by Closed, Return and P/L with `aria-sort`).
  - `Strategy.tsx` renders all eight sections.

- [ ] **Step 1: Write the failing tests**

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
````

`web/src/pages/strategy/StrategyTrades.test.tsx`:

````tsx
// The Strategy page's trade-level sections: anatomy, recent trades, is it worth it, month by month, all trades.
import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { StrategyView } from '../../lib/api'
import { renderApp, strategyFixture } from '../../test/renderApp'
import { reasonWord, sessionsText } from './Anatomy'

const withView = (view: StrategyView) => ({ strategy: [{ id: view.id, book: 'real' as const, view }] })
const rows = (region: HTMLElement) => within(region).getAllByRole('row').slice(1)

describe('Strategy page, trade by trade', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('opens the newest charted trade in the anatomy chart', async () => {
    renderApp('/strategies/rsi2')
    const anatomy = await screen.findByRole('region', { name: 'Trade anatomy' })
    expect(within(anatomy).getByText('HON · real · bought Thu 10 Sep, sold Fri 18 Sep · stop')).toBeTruthy()
    expect(anatomy.textContent).toContain('−8.01%')
    expect(within(anatomy).getByText('−1.00 R')).toBeTruthy()
    expect(within(anatomy).getByText('6 sessions')).toBeTruthy()
    expect([sessionsText(0), sessionsText(1), reasonWord('signal'), reasonWord('')]).toEqual(
      ['Same day', '1 session', 'Signal', '—'])
    expect(within(anatomy).getByRole('img', { name: 'HON daily bars with the buy, the sell and the stop' })).toBeTruthy()
    expect(within(anatomy).getByText(/^Stop .* · −8%$/)).toBeTruthy()
    fireEvent.click(within(anatomy).getByRole('button', { name: 'Table' }))
    expect(within(anatomy).getAllByRole('row')).toHaveLength(31) // a header and 30 sessions
  })

  it('picks another recent trade for the chart', async () => {
    renderApp('/strategies/rsi2')
    const recent = await screen.findByRole('region', { name: 'Recent trades' })
    const buttons = within(recent).getAllByRole('button')
    expect(buttons).toHaveLength(8)
    expect(buttons[0].getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(within(recent).getByRole('button', { name: 'TXN, closed Thu 3 Sep' }))
    expect(within(recent).getByRole('button', { name: 'TXN, closed Thu 3 Sep' }).getAttribute('aria-pressed'))
      .toBe('true')
    const anatomy = screen.getByRole('region', { name: 'Trade anatomy' })
    expect(within(anatomy).getByText('TXN · real · bought Fri 28 Aug, sold Thu 3 Sep · signal')).toBeTruthy()
    expect(within(recent).getByRole('link', { name: 'All 34' }).getAttribute('href')).toBe('#trades-title')
  })

  it('lists a trade without a chart plainly, and says so when none has one', async () => {
    const anatomy = strategyFixture.anatomy
    const one = {
      ...anatomy, recent: anatomy.recent.map((r, i) => (i === 1 ? { ...r, chart: false } : r)),
      charts: anatomy.charts.filter((c) => c.key !== anatomy.recent[1].key),
    }
    const { unmount } = renderApp('/strategies/rsi2', withView({ ...strategyFixture, anatomy: one }))
    const recent = await screen.findByRole('region', { name: 'Recent trades' })
    expect(within(recent).getAllByRole('button')).toHaveLength(7)
    expect(within(recent).getByText('no chart')).toBeTruthy()
    unmount()
    const none = { ...anatomy, recent: anatomy.recent.map((r) => ({ ...r, chart: false })), charts: [], selected: null }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, anatomy: none }))
    const panel = await screen.findByRole('region', { name: 'Trade anatomy' })
    expect(within(panel).getByText('No chart for these trades.')).toBeTruthy()
  })

  it('plots yearly return against worst drop, labelled, with a table', async () => {
    renderApp('/strategies/rsi2')
    const worth = await screen.findByRole('region', { name: 'Is it worth it?' })
    expect(within(worth).getByText('Yearly return against the worst drop along the way')).toBeTruthy()
    for (const text of ['Backtest', 'Real book', 'Long-term accounts', 'S&P 500', '+23.4%/yr · 2006–2020',
      '+19.0%/yr · 12 months']) {
      expect(within(worth).getByText(text)).toBeTruthy()
    }
    fireEvent.click(within(worth).getByRole('button', { name: 'Table' }))
    expect(rows(worth).map((r) => r.textContent)).toEqual([
      'Backtest+23.4%−11.7%2006–2020', 'Real book+19.0%−5.6%12 months', 'Long-term accounts+21.4%−9.0%12 months',
      'S&P 500+20.5%−11.5%12 months',
    ])
  })

  it('marks a book with under a year of history as early', async () => {
    const points = strategyFixture.worth.points.map((p) => (p.key === 'book' ? { ...p, early: true, period: '7 months' } : p))
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, worth: { points } }))
    const worth = await screen.findByRole('region', { name: 'Is it worth it?' })
    expect(within(worth).getByText('+19.0%/yr · 7 months · early')).toBeTruthy()
  })

  it('sums up month by month against the long-term accounts', async () => {
    renderApp('/strategies/rsi2')
    const monthly = await screen.findByRole('region', { name: 'Month by month' })
    expect(within(monthly).getByText('Real book against your long-term accounts')).toBeTruthy()
    expect(monthly.textContent).toContain('Months ahead of long-term7 of 12')
    expect(monthly.textContent).toContain('Best month · Jan▲ up +6.9%')
    expect(monthly.textContent).toContain('Worst month · Apr▼ down −2.1%')
    fireEvent.click(within(monthly).getByRole('button', { name: 'Table' }))
    expect(rows(monthly)).toHaveLength(12)
  })

  it('lists every closed trade, newest first, and sorts by return or P/L', async () => {
    renderApp('/strategies/rsi2')
    const all = await screen.findByRole('region', { name: 'All trades' })
    expect(within(all).getByText('Real book · 34 closed trades')).toBeTruthy()
    expect(rows(all)).toHaveLength(34)
    expect(rows(all)[0].textContent).toBe('HONreal10 Sep18 Sep8▼ down −8.01%−1.00▼ down −$225.72Stop')
    const closed = within(all).getByRole('columnheader', { name: 'Closed' })
    expect(closed.getAttribute('aria-sort')).toBe('descending')
    fireEvent.click(within(all).getByRole('button', { name: 'Return' }))
    expect(rows(all)[0].textContent).toContain('HD')
    expect(within(all).getByRole('columnheader', { name: 'Return' }).getAttribute('aria-sort')).toBe('descending')
    fireEvent.click(within(all).getByRole('button', { name: 'Return' }))
    expect(rows(all)[0].textContent).toContain('−8.09%')
    fireEvent.click(within(all).getByRole('button', { name: 'P/L' }))
    expect(rows(all)[0].textContent).toContain('+$111.45')
  })

  it('says so when the book has no closed trades', async () => {
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, trades: [] }))
    const all = await screen.findByRole('region', { name: 'All trades' })
    expect(within(all).getByText('No closed trades yet.')).toBeTruthy()
  })

  it('links a book below its band on Home to its strategy', async () => {
    renderApp('/')
    const needs = await screen.findByRole('region', { name: 'Needs you' })
    const item = within(needs).getAllByRole('listitem').find((li) => li.textContent?.includes('below its expected band'))
    expect(item && within(item).getByRole('link', { name: 'Open' }).getAttribute('href')).toBe('/strategies/leader')
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_home_view.py` and, in `web/`, `npx vitest run src/pages/strategy/StrategyTrades.test.tsx`
Expected: pytest `1 failed, 14 passed` with `AssertionError: assert '/strategies' == '/strategies/leader'`; vitest `Failed to resolve import "./Anatomy"`.

- [ ] **Step 3: Implement, then regenerate `home.json`**

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
    trading = sum_series([book_history[b.id] for b in real_books if b.id in book_history])
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
        per_trade = round(fmean(returns), 3) if returns else None
        lo = hi = None
        if not returns or expected is None:
            verdict = "none"
        elif len(returns) < MIN_TRADES_FOR_VERDICT:
            verdict = "early"
        else:
            lo, hi = expected_band(expected.avg_trade_pct, expected.sd_trade_pct, len(returns))
            verdict = "below" if per_trade < lo else "above" if per_trade > hi else "in_band"
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

`web/src/pages/strategy/Anatomy.tsx`:

````tsx
import { useState } from 'react'
import { CandleChart, CandleTable } from '../../charts/CandleChart'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Panel, Seg } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { RecentTrade, StrategyView } from '../../lib/api'
import { monthLabel, num, pct, shortDate } from '../../lib/format'

const VIEWS = ['Chart', 'Table'] as const

export const reasonWord = (reason: string) => (reason ? reason[0].toUpperCase() + reason.slice(1) : '—')

/** "6 sessions" · "1 session" · "Same day" */
export function sessionsText(n: number): string {
  if (n === 0) return 'Same day'
  return `${n} session${n === 1 ? '' : 's'}`
}

function AnatomyPanel({ v, selected }: { v: StrategyView; selected: string | null }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const trade = v.anatomy.recent.find((r) => r.key === selected)
  const chart = v.anatomy.charts.find((c) => c.key === selected)
  return (
    <Panel id="anatomy" title="Trade anatomy" span={8} height={452}
      subtitle={trade && `${trade.symbol} · ${trade.money} · bought ${shortDate(trade.opened)}, sold ${shortDate(trade.closed)}`
        + ` · ${trade.exit_reason || 'closed'}`}
      actions={trade && chart && <>
        <span className="chip"><Delta value={trade.return_pct}>{pct(trade.return_pct, 2)}</Delta></span>
        {trade.r_multiple != null && <span className="chip num text-ink1">{num(trade.r_multiple, 2)} R</span>}
        <span className="chip num text-ink1">{sessionsText(trade.sessions)}</span>
        <Seg label="View" options={VIEWS} value={view} onChange={setView} />
      </>}>
      {v.anatomy.recent.length === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : !trade || !chart ? (
        <Empty>No chart for these trades.</Empty>
      ) : (
        <div className="mt-auto pt-3">
          {view === 'Chart' ? (
            <CandleChart bars={chart.bars} indicator={chart.indicator} stop={chart.stop} entry={chart.entry}
              exit={chart.exit} entryPrice={chart.entry_price} exitPrice={chart.exit_price}
              height={chart.indicator ? 216 : 300}
              ariaLabel={`${trade.symbol} daily bars with the buy, the sell${chart.stop != null ? ' and the stop' : ''}`} />
          ) : (
            <CandleTable bars={chart.bars} indicator={chart.indicator} entry={chart.entry} exit={chart.exit} />
          )}
        </div>
      )}
    </Panel>
  )
}

function RecentRow({ r, selected, onSelect }: { r: RecentTrade; selected: boolean; onSelect: () => void }) {
  const inner = (
    <>
      <BookMark kind={r.money} color="var(--s2)" />
      <span className="num font-semibold w-12 flex-none text-left">{r.symbol}</span>
      <span className="num text-xs text-ink3 w-14 flex-none whitespace-nowrap text-left">{monthLabel(r.closed, true)}</span>
      <span className="chip" style={{ padding: '3px 8px', fontSize: 11 }}>
        {r.exit_reason === 'stop' && <Icon name="shield" size={12} style={{ color: 'var(--serious)' }} />}
        {reasonWord(r.exit_reason)}
      </span>
      {!r.chart && <span className="text-2xs text-ink3">no chart</span>}
      <span className="ml-auto text-sm"><Delta value={r.return_pct} digits={1}>{pct(r.return_pct, 1)}</Delta></span>
    </>
  )
  const look = 'flex w-full items-center gap-2.5 h-11 px-2.5 rounded-[7px] text-left'
  return r.chart ? (
    <button type="button" className={`${look} ease`} aria-pressed={selected} onClick={onSelect}
      aria-label={`${r.symbol}, closed ${shortDate(r.closed)}`}
      style={selected ? { background: 'var(--panel2)', boxShadow: 'inset 0 0 0 1px var(--line2)' } : undefined}>
      {inner}
    </button>
  ) : (
    <div className={look}>{inner}</div>
  )
}

/** The anatomy chart and the recent trades that pick what it shows. */
export function AnatomySection({ v }: { v: StrategyView }) {
  const [selected, setSelected] = useState(v.anatomy.selected)
  return (
    <>
      <AnatomyPanel v={v} selected={selected} />
      <Panel id="recent" title="Recent trades" span={4} height={452}
        actions={v.trades.length > 0 && (
          <a href="#trades-title" className="text-xs">All {v.trades.length}</a>
        )}>
        {v.anatomy.recent.length === 0 ? (
          <Empty>No closed trades yet.</Empty>
        ) : (
          <ul className="mt-2 -mx-2.5">
            {v.anatomy.recent.map((r) => (
              <li key={r.key}>
                <RecentRow r={r} selected={r.key === selected} onSelect={() => setSelected(r.key)} />
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  )
}
````

`web/src/pages/strategy/WorthPanel.tsx`:

````tsx
import { useState } from 'react'
import { Scatter, type ScatterPoint, ScatterTable } from '../../charts/Scatter'
import { Panel, Seg } from '../../components/bits'
import type { StrategyView, WorthPoint } from '../../lib/api'
import { pct } from '../../lib/format'

const VIEWS = ['Chart', 'Table'] as const

/** Real is solid, paper hatched, and the backtest and the benchmark dotted; long-term money is slate. */
function look(p: WorthPoint, book: StrategyView['book']): Pick<ScatterPoint, 'color' | 'style'> {
  if (p.key === 'backtest') return { color: 'var(--s2)', style: 'dotted' }
  if (p.key === 'book') return { color: 'var(--s2)', style: book === 'paper' ? 'hatched' : 'solid' }
  if (p.key === 'long_term') return { color: 'var(--s1)', style: 'solid' }
  return { color: 'var(--ref)', style: 'dotted' }
}

export function WorthPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const points: ScatterPoint[] = v.worth.points.map((p) => ({
    key: p.key, label: p.label, period: p.period, x: p.drop_pct, y: p.return_pct, ...look(p, v.book),
    sub: `${pct(p.return_pct, 1)}/yr · ${p.period}${p.early ? ' · early' : ''}`,
  }))
  return (
    <Panel id="worth" title="Is it worth it?" subtitle="Yearly return against the worst drop along the way" span={7}
      height={380} actions={points.length > 0 && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      <div className="mt-auto pt-3">
        {view === 'Chart' || points.length === 0
          ? <Scatter points={points} ariaLabel="Yearly return against worst drop" />
          : <ScatterTable points={points} />}
      </div>
    </Panel>
  )
}
````

`web/src/pages/strategy/MonthlyPanel.tsx`:

````tsx
import { useState } from 'react'
import { MonthGrid, MonthTable } from '../../charts/MonthGrid'
import { Delta, Missing, Panel, Seg } from '../../components/bits'
import type { StrategyView } from '../../lib/api'
import { monthLabel, pct } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'

const VIEWS = ['Chart', 'Table'] as const

function Figure({ label, figure }: { label: string; figure: { month: string; value: number } | null }) {
  return (
    <div className="flex justify-between">
      <span className="text-ink2">{label}{figure && ` · ${monthLabel(`${figure.month}-01`)}`}</span>
      {figure ? <Delta value={figure.value} digits={1}>{pct(figure.value, 1)}</Delta> : <Missing />}
    </div>
  )
}

export function MonthlyPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const m = v.monthly
  const money = v.book ?? 'real'
  const word = MONEY_WORD[money]
  return (
    <Panel id="monthly" title="Month by month" subtitle={`${word} book against your long-term accounts`} span={5}
      height={380} actions={<Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      <div className="mt-4">
        {view === 'Chart'
          ? <MonthGrid months={m.months} bookLabel={word} money={money} ariaLabel="Monthly returns, book against long-term" />
          : <MonthTable months={m.months} bookLabel={word} />}
      </div>
      <div className="mt-auto border-t border-line pt-3.5 flex flex-col gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-ink2">Months ahead of long-term</span>
          <span className="num">{m.compared ? `${m.ahead} of ${m.compared}` : '—'}</span>
        </div>
        <Figure label="Best month" figure={m.best} />
        <Figure label="Worst month" figure={m.worst} />
      </div>
    </Panel>
  )
}
````

`web/src/pages/strategy/TradesPanel.tsx`:

````tsx
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Missing, Panel } from '../../components/bits'
import { type StrategyView, type TradeRow, useShell } from '../../lib/api'
import { monthLabel, num, pct, signedMoney } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'
import { reasonWord } from './Anatomy'

type SortKey = 'closed' | 'return' | 'pnl'
interface Sort { key: SortKey; dir: 'desc' | 'asc' }

const VALUE: Record<SortKey, (t: TradeRow) => string | number> = {
  closed: (t) => `${t.closed}|${t.opened}|${t.symbol}`,
  return: (t) => t.return_pct,
  pnl: (t) => t.pnl,
}

/** "18 Sep" this year, "26 Nov 2025" before it */
function day(iso: string, year: number): string {
  return Number(iso.slice(0, 4)) === year ? monthLabel(iso, true) : `${monthLabel(iso, true)} ${iso.slice(0, 4)}`
}

function SortHeader({ label, k, sort, onSort, right = false }: {
  label: string; k: SortKey; sort: Sort; onSort: (key: SortKey) => void; right?: boolean
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

/** Every closed trade in the primary book, newest first; sortable by closed date, return and P/L. */
export function TradesPanel({ v }: { v: StrategyView }) {
  const [sort, setSort] = useState<Sort>({ key: 'closed', dir: 'desc' })
  const shell = useShell()
  const year = new Date(shell.data?.now ?? Date.now()).getUTCFullYear()
  const word = MONEY_WORD[v.book ?? 'real']
  const onSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'desc' ? 'asc' : 'desc' } : { key, dir: 'desc' }))
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
              {sorted.map((t) => (
                <tr key={`${t.symbol}-${t.opened}`}>
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

`web/src/pages/strategy/Strategy.tsx`:

````tsx
// One strategy: how it trades and whether it is behaving the way its backtest said it would.
import { BookMark, Seg } from '../../components/bits'
import { type Expected, HttpError, type Money, type StrategyView, useStrategy } from '../../lib/api'
import { Soon } from '../Soon'
import { BookChips, MONEY_WORD } from '../strategies/Strategies'
import { AnatomySection } from './Anatomy'
import { BehavingPanel, ScorecardPanel } from './Behaving'
import { FunnelPanel } from './FunnelPanel'
import { HowItTrades } from './HowItTrades'
import { MonthlyPanel } from './MonthlyPanel'
import { SlotsPanel } from './SlotsPanel'
import { TradesPanel } from './TradesPanel'
import { WorthPanel } from './WorthPanel'

const BOOKS = ['Real', 'Paper'] as const

/** "Backtest 2006–2020" */
export function backtestText(expected: Expected): string {
  const source = expected.source || 'backtest'
  return `${source[0].toUpperCase()}${source.slice(1)}${expected.window ? ` ${expected.window}` : ''}`
}

function Header({ v, onBook }: { v: StrategyView; onBook: (book: Money) => void }) {
  return (
    <header className="mb-5">
      <div className="label">Strategy</div>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">{v.name}</h1>
          {v.summary && <p className="text-ink2 mt-1.5 max-w-[680px]">{v.summary}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <BookChips books={v.books} />
          {v.expected && <span className="chip"><BookMark kind="expected" />{backtestText(v.expected)}</span>}
        </div>
      </div>
      {v.toggle && v.book && (
        <div className="mt-4">
          <Seg label="Book" options={BOOKS} value={MONEY_WORD[v.book]}
            onChange={(word) => onBook(word === 'Real' ? 'real' : 'paper')} />
        </div>
      )}
    </header>
  )
}

export function Strategy({ id, book, onBook }: { id: string; book: Money; onBook: (book: Money) => void }) {
  const strategy = useStrategy(id, book)
  if (strategy.isPending) return <p className="text-ink3" role="status">Loading the strategy…</p>
  if (!strategy.data) {
    if (strategy.error instanceof HttpError && strategy.error.status === 404) {
      return <Soon title="Not found" text="There is no page here. Pick one from the menu." />
    }
    return <div role="alert" className="panel">This strategy couldn&rsquo;t load: {strategy.error.message}</div>
  }
  const v = strategy.data
  return (
    <>
      <Header v={v} onBook={onBook} />
      <div className="grid12">
        <HowItTrades steps={v.steps} sizing={v.sizing} />
        <BehavingPanel v={v} />
        <ScorecardPanel v={v} />
        <FunnelPanel v={v} />
        <SlotsPanel v={v} />
        {/* keyed by book: switching Real | Paper starts again from that book's newest charted trade */}
        <AnatomySection key={v.primary ?? 'none'} v={v} />
        <WorthPanel v={v} />
        <MonthlyPanel v={v} />
        <TradesPanel v={v} />
      </div>
    </>
  )
}
````


```bash
.venv/Scripts/kestrel demo --view home --now 2026-09-25T21:08:00+00:00 > web/src/test/fixtures/home.json
```

(Only the one attention link changes in `home.json`.)

- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .` and, in `web/`, `npx vitest run && npx tsc --noEmit && npm run build`
Expected: `136 passed` (`test_home_view.py` 15); `All checks passed!`; `Tests  115 passed (115)` (`StrategyTrades.test.tsx` 9); tsc prints nothing; `✓ built`. Until `home.json` is regenerated, `test_generated_file_is_current[home.json]` fails with the command above.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/views/home.py tests/test_home_view.py web/src/test/fixtures/home.json web/src/pages/strategy/Strategy.tsx web/src/pages/strategy/Anatomy.tsx web/src/pages/strategy/WorthPanel.tsx web/src/pages/strategy/MonthlyPanel.tsx web/src/pages/strategy/TradesPanel.tsx web/src/pages/strategy/StrategyTrades.test.tsx
git commit -m "feat(web): trade anatomy, is it worth it, month by month and all trades; Home links to the strategy"
```

---

### Task 13: CI on Windows, the docs, and the screenshot pass

**Files:**
- Modify (replace the whole file): `.github/workflows/ci.yml`
- Modify (exact lines below): `README.md`, `AGENTS.md`, `docs/specs/2026-09-25-kestrel-design.md`, `docs/specs/2026-09-26-phase-3a-strategies-design.md`

**Interfaces:** none (CI and documentation).

- [ ] **Step 1: Add the Windows job (replace the whole file)**

`.github/workflows/ci.yml`:

````yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  python:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest
  python-windows:
    # the paths, the console code page and the server's path checks behave differently on Windows
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest
  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: web/package-lock.json
      - run: npm ci
      - run: npm test
      - run: npm run build
````


- [ ] **Step 2: Update the docs**

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
- **Status:** design approved. Phases 0 (mockups), 1 (this repo, spec, design system, hygiene test) and 2 (the skeleton) are done; Phase 3 is next.
````

with:

````text
- **Status:** design approved. Phases 0 (mockups), 1 (this repo, spec, design system, hygiene test), 2 (the skeleton) and 3a (the Strategies pages) are done; Phase 3b (Books) is next.
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
    views/                  one Snapshot → a view model per page: home.py (net worth, allocation, comparison,
                            attention list, books), shell.py (name, settings, sources, counts)
````

with:

````text
    views/                  one Snapshot → a view model per page: home.py (net worth, allocation, comparison,
                            attention list, books), shell.py (name, settings, sources, counts),
                            strategy.py (the strategy list and one strategy's eight sections)
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
    src/pages/              one folder per page: home/ (Phase 2); accounts, books, strategies, … from Phase 3
````

with:

````text
    src/pages/              one folder per page: home/ (Phase 2); strategies/ and strategy/ (Phase 3a); books, accounts, … later
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
| 3 | Books + Strategies pages; the chart kit | next |
````

with:

````text
| 3 | Books + Strategies pages; the chart kit | 3a done (Strategies, the chart kit); 3b (Books) next |
````

In `docs/specs/2026-09-26-phase-3a-strategies-design.md`, replace:

````text
- **Status:** design approved in conversation. Awaiting spec review, then the implementation plan.
````

with:

````text
- **Status:** built (plan: [`../plans/2026-09-26-phase-3a-strategies.md`](../plans/2026-09-26-phase-3a-strategies.md)).
````

In `README.md`, replace:

````text
> **Status: Phase 2 of 5 — the skeleton runs.** Home works end to end on demo data; Accounts, Books, Strategies,
> Backtests, Activity and Settings arrive in later phases.
````

with:

````text
> **Status: Phase 3a of 5 — Home and the Strategies pages run.** Both work end to end on demo data; Books,
> Accounts, Backtests, Activity and Settings arrive in later phases.
````

In `AGENTS.md`, replace:

````text
**Status:** Phase 2 of 5 — the skeleton: contract, profile, demo connector, read-only server, shell and Home.
````

with:

````text
**Status:** Phase 3a of 5 — the skeleton plus the Strategies pages (the list, one strategy, the chart kit). Books is Phase 3b.
````


- [ ] **Step 3: Run everything from a clean start**

```bash
.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .
(cd web && npm ci && npx vitest run && npx tsc --noEmit && npm run build)
```
Expected: `136 passed`; `All checks passed!`; `Tests  115 passed (115)`; tsc prints nothing; `✓ built`.

- [ ] **Step 4: The screenshot pass (the check jsdom can't do)**

Run `.venv/Scripts/kestrel serve --no-open` and open `http://127.0.0.1:8030`. At 1440 × 1000, 1024, 768 and 390 × 844, in both themes (the theme button, or `localStorage.setItem('kestrel.theme', 'light'|'dark')` and reload), open `/`, `/strategies`, `/strategies/rsi2`, `/strategies/rsi2?book=paper`, `/strategies/ibs` and `/strategies/nope`, and paste this into the browser console on each:

```js
(() => {
  const over = [...document.querySelectorAll('section.panel, article.panel')]
    .filter((s) => s.scrollHeight > s.clientHeight + 1).map((s) => s.getAttribute('aria-labelledby'))
  return { sidewaysScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth, over }
})()
```
Expected everywhere: `{ sidewaysScroll: 0, over: [] }`.

Then look:
- **`/strategies/rsi2`, dark, 1440:** it matches `docs/design/mockups/strategy.html` section for section (the Real | Paper switch sits under the header instead of in the top bar, and there are no tabs, as the spec decided).
- **Hover and keys:** hovering the histogram shows "Trades returning …"; Tab to the slots strip and press End for "Fri 25 Sep · In use 4 of 5"; Real | Paper changes the address to `?book=paper`.
- **390 px:** the steps stack, the month grid scrolls sideways inside its panel, and the scatter's labels move into a key under the chart.
- **`/strategies/nope`:** the in-shell "Not found" page, with Trading › Strategies in the breadcrumb.

- [ ] **Step 5: Commit, push, and watch CI**

```bash
git add .github/workflows/ci.yml README.md AGENTS.md docs/specs/2026-09-25-kestrel-design.md docs/specs/2026-09-26-phase-3a-strategies-design.md
git commit -m "ci: a windows-latest Python 3.11 job; docs: Phase 3a is done"
git push
gh run watch --exit-status
```
Expected: all three CI jobs green (`python` 3.11 and 3.12, `python-windows`, `web`).

---

## Done when

- `/strategies` lists every strategy with its books and band, and `/strategies/<id>` shows the eight sections on demo data in both themes, with `?book=real|paper` in the address.
- 136 Python tests and 115 web tests pass locally and in CI (including Windows); ruff and tsc are clean.
- The screenshot pass shows no overflow and no sideways scroll at 390 to 1440 px.
- The parent spec's Phase 3 row reads "3a done"; Books is Phase 3b.

## Self-review

- **Spec coverage:** §2.1 list → Task 10; §2.2 header and toggle → Task 11; sections 1–4 → Tasks 4, 11; sections 5–8 → Tasks 5, 12; §2.3 primary book → Task 4; §2.4 links → Tasks 10, 12; §3.1 contract → Task 2; §3.2 derived figures → Tasks 4–5; §3.3 view models → Tasks 4–5 (mirrored in Task 10); §3.4 server and CLI → Task 6; §3.5 demo → Task 3; §4 web → Tasks 7–12; §5 follow-ups → Task 1 (items 1–5) and Task 13 (item 6); §6 testing → every task, the screenshot pass in Task 13; §7 out of scope → nothing here writes, places or connects.
- **Interpretations** (decided in the prototype, listed for the reviewer):
  - Lines and points follow the money encoding everywhere (real solid, paper dashed or hatched), so on `?book=paper` the primary paper book's funnel line is dashed and the real one solid; the spec's "primary solid, other dashed" describes the default (real) view.
  - A same-day trade (Opening leader) opens and closes on one bar: its entry bar opens at the entry price and closes at the exit price.
  - On a narrow chart where the scatter's labels can't all sit clear of each other, they move into a key under the chart instead of overlapping ("direct labels only where they don't collide", design system).
  - The Real | Paper switch sits under the page header; the mockup's top-bar placement belonged to its tabs, which the spec leaves out.
- **Placeholders:** none; every step has its file blocks or its exact command and output.
- **Names and types:** the Python view models (Tasks 4–5) and `web/src/lib/api.ts` (Task 10) share field names, pinned by the generated fixtures and `satisfies Widen<…>`; chart props (Tasks 7–9) are consumed with the same names in Tasks 11–12.
