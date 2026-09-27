# Phase 5 — one dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** finish kestrel as the only dashboard: command feeds (no second server), the six new contract blocks and a
debt category, the Books/Book, Plan, Reserves, Calendar, Backtests, Activity and Settings pages, and the `rails`
connector.

**Architecture:** the contract grows additively (Task 1); the demo connector gets fictional examples of every new
block (Task 2), so every page is built and tested against demo data. Each page is one vertical slice — a pure view
module in `src/kestrel/views/`, one GET route, its TypeScript types and hook in `web/src/lib/api.ts`, a page folder,
a route and a nav entry, a generated fixture — so page tasks can run in parallel branches and merge by appending.

**Tech stack:** Python 3.11 · pydantic 2 · FastAPI (GET only) · React 19 + TypeScript + TanStack Router/Query ·
Tailwind v4 with the Graphite tokens · Vitest + Testing Library · ruff.

**Spec:** [`../specs/2026-09-27-phase-5-one-dashboard-design.md`](../specs/2026-09-27-phase-5-one-dashboard-design.md).
Read it first; section numbers below point into it.

**Execution note:** this plan fixes every shared interface in code (the contract, view names, routes, hooks). Inside
a slice it states the behaviour and the tests by name and case rather than pasting finished code: each implementer
writes the failing test first (TDD), sees it fail, then writes the code. The earlier phases' plans show the house
style for views, pages and tests — copy their patterns (`views/strategy.py`, `pages/strategy/*`).

## Global Constraints

