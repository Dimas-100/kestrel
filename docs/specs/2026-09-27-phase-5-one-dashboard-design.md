# Phase 5 — one dashboard — design

- **Date:** 2026-09-27
- **Status:** approved for build (the owner asked for the finished product without approval rounds; the decisions below
  are recorded with their reasons so they can be reviewed afterwards).
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§4 information architecture, §7
  contract, §8 connectors, §10 safety, §11 phases). This phase finishes §11: Phase 3b (Books), Phase 4's `rails`
  connector and Phase 5 (Backtests, Activity, Settings). It adds what it takes for kestrel to replace the other
  dashboards on the machine: a feed that kestrel runs itself, and the investing views (Plan, Reserves, Calendar).

## 1. Why

kestrel was meant to be the one home for all the money. Two things stood in the way:

1. **A second server.** A private system's feed was only reachable over HTTP, so the desk's own web server had to be
   running for kestrel to show any book. The owner is retiring the other dashboards and their servers; kestrel must
   read everything itself.
2. **Pages and data that only lived in the other dashboards:** each book on its own page, the investing plan (targets,
   drift, thesis health, goals), cash and debt, the company calendar, the research record, and a system view of what
   ran.

**Decisions (2026-09-27):**

| Decision | Choice | Why |
|---|---|---|
| How a private system's data arrives without a server | A `feed` source may name a **command**: kestrel runs it, reads a contract document from its standard output, and reuses the result for a short while | The owner runs one program. The private code stays in its own repo and never enters kestrel's process (§2) |
| New kinds of data | Six additive contract blocks: `targets`, `theses`, `events`, `goals`, `exposures`, `backtests`; a `debt` category and two optional account fields | Each is a generic idea any personal system has; within v1 additions are allowed (§3) |
| Who computes what | The feed sends facts (a target, a thesis's health, an event). kestrel computes anything it can from data it already has — an account's actual share of a holding, a goal's progress, a book's drawdown — so two sources can't disagree about the same number | One number, one owner |
| New pages | Books, Book, Plan, Reserves, Calendar, Backtests, Activity, Settings | §4 |
| `rails` | Built, read-only, from trading-rails' paper state file and run log | It is the third public repo's own output; the spec always had it (§5) |
| Net worth with debt | Net worth = everything owned minus everything owed | A card balance is money already spent |

## 2. Command sources

A `feed` source takes exactly one of `url`, `path` or `command`:

```toml
[[sources]]
id = "desk"
kind = "feed"
label = "Trading desk"
command = ["../desk/.venv/Scripts/python.exe", "-m", "desk.feed_export"]  # argv: the program, then its arguments
cwd = "../desk"             # optional; relative to this file's folder (default: this file's folder)
timeout = 30                # optional; seconds, 1–120 (default 30 for a command, 5 otherwise)
refresh = "1m"              # optional; how long one run's output is reused, 5s–1h (default 1m)
stale_after = "15m"
```

- **Running it.** kestrel starts the program directly from the argv list, never through a shell, with no standard
  input, its own copy of the environment, and on Windows no console window. A program path that contains a slash is
  resolved against the profile's folder; a bare name (`python`) is looked up on `PATH`.
- **Reading it.** Standard output is read up to 20 MB, as UTF-8, and goes through the same checks as a file feed
  (JSON, finite numbers, contract version, `Snapshot` validation). Standard error is kept only for the error message.
- **Errors, worded for a person:** "no such program: python3" · "the command took longer than 30 s" · "the command
  failed (exit 2): <its last line on standard error, at most 160 characters>" · "the command printed more than
  20 MB" · then the usual feed messages ("the feed sent something that isn't JSON", …).
- **Reuse.** One source runs at most one command at a time. A result — good or bad — is reused for `refresh`; the next
  request after that runs it again while other requests wait for that run rather than starting their own. The cache
  lives in the server process and is keyed by the source id and its argv.
- **Freshness** is the payload's `generated_at`, as for any feed, so `stale_after` still means "how old the desk's data
  may be".
- **Safety.** The command is the owner's own configuration, like a shell alias: kestrel runs only what the profile
  names, with the owner's permissions. kestrel itself stays read-only: the program is a separate process whose code
  kestrel never imports; the import guard now also fails if `subprocess` is used anywhere but the command runner, or
  with `shell=True`. Settings shows the program's file name and arguments; nothing else about the environment.

## 3. Contract additions (v1, additive)

`CONTRACT_VERSION` stays `"1"`. Older documents stay valid; an older kestrel ignores the new blocks.

**Accounts.** `category` gains `"debt"` — money owed, such as a credit card. For a debt account `value` is the amount
owed, zero or more. Two optional fields: `rate_pct` (yearly interest: what cash earns, what debt costs) and `limit` (a
credit line's limit).

**Targets** — what the plan says an account should hold:

| Field | Meaning |
|---|---|
| `id` | unique |
| `account_id` | the account the target is about, or none for all accounts |
| `label` | "VTI", "Growth core" |
| `symbols` | what it measures; kestrel sums these holdings |
| `unit` | `"%"` — a share of the account's value (kestrel computes `actual` from holdings when the feed doesn't send it); `"x"` — a ratio the feed measures and sends as `actual` |
| `target`, `low`, `high` | the aim and the band around it; at least one of the three |
| `actual` | optional for `%`, required for `x` |
| `note` | why |

A target is **on plan** inside `[low, high]` (a missing end is open), **over** above it, **under** below it.

**Theses** — why each holding is owned: `symbol`, `name`, `status` (free text, "active"), `health`
(`ok` · `watch` · `alert` · `none`), `reasons` (what drove the health), `conviction` (free text, usually low / medium /
high), `opened`, `last_reviewed`, `wrong_if` (the conditions that would prove it wrong), `account_ids`.

**Events** — dated things about a company: `date`, `symbol`, `kind` (`earnings` · `filing` · `insider` · `dividend` ·
`other`), `title`, `detail`, `url`. A `url` must be `https://…` or empty; kestrel opens it in a new tab with
`rel="noopener noreferrer"`. Everything else is text.

**Goals:** `id`, `label`, `target` (money), `by` (optional date), `note`, and what it measures: an `account_id`, or a
`category`, or neither for net worth. kestrel computes the current value and the progress.

**Exposures** — what the money is really in, looking through funds: `symbol`, `name`, `value` (direct plus through
funds), `direct` (the part held directly), `sector`.

**Backtests** — the research record: `id`, `name`, `family`, `window` (free text: "develop", "confirm", …), `verdict`
(`pass` · `fail` · `refused` · `pending`), `at`, `strategy_id`, `trades`, `avg_trade_pct`, `t_stat`, `calmar`,
`max_drawdown_pct`, `note`.

**Duplicates across sources** (§3 of the 4b spec, extended): targets and goals and backtests by `id`, theses and
exposures by `symbol`, events by (`date`, `kind`, `symbol`, `title`). The first source wins, as before.

## 4. Pages

The sidebar groups become: **Overview** Home · **Money** Accounts, Plan, Reserves · **Trading** Books, Strategies ·
**Research** Backtests, Calendar · **System** Activity, Settings. The phone's bottom bar stays Home · Accounts · Books ·
Strategies · More; More lists the rest. Every page has an honest empty state that says which kind of source fills it.

### 4.1 Books (`/books`) and Book (`/books/<id>`)

- **Books:** every book, real first then paper: money badge, name and strategy, status, value, since start, a
  60-point sparkline of its growth since it started (deposits left out, coloured by the since-start sign), trades,
  per-trade result against the expected band, slots in use, next run. Totals for real and paper money above the table.
- **Book:** a header (name, money badge, status, strategy link, started, next run); **equity** — the book's value since
  it started against the benchmark from the same day, with its return and worst drop; **drawdown** under it on the same
  time axis; a **scorecard** (trades, win rate, average trade / win / loss, total P/L, best and worst trade, and the
  expected band when the strategy has one); **open positions** (entry, last, stop, room to stop, P/L; a missing stop is
  flagged); **trades** (all of them, newest first); **runs** of this book (recent and next).

### 4.2 Plan (`/plan`)

- **Targets, per account:** each row shows the actual against the aim and its band as a bar (the band shaded, the aim
  as a tick, the actual as a dot), the status, and the gap in money ("$212 under the low end"). Rows off plan first.
- **Theses:** symbol and name, health (an icon plus the word, never colour alone) with its reasons, conviction, days
  since the last review, whether it is held (and in which accounts), and the "wrong if" conditions behind a disclosure.
- **Goals:** each goal's current value, target, progress bar, the date, and the monthly amount that would reach it by
  then (when there is a date).
- **Needs you** (Home) gains: a target off plan (warning), a thesis with health `alert` (warning) or `watch` (note).

### 4.3 Reserves (`/reserves`)

Cash and debt accounts: balance, rate, and for a credit line its limit and utilization. Totals: cash, owed, cash
after debts, overall utilization. **The spread:** the highest rate owed against the best rate earned, and what a year
of each costs or earns at today's balances, shown apart and never netted (interest paid and interest earned are
different money). When the dearest debt costs more than the best cash earns and there is cash: "Paying $X of the
<debt> from cash would save about $Y a year", X the smaller of that debt and all the cash, Y = X × (its rate − the best
cash rate) / 100 — the best rate given up, so the saving is never overstated. Home's net worth subtracts debt; the
allocation waffle stays about what is owned, with a line under it for what is owed.

