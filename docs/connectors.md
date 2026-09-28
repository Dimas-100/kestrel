# Connectors

A connector reads one source and returns a Snapshot, the format in [`data-contract.md`](data-contract.md). kestrel
asks every source in your `profile.toml` each time a page loads. A source that can't be read shows as an error in the
sidebar's Sources block, and the rest of the page still works. Every connector only reads: none of them changes its
source's data.

| `kind` | Reads | Since |
|---|---|---|
| `demo` | nothing: a fictional year for "Alex" | Phase 2; the default when there is no `profile.toml` |
| `fdc` | [financial-data-collector](https://github.com/Dimas-100/financial-data-collector)'s SQLite warehouse | Phase 4a |
| `feed` | any system that serves the contract as JSON: at a URL, in a file, or printed by a command kestrel runs (your trading desk) | Phase 4b; commands Phase 5 |
| `rails` | a trading-rails install: its paper account (`paper.json`) and run log (`runs.jsonl`) | Phase 5 |

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
trading, cash, debt or other)` and exits with status 2. Use one of those five in `[sources.categories]` — `debt`
files an account as money owed (its `value` is what's owed, not what it holds); it never falls out of the type-based
default above on its own, so a card or a loan needs an explicit line here.

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

or, with no server at all, a program kestrel runs itself ([below](#a-command)):

```toml
[[sources]]
id = "desk"
kind = "feed"
label = "Trading desk"
command = ["../desk/.venv/Scripts/python.exe", "-m", "desk.feed_export"]  # the program, then its arguments
cwd = "../desk"             # optional: the folder it runs in (default: this profile's folder)
timeout = 30                # optional: seconds, 1 to 120 (default 30)
refresh = "1m"              # optional: how long one run's output is reused, 5s to 1h (default 1m)
stale_after = "15m"
```

A feed is one JSON document in the contract's own format, a Snapshot ([`data-contract.md`](data-contract.md)), served
at a URL, saved in a file, or printed by a command. It is how a system of your own, such as a trading desk, shows its
books, strategies, trades, runs and alerts (and its accounts, if it has any) without kestrel knowing anything else
about it.

- **Exactly one of `url`, `path` and `command`.** A `url` starts with `http://` or `https://`. A relative `path` is
  relative to the folder `profile.toml` is in.
- **`token_env`** names an environment variable, in capitals; the token itself never goes in the profile. kestrel
  reads it each time it asks the feed and sends it as `Authorization: Bearer …` to the configured URL and nowhere
  else: it doesn't follow redirects and doesn't use a proxy, and it never prints or logs the token. A token goes only
  over `https://`, or over `http://` to this computer (`127.0.0.1`, `::1` or `localhost`). A URL can't carry a user
  name or password (`http://name:secret@…`); use `token_env`.
- **Read-only, and asked each time a page loads.** One GET, with `Accept: application/json`,
  `User-Agent: kestrel/<version>` and no cookies, or one file read. Nothing is cached. (A command's output is reused
  for `refresh`: see below.)

A feed's shape is checked when the profile loads: a source with more than one of `url`, `path` and `command` (or
none), another scheme, a space or control character in the URL (write a space as `%20`), a port that isn't 1 to
65535, a user name in the URL, a `token_env` that isn't a variable's name (or that goes with a `path` or a `command`,
or with plain `http://` to another computer), a `command` that isn't a list of words in quotes, a `cwd` or `refresh`
without a `command`, a `refresh` outside 5s to 1h, or a `timeout` outside 1 to 60 (1 to 120 for a command) stops
`kestrel check` with `profile problem: …` and exit status 2, before any source is read. No message repeats the URL or
the command's arguments back.

### A command

With `command`, kestrel runs your system's export itself and reads what it prints, so the system needs no web server
of its own. The program prints the payload (the same JSON a URL would serve) on standard output and exits with 0.

- **The command is a list:** the program, then its arguments, each in quotes. kestrel starts the program directly,
  never through a shell, so nothing in it is read as a pipe, a wildcard or a second command. A program path with a
  slash in it (`../desk/.venv/Scripts/python.exe`) is relative to the folder `profile.toml` is in (one that starts
  with `~/` is in your home folder). A bare name (`python`) is looked up on `PATH` only, never in the folder kestrel
  was started from (Windows itself would look there first) nor through an empty or relative `PATH` entry. Arguments
  are passed exactly as written. On Windows, a batch file (`.bat` or `.cmd`) is refused, found on `PATH` or named:
  Windows runs one through `cmd.exe`, a shell; name the program it runs instead.