- Read-only: GET routes only; `tests/test_read_only_guard.py` must stay green; no write anywhere.
- Public repo: fictional demo data only (the demo's names, e.g. "Alex"); no machine paths, private hosts, real
  symbols from a real book, balances or email addresses (`tests/test_hygiene.py`).
- `CONTRACT_VERSION` stays `"1"`; every change to the contract is additive with defaults.
- Every page: an honest empty state naming the kind of source that fills it; works at 390 px (no horizontal page
  scroll; wide tables scroll inside `.table-scroll`); dark and light via tokens only (no raw colours); health, status
  and verdicts never by colour alone (an icon or a word too).
- Numbers go through `web/src/lib/format.ts` (`money`, `signedMoney`, `pct`, `num`); dates as the existing pages show
  them.
- Generated files are regenerated with the command the failing `tests/test_generated_files.py` prints.
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- Checks before every commit: `.venv/Scripts/python.exe -m pytest -q` · `.venv/Scripts/ruff.exe check .` · in `web/`:
  `npm test` · `npm run lint` · `npx tsc -b` (or `npm run build`).

## Review Focus

1. **A command that hangs or floods output** (a desk script stuck on a lock, a debug print loop): kestrel must answer
   within `timeout` + a second, kill the child, and show a readable error — never a hung page. Task 3 pins it.
2. **Debt counted as money owned** anywhere (net worth, allocation, account totals, goals by category): every sum over
   accounts must treat `debt` as owed. Task 2 pins net worth and allocation; Task 6 pins reserves totals.
3. **A target whose account has no holdings or a zero value** (a new account, an empty feed): the actual is unknown
   ("—"), never a division by zero or a fake 0 %. Task 5 pins it.
4. **Events with hostile text or links** (`javascript:` URLs, HTML in titles): the contract refuses non-https URLs;
   text renders as text. Task 1 and Task 7 pin it.
5. **Huge research records** (thousands of backtests): the view bounds its lists (families all, rows the newest 200)
   and the page stays usable. Task 8 pins it.

---

### Task 1: Contract additions

**Files:** modify `src/kestrel/contract.py`, `src/kestrel/connectors/__init__.py` (dedupe), test
`tests/test_contract.py`, `tests/test_connectors.py`; regenerate `docs/contract/snapshot.schema.json`; update
`docs/data-contract.md`.

**Produces (exact):**

```python
Category = Literal["long_term", "trading", "cash", "debt", "other"]

class Account(Model):            # existing fields unchanged, plus:
    rate_pct: float | None = None   # yearly interest: what cash earns (APY), what debt costs (APR)
    limit: float | None = None      # a credit line's limit (debt accounts)

class Target(Model):
    id: str
    account_id: str | None = None
    label: str
    symbols: list[str] = []
    unit: Literal["%", "x"] = "%"
    target: float | None = None
    low: float | None = None
    high: float | None = None
    actual: float | None = None
    note: str = ""
    # validator: at least one of target/low/high; unit "x" requires actual; low <= high when both

class Thesis(Model):
    symbol: str
    name: str = ""
    status: str = "active"
    health: Literal["ok", "watch", "alert", "none"] = "none"
    reasons: list[str] = []
    conviction: str = ""
    opened: dt.date | None = None
    last_reviewed: dt.date | None = None
    wrong_if: list[str] = []
    account_ids: list[str] = []

class Event(Model):
    date: dt.date
    symbol: str = ""
    kind: Literal["earnings", "filing", "insider", "dividend", "other"]
    title: str
    detail: str = ""
    url: str = Field(default="", pattern=r"^(https://[^\s<>\"']+)?$")

class Goal(Model):
    id: str
    label: str
    target: float
    account_id: str | None = None
    category: Category | None = None
    by: dt.date | None = None
    note: str = ""

class Exposure(Model):
    symbol: str
    name: str = ""
    value: float
    direct: float = 0.0
    sector: str = ""

class Backtest(Model):
    id: str
    name: str
    family: str = ""
    window: str = ""
    verdict: Literal["pass", "fail", "refused", "pending"]
    at: AwareDatetime
    strategy_id: str | None = None
    trades: int | None = None
    avg_trade_pct: float | None = None
    t_stat: float | None = None
    calmar: float | None = None
    max_drawdown_pct: float | None = None
    note: str = ""

class Snapshot(Model):           # plus these lists, all default []
    targets: list[Target] = []
    theses: list[Thesis] = []
    events: list[Event] = []
    goals: list[Goal] = []
    exposures: list[Exposure] = []
    backtests: list[Backtest] = []

_LIST_FIELDS gains "targets", "theses", "events", "goals", "exposures", "backtests".
```

Dedupe (`connectors/__init__.py`, both within one source and across sources, first wins, ids named in the source's
note like today): targets, goals and backtests by `id`; theses and exposures by `symbol`; events by
`(date, kind, symbol, title)` (not named in the note — they have no id).

- [ ] **Step 1: failing tests** in `tests/test_contract.py`:
  `test_new_blocks_default_empty` (a v1 document without them loads, all six lists empty);
  `test_debt_category_and_rates_round_trip`;
  `test_target_needs_an_aim` (no target/low/high → ValidationError);
  `test_ratio_target_needs_actual` (unit "x", actual None → error);
  `test_target_low_above_high_is_refused`;
  `test_event_url_must_be_https` (parametrize: `""` ok, `"https://example.com/a"` ok, `"http://x"`,
  `"javascript:alert(1)"`, `"https://a b"` refused);
  `test_backtest_verdicts` (unknown verdict refused);
  `test_merge_keeps_every_new_block`.
  In `tests/test_connectors.py`: `test_duplicate_new_block_ids_first_source_wins` (two demo-like parts with the same
  target id / thesis symbol / event tuple; the second source's detail names the target id and thesis symbol).
- [ ] **Step 2:** run them, see them fail for the missing names.
- [ ] **Step 3:** implement; regenerate the schema (`kestrel schema > docs/contract/snapshot.schema.json`).
- [ ] **Step 4:** full checks; `docs/data-contract.md` gets a short section per block (the tables of spec §3).
- [ ] **Step 5:** commit `feat(contract): targets, theses, events, goals, exposures, backtests and debt`.

### Task 2: Demo data for every new block, and debt in Home

**Files:** modify `src/kestrel/connectors/demo.py`, `src/kestrel/views/home.py`, `src/kestrel/views/accounts.py`
(categories), tests `tests/test_demo_connector.py`, `tests/test_home_view.py`, `tests/test_accounts_view.py`;
regenerate the web fixtures.

**Consumes:** Task 1's models. **Produces:** demo snapshot containing, deterministically (seed-driven like the rest):
a savings account (`category="cash"`, `rate_pct` 4.1) and a checking account (cash), a credit card
(`category="debt"`, value 640.0, `limit` 5000.0, `rate_pct` 24.9); 8 targets on the demo accounts (6 `%` with
target/low/high, 1 sleeve with low/high over two symbols, 1 `x` ratio with actual) — at least one over and one under
its band; a thesis for every demo holding (mixed health: 2 ok, 1 watch, 1 alert, rest none; reasons; wrong_if 2–3
lines each); 20 events over ±60 days of the demo `now` (earnings ahead, filings behind, 2 insider, 1 dividend) with
`https://www.sec.gov/...`-style links on filings; 3 goals (one per account type, one for net worth); exposures for
the demo holdings (direct + through a fund, sectors); 120 backtests over 12 families and windows develop/confirm
(mostly fail, ~15 % pass, 2 refused, 3 pending). All fictional; reuse the demo's existing symbols.

Home changes (spec §4.3): `net_worth.total` = owned − owed; `NetWorth` gains `owed: float` (0 when none); the
allocation's slices exclude debt. (The Needs-you items for targets and theses belong to Task 5, which owns the target
arithmetic.) Accounts view: a debt account's growth is not shown as market growth (its row shows the amount owed;
`growth` None).

