# Connectors

A connector reads one source and returns a Snapshot, the format in [`data-contract.md`](data-contract.md). kestrel
asks every source in your `profile.toml` each time a page loads. A source that can't be read shows as an error in the
sidebar's Sources block, and the rest of the page still works. Every connector only reads: none of them changes its
source's data.

| `kind` | Reads | Since |
|---|---|---|
| `demo` | nothing: a fictional year for "Alex" | Phase 2; the default when there is no `profile.toml` |
| `fdc` | [financial-data-collector](https://github.com/Dimas-100/financial-data-collector)'s SQLite warehouse | Phase 4a |
| `feed` | any system that serves the contract as JSON, at a URL or in a file (your trading desk) | Phase 4b |
| `rails` | a trading-rails install: paper books, the run log, backtests | later |

`kestrel check` tries every source and prints what it found; `kestrel serve --demo` and `kestrel check --demo` show
the demo whatever `profile.toml` says. When two sources use the same id, the one earlier in the profile wins (see
[the last section](#when-two-sources-use-the-same-id)).

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
- **Read-only.** The file is opened with `mode=ro` and `query_only` on top, and closed straight after each read. A
  sync running at the same time is fine: kestrel reads what the collector last committed. Reading a warehouse in WAL
  mode (the collector's mode) lets SQLite create its standard `-wal` and `-shm` coordination files beside it when
  they are missing; kestrel never changes the warehouse's data.
- **Cached.** kestrel keeps what it read, keyed to the warehouse's and its `-wal` file's size and modification time,
  so a sync shows up at once (and within a minute at most, for a same-size write that leaves both looking unchanged).
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

A category that isn't one of the four is a profile error: `kestrel check` stops before reading any source (see
Troubleshooting). A `categories` entry that matches no account is noted on the source's line.

### Values, history and money moved

- **Value and cash:** the newer of the broker's last snapshot (`account_values_daily`) and the last replayed day
  (`holdings_daily` plus `cash_daily`). When both are from the same day, the snapshot wins. A value is as of that
  day's US close.
- **History:** each account's holdings plus its cash, per day, ending on the account's value: the snapshot's total
  replaces the replayed day it shares, a newer snapshot adds its day, and an account with only a snapshot has a
  one-day history. So the Accounts total, the growth's "Now" and each account's chart agree.
- **History before the first snapshot** is reconstructed by the collector from the account's transactions. If those
  don't reach back to when the account was opened, the jump at the first snapshot shows up as market growth in "All".
- **Money moved in and out,** from `transactions`, so deposits never count as growth:
  - a `contribution` counts as its signed amount (a negative one is a reversal),
  - a `withdrawal` is always money out,
  - a `transfer` keeps its sign; a transfer of shares with no cash amount moves no money,
  - money moved on a day without history (a Saturday deposit) counts on the next day that has one, a newer
    snapshot's day included; money moved after the last day is left for the next sync.
- **Holdings:** the broker's latest snapshot of each account (`positions_latest`), each with the day it was
  reported. A position with no market value is left out and counted in the source's detail; one with no price is
  priced at its value over its quantity. When the replayed history is newer than that snapshot, the holdings are
  older than the value, and the account page says so under its holdings table.

### Benchmark

When the warehouse has prices for your profile's `[benchmark]` symbol, kestrel draws it from their adjusted closes
(dividends included, as they are in the accounts), starting at the last close on or before the first day of your
accounts' history. Pick a symbol the collector already prices, such as an index fund you hold. Otherwise there is no
benchmark line, and the source's detail says `no SPY prices in the warehouse`.

### Freshness

The source's last success is when the collector last finished its `derive` step without an error (the step that
rebuilds the daily history), else any step that finished without one. After `stale_after` it turns amber. A
warehouse that has never finished a step shows as stale.

### Troubleshooting

Run `kestrel check`. Under the source's line it lists each account as `id  category  name`, never a balance.

| The source's line says | What to do |
|---|---|
| `no warehouse at …` | Check `path`: it is relative to the folder `profile.toml` is in. |
| `… is not a financial-data-collector warehouse` | The file isn't a collector warehouse (or is empty): check `path`. |
| `this warehouse is at schema version 2 …` or `this warehouse is missing holdings_daily …` | Update financial-data-collector and run `fdc sync`. |
| `the warehouse couldn't be read: database is locked` | Another program held the file for more than five seconds. Refresh once it is done. |
| `no account matches categories 'brokerage-9'` | Use an id from the account lines, or the exact label. |
| `no SPY prices in the warehouse` | Set `[benchmark] symbol` to something the collector prices, or add it to the collector. |

An unknown category is a profile error, not a line under the source: `kestrel check` stops before reading any source
with `profile problem: <path>: sources.0: Value error, unknown category 'trade' for 'Brokerage' (use long_term,
trading, cash or other)` and exits with status 2. Use one of those four in `[sources.categories]`.

## `feed`: any system that serves the contract

```toml
[[sources]]
id = "desk"
kind = "feed"
label = "Trading desk"
url = "http://127.0.0.1:8000/api/feed"   # or: path = "../desk/feed.json" (relative to this profile's folder)
token_env = "KESTREL_DESK_TOKEN"          # optional, with a url: the NAME of the variable that holds a bearer token
timeout = 5                               # optional: seconds, 1 to 60 (default 5)
stale_after = "15m"
```

A feed is one JSON document in the contract's own format, a Snapshot ([`data-contract.md`](data-contract.md)), served
at a URL or saved in a file. It is how a system of your own, such as a trading desk, shows its books, strategies,
trades, runs and alerts (and its accounts, if it has any) without kestrel knowing anything else about it.

- **Exactly one of `url` and `path`.** A `url` starts with `http://` or `https://`. A relative `path` is relative to
  the folder `profile.toml` is in.
- **`token_env`** names an environment variable, in capitals; the token itself never goes in the profile. kestrel
  reads it each time it asks the feed and sends it as `Authorization: Bearer …` to the configured URL and nowhere
  else: it doesn't follow redirects and doesn't use a proxy, and it never prints or logs the token. A URL can't carry
  a user name or password (`http://name:secret@…`); use `token_env`.
- **Read-only, and asked each time a page loads.** One GET, with `Accept: application/json`,
  `User-Agent: kestrel/<version>` and no cookies, or one file read. Nothing is cached.

A feed's shape is checked when the profile loads: a source with both `url` and `path` (or neither), another scheme,
a user name in the URL, a `token_env` that isn't a variable's name (or that goes with a `path`), or a `timeout`
outside 1 to 60 stops `kestrel check` with `profile problem: …` and exit status 2, before any source is read.

### What is checked

In this order; the first check that fails is the source's error, and the rest of kestrel keeps working.

1. **The token**, when `token_env` is set: the variable must be set and not empty, and hold only visible characters.
2. **The answer:** status 200 only, at most 20 MB, and all of it inside `timeout`, counted from when kestrel starts
   asking: connecting, the headers and the body, chunked or not, however slowly the feed trickles them. The one step
   `timeout` can't cut short is looking up the host's address, which comes first (a local desk resolves at once). A
   body that ends before its `Content-Length` is refused. A file must exist and be at most 20 MB.
3. **JSON:** UTF-8 text (a byte-order mark is fine), not a web page, no `NaN`, `Infinity` or `-Infinity` (not
   valid JSON, though a lenient writer can produce them), and no number too large to use (`1e999`, or an integer
   thousands of digits long).
4. **The size:** at most 1,000,000 items in the payload's lists, counted together at any depth (a history's points
   and a chart's bars count too).
5. **The contract version:** the payload must say `"contract_version"`, and its major version must be 1. A newer
   minor version (`"1.4"`) loads; fields this kestrel doesn't know are ignored.
6. **The Snapshot:** every field the contract names. The first three problems are listed as `field.path: message`,
   then how many more (fewer than three when three wouldn't fit on the source's line). The lists are checked a
   batch at a time, so even a payload full of mistakes is described in a second or two.
7. **Dates and numbers the pages can use:** every date from 1970-01-01 to 2200-12-31, and every number at most
   1e15 either way and not NaN. Go's zero time, `0001-01-01T00:00:00Z`, is the usual date outside that range. The
   payload's own `sources` are left out of this check, since kestrel replaces them (below).
8. **The time:** `generated_at` no more than five minutes ahead of this computer's clock. A payload up to five
   minutes ahead reads as made now.

### What kestrel keeps

Every list the payload carries, and its benchmark. The payload's own `sources` are replaced by one row for the feed:
its label, `kind = "feed"`, a last success of the payload's `generated_at`, and a detail like
`2 books · 1 strategy · 61 trades` (the accounts first, when there are any). So a system that keeps serving an old
payload turns amber after `stale_after`. The payload's alerts pass through; the contract already limits their links
to pages inside kestrel.

### Build a payload

`kestrel demo` prints a complete, valid payload (the demo's fictional year), and `kestrel schema` prints the contract
as JSON Schema. The smallest payload kestrel accepts is:

```json
{"contract_version": "1", "generated_at": "2026-09-25T21:05:00+00:00"}
```

Serve it at any address on this computer, or save it to a file, and point a `feed` source at it. Set
`generated_at` each time the payload is rebuilt: it is how kestrel knows the feed is fresh.

### Troubleshooting

| The source's line says | What to do |
|---|---|
| `set KESTREL_DESK_TOKEN in the environment (token_env)` | Set the variable where kestrel runs, then restart `kestrel serve`. |
| `the token in KESTREL_DESK_TOKEN has a character a header can't carry …` | The variable holds more than the token: a space or a line break inside it. |
| `the feed couldn't be reached (…)` or `the feed couldn't be read (…)` | Is the system that serves the feed running? Check `url`. |
| `the feed stopped partway` | The feed closed the connection before it had sent the body it announced: did the system that serves it stop mid-answer? |
| `the feed answered 401` (or `403`, `404`, `503`, …) | The feed's own answer: check the token, the address, or the system itself. |
| `the feed redirected to …; kestrel doesn't follow redirects` | Set `url` to the feed's own address; a redirect to a sign-in page usually means the feed wants a token (`token_env`). |
| `the feed didn't answer within 5 s` or `the feed was still sending after 5 s` | Make the feed faster, or raise `timeout` (up to 60). |
| `the feed sent more than 20 MB` or `the feed file is more than 20 MB` | Send less: a feed carries what the pages show, not raw history. |
| `no feed file at …` | Check `path`: it is relative to the folder `profile.toml` is in. |
| `the feed sent something that isn't JSON: a web page …` | The address answers with a page, often a sign-in page: point `url` at the feed itself. |
| `the feed sent something that isn't JSON (…)` | Compare the feed with `kestrel demo`'s output. |
| `the feed sent NaN, which JSON doesn't allow` (or `Infinity`, `-Infinity`) | Send a number, or leave the field out; standard JSON has no way to write "not a number" or "infinite". |
| `the feed sent a number too large to use` | A number beyond what a float can hold (`1e999`), or an integer thousands of digits long: send the real value. |
| `the feed sent more than 1,000,000 items` | Send less: a feed carries what the pages show, not raw history. |
| `the feed doesn't say which contract it speaks …` | Add `"contract_version": "1"` to the payload. |
| `unsupported contract version '2'; this kestrel reads major version 1` | The feed speaks a newer contract: update kestrel. |
| `books.0.money: Input should be 'real' or 'paper'; …; and 2 more` | The payload doesn't match the contract: fix those fields in the feed. |
| `runs.0.time is 0001-01-01, outside 1970–2200` | A time the feed never set: Go writes an unset time as `0001-01-01T00:00:00Z`. Send the real time, or `null` (or nothing) where the contract allows it. |
| `books.0.value is too large` or `books.0.value isn't a number` | Send the real value: a number over 1e15, or NaN (which pydantic reads from the string `"NaN"`), can't be added up or drawn. |
| `the feed's generated_at is 4 hours ahead of this computer's clock …` | Check the clock, and the time zone offset, where the payload is made. |

## When two sources use the same id

Two sources can name the same thing: two warehouses that each have an account called "Brokerage", or the demo left in
next to a real feed. The source earlier in `profile.toml` keeps its item, and the later source's goes, with
everything that hangs off it:

| A later source's duplicate | Goes with it |
|---|---|
| account id | its holdings and its account history |
| book id | its book history, positions, trades, trade charts and runs |
| strategy id | nothing else: books keep pointing at the first source's strategy |

The later source's line in the sidebar then ends with `ignored duplicate ids: brokerage, rsi2` (the ids only, at
most five, then `and N more`, shrinking further — fewer names, then none, then a shortened line — whenever the full
note wouldn't fit the row), on its first row when it has several. To show the later source's item instead, move
that source up in the profile. `kestrel check` reads each source on its own, so it lists every source's accounts and
never shows this note.

The same thing can happen within a single source: a feed that sends two books (or accounts, or strategies) of the
same id is treated exactly like the cross-source case — the first item is kept, the later one dropped with whatever
hangs off it, and that source's own line gets the `ignored duplicate ids: …` note.

## `rails`

Later: a trading-rails install's paper books, run log and backtests. Until then a source of this kind shows as an
error that says it isn't available in this version.