- **Where and how it runs:** in `cwd` (relative to the profile's folder; by default the profile's folder itself), with
  no standard input, a copy of kestrel's environment (so a program that needs a token reads its own variable; there
  is no `token_env` here), and on Windows no console window.
- **Reading it:** standard output, up to 20 MB, as UTF-8, through every check below. Standard error is kept only for
  the error message: its last line.
- **Time:** a program still running after `timeout` seconds is stopped, and so is one that prints more than 20 MB;
  the page doesn't wait past `timeout`. Only the program itself is stopped: if it started programs of its own, they
  may run on.
- **Reuse:** one source runs its command at most once at a time. A run's result, good or bad, is reused for
  `refresh`; the first page load after that runs it again, and loads that arrive meanwhile wait for that run instead
  of starting their own. The same command in another `cwd` is another run.
- **Freshness** is still the payload's `generated_at`, so `stale_after` means how old the desk's data may be, however
  often the command runs.
- **Safety.** The command is your own configuration, like a shell alias: kestrel runs only what `profile.toml` names,
  with your permissions, so keep `profile.toml` where only you can change it. kestrel itself stays read-only: the
  program is a separate process whose code kestrel never imports, and a guard test fails if anything but the command
  runner uses `subprocess`, `os.system`, `os.popen`, `os.spawn*` or `os.exec*` (and a few like them), or if anything
  passes `shell=True`. (kestrel also opens your browser when `kestrel serve` starts, through Python's `webbrowser`,
  which that rule doesn't cover.) kestrel's own messages name only the program's file name, never its arguments or
  the environment. The last line of standard error in `the command failed (…): …` is the program's own words,
  though, and may repeat its arguments: keep secrets out of `command` and let the program read them from its
  environment.

### What is checked

In this order; the first check that fails is the source's error, and the rest of kestrel keeps working.

1. **The token**, when `token_env` is set: the variable must be set and not empty, and hold only visible characters.
2. **The answer:** status 200 only, at most 20 MB, and all of it inside `timeout`, counted from when kestrel starts
   asking: connecting, the headers and the body, chunked or not, however slowly the feed trickles them. The one step
   `timeout` can't cut short is looking up the host's address, which comes first (a local desk resolves at once). A
   body that ends before its `Content-Length` is refused. A file must exist and be at most 20 MB. A command must
   start, finish inside `timeout`, exit with 0, and print at most 20 MB.
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
| `no such program: python3` | Check the command's first word: a path is relative to the folder `profile.toml` is in; a bare name must be in a folder on `PATH` where kestrel runs (the folder kestrel was started from doesn't count). |
| `the command's folder doesn't exist: …` | Check `cwd`: it is relative to the folder `profile.toml` is in. |
| `the command couldn't start … (…)` | The first word isn't a program this computer can run (a folder, or a script with no program to run it): name the program, then the script, e.g. `["python", "export.py"]`. |
| `the command's folder can't be read: … (…)` | kestrel may not look into `cwd`: check the folder's permissions. |
| `export.cmd is a batch file, which Windows runs through cmd.exe …` | Name the program the batch file runs, with its arguments, instead. |
| `the command took longer than 30 s` | Make the export faster, or raise `timeout` (up to 120). |
| `the command failed (exit 2): …` | The program's own last line on standard error, at most 160 characters. Run the command yourself, in `cwd`, to see the rest. |
| `the command printed more than 20 MB` | Print less: a feed carries what the pages show, not raw history. |
| `the feed sent something that isn't JSON: a web page …` | The address answers with a page, often a sign-in page: point `url` at the feed itself. |
| `the feed sent something that isn't JSON (…)` | Compare the feed with `kestrel demo`'s output. A command prints only the JSON on standard output: send progress lines and warnings to standard error. |
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
same id. The first item is kept and the later one dropped, and that source's own line gets the
`ignored duplicate ids: …` note. What hangs off the dropped item stays, though: its positions, trades, holdings and
the rest carry the same id, so within one source they can't be told apart, and they show under the item that's kept.

