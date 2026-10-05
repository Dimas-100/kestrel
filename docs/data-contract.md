# The kestrel data contract

Every source kestrel reads speaks one format: a **Snapshot**. The built-in connectors produce one, and so can any
system of your own — serve a Snapshot as JSON and the `feed` connector plugs it in without a line of your system's
code entering this repo ([how](connectors.md#feed-any-system-that-serves-the-contract)).

- **Schema:** [`contract/snapshot.schema.json`](contract/snapshot.schema.json), generated from
  `src/kestrel/contract.py` (`kestrel schema`); a test fails if the two drift.
- **A complete example:** `kestrel demo` prints the demo Snapshot — a year of fictional accounts, books, trades and runs.
- **Entities and fields:** the table in the [design spec](specs/2026-09-25-kestrel-design.md#7-data-contract-v1), and
  the blocks added since in [Cash, debt, plan and research](#cash-debt-plan-and-research) below.

## Rules

- `contract_version` is `"1"`, and a feed must say so. Within a major version changes are **additive only**; kestrel
  ignores fields it does not know, and refuses an unknown major version (the source shows as `error` with the reason).
- Every timestamp carries an offset (`2026-09-25T17:08:00-04:00`); dates are `YYYY-MM-DD`.
- Money is in the profile's currency. `net_flow` on a value point is that day's deposits minus withdrawals, so
  performance is measured net of money moving in and out. Date a flow on the day the value first includes it: a
  deposit dated before the balance shows it reads as a loss that day and a gain the day it lands. kestrel only
  guards the extreme case (a deposit bigger than the value it lands on waits for the next point rather than turning
  the return line upside down). A point's optional `unexplained` (default 0) is the part of its `net_flow` that no
  recorded transaction explains yet: the balance moved and the source's records don't say why, most often a
  deposit the broker hasn't posted. It is already inside `net_flow`. kestrel only uses it to label that money as
  not posted yet.
- `status` on a source is `ok`, `stale` or `error`; kestrel also marks a source stale once its `last_success` is older
  than the profile's `stale_after` for it.
- An alert's `link` is a page inside kestrel (`/books`) or empty. A link to another site (`https://…`, `//host`) fails
  validation, so the payload is dropped and the source shows as `error`.
- A connector only reads. Nothing in the contract asks a source to change anything.
- A strategy, book or account `id` appears directly in a URL path (`/strategies/{id}`); an id must not contain `/`.
  When two sources use the same id, the one earlier in the profile keeps it and the later one's item is dropped
  ([connectors.md](connectors.md#when-two-sources-use-the-same-id)). Targets, goals and backtests are matched by
  `id` the same way, theses and exposures by `symbol`, and events by `date`, `kind`, `symbol` and `title`.

## Optional extras

The Strategy and Accounts pages draw more when a source sends these. Each is optional; without it, the page shows a
plain "not reported" state for that part and everything else still works.

- `Account.account_type`: display text for the kind of account (`Roth IRA`, `Brokerage`), shown beside the
  institution on the Accounts pages. `holdings` and `Account.cash` fill an account's holdings table.
- `Holding.as_of`: the day the holding was reported (`YYYY-MM-DD`). When an account's holdings are older than its
  value, the account page says so under the holdings table.

- `trade_charts`: daily bars around a closed trade (`date`, `open`, `high`, `low`, `close`). A chart matches its
  trade by `book_id`, `symbol` and `opened`. It may carry an `indicator` drawn in its own panel under the candles
  (`label`, `values` aligned with the bars, threshold `lines`) and the trade's `stop`. A chart whose bars don't
  include the open date, or that matches no trade, is ignored.
- `Expected.cagr_pct` and `Expected.max_drawdown_pct`: the backtest's yearly return and its worst drop (a negative
  percent), plotted on "Is it worth it?".
- `Strategy.watch`: names close to a signal (`symbol`, `label`, `value`, `note`), listed under "Where the money
  works".
- `Position.stop_resting`: `true` when a protective stop rests at the broker but its level isn't reported (a desk
  that manages its own stops and doesn't send their price, say); left out or `null` when a missing `stop_price`
  really does mean no stop. With `stop_price` empty and `stop_resting` true, kestrel shows "resting (level not
  reported)" instead of flagging the position — never inferred, only set when a source actually knows.

## Cash, debt, plan and research

Six more blocks — `targets`, `theses`, `events`, `goals`, `exposures` and `backtests` — and a `debt` category. Each
block is a list that defaults to empty, so a document written before they existed still loads, and an older kestrel
ignores them. A source sends facts (a target, a thesis's health, an event); kestrel works out what it can from data
it already has, such as an account's actual share of a holding or a goal's progress, so two sources can't disagree
about the same number.

### Accounts: cash and debt

`category` is `long_term`, `trading`, `cash`, `debt` or `other`. A `debt` account is money owed, such as a credit
card; its `value` is the amount owed, and below zero when the balance is in your favour (a card paid past zero is
money owed to you). Net worth is everything owned less everything owed, signed, so a credit balance adds. A debt
account's history carries what it owes, and its `net_flow` keeps its meaning — money in (a payment) minus money out
(a charge) — so a payment from checking nets to nothing and only interest reads as a change of its own. An account
with no `account_history` (a bank feed that reports only today's balance) is drawn flat at today's balance across the
net worth history, with no flows: the history's last point is the net worth every page shows, the flat line adds
nothing to market growth, and the chart says how many accounts are counted that way. Two optional fields:

| Field | Meaning |
|---|---|
| `rate_pct` | yearly interest, in percent: what cash earns (APY), what debt costs (APR) |
| `limit` | a credit line's limit |

### Transactions

Money that moved through an account, as the account's own records post it: a charge, a payment, a deposit,
interest. One row per posted transaction; a source leaves pending ones out and sends each row once. A row carries no
id of its own. Added 2026-10-05, after the six blocks above, and optional like them.

| Field | Meaning |
|---|---|
| `account_id` | the account it belongs to |
| `date` | the day it posted |
| `amount` | signed: money in positive, money out negative. On a card a payment is money in and a charge money out, the convention the account's `net_flow` uses |
| `description` | what the bank says it was |
| `counterparty` | optional: the other side, when the source names one |
| `category` | optional: the source's own word for it, shown as text |

The Account page lists an account's rows newest first with the totals in and out; an account with no rows shows no
list. A row for an account the document doesn't name is kept and never shown. When a later source reuses an account
id, the later account's rows go with it (see connectors.md).

### Targets

What the plan says an account should hold.

| Field | Meaning |
|---|---|
| `id` | unique |
| `account_id` | the account the target is about, or none for all accounts |
| `label` | display text: `VTI`, `Growth core` |
| `symbols` | what it measures; kestrel sums these holdings |
| `unit` | `"%"` (the default): a share of the account's value, and kestrel computes `actual` from holdings when it isn't sent · `"x"`: a ratio the source measures and sends as `actual` |
| `target`, `low`, `high` | the aim and the band around it; at least one of the three |
| `actual` | optional for `%`, required for `x` |
| `note` | why |

A target is **on plan** inside `[low, high]` (a missing end is open), **over** above it and **under** below it. A
target with no aim, a ratio without its `actual`, or a `low` above its `high` fails validation, so the payload is
dropped and the source shows as `error`.

### Theses

Why each holding is owned.

| Field | Meaning |
|---|---|
| `symbol`, `name` | the holding |
| `status` | free text; `active` by default |
| `health` | `ok`, `watch`, `alert` or `none` (the default) |
| `reasons` | what drove the health |
| `conviction` | free text, usually `low`, `medium` or `high` |
| `opened`, `last_reviewed` | dates, each optional |
| `wrong_if` | the conditions that would prove it wrong |
| `account_ids` | the accounts it is about |

### Events

Dated things about a company.

| Field | Meaning |
|---|---|
| `date` | the day |
| `symbol` | the company, or empty |
| `kind` | `earnings`, `filing`, `insider`, `dividend` or `other` |
| `title`, `detail` | what happened or will |
| `url` | `https://…` or empty |

A `url` that isn't `https://` (`http:`, `javascript:`), or that holds a space, a quote or `<`/`>`, fails validation, so
the payload is dropped and the source shows as `error`. Everything else in an event is shown as text.

### Goals

| Field | Meaning |
|---|---|
| `id` | unique |
| `label` | display text |
| `target` | the amount to reach |
| `account_id`, `account_ids`, `category` | what it measures: one account, a few accounts, a category, or none of these for net worth (at most one may be set) |
| `measure` | `value` (the current value of what it measures) or `deposits` (money moved in since 1 January of the goal's year — `by`'s year, or this year) |
| `by` | the date to reach it by, optional |
| `note` | why |

kestrel computes the current value and the progress.

### Exposures

What the money is really in, looking through funds.

| Field | Meaning |
|---|---|
| `symbol`, `name` | the company or asset |
| `value` | held directly plus through funds |
| `direct` | the part held directly (0 by default) |
| `sector` | free text |

### Backtests

The research record.

| Field | Meaning |
|---|---|
| `id` | unique |
| `name`, `family` | the candidate, and the family of candidates it belongs to |
| `window` | free text: `develop`, `confirm`, … |
| `verdict` | `pass`, `fail`, `refused` or `pending` |
| `at` | when it ran (a timestamp with an offset) |
| `strategy_id` | the strategy it tests, if any |
| `trades`, `avg_trade_pct`, `t_stat`, `calmar`, `max_drawdown_pct` | the results, each optional; the drawdown is a negative percent |
| `note` | free text |
