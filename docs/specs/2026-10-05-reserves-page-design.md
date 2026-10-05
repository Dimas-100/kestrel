# The Reserves page, as your reserves — design

- **Date:** 2026-10-05
- **Status:** design; built alongside.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§4 pages, §5 visual system).
  Reshapes the Reserves page that [the Phase 5 spec](2026-09-27-phase-5-one-dashboard-design.md) §4.3 defined; its
  totals and spread rules are unchanged. Builds on [`2026-10-05-transactions-design.md`](2026-10-05-transactions-design.md):
  the bank rows are what make the new figures possible.

## 1. Why

Reserves answers "what cash sits where, and what is owed?" with a row of totals, a paragraph about rates, and two
plain tables. It says nothing about time: how long the cash would last, or what has been coming in and going out.
Now that the bank feed carries ninety days of posted rows per account, the page can say both, from the data alone.

## 2. The page, top to bottom

**Header.** "Money · Reserves" and a sentence the view writes: the cash after debts, and, when there are bank rows,
how long the cash would last at the pace money has been leaving it.

### 2.1 Runway (left, 7 columns)

How long the cash would last.

- **The figure:** "6.3 months", the page's hero, with "at the pace money has left your cash these 90 days,
  about $4,900 a month" under it. The pace is what *left the cash accounts*: every outflow posted on a cash
  account over the window, scaled to a month. That includes transfers into investments and card payments, so it
  is the honest, conservative figure, and the words say so.
- **The ruler:** a bar from 0 to at least 12 months (further when the figure or the band needs it), ticks every three
  months, the runway as a dot. When the snapshot has a ratio target whose label contains "runway" (the investing
  feed's "Cash runway"), its band is shaded on the ruler and its aim is a tick, the same marks the Plan page's band
  bars use; the aria text says "Runway: 6.3 months; aim 6, band 4–8".
- **Always:** the cash total and how many accounts hold it.
- Without bank rows (or under two weeks of them, or no outflow at all): no figure, and the words "No bank
  transactions yet to measure the pace."

### 2.2 Money in and out (right, 5 columns)

The last three calendar months of the cash accounts' rows, a pair of bars per month: money in (solid, the cash
grey) and money out (the same grey washed, with a hairline), the figures above the bars, the month under them. A
Table toggle lists every month in the window: Month, In, Out, Net. Without rows: "No bank transactions yet."

### 2.3 Cash (left, 6 columns)

Every cash account, largest first: name and institution, a share bar of all the cash, the balance, the rate. A
balance older than a week says when it is from ("balance from 4 Aug"), since a manual balance can sit for months.

### 2.4 Debt (right, 6 columns)

Every debt, largest balance first, as today (owed, limit, utilization, rate; a credit balance in words), with a
utilization bar in the row and the word "high" in the warn colour from 30 %. A rated balance adds "about $X a
year in interest".

### 2.5 Earning against owing (full width)

The totals row (Cash, Owed, Net, Utilization) and the spread paragraph with the pay-down line, exactly as the
Phase 5 spec worded them. It moves from the top of the page to the bottom.

## 3. The view

`ReservesView` gains:

- `summary`: the header sentence.
- `runway`: `null`, or `months`, `monthly_out`, `days` (the window), `since` (the oldest row's day), and the band
  (`aim`, `low`, `high`, each nullable) from the first ratio target whose label contains "runway".
  The window is from the oldest to the newest row on any cash account, inclusive; it needs at least 14 days and
  some money out.
- `flows`: one entry per calendar month with rows: `month`, `money_in`, `money_out` (positive), ascending.
- `CashLine.share_pct` (of all the cash; `null` when there is none) and `DebtLine.yearly_cost` (`null` without a
  rate or a balance).

Only rows whose account is a cash account count; a card's charges are not cash leaving until the card is paid.

## 4. Where the code goes

- `src/kestrel/views/reserves.py`: the fields above.
- `web/src/pages/reserves/`: `Reserves.tsx` (composition), `RunwayPanel.tsx` (figure + ruler), `FlowsPanel.tsx`
  (bars + table), `CashPanel.tsx` and `DebtPanel.tsx` (the bars and notes), `SpreadPanel.tsx` (retitled).
- `docs/design-system.md`: a Components row for the runway ruler and the in/out bars.
- The reserves fixture is regenerated.

## 5. Testing

- **View:** the runway from a small set of rows with the band from a runway target; none without rows, under two
  weeks, or without outflow; flows per month over cash accounts only; shares and the yearly cost; the sentence
  with and without a runway; the demo has a runway, a band and three months of flows.
- **Page:** the hero figure, the ruler's aria text, and the no-rows words; the bars and the table; the share bars
  and the stale-balance note; the utilization bar and "high"; the spread panel's existing tests under its new
  title; the empty state.
- The screenshot pass on `/reserves` from the demo at 390, 1200, 1280 and 1440 px in both themes.

## 6. Out of scope

Spending categories, budgets, upcoming bills, and any figure that would need the feed to tag a transfer as such.