Histories follow the same rule by their id. When two account or book histories share an id, in one source or
across sources, the first is kept and every page draws that one; a later source's history goes even when that source
has no item of the id. A history isn't an item of its own, so this isn't noted on the source's line.

The plan and research blocks follow it too: targets, goals and backtests by their id, theses and exposures by their
symbol, and events by their date, kind, symbol and title. In one source or across sources, the first is kept and the
later one goes on its own (nothing hangs off these). The ids and symbols dropped are named in the same
`ignored duplicate ids: …` note; an event has no id, so a dropped event isn't.

## `rails`: a trading-rails install

```toml
[[sources]]
id = "rails"
kind = "rails"
label = "Paper (trading-rails)"
path = "../trading-rails/data"     # the folder holding paper.json and runs.jsonl; relative to this profile's folder
stale_after = "36h"
```

- **`path`** is the folder [trading-rails](https://github.com/Dimas-100/trading-rails)' paper broker and runner write
  to: its `paper.json` (cash, positions, open orders) and `runs.jsonl` (one line per step of every cycle it has run).
  A relative path is relative to the folder `profile.toml` is in, like `fdc`'s. It's required: a source with none, or
  an empty one, is a source error — `a rails source needs a path to its data folder …` — not a profile problem, so
  the rest of the page still works.
- **Read-only, file reads only.** kestrel never imports `trading_rails` (the read-only guard forbids it): it reads
  `paper.json` and `runs.jsonl` by their own keys, the way `paper.py` and `runner.py` write them, and nothing else
  about the install.
- **One paper book**, `rails-paper`: its value is the account's cash plus each position's quantity times a price for
  it. trading-rails never persists a "last price" (it always prices live, against a bar source kestrel can't reach),
  so the price used is that symbol's most recent fill in `paper.json`'s `fills` since its current position opened,
  or the position's average cost when the fills don't reach that far. Its `started` date is the first row of
  `runs.jsonl`, or, without a run log yet, the state file's own `as_of`.
- **Positions** carry their quantity, average cost, that same last price, their opened date (the BUY that started
  the current position, after the symbol was last flat, or the book's `started` when the fills don't explain it),
  and a resting protective stop when `paper.json`'s `open_orders` has one for that symbol. Nothing from a position
  that has since closed — its date or its last price — carries into a new one.
- **Closed trades** are matched at the average cost, per symbol, from `paper.json`'s `fills`, the way trading-rails
  keeps it: a BUY moves the average, a SELL leaves it where it is. A trade's entry price is the average held at the
  time of the sale, its `pnl` is (sell − average) × quantity less commissions, and it opens on the BUY that started
  its position — so the realized P/L adds up to what trading-rails' cash says. A SELL larger than the position closes
  only what was held; a SELL with no position at all (the fill history doesn't reach back far enough) is left out —
  never given an invented entry. `fills` carries no commission today; a `commission` a future format might send is
  netted out of the trade's `pnl` (a BUY's is carried with its shares, like the average).
- **A strategy stub**, id and name from the run log's own `strategy` field on its newest row when a future log sends
  one, else `rails` / "trading-rails": today's run log names no strategy of its own.
- **Runs**, one per cycle in `runs.jsonl` (its rows share one timestamp per cycle): `done`, or `failed` when one of
  its steps errored, with that step's own message as the detail. Only the log's most recent 2 MB is ever read (it is
  never rotated, and every page load re-reads it), so the very first line after that cut, almost certainly sliced in
  half, is dropped along with a genuinely torn last line — the log may still be growing, or a run crashed mid-write.
- **Book history** picks up an equity point from a run row that reports one (a future log's `equity`, top-level or
  inside `extra`); today's runner sends neither, so this is ordinarily empty.
- **Errors, worded for a person:** a missing folder (`no trading-rails data at …`), a missing `paper.json`
  (`no paper.json in … : run trading-rails' paper broker first`), torn JSON in it (`… isn't valid JSON …`), and an
  unreadable or non-UTF-8 `runs.jsonl` (`… couldn't be read (…)` / `… isn't UTF-8 text`) each show as the source's
  error; a missing `runs.jsonl` is not an error (there simply are no runs yet).
