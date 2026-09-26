# Phase 4a — Accounts and your real data — design

- **Date:** 2026-09-26
- **Status:** design decided autonomously (owner: "Go ahead proceed autonomously"); plan next.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§4 Accounts, §7 contract, §8 connectors, §9 profile, §11 phases). This document narrows Phase 4 to its first half: the `fdc` connector and the Accounts pages. The private trading desk's `feed` (and `rails`) is **Phase 4b**, with its own spec; Books stays **Phase 3b**.
- **Look:** [`../design-system.md`](../design-system.md). There is no Accounts mockup; the pages reuse the panels, tables and charts already built for Home and the Strategy page.

## 1. Why

kestrel only shows fictional money so far. Phase 4a points it at the owner's real accounts, through the local SQLite warehouse that financial-data-collector already fills (long-term, retirement and trading accounts). After it:

- Home's net worth, allocation and "trading vs your index money" are real.
- **Accounts** answers its question from the parent spec: *what does each account hold, and how much of its growth was my deposits vs the market?*
- Anyone else can do the same with their own collector warehouse, by adding one `[[sources]]` block to `profile.toml`.

Nothing personal enters git. Tests run against a small fictional warehouse built by the tests themselves.

**Decisions (made autonomously 2026-09-26, recorded for the owner):**

| Decision | Choice | Why |
|---|---|---|
| Slicing | 4a = `fdc` connector + Accounts pages; 4b = the desk's `feed` + `rails`; then 3b Books | Real accounts need no change to the trading desk, and holdings have no page without Accounts |
| Account ids | Slug of the collector's account **label** (unique there); a clash gets `-2`, `-3` | The collector's own `slug` column is not unique (it defaults to `other`) |
| Categories | From the account type by default; `categories` in the source's profile block overrides by id or label | The profile maps each account to a category (parent spec §8) |
| Benchmark | The connector serves the profile's benchmark symbol from the warehouse's price table when it has one | No second data source; an index fund someone holds is already priced there |
| Home trading line | Real books' history; with no real book history yet, the trading-category accounts' history | Until the feed exists, the trading account *is* the trading money |
| Demo | `kestrel serve --demo` (and `check --demo`) always shows the demo, whatever `profile.toml` says | The demo stays one flag away once a real profile exists |

## 2. The `fdc` connector

### 2.1 Profile

```toml
[[sources]]
id = "portfolio"
kind = "fdc"
label = "Portfolio"
path = "../financial-data-collector/data/warehouse.db"
stale_after = "36h"

[sources.categories]          # optional: account id or exact label -> long_term | trading | cash | other
"brokerage-2" = "trading"
```

- A relative `path` in any `[[sources]]` block is relative to the **profile file's folder**, not the working directory. `load_profile` makes it absolute; the built-in demo profile has no paths.
- An unknown category value, or a `categories` entry that matches no account, is reported by `kestrel check` (the first as a profile error, the second as a note on the source line).

### 2.2 Opening the warehouse

- `sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=5)`, then `PRAGMA query_only = 1`. One connection per snapshot, always closed.
- Required: `schema_version` with a version ≥ 3, the tables `accounts`, `transactions`, `prices`, `sync_runs`, `holdings_daily`, `cash_daily`, and the views `positions_latest`, `account_values_daily`. Anything missing raises a connector error worded for a person: "this warehouse is missing holdings_daily: update financial-data-collector and run `fdc sync`".
- No file at `path`: "no warehouse at <path>" (checked before connecting, so SQLite never creates one).
- Any other SQLite error becomes the source's error text. `collect()` already turns a connector exception into a red source row; the page never breaks.

### 2.3 Mapping

