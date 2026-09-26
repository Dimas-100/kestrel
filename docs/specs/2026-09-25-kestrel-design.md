# kestrel — design

- **Date:** 2026-09-25
- **Status:** design approved. Phase 0 (mockups) is done; Phase 1 (this repo, spec, design system, hygiene test) is the current commit.
- **Look:** Graphite, variant A. The full token and component rules are in [`../design-system.md`](../design-system.md), and reference mockups are in [`../design/mockups/`](../design/mockups/).

## 1. Why

People who invest for the long term *and* run a trading system usually end up with several dashboards:
- a brokerage site for the retirement and brokerage accounts,
- another for the trading account,
- a tool or spreadsheet for paper-trading books,
- notebooks for strategy research.

Nothing answers the two questions that matter: *how is all my money doing?* and *is my trading actually worth it compared with just holding the index?*

kestrel is one read-only home for all of it:
- net worth across every account,
- every trading book (real and paper) side by side,
- a page per strategy that explains how it trades and whether it is behaving the way its backtest said it would.

**Goals**

1. **One place for all money.** Open it and know within ten seconds how things are and whether anything needs you.
2. **Professional and lasting.** Restrained, token-driven design with no trend effects (no glass, glow or gradient washes), so it doesn't date.
3. **Personal but configurable.** It greets you by name. Everything personal comes from a local `profile.toml` and your own data sources. Someone else can clone it and point it at their own keys with minor adjustments.
4. **Read-only by construction.** It never places, changes or cancels an order.
5. **Explains the system.** Visuals show how each strategy trades, how it is going against its own expectation, and how it compares with your index money.

**Non-goals**
- Hosting, logins and multiple users.
- Placing orders. Your trading desk does that.
- Collecting data. A collector does that.
- Running backtests. kestrel shows their results.

## 2. Where it sits

Three small public repos, each with one job:

| Repo | Job |
|---|---|
| `financial-data-collector` | **collects** accounts, holdings, cash, transactions and prices into a local SQLite warehouse |
| `trading-rails` | **trades safely**: paper broker, safety gate, run log, backtests |
| `kestrel` | **shows**: reads both of the above, plus anything that speaks the kestrel data contract |

A private trading system plugs in through the generic **feed** connector (§8). Its code and details never enter this repo.

## 3. Decisions

| Decision | Choice | Why |
|---|---|---|
| Audience | One person per install; personal but configurable | No accounts or hosting to secure; each person runs their own copy |
| Scope | All money: long-term accounts, trading account, paper books, strategies | Replaces several dashboards with one |
| Home | Its own public repo | A read-only view is a different job from collecting or trading |
| Look | Graphite, variant A: Geist + Geist Mono, rufous accent, green/red gains and losses, comfortable density, dark default with full light-mode parity | Restraint ages best. The data is the colour. |
| Safety | Read-only: GET routes only, loopback bind, read-only data access | A dashboard should never be one bug away from an order |

## 4. Information architecture

**Shell**
- **Left sidebar, with grouped navigation:**
  - The app name and accent come from the profile.
  - "Good evening, {name}" and the current date/time.
  - A **Sources** block at the bottom: one row per connector with its last successful sync, amber when stale.
- **Top bar:** a breadcrumb, the page's controls (time range, money scope), when the data was last loaded ("Updated 17:08"; each source's own "n min ago" is in the sidebar's Sources block), refresh, and a theme toggle.
- **Phone:** the sidebar collapses behind a menu button, with a bottom tab bar for Home · Accounts · Books · Strategies · More.

| Group | Page | The question it answers |
|---|---|---|
| Overview | **Home** | How is all my money doing, and does anything need me? |
| Money | **Accounts** | What does each account hold, and how much of the growth is my deposits vs the market? |
| Trading | **Books** | How is each book doing (real or paper)? |
| Trading | **Strategies** | How does this system trade, and is it behaving as its backtest said? |
| Research | **Backtests** | What has been tested, and what passed? |
| System | **Activity** | What ran, what is due, what failed? |
| System | **Settings** | Your profile, and the status of each connector. |

