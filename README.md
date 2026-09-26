# kestrel

**One calm, read-only home for all your money.** Your long-term accounts, your trading account and every paper
book appear side by side. Each strategy gets a page that shows how it trades and whether it's behaving the way its
backtest said it would.

> **Status: Phase 4a of 5 — Home, Accounts and the Strategies pages run.** Accounts read your own data from
> financial-data-collector, or the demo; Books, Backtests, Activity and Settings arrive in later phases. See the [design spec](docs/specs/2026-09-25-kestrel-design.md).

## What it shows

- **Home:**
  - net worth, with how much of the growth was your deposits versus the market,
  - where your money sits,
  - **your trading vs your index money**, meaning whether the active side is earning its keep net of drawdown,
  - what needs you,
  - every book at a glance,
  - today's runs,
  - open positions with their room to stop.
- **Strategies:**
  - the rule drawn as four steps,
  - real trades against the backtest's spread of outcomes,
  - a running average inside the expected funnel,
  - how much of the money is working,
  - trade anatomy,
  - return against worst drop,
  - month by month.
- **Accounts:**
  - every account's value, and how much of its growth was your deposits versus the market,
  - what each account holds, its weight and its gain,
  - everything you hold, added up across accounts.
- **Books, Backtests, Activity and Settings** are built from the same components.

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
| **kestrel** | shows it all; reads the two above, or any source that speaks its data contract |

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
   `profile.toml`, and `[sources.categories]` files your trading accounts under `trading`. Set `[benchmark]` to a
   symbol the collector already prices (an index fund you hold, for example; SPY often isn't priced there).
3. Run `kestrel check`: the source should read `ok`, with every account and its category listed under it (never a
   balance). Then `kestrel serve`; `kestrel serve --demo` still shows the demo.

Every source and what it reads: [docs/connectors.md](docs/connectors.md).

## License

MIT, see [LICENSE](LICENSE).
