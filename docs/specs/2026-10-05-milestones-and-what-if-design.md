# Milestones, and what-if — design

- **Date:** 2026-10-05
- **Status:** design; built alongside, milestones first, then what-if.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§4 pages, §5 visual system).
  Builds on the Plan ([`2026-10-05-plan-page-design.md`](2026-10-05-plan-page-design.md)), Reserves and Activity
  redesigns of the same day.

## 1. Why

The owner asked for a dashboard that feels personal and is enjoyable to open. The clearest signal of what the app is
for came in their own words: "almost at 15,000, let's go." kestrel already holds everything needed to answer that
feeling, in the history it draws and the goals it tracks. Two additions, both read-only, both derived from data the
pages already have: moments worth noticing (milestones), and questions the owner can ask the numbers (what-if).

## 2. Milestones

### 2.1 The next round number

A round number is a multiple of the *step* for the figure's size: half the power of ten below it. For $14,215 the
step is $5,000 and the next round number $15,000; for $168,278 it is $50,000 and $200,000; for $1,421 it is $500
and $1,500.

- **Home, Net worth.** Under the hero's "you own · owe" line, a second line: "$387 to $15,000". On the chart, the next
  round number as a dotted reference line in the reference grey with its own legend entry, so the eye sees how close
  the line is to it. The reference line is drawn only when the number sits within the chart's own range plus a
  quarter of it, so a far-off number never squashes the history.
- **Crossing it.** When the history's last point is at or above a round number the point before it was below, Home
  says so for that day: a chip in the Net worth panel's corner, with the check icon, "Passed $15,000 today". Nothing
  is stored: the next day the chip is gone, and the record below keeps the date.

### 2.2 The record

On Plan, under the Milestones timeline, a **Passed** list: every round number the net-worth history crossed, with
the first day it did (the last eight), and every goal reached, with the day its scope first met the target. Newest
first. A goal with no history, or a deposits goal, has no day: it is listed as reached without one.

`GoalRow` gains `reached_on` (the first day the scope's value met the target, from the account history; null
without it or for a deposits goal), and the Plan view gains `passed` (date, label, kind: round or goal).

### 2.3 The reveal

The progress rings draw their arc once when the page opens, over about 600 ms, the one orchestrated moment the
design system allows a page; a reached goal's ring ends in the check and its card says "Reached 12 Oct". Under
`prefers-reduced-motion: reduce` the arc is simply there.

### 2.4 The streak

Activity's week panel says, in its subtitle, how many weekdays in a row every job has run: "Every job has run for 11
weekdays in a row." Counted back from the last finished weekday across the runs the snapshot holds: a day counts
when every job the grid knows by then ran that day and nothing failed or ran late. A job is judged only from the
first day it appears, so a feed that reports a job's latest run alone (investing's refresh) never breaks the days
before it, and the count stops where the history ends. 0 is said as "The streak starts with tomorrow." The view
supplies `streak_days`. For the streak to mean anything the feeds must carry the week: webull's feed sends every run
of the past week per job (2026-10-05), not only the latest.

## 3. What-if

Read-only arithmetic in the page, from figures the view already sends. Nothing is written anywhere, and the page
says what it assumes.

### 3.1 Reserves: pay down the dearest card

In *Earning against owing*, under the pay-down sentence, a range input "Pay $X of the {card} from cash", from 0 to
the smaller of the card's balance and all the cash, starting at the view's own pay-down figure. Beside it, live:
"saves about $Y a year · leaves $Z in cash", Y = X × (the card's rate − the best cash rate) / 100, Z = cash − X.
Shown only when the view sends a pay-down (a rated card balance, cash, and the card dearer than the cash earns).

### 3.2 Plan: a monthly amount toward a goal

On each of the next goals' cards, a range input "a month", from 0 to three times the view's straight-line amount
(or $1,000 without one), starting at the view's amount. Beside it, live: "reaches {target} by {month year}", the
months being the remaining amount over the monthly amount, rounded up, from today; at 0 a month, "never at this
pace". For a value goal the line keeps its caveat, "before any market growth".

## 4. Where the code goes

- `src/kestrel/views/home.py`: `NetWorth.next_round`, `to_go`, `passed_today`; a `round_step` helper.
- `src/kestrel/views/plan.py`: `GoalRow.reached_on`, `PlanView.passed`.
- `src/kestrel/views/activity.py`: `streak_days`.
- `web/src/pages/home/NetWorthPanel.tsx`: the line, the reference series, the chip.
- `web/src/pages/plan/MilestonesPanel.tsx`: the Passed list, "Reached {date}", the what-if range;
  `ProgressRing.tsx`: the reveal; `whatif.ts` (pure: months to reach, the date).
- `web/src/pages/activity/WeekPanel.tsx`: the streak subtitle.
- `web/src/pages/reserves/SpreadPanel.tsx`: the pay-down range.
- `docs/design-system.md`: the reference-line note and the range input.
- Fixtures regenerated.

## 5. Testing

- **Views:** the step and the next round number across sizes; to-go; passed today only on a crossing (not when
  the previous point was already above, not without a previous point); the record's dates and order; `reached_on`
  from history and null for a deposits goal; the streak with a failed day, a weekend, and no runs.
- **Pure (vitest):** months to reach and the date; never at zero.
- **Pages:** the to-go line and the reference legend; the chip on a crossing and its absence otherwise; the Passed
  list; "Reached {date}"; the streak subtitle; the ranges' live text on Reserves and Plan; reduced motion leaves the
  ring static (the class is absent).

## 6. Out of scope

The monthly letter, pins and shortcuts, and any figure that would need storage: everything here is recomputed from
the snapshot on every load.
