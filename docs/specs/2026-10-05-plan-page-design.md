# The Plan page, as your plan — design

- **Date:** 2026-10-05
- **Status:** design; built alongside.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§4 pages, §5 visual system).
  Reshapes the Plan page that [the Phase 5 spec](2026-09-27-phase-5-one-dashboard-design.md) §4.2 defined; the
  targets, theses and goals data and their rules are unchanged.

## 1. Why

The Plan page answers "am I on plan?" with three lists at one weight: targets, theses, goals. It is the only money
page with no chart, no hero and no sense of time, so nothing on it reads as *yours* or as *what's next*. The owner
asked for a page that is more personal and more appealing to look at.

The page keeps every fact it shows today and changes what leads: the goals in time, then what to do this month,
then how each account sits against its plan, and the theses last. Nothing new arrives from a source.

## 2. The page, top to bottom

**Header.** "Money · Plan" and a summary the view writes in words: how many goals are ahead, which is next and how
far along it is, then the targets off plan and the theses that need a look. "Every target sits on plan." when none
is off. The empty state is unchanged.

### 2.1 Milestones (full width)

The goals in time.

- **The line.** A timeline from today to the furthest dated goal, with year ticks. Months are placed on a
  logarithmic scale, `ln(1 + months) / ln(1 + furthest)`, so the next year has room and 2064 still fits. Each dated
  goal is a dot on the line (a check once reached); an overdue, unreached goal sits at today's end in the warn colour
  with the word "overdue". Hover or ← → show a tooltip: label, progress, current / target, by, the monthly line.
- **The next three.** Under the line, cards for the three nearest dated goals that aren't reached: a progress ring
  (the arc is the share reached; the percent sits inside, mono), the label, the scope, "current / target", "by
  {date} · {n} months", and the straight-line monthly amount said for what it is (deposits, or before any market
  growth). A reached goal's ring is full with a check; an overdue one says "was due {date}".
- **Ongoing.** Goals with no date, as one compact row each: label, scope, a progress bar, current / target.
- **Table.** A Chart / Table toggle; the table lists every goal: Goal, Scope, Progress, Current, Target, By, Months
  left, Monthly. A goal kestrel can't see ("—" and why) keeps its reason in the Progress cell.

This panel replaces Goals. The ring and the dots use the accent for progress (the design system's fill) and the
status colours only with a word or an icon beside them.

### 2.2 This month (left, 5 columns)

What to do, worked out from the data, as items like Home's *Needs you* (icon tile, caps level word, a title, a line
of detail), newest-serious first:

| From | Level | Title | Detail |
|---|---|---|---|
| a target under or over plan, gap in money | warning | "Add $212 to XLP in Roth IRA" / "Trim $390 from XLV in Roth IRA" | "16.0% held · aim 20.0% · band 18–22%" |
| a target off plan, gap in points or ratio | warning | "XLP is 4.0 pts under its band in Roth IRA" | the same figures |
| a thesis on alert | warning | "Review HD: thesis on alert" | its first reason |
| a thesis on watch | note | "Look at XLE: thesis on watch" | its first reason |
| a goal overdue and unreached | warning | "Household $20k was due 31 Dec 2026" | "62% there" |
| a dated, unreached goal due within twelve months | note | "Put about $1,250 a month toward Save into savings this year" | "to reach $1,800 by 31 Dec 2026 · 75% there" |

With nothing to do: a check and "Nothing to do this month: every target is on plan, every thesis holds, and no goal
is due within the year."

The view builds this list (`actions`); Home's own *Needs you* wording is untouched.

### 2.3 Allocation against plan (right, 7 columns)

One block per account that has percent targets, off-plan accounts first:

- The account's name (a link to its page) and "{on} of {n} on plan".
- **The actual bar:** a stacked bar of the targets' actual shares in the account's category hue (long-term slate,
  trading rufous), segments split by 2 px gaps in the panel colour, the remainder in the neutral cash grey as
  "Other". A segment prints its label and percent inside when it is wide enough; otherwise the legend carries it.
- **The aim bar,** under it: the aims as dotted outlines (the *expected* convention), the same order and scale. A
  target with a band and no aim shows its band's middle, dotted, and the legend says "band 15–25%".
- **The legend:** one line per target: label (symbols), "actual → aim (band)", and the status word; "Under" and
  "Over" in the warn colour with the gap in words ("$212 under the low end", "4.0 pts over the high end").
- A ratio target, or one with no account, can't be a share: it keeps its band bar as a row under "Other targets".
- **Table.** The toggle's table: Target, Account, Actual, Aim, Band, Status, Gap.

### 2.4 Theses (full width)

The same rows, grouped alert → watch → ok → not rated, a health strip of chips at the top ("1 alert · 1 watch · 2 ok
· 9 not rated"), the symbol's logo when the owner has one, and the held value beside "held in …". The "Wrong if…"
disclosure stays.

## 3. The view

`PlanView` gains `summary` (the header sentence) and `actions` (§2.2, as the existing Attention shape with an empty
link). Everything else the page needs it computes from the rows it already receives: timeline positions, the next
three goals, the bar segments.

## 4. Where the code goes

- `src/kestrel/views/plan.py`: `summary`, `actions`.
- `web/src/pages/plan/`: `Plan.tsx` (composition), `MilestonesPanel.tsx` + `timeline.ts` (pure: months between,
  the log position, year ticks, the next three), `ProgressRing.tsx`, `ThisMonthPanel.tsx`, `AllocationPanel.tsx` +
  `allocation.ts` (pure: the segments), `ThesesPanel.tsx` (regrouped). `GoalsPanel.tsx` goes; its `monthlyText`
  moves to `timeline.ts`. `PlanBar.tsx` stays for the ratio rows and the table's gap column.
- `docs/design-system.md`: Components rows for the milestone timeline, the progress ring and the allocation bar.
- The plan fixture is regenerated.

## 5. Testing

- **View:** the summary's variants (goals ahead and the next; no goals; nothing off plan); every action row of §2.2,
  their order, the empty list; Home's attention items unchanged.
- **Pure functions (vitest):** the log position is 0 at today, 1 at the furthest, and gives three months more than a
  fifth of the line against forty years; year ticks fall on 1 January; the next three skip reached goals; segments
  sum to at most 100 with "Other" as the remainder and an aim of the band's middle when there is none.
- **Page:** the header sentence; the next three cards with their rings and the table toggle; This month's items by
  level and its empty line; one allocation block per account, off-plan first, with the legend's gap words and the
  table; the theses chips and order; the existing gap-wording, overdue and "—" tests, moved to where those strings
  now show.
- The screenshot pass on `/plan` from the demo at 390, 1200, 1280 and 1440 px in both themes.

## 6. Out of scope

Editing targets, theses or goals from the page (kestrel is read-only), goal history over time (no source records it
yet), and any new data from the feeds.