### 4.4 Calendar (`/calendar`)

Upcoming events (date ascending, grouped by week) and the last 90 days (newest first), filterable by kind; events for
something held are marked. Counts by kind at the top.

### 4.5 Backtests (`/backtests`)

Totals (candidates, families, passes per window), then one row per family: its candidates, its best result (the
furthest window passed, then the higher t), a verdict chip per window, and when it last ran. A filter (all · passed ·
failed) and a search box. The newest 200 results are listed below.

### 4.6 Activity (`/activity`)

Runs by day — today, then what is next, then the last seven days — with late and failed first within a day; every
alert, by level; every source with its status, last success, age and `stale_after`.

### 4.7 Settings (`/settings`)

Read-only: who (name), the look (theme, accent, gain/loss colours, density), currency, time zone, benchmark; every
source with its kind, what it reads (a URL without its query or fragment, a path, or the command's file name and
arguments), `stale_after`, `refresh`, `timeout`, the name of a token variable (never its value), and its live status
(times in the profile's time zone); the contract version, kestrel's version and which profile file is in use (or "demo
data").

## 5. The `rails` connector

```toml
[[sources]]
id = "rails"
kind = "rails"
label = "Paper (trading-rails)"
path = "../trading-rails/data"     # the folder holding paper.json and runs.jsonl
stale_after = "36h"
```

It reads trading-rails' paper state (cash, positions with quantity, average cost and last price) and its run log.
One paper book (`rails-paper`) whose value is cash plus positions at their last price; its positions; a run per logged
run (done or failed); closed trades when the state records fills. A missing folder or file is an error row; a torn
file is an error row, never a crash.

## 6. Private feeds (outside this repo)

Two private systems on the owner's machine each gain a small exporter that prints one contract document to standard
output: the trading desk (books, strategies, trades, runs, alerts, backtests) and the investing notebook (targets,
theses, events, goals, exposures, cash and debt accounts, runs, alerts). Their code and specs live in their own
repos; nothing about them enters this one. Accounts and holdings keep coming from `fdc` alone, so nothing is counted
twice.

## 7. Demo data

The demo connector gains fictional examples of every new block and a cash and a debt account, so every page renders
from `kestrel serve --demo` and the tests run against it. Fixtures for the new views are generated files (the
generated-file test covers them).

## 8. Testing

- **Backend:** contract round-trips for every new model (including a bad `url`, `unit: "x"` without `actual`, a
  target with no aim); the command runner (a tiny Python script as the fixture program: success, exit 1, timeout,
  missing program, too much output, reuse within `refresh`, one run for concurrent callers); each new view against the
  demo data and edge cases (no source, empty blocks); `rails` against fixtures; the guard's new `subprocess` rule.
- **Front end:** a render test per new page; pure-function tests for the plan bar and the drawdown series.
- **Screens:** every page at 390, 1200, 1280 and 1440 px in both themes, demo and real data, no overflow.

## 9. Not in this phase

Editing anything from kestrel (it stays read-only); a bank connector of kestrel's own (bank money arrives through a
feed); prebuilt web assets in releases.
