# Phase 3a — Strategies — design

- **Date:** 2026-09-26
- **Status:** design approved in conversation. Awaiting spec review, then the implementation plan.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§4 Strategy page, §7 contract, §11 phases). This document narrows Phase 3 to its first half. The Books pages are **Phase 3b**, with their own spec.
- **Look:** [`../design-system.md`](../design-system.md) and the approved mockup [`../design/mockups/strategy.html`](../design/mockups/strategy.html).

## 1. Why

The Strategy page is the "understand the system" page. It answers two questions for each strategy:

- How does it trade?
- Is it behaving the way its backtest said it would?

Phase 3a builds that page and the strategy list, the charts they need, and a small additive extension of the data contract. It also fixes the follow-ups parked at the end of Phase 2. One of them must land before a real feed is connected (§7).

**Decisions (owner, 2026-09-26):**

| Decision | Choice |
|---|---|
| Slicing | Strategies first (3a), Books second (3b) |
| Page scope | The mockup's Overview sections on one scrolling page, plus a full, sortable trades table. No tabs until Rules, Backtest and Journal have data of their own. |
| New data | Added to the Snapshot as optional fields (option A). A source stays one JSON document; no second API. |

## 2. Pages

### 2.1 `/strategies`: the list

- One card per strategy, in a 2-column grid (1 column below 900 px).
- Each card shows:
  - the name and summary;
  - a chip per book: the book mark (solid = real, hatched = paper), the money, the status and the number open (for example "Real · running · 4 open");
  - the per-trade-vs-expected band bar (the Home `BandBar`) for the strategy's primary book (§2.3), with the verdict text;
  - the number of closed trades and an "Open" link.
- **Empty state:** "No strategies yet."

### 2.2 `/strategies/<id>`: one strategy

**Header**
- A caps "Strategy" label, the name (h1), the summary, and the book chips.
- **The Real | Paper toggle:**
  - shown only when the strategy has both a real and a paper book;
  - selects the *primary book* the page focuses on (§2.3);
  - kept in the URL as `?book=real|paper` so a view can be linked;
  - defaults to `real`.
- An unknown id renders the in-shell "Not found" page.

**Sections**, in order. Every chart has a Chart | Table switch and a hover or keyboard tooltip. Every section has a plain-English empty state.

1. **How it trades.**
   - `Strategy.steps` as up to four cards, joined by arrows: step number, caps label, title, text, and parameter chips.
   - Below them, the `Strategy.sizing` line.
   - Empty state: "This strategy hasn't described its rules."
2. **Is it behaving?**
   - **Histogram:** the primary book's closed-trade returns in 1-point buckets from −10% to +10%. Returns outside the range fold into the end buckets. Real trades are drawn as solid bars; the backtest's `Expected.distribution` as dotted-outline bars behind them.
   - **Scorecard:**
     - rows for win rate, average trade, average win, average loss and trades per month, each actual vs expected;
     - a ✓, or a ⚠ with hidden status text, when the actual differs from the expected by more than the band for that measure (§3.2);
     - a progress bar "n / review_at_trades trades";
     - a one-line summary of the other book (trades, average per trade, win rate), when the strategy has one.
   - Without an `expected`, the page shows the actual figures alone, with "No backtest to compare with."
3. **Average per trade, as trades add up.**
   - The running mean of trade returns in close order: the primary book solid, the other book dashed.
   - The expected mean ± 1.96·sd/√n drawn as a dotted band that narrows with n, starting at trade 3.
   - A legend, and end labels for each line.
4. **Where the money works.**
   - The primary book's slots in use for each of the last 40 sessions. A trade occupies a slot from its open date up to and including its close date; an open position occupies one from its open date to the last session.
   - Tiles for average in use, "money working" (average in use ÷ `slots_total`) and idle sessions.
   - "Close to a signal" chips from `Strategy.watch`, hidden when that list is empty.
   - Empty state when the book has no `slots_total`: "This book doesn't report slots."
5. **Trade anatomy.**
   - A candle chart of the selected trade's `bars`, with an indicator panel underneath on the same time axis when the chart carries one. The panel has one y axis and dotted threshold lines. It is a small multiple, never a second axis.
   - Markers:
     - a buy marker at the entry bar;
     - a sell marker at the exit bar;
     - the holding window shaded;
     - the stop drawn as a line across the holding window, only when `TradeChart.stop` is given.
   - A recent-trades list beside it: the primary book's last 8 closed trades. Trades with a chart are selectable buttons; the others are listed plain, with "no chart".
   - The newest charted trade is selected by default.
   - Chips for return, R and sessions held.
