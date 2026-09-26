# Connectors

A connector reads one source and returns a Snapshot, the format in [`data-contract.md`](data-contract.md). kestrel
asks every source in your `profile.toml` each time a page loads. A source that can't be read shows as an error in the
sidebar's Sources block, and the rest of the page still works. Every connector only reads: none of them changes its
source's data.

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

## `feed` and `rails`

Phase 4b. Until then a source of either kind shows as an error that says it isn't available in this version.
