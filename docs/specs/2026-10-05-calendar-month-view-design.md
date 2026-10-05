# The Calendar as a month — design

- **Date:** 2026-10-05
- **Status:** design; built alongside.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§4 pages, §5 visual system).
  Changes the Calendar page that [the Phase 5 spec](2026-09-27-phase-5-one-dashboard-design.md) §4.4 defined.

## 1. Why

The Calendar page answers "what's coming up, or just happened, for what I hold?" with two lists: the weeks ahead
and the last 90 days. A list says *what* well and *when* badly: to see whether next week is busy, or how far off
the next earnings date is, the reader has to read dates one by one. A month grid shows the shape of the month at a
glance, and the lists stay one click away as the grid's table view.

Nothing new arrives from a source. The grid is another arrangement of the same event rows the page already has,
so the contract, the connectors and the server view do not change.

## 2. The page

Above the panels, the counts by kind on the left and two segmented controls on the right: **View** (Month · List)
and **Kind** (All · Earnings · Filing · Insider · Dividend · Other). Month is the default. The kind filter applies to
whichever view is showing.

**List** is the page as it was: Upcoming (by week) and Recent (the last 90 days), unchanged.

**Month** is two panels:

- **The month** (8 columns): the month's name as the title ("October 2026"), a Previous / Next pair and a Today
  button on the right, and the grid (§3). Previous and Next are disabled at the ends of the range the events cover.
  Today jumps to the current month and selects today.
- **Selected day** (4 columns): the selected date as the title ("Mon 5 Oct"), how many events it has as the
  subtitle, and those events as the same rows the lists use (symbol, title, kind chip, Held, detail, Source link).
  A day with nothing says "Nothing on this day." Today is selected when the page opens.

Under 1180 px the two panels stack, the month first.

## 3. The grid

- A real `<table>` with `role="grid"`: seven column headers, Monday to Sunday (the server already groups weeks from
  Monday), and one row per week of the month, five or six. Days that belong to the neighbouring months fill the
  first and last rows muted and are not interactive.
- A day cell is a button. It shows the day number (mono) and up to three events, each as a small mark carrying the
  kind's first letter (E, F, I, D, O) beside the symbol. A fourth event and beyond collapse to "+n". The letter is
  the cue, never a colour: all marks share the ink colour. An event for something held has a filled mark and a
  semibold symbol; one that isn't held has an outlined mark. Screen-reader text names the kind and says "held".
- Today's number carries a 1 px accent ring and the text "today" for screen readers. The selected day's cell is
  raised (`--panel2` with an inset `--line2` hairline) and marked `aria-selected`.
- Each button is labelled "Mon 5 Oct, 2 events" so a screen reader hears the day without entering it.

**Range.** The months run from the earlier of the first event's month and today's month to the later of the last
event's month and today's month. With no events at all the page keeps its existing empty state and shows no grid.

## 4. Keyboard

The grid is one tab stop: the selected day's button is in the tab order, the rest are not. Inside it:

| Key | Moves |
|---|---|
| ← → | one day |
| ↑ ↓ | one week |
| Home / End | the week's Monday / Sunday |
| PageUp / PageDown | the same day a month earlier / later, when that month is in range |
| Enter / Space | selects the focused day (a click does the same) |

Moving past the month's edge turns the page to the neighbouring month when it is in range, and stays put when it
is not. Focus follows the move.

## 5. Phone (390 px)

Seven columns in 358 px leaves about 48 px per cell, too narrow for a symbol. Under 640 px a cell shows the day
number and the kind marks only, in a row, with "+n" beyond three; the symbols appear in the Selected day panel,
which is one tap away and sits right under the grid. Cells are at least 44 px tall. No panel overflows and the
page never scrolls sideways.

## 6. Where the code goes

- `web/src/pages/calendar/MonthView.tsx`: the pure date helpers (the month a date is in, a month's grid of days,
  stepping months, the range the events cover, events by day) and the `MonthView` component (grid + keyboard).
- `web/src/pages/calendar/Calendar.tsx`: the View control, the two month panels, and the lists as before. The
  event row moves out to `EventItem.tsx` so both views render the same row.
- `web/src/styles/tokens.css`: the `.cal` block (cells, marks, the phone rule), with tokens only.
- `docs/design-system.md`: a Components row for the month calendar.

## 7. Testing

- **Pure functions (vitest):** a month's grid starts on the Monday on or before the 1st and ends on the Sunday on
  or after the last day (five rows for October 2026, six for a month that needs them); stepping across a year end;
  the range the demo events cover (July to November 2026 with today 2026-09-25); events grouped by day.
- **The grid:** seven column headers and `role="grid"`; the demo's October shows COST on the 5th; a day with four
  events shows three and "+1"; the held mark and the kind letter carry screen-reader text; Previous is disabled on
  the first month and Next on the last; → moves focus one day, PageDown turns the month, Enter selects.
- **The page:** Month is the default and the Selected day panel shows today with "Nothing on this day." when it
  has none; selecting a day lists its events; the kind filter narrows the grid; List shows Upcoming and Recent as
  before (the existing tests, now behind the List control); the empty state is unchanged.
- **The screenshot pass** (the check jsdom can't do): `/calendar` from `kestrel serve --demo` at 390, 1200, 1280 and
  1440 px in both themes: no overflow, no sideways scroll, and the phone cells readable.

## 8. Out of scope

A week or agenda strip, dragging between months, and any event that isn't already in the snapshot. Nothing is
written anywhere: the selected day and the view live in the page's state only.