6. **Is it worth it?**
   - A scatter of yearly return (y) against worst drop (x, positive magnitude, left is better). Points:
     - **the backtest** (dotted ring), when `Expected.cagr_pct` and `max_drawdown_pct` exist;
     - **the primary book** (solid), from its history (§3.2);
     - **the long-term accounts** (solid, `--s1`);
     - **the benchmark** (dotted ring, `--ref`).
   - Every point is directly labeled with its sub-label (period, and "early" where it applies).
   - A dotted "return = worst drop" guide line.
7. **Month by month.**
   - The last 12 calendar months, oldest first: a row of monthly returns for the primary book and one for the long-term accounts. Cells use a diverging fill (`--up` / `--down` at an opacity scaled by magnitude) with the value printed in each cell.
   - An "ahead?" row (✓ or −, with hidden text).
   - A year label above the months.
   - Below: "months ahead of long-term n of m", the best month and the worst month.
8. **All trades.**
   - The primary book's closed trades, sortable by closed date (default, newest first), return and P/L.
   - Columns: symbol (with book mark), opened, closed, days held, return (`Delta`), R, P/L (`Delta`), why it closed.

### 2.3 The primary book

- A strategy's books are the snapshot's books whose `strategy_id` is the strategy's id.
- The primary book is the book matching the `?book=` money. When several match, the one with the most closed trades wins, and ties go to the first listed.
- If the requested money has no book, the other money's book is used and the toggle is not shown.
- A strategy with no books still renders sections 1 and 6 (backtest only) and empty states elsewhere.

### 2.4 Links

- Home's "… is below its expected band" attention item links to `/strategies/<strategy_id>`.
- The sidebar's Strategies item opens `/strategies`.
- The Books links stay on the Phase 3b placeholder.

## 3. Data and server

### 3.1 Contract additions (additive; `contract_version` stays `"1"`)

| Model | Change |
|---|---|
| `Bar` (new) | `date`, `open`, `high`, `low`, `close` |
| `IndicatorLine` (new) | `value: float`, `label: str` |
| `Indicator` (new) | `label: str`, `values: list[float \| None]` (aligned with `bars`), `lines: list[IndicatorLine] = []` |
| `TradeChart` (new) | `book_id`, `symbol`, `opened: date`, `bars: list[Bar]`, `indicator: Indicator \| None`, `stop: float \| None`. It matches a `Trade` by (`book_id`, `symbol`, `opened`). |
| `Snapshot` | `trade_charts: list[TradeChart] = []` |
| `Expected` | `cagr_pct: float \| None = None`, `max_drawdown_pct: float \| None = None` (worst drop, negative) |
| `WatchItem` (new) | `symbol`, `label: str` (for example "RSI(2)"), `value: float \| None`, `note: str = ""` |
| `Strategy` | `watch: list[WatchItem] = []` |

- A `TradeChart` whose bars don't include the trade's open date is ignored (not an error).
- `docs/contract/snapshot.schema.json` is regenerated.
- `docs/data-contract.md` gains a short "Optional extras" note.

### 3.2 Derived figures (server, `views/strategy.py`, pure functions of one Snapshot)

- **Buckets:** 20 buckets, bucket i = [−10 + i, −9 + i), with the ends folded. Each holds a count and a share %.
- **Scorecard band per measure**, used only for ✓/⚠:
  - win rate: ±1.96·√(p(1−p)/n), in points;
  - average trade: the expected band from `metrics.expected_band`;
  - average win and average loss: ⚠ when outside ±50% of the expected value;
  - trades per month: ⚠ when outside ±50%.
  
  Fewer than 10 closed trades shows "too early" rather than ✓/⚠.
- **Trades per month:** closed trades ÷ months between the book's `started` and today (at least 1).
- **Running mean:** in close order (ties broken by opened date, then symbol).
- **Slots in use:** per session, from the book history's dates, or weekdays if it has no history.
- **Yearly return and worst drop for a book:**
  - from `metrics.growth_index` over the book's history;
  - the worst drop is `max_drawdown_pct`;
  - the return is annualized as (index_end)^(365/days) − 1 when the history spans at least 365 days;
  - when it spans 90–364 days it is still annualized but labeled "early";
  - under 90 days the point is omitted.
  
  Long-term accounts and the benchmark use the same rule over their own history, labeled with the period ("12 months").
- **Monthly returns:** the month-end over previous-month-end of the growth index, over the last 12 complete-or-current months present in the history.

### 3.3 View models