**Home** (`design/mockups/home.html`, top to bottom):
1. A one-sentence summary written from the data ("All your money is ▲ +$412.30 today. Trading is ahead of your index money by 2.4 pts this year. One item needs you.").
2. **Net worth.** The hero figure, then Today / Month / Year deltas (the year notes how much of it was deposits). Below that, a one-year line with a dotted *what you deposited* step line; the gap between the two is labelled as market growth.
3. **Where it sits.** A 100-cell waffle (long-term / trading / cash) and the accounts list.
4. **Trading vs your index money.** The headline comparison:
   - year-to-date return of the real trading books against the long-term accounts and the benchmark, all starting at 0%,
   - each line's worst drop,
   - a plain-English verdict with its sample-size caveat.
5. **Needs you.** Serious, then warning, then note. Each item has an icon, a label, one line of detail, and a link to the page that resolves it. Examples: an unprotected position, a stale source, a strategy below its expected band.
6. **Books.** Every book in one table:
   - real or paper mark and badge,
   - value, today, since start,
   - **per-trade result against the expected band**,
   - slots in use,
   - status and next run.
7. **Today.** The day's scheduled runs as a timeline with a *now* line.
8. **Open positions.** Entry, last, stop, *room to stop* as a bar, and P/L. A position with no stop is flagged.

**Strategy page** (`design/mockups/strategy.html`):
1. **Header:** the strategy's name, a one-sentence description, a chip per book (real / paper / backtest), and tabs (Overview · Trades · Rules · Backtest · Journal).
2. **How it trades.** The rule as four steps (universe → entry → protect → exit), each with its parameters, plus a sizing line.
3. **Is it behaving?** Real trade returns over the backtest's distribution (1-point buckets). A **Scorecard** beside it gives actual vs expected for win rate, average trade, average win, average loss and trades per month, a progress bar to the review sample, and the paper book's summary.
4. **Average per trade, as trades add up.** Running average for real (solid) and paper (dashed) inside the expected 95% funnel, which narrows with sample size.
5. **Where the money works.** Slots in use per session over the last 40 sessions, average in use, money working, idle sessions, and the names closest to a signal.
6. **Trade anatomy.** A candle chart of one trade with the buy and sell markers, the holding window and the resting stop, plus an RSI panel with thresholds underneath on the same time axis (small multiples, never a second y-axis). A recent-trades list beside it selects the trade.
7. **Is it worth it?** Yearly return against worst drop for:
   - the backtest,
   - the real book (flagged "early"),
   - the long-term accounts,
   - the benchmark,
   
   with a return = worst-drop guide line.
8. **Month by month.** The real book and the long-term accounts as a diverging grid with an "ahead?" row.

**Accounts, Books, Backtests, Activity, Settings** reuse the same components. Their layouts are specified in the phase that builds them.

## 5. Visual system (summary)

- **Real = solid · Paper = hatched (lines: dashed) · Expected, benchmark or backtest = dotted.** This holds on every chart, badge and row, and is never carried by colour alone.
- Graphite neutrals, one accent (profile-configurable: rufous, slate or mono), 1-px hairlines, and no shadows except popovers.
- Two data hues taken from the bird: slate blue (long-term) and rufous (trading). They are validated as a colour-blind-safe pair in both themes.
- Gains and losses are green/red by default, or blue/orange by profile choice. They always carry a sign and ▲/▼.
- Geist for the UI and Geist Mono for every number. Tabular figures in tables, proportional figures in the hero.
- Every chart has a table view and a hover layer. Every page is keyboard navigable and meets WCAG AA contrast.

All values, and the validator results behind them, are in [`../design-system.md`](../design-system.md).

## 6. Architecture