- [ ] **Step 1: failing tests:** `test_demo_has_every_new_block` (counts and the over/under targets exist);
  `test_net_worth_subtracts_debt` (a snapshot with 1000 owned, 200 debt → 800; allocation shares sum to 100 over the
  owned categories only); `test_debt_account_has_no_market_growth`.
- [ ] **Step 2–4:** fail, implement, regenerate fixtures, full checks (vitest: update the Home test only where the
  net-worth figure changed; add a line "owed" rendering test in `NetWorthPanel` when `owed > 0`).
- [ ] **Step 5:** commit `feat(demo): every new block in the demo; net worth net of debt`.

### Task 3: Command feeds

**Files:** create `src/kestrel/connectors/command.py`; modify `src/kestrel/profile.py` (`_feed_shape`),
`src/kestrel/connectors/__init__.py` (`build`), `src/kestrel/connectors/feed.py` (a `command=` mode sharing
`parse`/`keep`), `tests/test_read_only_guard.py` (new rule), docs `docs/connectors.md`, `profile.example.toml`;
tests `tests/test_command_feed.py`, `tests/test_profile.py`, fixture program `tests/fixtures/feed_program.py`.

**Produces:**

```python
# connectors/command.py
MAX_OUTPUT = 20 * 1024 * 1024
DEFAULT_TIMEOUT = 30.0
DEFAULT_REFRESH = timedelta(minutes=1)

def run(argv: list[str], *, cwd: Path, timeout: float, limit: int = MAX_OUTPUT) -> bytes:
    """Run argv (never through a shell), stdin closed, no console window on Windows. Returns stdout.
    Raises ConnectorError worded for a person: 'no such program: <name>', 'the command took longer than <t> s',
    'the command failed (exit <n>): <last stderr line, <=160 chars>', 'the command printed more than 20 MB'.
    On timeout or overflow the child is killed before returning."""

def cached_run(key: tuple, argv: list[str], *, cwd: Path, timeout: float, refresh: timedelta,
               now: Callable[[], float] = time.monotonic) -> bytes:
    """One run per key at a time; a result (bytes or the ConnectorError) is reused for `refresh`; callers arriving
    while a run is in flight wait for it. Module-level cache guarded by a lock per key."""
```

