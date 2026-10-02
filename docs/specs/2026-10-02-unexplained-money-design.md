# Money the records don't explain yet — design

- **Date:** 2026-10-02
- **Status:** design; built alongside.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§7 contract, §8 connectors). Builds on
  [`2026-09-30-fdc-debt-and-flows-design.md`](2026-09-30-fdc-debt-and-flows-design.md) (the `fdc` reader at the
  collector's version 6).
- **Companion:** financial-data-collector's migration 7 (`unexplained_daily`), described in §3.

## 1. Why

A deposit reaches a broker's balance before it reaches the broker's activity feed. A SnapTrade balance can show a
deposit the morning it is made while the activity list still has no `CONTRIBUTION` hours later. The `fdc` reader
takes money moved only from transactions, so that day's `net_flow` is 0 and the deposit reads as market growth: the
account looks up several percent for the day, and the Home page's Trading line jumps by several points. Deposits
the feed has already posted are netted out correctly. Only one it hasn't posted yet goes wrong, and it goes wrong
every time.

The same gap shows up whenever the balance and the records disagree for a day. Examples are a money-market sweep
counted in both cash and the fund, and a trade or dividend the feed dates a day off. In a real warehouse those are
common and almost all come in runs that cancel out within days. They are value errors that correct themselves, not
money moved (§2).

## 2. The rule

On each day of an account's replayed history, the change the transactions as dated don't explain is **money moved
that the records don't explain yet**. It is not market growth.

```
unexplained cash     = cash today − cash yesterday − cash of every transaction applied today
unexplained shares_s = shares_s today − shares_s yesterday − shares_s of every transaction applied today
                       − shares_s yesterday × (split factor of s since yesterday − 1)
unexplained          = unexplained cash + Σ unexplained shares_s × close_s today      (no close: 0)
```

"Today" and "yesterday" are the replay's own output (`cash_daily`, `holdings_daily`), the same figures an account's
value is built from. So the account's value change splits exactly into:
- market moves on yesterday's shares;
- what today's transactions did;
- the unexplained amount.

- **An ordinary day is 0** by construction: the replay's output is yesterday's plus today's transactions. Only a day
  where a statement re-anchors the replay can differ.
- **A deposit the feed hasn't posted** is its amount on the day the balance shows it. When the feed posts it, the
  collector rebuilds the history from scratch on its next run. If the deposit is dated that same day, it now explains
  the change and the unexplained amount goes back to 0. If it is dated later, that later day's unexplained amount is
  minus the deposit, and the two days net to the right figure.
- **A trade the feed hasn't posted** shows as cash out and shares in. At the day's close those nearly cancel; what
  remains is the gap between the fill and the close, until the trade posts.
- **A stock split** without a transaction is not money moved: the shares the split adds are expected. This holds
  even if the broker shows the new shares a day late.
- **An account's first day** has no yesterday, so it has no unexplained amount.
- **A deposit the feed dates after the balance showed it** is that money, not more on top of it. The replay pairs the
  posted deposit with the cash it couldn't explain earlier, allowing for 1% of difference from income landing beside
  it, instead of adding it again as money in transit. The posting day then has an unexplained amount of minus the
  deposit, which cancels the recorded deposit.
- **A spike that reverses by itself is not money moved.** Sometimes a value is wrong for a day or two and then right
  again, with no transaction involved: a money-market sweep counted in both cash and the fund, or a reinvestment shown
  late. Unexplained amounts that cancel within a week, to a dollar or 1% of their size, are left out. A cancelled run
  stays open to the days after, so a late remainder can still join it. In a real warehouse this removed every
  sweep spike and left the long-term return exactly as before. A posting day never cancels a spike,
  because a transaction recorded it.
- **Under a dollar** is left out, as rounding or a fill's gap to the close.

The amount stays a little imprecise in one way, and that is accepted. A dividend or a fill the records date a day off
moves a few dollars between growth and money moved for that day, until the feed catches up.

## 3. The collector (financial-data-collector, migration 7)

- `derive/history.py`'s `replay` produces a new derived list, written by `rebuild` to a new table:

  ```sql
  CREATE TABLE unexplained_daily (
    as_of_date  TEXT NOT NULL,
    account_id  INTEGER NOT NULL REFERENCES accounts(id),
    cash        REAL NOT NULL,   -- the cash change no transaction explains
    holdings    REAL NOT NULL,   -- the share changes no transaction or split explains, at the day's close
    amount      REAL NOT NULL,   -- cash + holdings: money moved that the records don't explain yet
    PRIMARY KEY (as_of_date, account_id)
  );
  ```

  A row is written only where the amount is at least a dollar either way, and only where no reversal cancelled it.
  Like every derived table, it is rebuilt from scratch on each `derive`, so a spike can only be recognised once the
  days that reverse it have arrived.
- `replay` takes the split factors as a new optional argument. `Store.splits_by_symbol()` reads them from `prices`:
  every row whose `split_factor` is set and is not 1.
- `unexplained_daily` joins the counted tables, `AGENTS.md`'s table list and `docs/QUERIES.md`.

## 4. kestrel

- **Contract.** `ValuePoint` gains `unexplained: float = 0.0`, the part of `net_flow` that no recorded transaction
  explains. The change is additive within version 1. A feed that has no such figure leaves it at 0.
- **`fdc` reader.**
  - When the warehouse has `unexplained_daily` (version 7), each amount is filed under a history day the same way a
    transaction is (on that day, or the next point after it). It is added to that point's `net_flow` and recorded in
    `unexplained`.
  - It is skipped for an account whose `flows` is `balance`, because every change there is already money moved.
  - A debt keeps the contract's sign: the stored balance rising is money in, the same as its flows.
  - A version-6 warehouse still loads, without the figure. `MIN_VERSION` stays 6.
- **Views.** The Accounts view's `Flow` gains `unexplained`. Every other view already reads `net_flow`, so the day's
  change, the growth index, deposits and goals all follow without change.
- **Account page.** In the "Money in and out" list, a row whose `unexplained` is not 0 says **"not posted yet"** next
  to its direction. Its `title` explains the rest: the balance moved, and the account's records don't show why yet,
  most often a deposit the broker hasn't posted. When the records catch up, the note goes away on its own.

## 5. Testing

The collector's `tests/test_history.py`:
- a deposit that the balance shows and no transaction records is unexplained on that day, and 0 on every other day;
- once the deposit is recorded on that day, nothing is unexplained;
- if it is recorded a day later, the two days are +amount and −amount, and the cash is not counted twice, even when a
  few cents of income blur the match;
- a spike that reverses within a week leaves nothing unexplained, including a run that a late remainder closes;
- money that stays past a week is unexplained, even if it leaves later;
- less than a dollar is left out;
- a split the records carry as a transaction is not counted twice;
- a trade the feed hasn't posted leaves only the fill-to-close gap;
- a 10-for-1 split with no transaction, shown on time or a day late, leaves nothing unexplained over the two days;
- a deposit in transit (dated before the balance shows it) leaves nothing unexplained;
- the first day has no row;
- `rebuild` writes the table;
- migration 7 upgrades a version-6 warehouse.

kestrel:
- `tests/test_fdc_connector.py`: a version-7 warehouse's unexplained amount adds to `net_flow` and is recorded in
  `unexplained`; it is filed like a transaction; it is skipped for a `balance` account; a version-6 warehouse loads
  without it; a debt keeps its sign; the Home day % and the growth index treat it as money moved.
- `tests/test_accounts_view.py`: `Flow.unexplained`.
- The web Account test: the "not posted yet" note.
- Generated files: the contract schema and the fixtures.

## 6. Out of scope

- Guessing what the unexplained money was (a deposit, interest or a fee).
- A Home-page alert for it.
- Feeds other than `fdc`. A feed may send `unexplained` if it knows it.