```
kestrel/
  pyproject.toml            python package `kestrel`; CLI `kestrel serve | check | demo`   (Phase 2)
  profile.example.toml      demo profile (committed); profile.toml is gitignored
  src/kestrel/
    contract.py             pydantic v2 models: the versioned data contract (§7)
    profile.py              profile.toml → Profile; falls back to the demo profile
    connectors/             base protocol · demo · fdc · rails · feed   (§8)
    aggregate.py            connectors → view models (net worth, allocation, comparisons, attention list)
    server.py               FastAPI, GET routes only, binds 127.0.0.1, serves web/dist
  web/                      React + TypeScript + Vite + Tailwind v4, TanStack Router + TanStack Query
    src/design/             tokens.css (the design-system tokens), type, primitives
    src/charts/             in-house SVG chart kit on d3-scale / d3-shape / d3-array
    src/components/         Shell, Sidebar, Greeting, Panel, Stat, BookMark, Table, Chip, …
    src/routes/             home · accounts · books.$id · strategies.$id · backtests · activity · settings
  docs/                     this spec, design-system.md, data-contract.md, connectors.md, mockups
  tests/                    pytest: contract, connectors, GET-only, import guard, hygiene
```

**Why these choices (longevity):**
- **Server:** FastAPI + pydantic.
  - The contract's JSON Schema is generated from the models, so documentation can't drift.
  - It uses the same small Python stack as the two sibling repos.
- **Front end:**
  - React + TypeScript + Vite + Tailwind v4 (Tailwind only reads the CSS-variable tokens).
  - A URL router so every page and selection is a deep link and the back button works.
  - A chart kit built on d3's stable math modules rather than a charting framework. The real/paper/expected encodings need full control, and d3-scale/d3-shape APIs have been stable for a decade. lightweight-charts is added only if a real price chart outgrows the SVG candle view.
- **Fonts** are self-hosted (@fontsource) so the app works offline and never calls a CDN.
- **Delivery:** `npm run build` writes `web/dist`, which the server serves. Later, release archives can ship a prebuilt `web/dist` so Node isn't needed to run it.

## 7. Data contract v1

Every connector returns these entities. All money is in the profile currency; all timestamps are ISO-8601 with an offset.

| Entity | Key fields |
|---|---|
| `Source` | `id`, `label`, `kind`, `last_success`, `status` (ok · stale · error), `detail` |
| `Account` | `id`, `name`, `institution`, `category` (long_term · trading · cash · other), `value`, `cash`, `as_of` |
| `Holding` | `account_id`, `symbol`, `name`, `quantity`, `price`, `value`, `cost_basis` |
| `ValuePoint` | `date`, `value`, `net_flow` (deposits − withdrawals that day); used for accounts, books and net worth |
| `Book` | `id`, `name`, `money` (real · paper), `strategy_id`, `account_id?`, `status` (running · paused · parked), `started`, `value`, `slots_total?`, `next_run?` |
| `Position` | `book_id`, `symbol`, `quantity`, `entry_price`, `last_price`, `stop_price?`, `opened` |
| `Trade` | `book_id`, `symbol`, `opened`, `closed`, `entry_price`, `exit_price`, `quantity`, `pnl`, `return_pct`, `r_multiple?`, `exit_reason` |
| `Strategy` | `id`, `name`, `summary`, `steps[]` (label, text, params), `sizing`, `expected` (win_rate, avg_trade_pct, avg_win_pct, avg_loss_pct, trades_per_month, sd_trade_pct, distribution[], source, window), `review_at_trades` |
| `Run` | `time`, `label`, `book_id?`, `status` (done · due · late · failed · paused), `detail` |
| `Alert` | `level` (serious · warning · note), `title`, `detail`, `link` |

**Versioning:**
- Every feed declares `contract_version` (`"1"`).
- Within a major version, changes are additive only.
- kestrel refuses an unknown major version and shows that source as `error`, with the reason, in Sources.

## 8. Connectors