`FeedConnector(..., command: list[str] | None = None, cwd: Path | None = None, refresh: timedelta = DEFAULT_REFRESH)`;
`snapshot()` for a command = `parse(cached_run((source_id, tuple(argv)), ...))` then `keep(...)`, exactly like a file.
Profile: exactly one of `url`/`path`/`command`; `command` is a non-empty list of non-empty strings (message:
'a command is a list: the program, then its arguments, e.g. command = ["python", "-m", "desk.feed"]'); `cwd` a
non-empty string; `timeout` 1–120 for a command (1–60 otherwise, unchanged); `refresh` a duration from 5s to 1h;
`token_env` is refused with a command. `_resolve_paths` resolves `cwd` and a program path containing `/` or `\`
against the profile folder; a bare program name stays for PATH lookup.

Guard rule (`tests/test_read_only_guard.py`): `test_only_the_command_runner_starts_programs` — `subprocess` (and
`os.system`, `os.popen`, `os.spawn*`, `os.exec*`) appear only in `connectors/command.py`; no call anywhere passes
`shell=True`.

- [ ] **Step 1: failing tests** (`tests/test_command_feed.py`; the fixture program is a tiny Python script run with
  `sys.executable`, modes chosen by argv: `ok` prints the demo snapshot JSON, `fail` writes "boom\nlast line" to
  stderr and exits 2, `sleep` sleeps 10 s, `flood` prints 21 MB, `count` appends a line to a temp file then prints
  JSON): success returns a Snapshot with one source row of kind `feed`; exit 2 → "the command failed (exit 2): last
  line"; `sleep` with timeout 1 → "the command took longer than 1 s" in under 3 s; missing program → "no such program";
  flood → "more than 20 MB"; two snapshots within `refresh` run the program once (count file has 1 line); after
  `refresh` it runs again (inject `now`); 5 threads at once → one run; an error result is reused within `refresh` too.
  Profile tests: both `url` and `command` refused; `command = "python x"` (a string) refused with the list message;
  `token_env` with a command refused; `refresh = "1s"` refused; relative `cwd` and `./tools/x.py` resolved against
  the profile folder, `python` left alone. Guard test as above.
- [ ] **Step 2–4:** fail, implement, full checks.
- [ ] **Step 5:** docs: `docs/connectors.md` feed section gains the command form, its errors and the safety note
  (spec §2); `profile.example.toml` gains a commented command example. Commit
  `feat(feed): a feed can be a command kestrel runs itself`.

### Task 4: Books and Book

**Files:** create `src/kestrel/views/books.py`, `web/src/pages/books/{Books.tsx,Books.test.tsx}`,
`web/src/pages/book/{Book.tsx,Book.test.tsx,EquityPanel.tsx,…}`; modify `src/kestrel/views/home.py` (move
`_book_rows` and `BookRow` into `views/books.py` as `book_rows()`/`BookRow` and import them back — Home's output must
not change), `src/kestrel/server.py`, `src/kestrel/cli.py` (`--view books|book`), `web/src/lib/api.ts`,
`web/src/router.tsx`, tests `tests/test_books_view.py`, `tests/test_generated_files.py`.

**Produces:** `GET /api/books` → `BooksView{as_of, real_value, paper_value, rows: list[BooksRow]}` where
`BooksRow = BookRow + spark: list[float]` (last 60 values of the book's history, oldest first);
`GET /api/books/{id}` → `BookView{as_of, book: BooksRow, strategy_id, strategy_name, account_id,
equity: {dates, values (growth index %), benchmark (same start, %), return_pct, max_drop_pct},
drawdown: {dates, values (% below running peak, <= 0)}, scorecard: {trades, win_rate, avg_trade_pct, avg_win_pct,
avg_loss_pct, total_pnl, best_pct, worst_pct, band_lo, band_hi, verdict}, positions: list[{symbol, quantity,
entry_price, last_price, stop_price, room_pct (to stop, None without stop), pnl, pnl_pct, opened, days, flag
('no_stop'|None)}], trades: list[Trade] newest first, runs: list[Run] (this book's, next first then newest)}`;
404 for an unknown id. Hooks `useBooks()`, `useBook(id)`. Routes `/books`, `/books/$bookId`; Home's books table rows
link to `/books/<id>`.

- [ ] **Step 1: failing tests:** `test_books_view_real_first_then_paper_with_totals`; `test_spark_is_last_60_values`;
  `test_book_view_equity_and_drawdown_share_dates` (drawdown ≤ 0, 0 at each new peak);
  `test_book_scorecard_matches_home_verdict`; `test_position_without_stop_is_flagged`; `test_unknown_book_404`;
  `test_home_unchanged_after_the_move` (Home fixture identical). Vitest: Books renders real and paper sections from
  the fixture, sparkline present, a row links to its book; Book renders header, equity, drawdown, scorecard, positions
  (a no-stop flag shows text, not colour only), trades; unknown id shows "Not found".
- [ ] **Step 2–4:** fail, implement (reuse `LineChart` for equity and drawdown on one time axis — small multiples),
  regenerate fixtures (`books.json`, `book-<demo id>.json`), full checks.
- [ ] **Step 5:** commit `feat(books): the Books list and a page per book`.

### Task 5: Plan

**Files:** create `src/kestrel/views/plan.py`, `web/src/pages/plan/*`; modify server, cli (`--view plan`), api.ts,
router, Shell `NAV` (Money: Accounts, Plan), tests `tests/test_plan_view.py`, generated files.

**Produces:** `GET /api/plan` → `PlanView{as_of, accounts: list[{account_id, name, rows: list[TargetRow]}],
unscoped: list[TargetRow], theses: list[ThesisRow], goals: list[GoalRow], counts: {off_plan, theses_alert,
theses_watch}}`. `TargetRow{id, label, symbols, unit, target, low, high, actual, status ('on'|'over'|'under'|
'unknown'), gap (money for %, ratio units for x; None when unknown), gap_text, note}` — off plan first, then by label.
Actual for `%` = sum of the account's holdings whose symbol is in `symbols` ÷ the account's value × 100; unknown when
the account is missing or its value is 0. `gap` for `%`: money to the nearest band end (`(low − actual)/100 × value`).
`ThesisRow{symbol, name, health, reasons, conviction, status, opened, last_reviewed, days_since_review, held,
held_value, account_names, wrong_if}` — alert, watch, ok, none; then symbol. `GoalRow{id, label, scope_text,
current, target, progress_pct (0–100, capped), by, months_left, monthly_needed (None without `by` or when reached),
reached}` — current = the account's value / the category's owned total / net worth (owned − owed).

Home's Needs-you (`views/home.py` attention) gains, using this task's target evaluation: each target off plan →
`warning` "<label> is over/under plan in <account name>" linking `/plan`; each thesis with health `alert` →
`warning`, `watch` → `note`, "<symbol>: thesis needs a look" with the first reason as detail, linking `/plan`.

- [ ] **Step 1: failing tests:** `test_attention_lists_off_plan_targets_and_alert_theses` (levels, links, wording);
  `test_percent_actual_from_holdings`; `test_zero_value_account_is_unknown`;
  `test_ratio_target_uses_feed_actual`; `test_sleeve_sums_its_symbols`; `test_status_and_gap_money`;
  `test_off_plan_first`; `test_theses_sorted_by_health_and_held_flag`; `test_goal_progress_and_monthly_needed`
  (a goal due in 10 months with 1 000 to go → 100/month); `test_goal_reached_caps_progress`; `test_no_source_is_empty`.
  Vitest: the plan bar (pure geometry function `bandGeometry(low, high, target, actual, domain)` with its own tests:
  open ends, actual outside the domain clamps with an arrow marker) and the page (off-plan row first; health shows its
  word; wrong_if behind a disclosure; goals with progress text; empty state names "an investing feed").
- [ ] **Step 2–4:** fail, implement, fixtures, checks. **Step 5:** commit `feat(plan): targets, theses and goals`.

### Task 6: Reserves

**Files:** create `src/kestrel/views/reserves.py`, `web/src/pages/reserves/*`; modify server, cli, api.ts, router,
`NAV` (Money: …, Reserves), tests `tests/test_reserves_view.py`, generated files.

**Produces:** `GET /api/reserves` → `ReservesView{as_of, cash: list[{id, name, institution, value, rate_pct, as_of}],
debts: list[{id, name, institution, owed, limit, utilization_pct, rate_pct, as_of}], totals: {cash, owed,
net (cash − owed), utilization_pct (Σ owed / Σ limit over lines with a limit; None without)}, spread: {owed_rate_pct
(highest APR among debts with a balance), earned_rate_pct (best cash rate), yearly_cost (Σ owed × its rate),
yearly_earned (Σ cash × its rate), gap (earned − cost)} | None}`. Cash = accounts of category `cash`.

- [ ] **Step 1: failing tests:** totals and utilization; a debt with no limit is left out of utilization; a zero
  balance debt doesn't set the owed rate; spread None with no debt; no cash/debt → empty view. Vitest: page renders
  both tables, the spread sentence ("Your card costs 24.9 %, your savings earn 4.1 %: about $X a year"), the empty
  state names "a feed with cash or debt accounts".
- [ ] **Step 2–4, Step 5:** commit `feat(reserves): cash, debt and the spread`.

### Task 7: Calendar

**Files:** create `src/kestrel/views/calendar.py`, `web/src/pages/calendar/*`; modify server, cli, api.ts, router,
`NAV` (Research: Backtests, Calendar), tests `tests/test_calendar_view.py`, generated files.

**Produces:** `GET /api/calendar` → `CalendarView{as_of, today, upcoming: list[WeekGroup{week_start, items}],
recent: list[EventRow] (last 90 days, newest first), counts: dict[kind, int]}`; `EventRow = Event + held: bool`
(symbol in any holding or open position). Page: kind filter chips (all · earnings · filing · insider · dividend ·
other), links open in a new tab with `rel="noopener noreferrer"`, text only.

- [ ] **Step 1: failing tests:** grouping by ISO week (Monday start) in the profile's time zone; recent excludes >90
  days and future; held flag; counts. Vitest: filter narrows the list; a link has target `_blank` and the rel; an
  event title with `<b>` renders literally.
- [ ] **Step 2–4, Step 5:** commit `feat(calendar): company events ahead and behind`.

### Task 8: Backtests

**Files:** create `src/kestrel/views/backtests.py`, `web/src/pages/backtests/*`; modify server, cli, api.ts, router,
tests `tests/test_backtests_view.py`, generated files.

**Produces:** `GET /api/backtests` → `BacktestsView{as_of, totals: {results, candidates (distinct name), families,
passes_by_window: dict[str,int]}, windows: list[str] (in order of first appearance of each window in the newest
results, then alphabetical), families: list[{family, candidates, best: Backtest | None, verdicts: dict[window,
verdict] (the best verdict per window: pass > pending > fail > refused), last_at}] (families with a pass first, then by
last_at desc), rows: list[Backtest] (newest 200)}`. "Best": the furthest window (by `windows` order) with a pass,
ties by higher `t_stat`; none passed → the newest result.

- [ ] **Step 1: failing tests:** totals; best per family; verdict per window precedence; rows capped at 200 with 5 000
  inputs, in under 1 s; empty. Vitest: filter all/passed/failed; search by family or name; a verdict chip carries its
  word.
- [ ] **Step 2–4, Step 5:** commit `feat(backtests): the research record`.

### Task 9: Activity

**Files:** create `src/kestrel/views/activity.py`, `web/src/pages/activity/*`; modify server, cli, api.ts, router,
tests `tests/test_activity_view.py`, generated files.

**Produces:** `GET /api/activity` → `ActivityView{as_of, days: list[{date, label ('Today'|'Tomorrow'|weekday
date), runs: list[RunRow{time, label, book_id, book_name, status, detail}]}], counts: dict[status,int],
alerts: list[Alert] (serious, warning, note), sources: list[{id, label, kind, status, last_success, age_text,
stale_after, detail}]}`. Days: today first, then future days ascending, then the past 7 days descending; within a day
failed and late first, then by time.

- [ ] **Step 1: failing tests:** ordering of days and within a day; runs older than 7 days dropped; counts; sources
  carry stale_after from the profile. Vitest: the page lists today first, a failed run shows its word and icon, the
  sources table.
- [ ] **Step 2–4, Step 5:** commit `feat(activity): what ran, what is due, what failed`.

### Task 10: Settings

**Files:** create `src/kestrel/views/settings.py`, `web/src/pages/settings/*`; modify server (the app needs the
profile's origin: `create_app(profile, profile_origin: str = "demo data")`), cli (`serve` passes the file it loaded),
api.ts, router, tests `tests/test_settings_view.py`, generated files.

**Produces:** `GET /api/settings` → `SettingsView{as_of, you, app, benchmark, profile (the file path or "demo
data"), contract_version, version, sources: list[{id, label, kind, reads (url, or path, or "<program file name>
<args…>"), stale_after, refresh, timeout, token_env, status, last_success, detail}]}`. Never a token value, never the
environment.

- [ ] **Step 1: failing tests:** a command source shows its program's file name and args (not the full path); a
  url with a token shows `token_env` name only; demo profile says "demo data". Vitest: renders every section.
- [ ] **Step 2–4, Step 5:** commit `feat(settings): the profile and every source, read-only`.

### Task 11: The `rails` connector

**Files:** create `src/kestrel/connectors/rails.py`; modify `connectors/__init__.py` (`build`), `profile.py`
(`path` required for rails), docs `docs/connectors.md`, `profile.example.toml`; tests `tests/test_rails_connector.py`,
fixtures `tests/fixtures/rails/{paper.json,runs.jsonl}` (written from trading-rails' own formats: read
`../trading-rails/src/trading_rails/paper.py` and `runner.py` for the exact keys; no real data).

**Produces:** `RailsConnector(source_id, label, folder: Path)` → a Snapshot with one book `rails-paper` (`money`
paper, `strategy_id` from the latest run's strategy or `"rails"`, `started` = first run's date or the state file's
date), value = cash + Σ quantity × last price (average cost when no last price), positions, a Strategy stub (name
from the run log, summary "From trading-rails"), runs from the run log (one per run id: `done`, or `failed` when a
step failed), book history from the run log's equity points when present, and a Source row (`last_success` = the
newest run's time). Errors: missing folder, missing `paper.json`, torn JSON — each a readable ConnectorError.

- [ ] **Step 1: failing tests** for each of the above against fixtures. **Steps 2–4**, **Step 5:** commit
  `feat(rails): read trading-rails' paper state and run log`.

### Task 12: Navigation, docs and the finish

**Files:** `web/src/shell/Shell.tsx` (final `NAV` per spec §4; phone "More" lists Plan, Reserves, Backtests,
Calendar, Activity, Settings), `README.md` (pages, command feeds, rails), `docs/specs/2026-09-25-kestrel-design.md`
(§11 all phases done; §4 groups), this plan's checkboxes, `AGENTS.md` if a rule changed.

- [ ] **Step 1:** the Shell test asserts every NAV entry has a route that renders (no `Soon` left).
- [ ] **Step 2:** screenshot pass: every page at 390, 1200, 1280, 1440 px, dark and light, demo data; no overflow,
  no clipped labels. Fix what it finds.
- [ ] **Step 3:** commit `docs: phase 5 finished`.