| Contract | From the warehouse |
|---|---|
| `Account.id` | slug of `accounts.label` (lowercase; runs of anything outside `a-z0-9` become `-`; trimmed; empty → `account`); clashes get `-2`, `-3` in `accounts.id` order |
| `Account.name` | `accounts.label` |
| `Account.institution` | `accounts.institution`, display-cased: `fidelity` → Fidelity, `webull` → Webull, anything else title-cased |
| `Account.account_type` (new, §3) | `accounts.account_type`, display text: `roth_ira` → Roth IRA, `traditional_ira` → Traditional IRA, `brokerage` → Brokerage, `crypto` → Crypto, `401k` → 401(k), else title-cased with `_` → space |
| `Account.category` | profile override, else by type: `roth_ira`, `traditional_ira`, `ira`, `rollover_ira`, `sep_ira`, `simple_ira`, `401k`, `403b`, `457b`, `hsa`, `pension`, `brokerage` → `long_term`; `checking`, `savings`, `cash`, `money_market` → `cash`; anything else (incl. `crypto`) → `other` |
| `Account.value`, `cash`, `as_of` | the most recent of (a) the last `account_values_daily` row (`total`, `cash`) and (b) the last history point (§ below; cash from `cash_daily`). On the same date the snapshot row wins. `as_of` = that date at 16:00 America/New_York (the US close) |
| `Holding` | `positions_latest` rows for the account (joined by label): `symbol`, `description` → `name`, `quantity`, `price`, `market_value` → `value`, `cost_basis_total` → `cost_basis`. A row with no `market_value` is left out and counted in the source detail; a row with no `price` gets `market_value / quantity` |
| `account_history` | one `Series` per account: per date, `SUM(holdings_daily.market_value)` + `cash_daily.amount` (the same join `portfolio_daily_full` uses, grouped by account too), dates ascending |
| `ValuePoint.net_flow` | `transactions` per account and `trade_date`: `contribution` counts as its signed `amount` (a negative one is a reversal); `withdrawal` always counts as `-abs(amount)`; `transfer` counts as its signed `amount`. A flow on a date with no history point is added to the next history date (so a weekend deposit is never lost); flows after the last point are dropped |
| `benchmark` | when `prices` has rows for the profile's `benchmark.symbol`: `Benchmark(symbol, label, points)` from `adj_close` by date (dividends included, like the accounts). Otherwise no benchmark, and the source detail says "no <SYMBOL> prices in the warehouse" |
| `Source` | `kind = "fdc"`; `last_success` = the latest `finished_at` of an `ok` `derive` run (else of any `ok` run; else none); `detail` like "4 accounts · 15 holdings · prices to 24 Sep", plus the left-out and benchmark notes |

The connector returns only accounts, holdings, account history, the benchmark and its source. It reads nothing about books or strategies.

### 2.4 Performance

The server collects once per request. On a household warehouse (a handful of accounts, a few years of days, a few dozen holdings) the connector's queries should take a few milliseconds; the plan measures it. If a snapshot ever takes over 100 ms, a cache keyed by the file's `(mtime, size)` goes in, not before.

## 3. Contract (additive; `contract_version` stays `"1"`)

- `Account.account_type: str = ""`: display text for the kind of account ("Roth IRA", "Brokerage"). Regenerate `docs/contract/snapshot.schema.json`.
- The demo connector gains fictional holdings for its accounts and an `account_type` on each, so the Accounts pages and their web fixtures have data.

## 4. Pages

### 4.1 `/accounts`: all accounts

Top to bottom:

