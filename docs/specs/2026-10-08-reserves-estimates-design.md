# Reserves: estimates with their definitions — design

- **Date:** 2026-10-08
- **Status:** design; built alongside.
- **Parent spec:** [`2026-10-05-reserves-page-design.md`](2026-10-05-reserves-page-design.md). Its share bars, in/out
  bars and table, ruler and pay-down slider stay; this spec redefines the figures under them and reorders the page.

## 1. Why

The page's building blocks work and its totals reconcile (cash − recorded debt = the difference), but three of its
estimates mislead on real data, and the caveats that would say so are missing or buried:

- **The pace counts moves between your own accounts.** Checking → savings and back, or a Zelle to yourself from one
  bank into another, posts as money out on one cash account and money in on another. Total cash doesn't change and
  nothing was spent, yet the pace rose and the runway fell. On the owner's real rows this inflated the pace by about
  a quarter.
- **The interest figures read as complete when they aren't.** When an APR is on record for only part of what is
  owed, "the highest rate you pay" and "a year of interest costs" describe that part, not the whole.
- **A partial month looks like a full one.** The window starts mid-month and ends today, so the first and last bars
  are a few days' worth beside full months.
- **Freshness and missing data** (an old balance, the last bank row, a card without a limit or a rate) are either
  unsaid or a muted line far from the figure they qualify.

## 2. Definitions