- `StrategyCard` / `StrategiesView` for the list.
- `StrategyView` for one strategy: header, steps, sizing, `behaving` (buckets, scorecard, review progress, other-book summary), `funnel` (per-book running means, band), `slots` (days, counts, tiles, watch), `anatomy` (recent trades, charts), `worth` (points), `monthly` (months, rows, ahead, summary), `trades`.
- Field names are fixed in the plan, mirrored by hand in `web/src/lib/api.ts`, and pinned by generated fixtures plus the `satisfies Widen<…>` check.

### 3.4 Server and CLI

- `GET /api/strategies` returns `StrategiesView`.
- `GET /api/strategies/{id}?book=real|paper` returns `StrategyView`:
  - an unknown id gets a JSON 404;
  - a `book` other than `real` or `paper` gets a 422 (FastAPI validation).
- Both routes are GET-only and covered by the existing route walk and read-only guard.
- `kestrel demo --view strategies` and `kestrel demo --view strategy --id rsi2 [--book real|paper]` print these views.
- Generated fixtures: `web/src/test/fixtures/strategies.json` and `strategy-rsi2.json`, pinned by `tests/test_generated_files.py`.

### 3.5 Demo data

- **Trade charts:** each book's 8 most recent closed trades get a `TradeChart`:
  - about 30 sessions of bars, with the entry bar's open equal to the trade's entry price and the exit bar's open equal to its exit price;
  - an RSI(2) indicator computed from the bars for Mean reversion books, with lines at 10 ("buy under 10") and 70 ("sell over 70");
  - no indicator for the other strategies;
  - an 8%-below-entry stop for Mean reversion.
- **Backtest figures:** Mean reversion's `expected` gains `cagr_pct = 23.4` and `max_drawdown_pct = -11.7`.
- **Watch list:** Mean reversion gets `watch` = three fictional names with RSI(2) readings under 20.
- Everything stays deterministic for a given seed. It remains fictional (tickers are ordinary large caps and sector funds).

## 4. Web

- **Routes:** `/strategies` and `/strategies/$strategyId`, with a validated `book` search param.
- **Hooks:** `useStrategies()` and `useStrategy(id, book)`.
- **New charts in `web/src/charts/`:**
  - `Histogram`;
  - `Funnel` (the existing `LineChart` gains an optional `band` series drawn as a dotted-edge wash);
  - `SlotsStrip`;
  - `CandleChart` (candles plus the optional indicator panel on the shared x axis);
  - `Scatter`;
  - `MonthGrid`.
- **Pure geometry** (scales, bucket layout, candle geometry, tooltip clamping) lives in tested helpers. Heavy figures come from the server.
- **All of the design system applies:** tokens only, real/paper/expected encoding, ▲/▼ on gains and losses, the true minus sign, a table view for every chart, keyboard access and AA contrast.

## 5. Phase 2 follow-ups folded in

1. **The comparison's shared start ignores any series with fewer than 2 points.** On its first day, a new real book must not empty the panel. This **must land before any real feed.**
2. **Comparison with no dates:** the subtitle names no "since" date (the empty 12-month case).
3. **The server's lexical path check also refuses a NUL character**, returning the index instead of a 500.
4. **Type scale in px:**
   - The Tailwind `text-*` sizes are redefined in px in `@theme` to the design-system scale (11, 12, 13, 14, 15, 20, 24, 28, 38, 48), so the 14 px root no longer shrinks them.
   - The hero is 48 px on desktop.
5. **Two small design fixes:** `num()` shows no minus on a value that displays as zero, and `.mark.expected` gets the 4–6% ink wash.
6. **CI:** a `windows-latest` Python 3.11 job.

## 6. Testing

- **Python:**
  - the contract additions (round trip; a chart for a trade that doesn't exist is ignored);
  - demo consistency (every chart matches a trade; the entry and exit prices lie in their bars' ranges; the stop is 8% below entry);
  - `views/strategy.py`:
    - each section on demo data;
    - edge cases: a paper-only strategy, no trades, trades without charts, a book under 90 days, a missing `expected`, no `slots_total`, an empty watch list;
  - routes (200 / 404 / 422, GET-only);
  - the CLI views;
  - generated-file drift.
- **Web:**
  - geometry helpers;
  - each chart (render, hover or keyboard tooltip, table view, empty input);
  - the strategies list;
  - the strategy page (the toggle updates the URL and content, trade selection, empty states).
- **Screenshot pass:** `/strategies` and `/strategies/rsi2` at 390, 768, 1024 and 1440 px in both themes: no panel overflow, no sideways scroll, and a match with the mockup.

## 7. Out of scope (3a)

- The Books pages (3b).
- Rules, Backtest and Journal tabs.
- Real connectors (Phase 4).
- Editing or placing anything; kestrel stays read-only.
