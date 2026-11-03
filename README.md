# kestrel — RETIRED 2026-11-03

This project is retired. This repo on GitHub is the frozen archive; nothing runs it any more.

**What it was:** one calm, read-only home for all your money: long-term accounts, a trading account and every paper
book side by side, a page per strategy comparing real trades with the backtest, and the research record (Home,
Accounts, Plan, Reserves, Books, Strategies, Backtests, Calendar, Activity, Settings). It read a local financial-data
warehouse plus two command feeds, and never placed an order.

**Why it retired:** its owner moved to a personal agent app that shows the same trading pages (books, strategies with
their backtest bands, trade anatomy, the backtest record) next to everything else, and kestrel went unopened. The
trading system it read now saves its feed document to a file that the new app reads directly, so kestrel's two command
feeds were archived with it.

**What's here:**

- `main` and the tag `kestrel-final`: the last working version (all five phases built). `kestrel serve --demo` still
  runs it on fictional data ("Alex"), as described in the [design spec](docs/specs/2026-09-25-kestrel-design.md).
- The branches `reserves-estimates` and `plan-accuracy` (tagged `archive/reserves-estimates` and
  `archive/plan-accuracy`): two features that were in progress and never reviewed or merged.

Nothing reads from or writes to this repo any more. Licensed as before ([LICENSE](LICENSE)).
