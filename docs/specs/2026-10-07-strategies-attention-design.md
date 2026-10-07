# Strategies that say what runs, how it performs, what needs you, and what the next review needs — design

- **Date:** 2026-10-07 · **Status:** approved by the owner's goal statement (2026-10-07), built autonomously.
- **Parent specs:** [`2026-09-26-phase-3a-strategies-design.md`](2026-09-26-phase-3a-strategies-design.md) (the pages
  this reshapes), [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) §7 (the contract).
- **Sibling:** the webull desk's feed grows in the same step (webull `docs/superpowers/specs/2026-10-07-kestrel-feed-strategy-facts-design.md`).
- **Look:** [`../design-system.md`](../design-system.md). No new colours; status carries a word or an icon.

## 1. Why

The Strategy pages were built to answer "how does it trade, and is it behaving like its backtest?". Two weeks of a
live real book showed what they get wrong or leave out:

1. **They describe the wrong book.** RSI2's steps come from the parked *paper* track ("paper BUY queued"), the
   stop rule is a footnote, the gates (regime, daily loss halt, caps) are missing, and the review bar is the retired
   proof-phase charter's 30 trades. The plan in force (swing plan v2.1) says 20 closed trades from 2026-10-02 or
   2026-11-02. The IBS book has a decision review on 2026-10-30 with seven pre-registered criteria; the page says
   nothing about any of it.
2. **Some figures mislead.** "Where the money works" counts a lot twice on the day it closes and another opens
   in its slot, and counts each FIFO slice of one fill as its own lot. "Money working" is a slot count, not
   dollars: five $590 lots in a $3,500 account are 100% of the slots and 84% of the money. "In band" on 16 trades
   reads as a verdict; the plan judges the system over 30–50.
3. **Nothing says how the money is actually doing.** No realized vs unrealized P&L, no stop coverage, no
   drawdown, no deposit-adjusted return, and a real book with no value history gives the "worth it" and monthly
   panels nothing to draw, silently.