1. **Header.** Caps "Money", h1 "Accounts", and a sentence written from the data: "4 accounts, $48,210.55 in all. This year the market added ▲ $3,102.40 and you deposited $6,500.00."
2. **Growth.** A panel with a Seg for the window (This year · 1 year · All) and four tiles: *Started at* (the value at the window's start), *You put in* (deposits minus withdrawals in the window), *The market added* (the rest: end − start − deposits, ▲/▼), *Now*. Under the tiles, one stacked bar in the same order (start, deposits, market) with a table view. "All" starts at the first history point.
3. **Accounts.** One row per account, largest first: name, "Institution · type", category chip, value, share of all accounts, today's change, and this year's market growth. Each row links to `/accounts/<id>`. On a phone the table scrolls sideways inside its panel, like every other table.
4. **Everything you hold.** Holdings combined across accounts by symbol: symbol, name, value, share of all holdings, and which accounts hold it. Largest first; the first 12, then "Show all N". Cash appears as one row ("Cash", summed across accounts) when any account has cash.

Empty states: no accounts → "No accounts yet. Add a source in profile.toml (see docs/connectors.md)."; an account with no history → its growth shows "—".

### 4.2 `/accounts/<id>`: one account

1. **Header.** Caps "Account", h1 the name, "Institution · type", the category chip, and "as of Fri 25 Sep".
2. **Value** (span 8). The account's value over the window, with the dotted "Start + deposits" line Home's net worth panel already draws, so the gap between the lines is market growth. A table view. Its Seg (This year · 1 year · All; default 1 year) sets the window for this panel and the next.
3. **Growth** (span 4). The same four tiles for that window, then "Money in and out": the last 8 non-zero flows (date, ▲ in / ▼ out, amount).
4. **Holdings** (span 12). Symbol, name, quantity, price, value, weight (a thin bar plus the percent), cost basis, and unrealized gain ($ and %, ▲/▼; "—" when the cost is unknown). Sortable by value (default) or gain. A final "Cash" row. Totals row.

An unknown id is the in-shell "Not found" page, with Money › Accounts in the breadcrumb.

### 4.3 Links

- Home's "Where it sits" account rows link to `/accounts/<id>`.
- The sidebar's Accounts item (count = accounts) now opens the real page; the Phase 2 placeholder goes.

## 5. Data and server

### 5.1 Derived figures (`views/accounts.py`, pure functions of one Snapshot)

- **Window start:** "This year" = 1 Jan of the profile-timezone year; "1 year" = today − 365 days; "All" = the first history point. The start value is the last point on or before the start date (or the first point after it, when history begins later).
- **Growth(window):** `start` = start value; `deposits` = Σ `net_flow` of points after the start point, up to the end; `end` = the last point's value; `market = end − start − deposits`. All rounded to cents; a window with fewer than 2 points has no growth (null).
- **Combined holdings:** grouped by `symbol`; `value` summed; `share` of the holdings total (cash included); accounts listed by name.
- **Weights and gains** (one account): `weight = value / (holdings + cash)`; `gain = value − cost_basis`, `gain_pct = gain / cost_basis` when the cost basis is known and non-zero.

### 5.2 View models and routes

- `AccountsView`: header sentence parts, `growth` per window (`ytd`, `1y`, `all`), `accounts` (rows), `holdings` (combined), `as_of`.
- `AccountView`: header, `points` (the value series with `net_flow`), `growth` per window (`1y`, `all`, `ytd`), `flows` (the last 8), `holdings` (rows), `cash`, `totals`.
- `GET /api/accounts` → `AccountsView`; `GET /api/accounts/{account_id}` → `AccountView`, or JSON 404 `{"detail": "no such account: <id>"}`. Both GET-only, registered before the `/api/{rest:path}` catch-all.
- `kestrel demo --view accounts` and `--view account --id ID` print them; two generated web fixtures (`accounts.json`, `account-<first demo id>.json`) are pinned by `tests/test_generated_files.py`.

### 5.3 CLI

- `kestrel serve --demo` and `kestrel check --demo` use the built-in demo profile even when `profile.toml` exists.
- `kestrel check` prints, under each source line, one line per account that source returned: `id  category  name`. It never prints balances.

### 5.4 Home

- The comparison's trading line: real books' history when any real book has two or more points; otherwise the history of the `trading`-category accounts. The line keeps the label "Trading".
- "Where it sits" rows become links (§4.3).

## 6. The owner's setup (local only, never committed)

After the build, on the owner's machine:

- `kestrel/profile.toml` (gitignored): `you.name`, a benchmark the warehouse already prices (the owner's index fund), and one `fdc` source pointing at `../financial-data-collector/data/warehouse.db`, with the trading-desk accounts mapped to `trading`.
- `kestrel check` shows the source `ok` and every account with the intended category.
- Nothing changes in financial-data-collector.

## 7. Safety and privacy

- Read-only: `mode=ro` plus `query_only`. A test proves an `INSERT` through the connector's connection fails and the fixture file's bytes are unchanged after a snapshot.
- The test warehouse is built in `tests/` from a subset of the collector's schema (its view definitions copied, with the source noted), filled with fictional accounts ("Alex …") and made-up numbers. Never a copy of real data; `data/` stays gitignored.
- Source details and errors can include the local path; they are served only on 127.0.0.1, like everything else.
- The hygiene test keeps machine paths and personal emails out of tracked files; the owner's `profile.toml` is gitignored.

## 8. Docs

- `docs/connectors.md` (new): what a connector is, the `demo` and `fdc` sources (profile block, account mapping, categories, flows, benchmark, freshness, troubleshooting with `kestrel check`); `feed` and `rails` marked "Phase 4b".
- `profile.example.toml`: a commented `fdc` block.
- README: "Point it at your own data" in three steps. AGENTS.md and the parent spec's delivery table: Phase 4a done.

## 9. Testing

- **Connector** (`tests/test_fdc_connector.py`, fixture builder `tests/fdc_fixture.py`): ids from labels and clashes; category defaults and overrides by id and by label; value from the snapshot vs the newer history point; history with flows (withdrawal sign, weekend deposit moved to the next date, flows after the last point dropped); holdings (no market value left out and counted, no price derived); benchmark present and absent; `last_success` from `sync_runs`; errors (no file, missing table, old schema version); read-only proof; relative path resolved against the profile's folder.
- **Views** (`tests/test_accounts_view.py`): window starts, growth math (including history that begins after the window start, and fewer than 2 points), combined holdings and cash row, weights and gains with unknown cost, the header sentence; Home's trading-line fallback.
- **Server and CLI:** the two routes (200, JSON 404, GET-only), `--demo` on serve and check, `check` account lines, generated fixtures.
- **Web** (vitest): the Accounts list (header, growth tiles per window, rows linking, combined holdings with "Show all"), one account (chart with the deposits line, tiles, flows, holdings sort and totals, cash row), not found, loading and error states, Home rows as links.
- **Browser pass:** `/accounts`, `/accounts/<id>`, `/`, at 1440, 1280, 1024, 768 and 390 px in both themes: no sideways scroll, no panel overflow.

## 10. Out of scope (4a)

- The desk's `feed`, `rails`, books and strategies from real data (4b).
- Per-holding analytics (returns vs the benchmark, highs, trends), transactions and dividends pages, tax lots.
- Editing anything: kestrel stays read-only; accounts are named and typed in the collector.