**A move between your own accounts** is a pair of posted rows on two *different* cash accounts, one money out and one
money in, of the same amount to the cent, posted at most 3 days apart, **and corroborated by their words**: both
read as a transfer (the feed's category says "transfer", or the text says transfer, Zelle, "withdrawal to" or
"deposit from"), or one does and the other names the same party (a word of four letters or more in common, past the
words every bank row uses — a Zelle to yourself arrives as your name). Round amounts are common, so the same amount
on the same day alone is not enough: a first build without the words paired a brokerage deposit with an unrelated
transfer in from an account not on file. Pairs are matched closest date first, then a pair at the same bank, each
row in at most one pair. Moved rows are left out of the pace and out of the monthly in/out bars, and each figure says
how much it left out. Money to a card, a brokerage or a person is not a move: it left the cash, so it still counts.
The rule needs no tag from the feed; an unmatched side (the other account isn't one of yours on file) counts.

**The pace** is every remaining outflow on a cash account over the window (oldest to newest cash row, inclusive, at
least 14 days), per day. Income is not netted against it: coverage answers "how long would the cash last if nothing
came in".

**Coverage** is today's cash ÷ the pace per day, rounded *down* to whole days (never overstated), and never below
zero. Under 60 days it reads in days ("4 days"); from 60 on, in months to one decimal. The ruler stays in months, so
a plan's runway band still fits on it.

**A partial month** is a month the window doesn't cover end to end: the first (from the oldest row) and the current
one (to the view's day, "month to date"). Each month carries its first and last covered day.

**Rates on record** is the part of what is owed (positive balances) on lines that carry an APR, and the part of the
cash on accounts that carry an APY. Interest figures are computed on that part only and say so; "the highest rate"
becomes "the highest rate on record".

**Fresh** means a balance or the newest bank row is at most 7 days older than the view's day (the Cash panel's
existing rule). Older ones are called out by name beside the figure they feed, with the warn icon and a word.

## 3. The page, top to bottom

1. **Header** — the view's sentence: the difference ("$X in cash after recorded debts", or "Recorded debts are $X
   more than your cash"), then the coverage with the moves left out.
2. **Where you stand** (full width, the page's *lead* panel: a faint `--acc` wash, an accent-tinted hairline and a 3 px
   accent edge, so it reads as the page's summary and follows the owner's chosen accent) — Cash − Recorded debt =
   Difference as three 30–34 px figures in balanced columns with the operators between them, stacked on a phone; under
   each, its count ("3 accounts", "3 debts on record"); under a hairline, how fresh the balances are ("Balances from
   6–7 Oct") and a warn note naming any older than a week.
3. **Coverage** (7 columns) — the hero in days or months and the run-out day when it is days ("your cash would run
   out around Mon 12 Oct"); a scale in the hero's unit with the coverage as an accent fill and its figure above the
   fill's end: in days, whole weeks (two at least, so 4 days fills a visible part of a 14-day bar) with day ticks up to
   three weeks and a plan's months-aim said in words when it lands past the end; in months, quarters with the band and
   aim drawn. Under it the three assumptions that move the figure most (pace a day, window, what was left out), then
   *How it's worked out* as a closed disclosure: pace per day and month, window, moves left out ("$1,050.00 moved
   between your own accounts (7 transfers)"), what is counted, and that no income is assumed. A warn note when the
   newest bank row is over a week old.
4. **Money in and out** (5 columns) — the last three months' bars; a partial month's label says "to date" (the
   current one) or "from 10 Jul" (the first), and every month's net sits under its label, signed. The table adds
   Days, Net and Moved columns. The subtitle says moves between your accounts are left out.
5. **Cash** (full width, as tall as its rows) — each row leads with its institution's tile (the owner's logo, else
   initials), as the debt cards do; share bars (the bar steps aside under 640 px, the percent stays), balance, rate,
   stale note.
6. **Debt** (full width) — a card per debt (institution tile, balance, utilization bar or "No limit on record", APR or
   "APR not on record", the balance's date), largest first, side by side in one row on a desktop: one track per card,
   three at least (a lone card isn't stretched) and four at most, each 240 px or wider, wrapping below that and one
   column on a phone. The subtitle carries the total utilization and how many lines it covers. *(The first build put
   Cash and Debt side by side at 6 columns; three stacked cards stretched the row to ~700 px beside a 3-row table.)*
7. **Earning against owing** (full width) — a rate-coverage note first when rates are on record for less than all of
   what is owed (warn icon; "Rates are on record for $640.00 of the $1,890.00 you owe (33.9 %)"), naming the lines
   without one; one spread sentence worded "on record"; then *Try paying the {card} from cash*: the slider with the
   amount beside it, three aligned Now → After blocks that move with it (Cash, Coverage, Interest saved a year — the
   now figure muted, an arrow, the after figure large, what changed under it), and the exact table beneath. The view's
   own "Paying … would save …" sentence is no longer repeated above the slider: the saving's block says it.

## 4. The view

- `Runway`: + `unit` ("days" | "months"), `days_cover`, `daily_out`, `through` (the newest row), `moved` and
  `moved_count` (the out side of the pairs in the window), `stale` (the newest row is over a week old).
  `months` is clamped at zero.
- `MonthFlow`: + `start`, `end` (covered days), `partial`, `net`, `moved`.
- `Totals`: + `cash_count`, `debt_count`, `limited_count`, `oldest_as_of`, `newest_as_of`, `stale` (names of
  balances over a week old).
- `rates` (new, `null` with nothing owed and no cash): `owed`, `rated_owed`, `rated_owed_pct`, `unrated` (names of
  lines with a balance and no rate), `cash`, `rated_cash`.
- `summary`: worded as in §3.1.

## 5. Testing

- **View:** a checking ↔ savings move and a cross-bank move left out of the pace and the flows; a move more than 3
  days apart, or to a card, still counts; each row matched once; coverage in days, rounded down, and in months from
  60 days; partial first and current months; rates on record and the unrated names; the stale lists; the sentence
  for a negative difference.
- **Page:** the top row's three figures and freshness; the coverage hero in days and its assumptions; the partial
  label and the net under each month; the debt cards with "No limit on record" / "APR not on record"; the rate note;
  the before → after figures.
- The screenshot pass on `/reserves` from the demo at 390, 1200, 1280 and 1440 px in both themes.

## 6. Out of scope

A cash-balance trend (until the history behind it is reliable), a donut, spending categories, and tagging transfers
in the feed.