4. **The comparisons are loose.** Monthly returns compare a book that started mid-month with a full month of the
   long-term accounts, and the backtest chip says "2006–2026" without saying the configuration, the sizing, the
   costs modelled, the sample or the research stage. The IBS evidence (round-5 develop and confirm, the
   deployment proposal's caveats) never reaches kestrel.
5. **The system is a black box.** Nothing shows last night's signals, what the gate refused and why, what is
   queued, what filled, what expired, whether the runs happened, or how old the prices are.
6. **The order is wrong.** The rule cards come first and the attention items are on Home. A page about a running
   system should lead with what needs you and how far the next review is.

Everything stays read-only; nothing here places, changes or cancels anything.

**Adherence principle (owner):** the combined record of hand-placed and system-placed trades is kept on one book,
and every adherence figure judges a trade against the rules in force when it was entered. A hand entry in the weeks
the real book ran the RSI2 rules by hand (before the first system fill, 2026-09-16) was the way the rules were run
then; after plan v2.0 (2026-10-02) a hand entry or hand exit is a deviation. The desk's own journal scoring
(`plan_followed`) is shown as it is, never recomputed by kestrel.

## 2. The contract (additive; `contract_version` stays `"1"`)

| Model | Added |
|---|---|
| `Step` | `kind: "step" \| "gate" = "step"`. A gate is a limit or a circuit breaker (regime, loss halt, caps); steps are the flow. |
| `RuleVersion` (new) | `version`, `effective: date`, `summary` |
| `Criterion` (new) | `key`, `label`, `measure`, `target`, `value` (the latest reading as text), `status: pass \| fail \| pending \| info` |
| `Review` (new) | `label`, `at_trades`, `counted_since: date`, `by: date`, `last_at: date`, `last_note`, `criteria: list[Criterion]`, `doc` (a document's name, never a path) |
| `Strategy` | `rules_version`, `rules_effective: date`, `rules_history: list[RuleVersion]`, `review: Review` (`review_at_trades` stays for older feeds) |
| `Expected` | `stage`, `config`, `sizing`, `costs`, `sample`, `caveats: list[str]` |
| `Backtest` | `config`, `sizing`, `costs`, `sample`, `caveats`, `cagr_pct` (`window` already names the stage) |
| `Trade` | `entry_by: system \| hand`, `exit_by: system \| hand`, `rules_version`, `plan_followed: bool \| None` (the desk's scoring; None = not scored), `note` |
| `Book` | `capital: float` (what returns are measured against), `capital_basis` (what that is, in words), `prices_as_of: date` (the latest close its marks use) |
| `Decision` (new) | `book_id`, `time`, `kind: signal \| queued \| blocked \| placed \| filled \| expired \| cancelled \| skipped \| error`, `symbol`, `side: buy \| sell \| ""`, `detail`, `value` (the indicator reading), `label` ("RSI(2)") |
| `Snapshot` | `decisions: list[Decision] = []` |

Every new field defaults, so a feed written before this loads unchanged, and `docs/contract/snapshot.schema.json`
is regenerated.

## 3. The views (`views/strategy.py`, pure functions of one Snapshot)

### 3.1 Attention (new, leads the page)

The strategy's own items, in Home's `Attention` shape and order (serious, warning, note):

- a real position of its books with no stop on record (serious);
- a snapshot alert that links to this strategy's page or names one of its books (its own level);
- a late or failed run of one of its books (warning);
- prices older than 3 sessions for a book with open positions (warning: "Marks are from <date>");
- the review due: trades reached, or the date passed or within 7 days (note);
- a book paused (note);
- fewer than `LIMITED_UNTIL` (30) closed trades on the primary book: "n trades so far — limited evidence" (note).

### 3.2 Review progress (new)

From `Strategy.review`, else from `review_at_trades`: the label, trades counted on the primary book since
`counted_since` (or since its start) against `at_trades`, the days left to `by`, `due: bool`, the last review's
date and note, the criteria with their status, and the document's name. A date review with no trade bar shows the
date and the criteria; a trade review shows the progress bar.

### 3.3 Rules (reshaped "How it trades")

`steps` (kind `step`, all of them, no cap at four), `gates` (kind `gate`), `sizing`, `version`, `effective`,
`history`. The web lays the steps out as the numbered flow and the gates as a list under "Gates and limits".

### 3.4 Performance (new)

For the primary book: `realized_pnl` (closed trades), `unrealized_pnl` (positions at their last price),
`total_pnl`, `capital` and `capital_basis` (from the book; when the book sends none, the sum of its positions'
cost is used and the basis says so), `deployed` (positions at the last price), `deployed_pct` of capital,
`positions`, `stops_covered` (a `stop_price` or `stop_resting`) of `stops_total` (real books only; paper says
"paper: stops are the runner's"), `drawdown_now_pct` and `drawdown_worst_pct` and `return_pct` from the growth
index of the book's history (deposit-adjusted, so `net_flow` never reads as gain), the period (`since`, `days`),
and `unavailable: list[str]`: a plain sentence for each figure that can't be shown and why ("This book sends no
value history, so drawdown and return since start can't be measured").

### 3.5 Last decision cycle (new)

The primary book's `decisions` on its latest session day (ET date of `time`), grouped by kind with counts, each
row with its symbol, side, reading and detail; the book's runs (the latest per label, and the next due); the
prices' date and a freshness word (fresh: the last session; otherwise "n sessions old"). Empty state: "This book
doesn't report its decisions."

### 3.6 Adherence (new)

Per `RuleVersion` in force (a trade belongs to the version whose `effective` is the latest on or before its
`opened`; trades before the first version are "before the first written rules"): closed trades, system and hand
entries, system and hand exits, `followed` / `broken` / `unscored` from `plan_followed`. `deviations`: the trades
whose `plan_followed` is False, and — only under a version whose rules were run by the system (the feed marks this
by the version's summary; kestrel treats every version after the first as system-run unless the strategy has no
system entries at all) — a hand entry or a hand exit. A note states the method.

### 3.7 Fixed and qualified figures

- **Slots:** a lot is one `(symbol, opened)`; it holds a slot from `opened` up to but not including `closed`, and
  on `closed` itself only when `opened == closed`; an open position holds one from `opened` to the last session.
  Beside the slot tiles: `deployed` and `deployed_pct` of `capital`, with a sentence that slots and dollars differ.
- **Evidence:** `behaving.evidence` is `none` (0), `early` (under 10), `limited` (10–29) or `adequate` (30+), and
  `evidence_text` says the count and the bar ("16 real trades so far — limited evidence; the plan judges the system
  over 30–50"). The strategy card carries the same `evidence` and words its verdict with it.
- **Monthly:** each month row carries `partial: bool` and the dates it covers. The long-term accounts are measured
  over the same dates as the book that month (the growth index at the book's first and last point of the month,
  carried from the last point on or before). A month the book didn't cover from its first session, or the current
  month, is `partial`, and the grid labels it.
- **Worth it:** the long-term accounts and the benchmark are measured over the book's own window (from the book's
  first history date) and labelled with the same period; with no book history, only the backtest point shows and
  the panel says why.
- **Research:** `research.expected` basis (stage, config, sizing, costs, sample, caveats) and
  `research.backtests` (the snapshot's backtests with this `strategy_id`, newest first).

### 3.8 Trades

`TradeRow` gains `entry_by`, `exit_by`, `rules_version`, `plan_followed`, `note`.

### 3.9 Cards

`StrategyCard` gains `evidence`, `attention` (serious + warning count), `realized_pnl`, `unrealized_pnl`,
`review_text` ("12 of 20 trades · by 2 Nov" / "Decision review 30 Oct · 3 of 5 passing").

## 4. The web

Panel order on `/strategies/<id>`:

1. Header: name, summary, book chips, the Real | Paper toggle, a rules chip ("Rules v2.1 · since 5 Oct").
2. **Needs you** (span 5) · **Next review** (span 7, progress bar or date, the criteria as a table).
3. **How the money is doing** (span 12): tiles for realized, unrealized, total P&L, return since start with the
   capital basis under it, deployed of capital beside slots in use, stop coverage, drawdown now / worst; the
   `unavailable` sentences under the tiles.
4. **How it trades** (span 12): the steps flow, then "Gates and limits", then sizing and the version line.
5. **Last decision cycle** (span 7) · **Scorecard** (span 5) with the evidence sentence under the table.
6. **Is it behaving?** (span 7) · **Average per trade** (span 5): with `evidence` early or limited, the panel's
   subtitle says so and the chart height drops to its compact size.
7. **Where the money works** (span 5) · **Trade anatomy** (span 7).
8. **Adherence** (span 12): one row per rules version, the deviations listed under it, the method note.
9. **Research context** (span 12): the expected basis as labelled lines, the caveats, and the backtests table.
10. **Is it worth it?** (span 7) · **Month by month** (span 5), at the bottom, partial months labelled.
11. **All trades** (span 12), with "Entry", "Exit" (system / hand) and "Plan" (✓ / ✗ / —) columns.

The Backtests page's Results table shows each row's stage, configuration, sizing, costs and sample as a muted line
under its name. Every chart keeps its table view, every panel its keyboard access, and the pass at 390, 1200,
1280 and 1440 px in both themes is run before merge.

## 5. The feed (webull, read-only)

- **Strategy `rsi2`:** steps from the *real* track in plain words with parameters; gates from the live autopilot
  config (regime, daily loss halt, max lots/positions, per-order cap, orders and decisions per day, kill file) and
  the plan's rules (hold through earnings, no time stop, backstops); `rules_version` v2.1, `rules_history` v1.0 /
  v2.0 / v2.1; `review`: System review, 20 trades counted from 2026-10-02 or by 2026-11-02, last 2026-10-02 with
  its note, criteria = the plan's §9 metrics with plan-followed % computed from the journal.
- **Strategy `ibs`:** `review`: Decision review by 2026-10-30, criteria 1–7 of the evaluation plan: 1 and 2
  computed from the ledger; 3–7 from the latest Friday review file when one exists, else pending.
- **Expected:** stage, config, sizing, costs, sample and caveats for both; the IBS caveats from the round-5 memo
  and the deployment proposal (selection and override, two partial years, close fills, stuck lots, no dividends in
  paper, simulated fills).
- **Backtests:** the IBS round-5 develop and confirm rows (`strategy_id` ibs) beside the RSI2 rows, each with
  config, sizing, costs, sample and caveats.
- **Trades (real):** `entry_by` from the placement match, `exit_by` and `exit_reason` (signal / stop / backstop /
  hand) from the autopilot's placed SELLs, `rules_version` from the version in force at entry, `plan_followed`
  from the journal's YAML blocks matched by symbol, exit day and entry price. IBS round trips: system both ways,
  followed by construction.
- **Books:** `rsi2-real` gets a history from the nightly net-liq rows with the contributions ledger as
  `net_flow`, `capital` = the latest net liq, `capital_basis` naming it; paper books name their starting cash;
  every book carries `prices_as_of`.
- **Decisions:** the RSI2 queue, the autopilot's audit rows and the fills of the last 5 sessions; the IBS ledger's
  signal, gate, placed, fill, unfilled, cancel, skipped and error rows of the last 2 sessions.

All of it reads files the desk already writes; the feed's import guard and contract test are extended, never
loosened.

## 6. Testing

- **Python:** the contract (round trip, defaults); each new section on fixtures and on the demo; the slot rule
  (same-day close and open counts one; two slices of one fill count one); the evidence words; matching-date monthly
  figures and the partial flag; adherence per version (a hand entry before v2.0 is not a deviation, after it is;
  a scored `plan_followed: false` always is); the attention items; routes unchanged; generated files.
- **Web:** each panel renders, has its table view where it charts, and its empty state; the card's evidence
  words; the Backtests detail line.
- **Feed (webull):** each new block on the fictional desk; the guard and contract tests extended.
- **Screenshot pass** per AGENTS.md invariant 4.

## 7. Out of scope

- Editing or placing anything. Reviews are read, never written. Home's attention list is unchanged (it still links
  here). The Books pages keep their current shape.
