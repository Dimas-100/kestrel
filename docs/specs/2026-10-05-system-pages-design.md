# The system pages, Activity and Settings — design

- **Date:** 2026-10-05
- **Status:** design; built alongside, Activity first, then Settings.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§4 pages, §5 visual system).
  Reshapes the two pages [the Phase 5 spec](2026-09-27-phase-5-one-dashboard-design.md) §4.6 and §4.7 defined;
  what they show is unchanged, how it reads is not.

## 1. Why

Activity answers "what ran, what is due, what failed?" with three lists at one weight and no clock: the eye can't
see when today's runs happen, where *now* is, or whether a job ran every day this week. Settings is a column of
label-value rows and a six-column table: correct, and flat. Both should read like the owner's own system: the day
at a glance, the week's reliability at a glance, and the owner's own choices shown as what they are.

## 2. Activity

**Header.** "System · Activity" and a sentence the view writes: today's runs ("Every run so far today is done." /
"1 run failed or late today." / "No runs today."), the next one ("Next: Evening suite at 17:30."), the sources
("Every source is fresh." / "1 source is stale or failing."), and the alerts when there are any ("1 alert.").

### 2.1 Today (full width)

- **The day line.** A hairline for the day in the profile's time zone, ticks at 00, 06, 12, 18 and 24, each of
  today's runs as its status icon at its time (the same icons and colours Home's Today panel uses: check for done,
  clock for late, alert for failed, a ring for due), and the *now* rule: a 1 px accent line with the time, the
  design system's own mark. Hover or ← → show a tooltip with the label, time, status and detail.
- **The list** under it: today's runs in time order with the status word, as today's rows already read, so the
  line always has its table beside it. "Next: {label} at {time}" leads the list when a run is still due.
- Without runs today: "Nothing has run yet today." and the next run when there is one.

### 2.2 The week (left, 7 columns)

A grid, as a real table: one row per job (its label), one column per day from a week ago to today, a cell per
(job, day) with the status icon and the word for screen readers; a blank where the job had no run that day. When
a job ran more than once in a day the cell shows the worst of them (failed, then late, then due, then paused, then
done). Rows are in the order the jobs run through the day. This is the reliability view: a column of checks is a
good week; a clock or an alert stands out.

### 2.3 Alerts (right, 5 columns)

As today: every alert by level, with the icon tile, the level word, the title, the detail and the link.

### 2.4 Sources (full width)

One card per source instead of the table: the status icon and word, the label, the kind as a chip, "updated 2
minutes ago · stale after 36h", the last success day and time in the profile's zone, and the detail (a failed
source's reason). Three abreast, stacked on a phone.

### 2.5 The view

`ActivityView` gains `summary` (the sentence), `next_run` (the earliest run still due at or after now, or null) and
`week` (one row per job: `label`, `cells` of `{date, status}` for the eight days, `status` null where nothing ran).
`days`, `counts`, `alerts` and `sources` stay as they are: the list under the day line and the week grid's table are
built from them.

### 2.6 The demo

The demo's runs cover the past week, not just today, so the grid has something to say: every job done each
weekday, one failed run and one late run in the week.

## 3. Settings

**Header.** "System · Settings" and "Read-only: everything here comes from {profile}."

### 3.1 You (left, 7 columns)

The owner's name as the panel's hero, then the look as a definition list whose values show what they are: the
theme with its icon (sun, moon, or both for *system*), the accent with a swatch in that accent, the gain and loss
colours with the two swatches, density, currency, and the time zone with the current time there.

### 3.2 About (right, 5 columns)

The benchmark (symbol and label), the profile in use (or "demo data"), the contract version and kestrel's
version, as a definition list.

### 3.3 Sources (full width)

The same source card as Activity, with what the page is for: what the source reads (a URL without its query, a
path, or the command's file name and arguments), its timing ("stale after 36h · reuses for 1m · times out at
30s"), the name of its token variable (never its value), and its live status with the last success. Three
abreast, stacked on a phone. Never a machine path, never a secret: the view's rules are unchanged.

## 4. Where the code goes

- `src/kestrel/views/activity.py`: `summary`, `next_run`, `week`. `src/kestrel/connectors/demo.py`: a week of runs.
- `web/src/components/SourceCard.tsx`: the shared card.
- `web/src/pages/activity/`: `Activity.tsx`, `TodayPanel.tsx` (the day line + list), `WeekPanel.tsx`,
  `AlertsPanel.tsx`, `SourcesPanel.tsx`; `dayline.ts` (pure: the x of a time, the ticks).
- `web/src/pages/settings/Settings.tsx` with the definition lists and the cards.
- `docs/design-system.md`: Components rows for the day line, the week grid and the source card.
- The activity, home and settings fixtures regenerated.

## 5. Testing

- **View:** the sentence's variants; the next run; the week grid's rows, order, blanks and the worst-of rule;
  the demo's week.
- **Pure (vitest):** a time's x on the day line in the profile's zone; the ticks.
- **Page, Activity:** the sentence; the day line's icons and the now rule; the list and the next line; the grid's
  cells with words; a failed run with its word; a source card's detail and its last success in the profile's zone;
  the empty states; loading and error.
- **Page, Settings:** the name hero, the look values and swatches, the current time in the zone; the about rows; a
  source card with its program file name, timing and token name only; never a machine path or a token value.
- The screenshot pass on `/activity` and `/settings` from the demo at 390, 1200, 1280 and 1440 px in both themes.

## 6. Out of scope

Editing anything (kestrel is read-only), run logs beyond what a feed sends, and a source's history.
