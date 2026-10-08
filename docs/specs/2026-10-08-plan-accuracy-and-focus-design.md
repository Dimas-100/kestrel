# The Plan page: accurate to the plan, then focused — design

- **Date:** 2026-10-08
- **Status:** design; built alongside.
- **Parent spec:** [`2026-10-05-plan-page-design.md`](2026-10-05-plan-page-design.md). This spec replaces its §2.2
  (This month) and §2.3 (Allocation against plan), and amends §2.1 (Milestones) and §2.4 (Theses).

## 1. Why

An owner review of the Plan page found two accuracy problems, which this spec fixes before any visual change:

1. **The actions contradicted the plan.** Every off-band target became "Add $X" or "Trim $X", but a plan can
   say that drift is closed with new money only ("contributions converge over time — no rebalancing trades"),
   or that a holding is held and diluted ("below target = revisit, not a buy signal"). kestrel told the owner to
   trim two holdings the plan says never to sell. Separately, the investing feed derived every band as ±25 % of
   the aim, so a sleeve the plan bands at 3–7 % showed as 3.75–6.25 %.
2. **The allocation bars double-counted.** A sleeve row ("Growth core": three symbols) and its own members'
   rows were stacked in one bar, which then added past 100 % and was scaled down, so every segment shrank: a
   holding at 32 % of the account drew as about 25 %.

The rest of the review asked for:

- the monthly goal requests to say how they overlap (a deposit into one account is part of a goal over all of
  them, not on top of it);
- the goals due on one day to show as one labelled cluster;
- targets kestrel can't measure never to read as "Every target sits on plan";
- a more focused page.

## 2. The contract: how a target is brought back

`Target` gains `rebalance`, one of:

| Value | Meaning | Off the band, kestrel says |
|---|---|---|
| `trades` (the default, today's behaviour) | a trade brings it back | under: "Add $X to …"; over: "Trim $X from …" |
| `contributions` | new money only, never a sale | under: "Steer new money to …"; over: "… dilutes as new money goes elsewhere" |
| `hold` | held and diluted: no new money, no sale | under: "Revisit …: a decision, not a buy"; over: dilutes, as above |

The status (on / over / under) stays the plain fact; only the words for what to do change. A source that sends
no `rebalance` keeps today's wording. The investing feed sends each target's policy and, where the plan
gives one, its own band (`min` / `max` per entry in `sizing-targets.json`) instead of the ±25 % default.

## 3. The view

- `TargetRow` gains `rebalance`; `parent` (the id of the multi-symbol row in the same account whose symbols
  include every one of this row's, or null), so a sleeve and its members are never summed together.
  `AccountTargets` gains `untargeted_pct`: the share of the account held in no symbol any of its "%" targets
  names, cash included; null when kestrel can't measure it.
- `Counts` gains `unknown` (targets kestrel can't measure) and `need_trade` (off-band targets whose policy is
  `trades`).
- **The summary** says off-band targets with how many need a trade ("4 targets are outside their bands; none
  needs a trade."), says "Every target sits on plan." only when every target is measured and on plan, and
  otherwise names what it can't measure ("3 of 4 targets on plan; 1 can't be measured yet.").
- **Goals that contain each other.** `GoalRow` gains `part_of`: the ids of other unreached value goals whose
  accounts include every account of this goal (a Roth deposit raises the household's value). And `pace`: when the
  history is reliable, the actual since the window opened against the straight line to the target. The window opens
  on 1 January (of `by`'s year for a deposits goal, this year for a value goal). "Reliable" means every account in
  scope has history from within a week of that day and there are at least eight points since. Otherwise `pace` is
  null and `pace_note` says why.
- **Actions** become `PlanAction` (level, kind, title, why, detail, anchor), ranked; the page shows the first three
  as this month's priorities. The order:
  1. warnings: a thesis on alert, an overdue goal, a `trades` target off its band (largest gap first);
  2. the money a month toward a goal due within a year: the goal whose scope contains the others first. Its `why`
     names the deposits inside it (the demo's "Save into savings this year ($150.00 a month) is part of this,
     not on top of it: $150.00 of the $1,233.78");
  3. a `contributions` target under its band (steer new money there);
  4. theses on watch, as one item;
  5. a `hold` target under its band (revisit);
  6. the targets that dilute, one item per account;
  7. a goal already named inside another's priority ("part of Net worth milestone").

  Home's *Needs you* keeps its wording for `trades` targets and leaves out the ones that close on their own.
  A `contributions` target under its band is a note there.

## 4. The page, top to bottom

1. **This month.** Three numbered priority cards, full width: what, why, the figures, and a link to the place on the
   page that backs it. The rest under "Also this month (n)", closed. Nothing to do: one line, which names the
   targets that can't be measured instead of claiming they are on plan.
2. **Milestones.** The timeline draws the goals due on one day (or within a few pixels) as one cluster: a ring with
   the count and a label above it ("3 goals · 31 Dec 2026"); the tooltip lists each. The next cards group under
   their date. Each card keeps its ring; its what-if slider opens on demand ("Try a monthly amount"). A card with a
   reliable `pace` draws a small chart: the actual solid, the required straight line dotted (the expected
   convention). Later dated goals and the ongoing ones are compact rows. The Passed record shows the newest three;
   the rest sit under "n earlier". The table gains a Pace column (ahead / behind by $X).
3. **Allocation against plan.** One block per account, two abreast on a wide screen. Each target is one row: a
   horizontal chart on the account's shared scale, with the band as a wash, the aim as a dotted tick and the actual
   as a solid bar. The row also carries the figure, the status word and the policy's words. A sleeve's members sit
   indented under it. A line says the share no target covers. The bars are never stacked, summed or normalised.
   A ratio target draws on its own scale. The table view is unchanged plus a Policy column.
4. **Theses.** Exceptions first (alert, then watch), open. The healthy ones sit under "n holding", closed, and the
   not-rated ones under "n not rated", closed.

## 5. Testing

- **View:** each policy's action wording and level; the band from the feed; `parent` for a sleeve's members;
  `untargeted_pct`; the summary with unknown targets; `part_of` and the umbrella action's wording; the ranking;
  `pace` reliable and not; Home's attention by policy.
- **Pure functions:** the timeline clusters; the range-row geometry never normalises (a 32 % actual is 32 % of the
  domain's width); nesting order.
- **Page:** three priorities and the closed rest; the cluster label; the what-if opens on demand; a sleeve's members
  nest; theses exceptions open and the healthy ones closed; the Passed record's newest three.
- The screenshot pass on `/plan` from the demo at 390, 1200, 1280 and 1440 px in both themes.
