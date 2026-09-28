# kestrel

**One calm, read-only home for all your money.** Your long-term accounts, your trading account and every paper
book appear side by side. Each strategy gets a page that shows how it trades and whether it's behaving the way its
backtest said it would.

> **Status: all five phases are built.** Every page below runs, reading whatever mix of `fdc`, `feed` and `rails`
> sources your [profile](#run-it) names, or the demo. See the [design spec](docs/specs/2026-09-25-kestrel-design.md)
> and its [Phase 5 finish](docs/specs/2026-09-27-phase-5-one-dashboard-design.md).

## What it shows

One line per page; each has its own empty state naming what kind of source fills it.

- **Home** — net worth (deposits vs. market, and minus what's owed), where the money sits, trading vs. index money,
  what needs you, every book at a glance, today's runs, open positions with their room to stop.
- **Accounts** — every account's value and its deposits-vs-market growth, everything held added up across accounts.
- **Account** — one account's value, growth and holdings.
- **Plan** — targets against their band per account, thesis health and conviction, goal progress.
- **Reserves** — cash and debt: balances, rates, credit utilization, and the spread between what you earn and what
  you owe.
- **Books** — every real and paper book: value, since-start return, trades, slots, next run.
- **Book** — one book's equity against its benchmark, drawdown, scorecard, open positions and trades.
- **Strategies** — every strategy at a glance, real book vs. paper book.
- **Strategy** — the rule as four steps, real trades against the backtest's expected spread, trade anatomy, month by
  month.
- **Backtests** — the research record: one row per family, its best result, a verdict chip per window.
- **Calendar** — upcoming and recent dated events (earnings, filings, dividends, …), filterable by kind.
- **Activity** — runs by day, every alert, and every source's own status and freshness.
- **Settings** — read-only: who you are, the look, currency and time zone, and every source's kind, what it reads
  and its live status.

Reference mockups, drawn with fictional demo data; clone and open them in a browser:
[Home](docs/design/mockups/home.html) ·
[Home, light](docs/design/mockups/home-light.html) ·
[Strategy](docs/design/mockups/strategy.html) ·
[Phone](docs/design/mockups/phone.html)

## Principles

- **Read-only.** kestrel never places, changes or cancels an order. Your trading desk does that.
- **Personal, not published.**
  - It greets you by name and shows your accounts, but all of that comes from a local, gitignored `profile.toml` and
    your own data sources.
  - Nothing personal lives in the repo.
  - Someone else can clone it and point it at their own keys.
- **Made to last.**
  - A restrained, token-driven design ([Graphite](docs/design-system.md)): graphite neutrals, one accent, and the data
    as the only colour.
  - Real money is solid, paper is hatched, and expected is dotted, everywhere.

## How it fits

| Repo | Job |
|---|---|
| [financial-data-collector](https://github.com/Dimas-100/financial-data-collector) | collects accounts, holdings and prices |
| [trading-rails](https://github.com/Dimas-100/trading-rails) | trades safely: paper broker, safety gate, backtests |
| **kestrel** | shows it all: `fdc` reads financial-data-collector's warehouse, `rails` reads trading-rails' own paper state and run log, and `feed` reads any other system — of your own, such as a private trading desk — that speaks kestrel's data contract, over a URL, a file, or a command kestrel runs itself |

## Run it

Needs Python 3.11+ and Node 24+.

```bash
git clone <this repo> && cd kestrel
python -m venv .venv && .venv/bin/pip install -e .      # Windows: .venv\Scripts\pip
(cd web && npm ci && npm run build)
.venv/bin/kestrel serve                                  # opens http://127.0.0.1:8030 with demo data
```

Make it yours: copy `profile.example.toml` to `profile.toml` (gitignored) and set your name, look and sources.
`kestrel check` validates the profile and tries every source; `kestrel demo` prints the demo data as an example feed;
`kestrel schema` prints the [data contract](docs/data-contract.md).

### Point it at your own data

1. Fill a warehouse with [financial-data-collector](https://github.com/Dimas-100/financial-data-collector)
   (`fdc sync`).
2. In `profile.toml`, swap the demo source for the commented `fdc` block: `path` is the warehouse, relative to
   `profile.toml`, and `[sources.categories]` files your trading accounts under `trading`. A card or a loan doesn't
   come from the collector (its values are what an account holds): it arrives from a feed as a `debt` account (step
   5). Set `[benchmark]` to a symbol the collector already prices (an index fund you hold, for example; SPY often
   isn't priced there).
3. Run `kestrel check`: the source should read `ok`, with every account and its category listed under it (never a
   balance). Then `kestrel serve`; `kestrel serve --demo` still shows the demo.
4. Running [trading-rails](https://github.com/Dimas-100/trading-rails)? Add the commented `rails` block: `path`
   points at the folder holding its `paper.json` and `runs.jsonl`. No export step — kestrel reads its files directly.
5. A system of your own, such as a private trading desk, plugs in through a `feed` source three ways: a `url` it
   serves the contract at, a `path` to a file it writes, or a **`command`** kestrel runs itself and reads from
   standard output — the last needs no server at all, so a desktop program with no web server of its own still shows
   up. `kestrel demo` prints an example payload; the commented `feed` block in `profile.example.toml` shows all
   three.

Every source and what it reads: [docs/connectors.md](docs/connectors.md).

## License

MIT, see [LICENSE](LICENSE).