Each connector reports its freshness. A source older than its profile `stale_after` turns amber in the sidebar and raises a `warning` alert.

| Connector | Reads | Notes |
|---|---|---|
| `demo` | nothing: seeded, deterministic, fictional data | The default when there is no `profile.toml`. It is what the mockups show. |
| `fdc` | the collector's SQLite warehouse, opened read-only (`file:…?mode=ro`) | Uses its published views (latest positions, daily account values, daily portfolio, daily holdings). The profile maps each account to a category. |
| `rails` | trading-rails' paper state JSON, run log JSONL and backtest output | Paper books, runs and trades from a trading-rails install |
| `feed` | an HTTP URL or a local file returning contract JSON | An optional bearer token is read from an env var **named** in the profile. It has timeouts, and every payload is schema-validated before use. This is how any private system plugs in. |

## 9. Profile

`profile.example.toml` (committed; the real `profile.toml` is gitignored). Secrets never go in the profile; it only names environment variables.

```toml
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

[benchmark]
symbol = "SPY"
label = "S&P 500"

[[sources]]
id = "portfolio"
kind = "fdc"
path = "../financial-data-collector/data/warehouse.db"
stale_after = "36h"

[[sources]]
id = "paper"
kind = "rails"
path = "../trading-rails/data"

[[sources]]
id = "desk"
kind = "feed"
url = "http://127.0.0.1:8000/api/feed"
token_env = "KESTREL_DESK_TOKEN"
stale_after = "15m"
```

## 10. Safety and privacy

- **Read-only.**
  - The server exposes GET routes only; a test walks the app's routes and fails on any other method.
  - An import guard (AST walk of `src/`) fails if any module imports or calls an order-placing API.
  - SQLite is opened with `mode=ro`.
- **Local-only.** The server binds `127.0.0.1` and allows no CORS origins. There is no auth because nothing leaves the machine.
  - A request whose `Host` is anything but `127.0.0.1` or `localhost` is refused with 400 (a DNS-rebinding guard).
- **Untrusted input.** Feed text is rendered as text only (never `dangerouslySetInnerHTML`). A payload that fails schema validation is dropped and the source is shown as `error`.
- **Nothing private in git.** `profile.toml`, `.env*`, `data/`, `dist/` and `node_modules/` are gitignored. The committed demo data is fictional. `tests/test_hygiene.py` fails the build on machine paths, private hosts or personal email addresses in any tracked file.

## 11. Delivery

Each phase gets its own spec, plan and build.

| Phase | Scope | State |
|---|---|---|
| 0 | Graphite mockups; variant A chosen | done |
| 1 | This repo: spec, design system, mockups, hygiene test | this commit |
| 2 | Skeleton: contract, profile, `demo` connector, server, shell (sidebar, greeting, routing, theming), Home | done |
| 3 | Books + Strategies pages; the chart kit | next |
| 4 | Accounts; `fdc`, `rails`, `feed` connectors | |
| 5 | Backtests, Activity, Settings | |

## 12. Testing

- **Backend (pytest):**
  - contract validation, including JSON Schema round-trips,
  - each connector against fixtures (a small SQLite fixture, feed JSON fixtures, including malformed and wrong-version payloads),
  - the GET-only route walk,
  - the import guard,
  - the hygiene test.
- **Front end:**
  - Vitest + Testing Library: a render test per page against demo data, and pure-function tests for chart geometry and number formatting.
  - A screenshot pass per page in the running app at 1440 px and 390 px, in both themes, checking that no panel overflows.
- **CI:** GitHub Actions on Python 3.11 / 3.12 and Node LTS: ruff, pytest, lint, vitest, build.

## 13. Open items

- A source for bank or savings balances: a collector feed, or a `file` source in the contract format.
- Prebuilt web assets in releases, so Node isn't required to run it.
- Exact layouts for Accounts, Books, Backtests, Activity and Settings (Phases 3–5).
