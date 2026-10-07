# Strategies: attention, review, performance, cycle, adherence — implementation plan

**Goal:** the Strategy pages lead with what needs you and how far the next review is, show how the money is doing
on a documented capital basis, say which rules and gates run and which rules each trade was judged against, show
the last decision cycle, and qualify every verdict by its sample. The desk's feed supplies the facts.

**Spec:** `docs/specs/2026-10-07-strategies-attention-design.md` (kestrel) and webull
`docs/superpowers/specs/2026-10-07-kestrel-feed-strategy-facts-design.md` (the feed).

**Tech:** Python 3.11 + pydantic + pytest (`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`,
`ruff check .`); React + TypeScript + vitest (`web/`: `npm test`, `npm run build`); generated files via the
commands `tests/test_generated_files.py` prints.

## Constraints

- Read-only: GET routes only, no new routes. Nothing personal in git: demo data stays fictional; the feed's tests
  use the fictional desk fixture.
- Additive contract: every new field defaults; `contract_version` stays "1"; the schema is regenerated.
- Design system: tokens only; status carries a word or icon; every chart has a table view.

## Tasks

### kestrel

- [ ] **K1 Contract.** `Step.kind`, `RuleVersion`, `Criterion`, `Review`, `Strategy.rules_*`/`review`,
  `Expected` basis fields, `Backtest` basis fields + `cagr_pct`, `Trade.entry_by/exit_by/rules_version/
  plan_followed/note`, `Book.capital/capital_basis/prices_as_of`, `Decision`, `Snapshot.decisions`.
  Tests: round trip with every field; defaults load an old document. Regenerate `docs/contract/snapshot.schema.json`.
  Document in `docs/data-contract.md` ("Optional extras").
- [ ] **K2 Demo.** The demo strategies carry rules versions, reviews with criteria, gates, expected basis and
  caveats; demo trades carry entry/exit origin, the rules version and a scoring (a few hand entries under the first
  version, one deviation under the current one); demo books carry capital, basis and prices_as_of; demo decisions
  for the real RSI2 book and the IBS book; demo backtests carry the basis fields. Deterministic for the seed.
- [ ] **K3 Views.** `views/strategy.py`: `_attention`, `_review`, `_rules`, `_performance`, `_cycle`,
  `_adherence`, `_research`; the slot rule; `evidence`; matching-date monthly with `partial`; worth over the book's
  window; `TradeRow` + `StrategyCard` additions. Tests in `tests/test_strategy_view.py` and
  `tests/test_strategy_sections.py` (fixtures + demo). Regenerate the web fixtures.
- [ ] **K4 Web.** `lib/api.ts` types; new panels `AttentionPanel` (strategy), `ReviewPanel`, `PerformancePanel`,
  `CyclePanel`, `AdherencePanel`, `ResearchPanel`; reshaped `HowItTrades` (steps + gates + version),
  `SlotsPanel` (deployed vs slots), `ScorecardPanel` (evidence line), `MonthlyPanel` (partial labels),
  `WorthPanel` (window note), `TradesPanel` (origin + plan columns), `Strategies` card (evidence, attention,
  review text), `Backtests` detail line; `Strategy.tsx` order. Tests per panel; `npm run build`.
- [ ] **K5 Finish.** Spec status, `docs/connectors.md` feed table, screenshot pass (390/1200/1280/1440, both
  themes) via the demo server on 8031, PR, merge, restart the live server.

### webull (the feed)

- [ ] **W1 Spec + rules.** Spec doc; `RULES` (versions with effective dates), `RSI2_REVIEW`, `IBS_REVIEW`
  constants; `_steps` from the real track with gates from `AutopilotConfig.from_env()` and the plan; `_expected`
  basis + caveats; the IBS round-5 develop/confirm backtest rows with basis fields.
- [ ] **W2 Trades.** `entry_by` (placement match), `exit_by` + `exit_reason` from the autopilot's placed SELLs,
  `rules_version` by entry day, `plan_followed` from `playbook/journal.md` YAML blocks (symbol + exit day + entry
  price). IBS round trips: system/system, followed.
- [ ] **W3 Books + history.** `capital`, `capital_basis`, `prices_as_of`; `rsi2-real` history from net-liq rows
  with the contributions ledger as `net_flow`.
- [ ] **W4 Decisions.** The RSI2 queue + autopilot audit rows + fills of the last 5 sessions; the IBS ledger's
  rows of the last 2 sessions. Bounded.
- [ ] **W5 Tests + guards.** `tests/test_feed_service.py` per block on the fixture; `tests/test_feed_contract.py`
  shapes extended; guard test unchanged and green; `tests/feed_fixture.py` gains a journal, contributions and
  decisions. Commit on `main`; delete this plan's webull twin (webull deletes executed plans).
