# kestrel design system — Graphite

This is the single source of truth for how kestrel looks. The web app's `src/styles/tokens.css` implements these
tokens. The mockups in [`design/mockups/`](design/mockups/) are drawn from them; open any of those files in a
browser.

**Principles**
1. **The data is the colour.** The chrome is graphite neutrals and one accent. Colour appears only where it
   carries meaning.
2. **One encoding for money state everywhere.** Real is solid, paper is hatched, and expected is dotted (see below).
3. **Never colour alone.** Every colour cue is paired with a sign, an icon, a label, a pattern or position.
4. **Quiet structure.** Structure comes from 1-px hairlines, not shadows, glow or gradients. Motion appears only for state changes.
5. **Plain English.** Every panel title is a question or a noun a non-trader understands.

## Tokens

The CSS custom properties live on the app root. Dark is the default; light has full parity. The theme follows the
system setting unless the profile or the toggle picks one.

### Surfaces and ink

| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | `#0B0C0E` | `#F2F3F5` | page |
| `--side` | `#0E0F12` | `#F8F9FA` | sidebar, phone app bar and tab bar |
| `--panel` | `#121418` | `#FFFFFF` | panels (the chart surface) |
| `--panel2` | `#181B20` | `#F5F6F8` | raised inside a panel: selected, tooltip, callout |
| `--line` | `#22262C` | `#E3E5E9` | hairlines, gridlines, table rules |
| `--line2` | `#2E333A` | `#D3D7DD` | stronger hairline: controls, zero baselines |
| `--ink1` | `#ECEEF1` | `#0F1114` | primary text and the net-worth line |
| `--ink2` | `#A7ADB6` | `#4A5059` | secondary text |
| `--ink3` | `#7D848E` | `#666D77` | muted text, axis labels |
| `--logo-plate` | `#EEF0F3` | `#FFFFFF` | the light backing behind an owner-supplied logo (brand marks are drawn for white); never text or data |

Text contrast measured on `--panel` (WCAG):
- **Dark:** ink1 15.9, ink2 8.2, ink3 4.9.
- **Light:** ink1 18.9, ink2 8.1, ink3 5.2.

Muted text on the sidebar background is 5.1 (dark) and 5.0 (light). Every text colour meets AA (4.5:1).

### Accent

This is the profile setting `app.accent`. It is used for the brand mark, the active navigation icon, the *now* line, the
selected tab underline, focus rings, links and progress fills. It is **never** used as a data series.

| Accent | Dark `--acc` / `--acc-ink` | Light `--acc` / `--acc-ink` |
|---|---|---|
| **rufous** (default) | `#D46C38` / `#E3875A` | `#C45A24` / `#A9481A` |
| slate | `#5B93DB` / `#7FAAE3` | `#2F6DB5` / `#255A97` |
| mono | `#ECEEF1` / `#ECEEF1` | `#0F1114` / `#0F1114` |

`--acc-ink` is the text version. Its contrast is 6.9 on the dark panel and 5.8 on the light one.

### Data series

There are two hues, taken from the kestrel's own plumage. Everything else stays neutral.

| Token | Dark | Light | Meaning |
|---|---|---|---|
| `--s1` | `#5B93DB` slate | `#2F6DB5` | long-term money |
| `--s2` | `#D46C38` rufous | `#C45A24` | trading money, and the strategy's own marks |
| `--s3` | `#8A9099` | `#9AA0A8` | cash (neutral on purpose: uninvested) |
| `--ref` | `#7D848E` | `#666D77` | reference lines: benchmark, backtest, expected band |

Validated with the data-viz palette validator, adjacent pairs:
- **Dark (on `#121418`):** passes every check. Lightness band, chroma, CVD ΔE 22.8 (protan), normal-vision ΔE 26.1, contrast ≥ 3:1.
- **Light (on `#FFFFFF`):** passes every check. CVD ΔE 21.4, normal-vision ΔE 27.8.

A third or later categorical series is not a new hue. It folds into "Other" or moves to small multiples.

### Gains and losses

This is the profile setting `app.gain_loss`.

| Mode | Dark up / down | Light up / down |
|---|---|---|
| **green-red** (default) | `#4CC38F` / `#EA5B60` | `#11845A` / `#D1363B` |
| blue-orange | `#5B93DB` / `#D46C38` | `#2F6DB5` / `#C45A24` |

Green/red measures CVD ΔE 7.9 (deutan), which sits in the 6–8 band. That is legal **only with secondary encoding**, so every
delta always carries a sign and ▲/▼, and a loss is never shown by colour alone. Text contrast:
- **Dark:** 8.4 / 5.4.
- **Light:** 4.7 / 4.9.

Blue-orange is the colour-blind-safe choice. In that mode, gains and losses share hues with the data series, so the
sign and arrow carry the meaning.

### Status

| Token | Dark | Light | Always with |
|---|---|---|---|
| `--good` | `#4CC38F` | `#11845A` | check icon |
| `--warn` | `#E8B84B` | `#9A6700` | clock or alert icon + "Warning" |
| `--serious` | `#EC835A` | `#C2562A` | shield icon + "Serious" |

A status colour is never used as a series colour.

## Money state: real, paper and expected

This is the one convention that matters most. It is identical on every chart, badge and row.

| State | Fills (bars, marks, slots, badges) | Lines |
|---|---|---|
| **Real** money | solid | solid 2 px |
| **Paper** money | 45° hatch: 1.5 px ink every 4 px, with a 1.25 px inset outline | dashed `5 3.5` |
| **Expected**, benchmark or backtest | dotted outline `1.5 2.5` with a 4–6 % ink wash | dotted `1.5 3.5`, round caps |

The book mark is a 12 px square in this encoding and appears next to every book name. The money badge is the mark
plus the word (REAL / PAPER), so it reads in greyscale and print too.

## Typography

- **UI:** Geist, weights 400, 500 and 600.
- **Numbers:** Geist Mono, weights 400, 500 and 600, with `font-variant-numeric: tabular-nums` in tables and axes.
- **Numbers inside a sentence** (page summaries, panel subtitles, notes, a stat block's second line) stay in Geist with tabular figures: mono mid-sentence reads as a glitch. `p .num`, `.prose .num` and `.panel-sub .num` do this.
- The hero figure uses the sans with proportional figures, and its cents are dimmed.
- Both faces are self-hosted in the app. The static mockups load them from Google Fonts.
- Fallbacks: `ui-sans-serif, system-ui` / `ui-monospace`.

| Role | Size / weight |
|---|---|
| Hero figure | 48 px / 600, tracking −0.035em (phone 38 px) |
| Page title | 28 px / 600, tracking −0.025em |
| Greeting name | 26 px / 600 |
| Panel title | 14 px / 600 |
| Body | 14 px / 400 (13 px in dense lists) |
| Secondary line | 12 px, `--ink3` |
| Label (caps) | 11 px / 500, uppercase, tracking 0.08em, `--ink3` |
| Axis and tick | 11 px mono, `--ink3` |

## Layout and spacing

- **Base unit:** 4 px. Spacing steps are 4 · 8 · 12 · 16 · 20 · 24 · 32.
- **Desktop shell:** a 256 px sidebar, then the main column with 32 px side padding and a 12-column grid with 16 px gaps (1120 px of content at 1440).
- **Panels:**
  - 1 px `--line` border, radius 10, padding 20 (14 in compact density).
  - Heights are fixed per row, so grids stay aligned.
  - Panel content must never overflow; the screenshot check enforces this.
- **Table rows:** 56 px (44 px compact), with a hairline between rows and none after the last.
- **Radii:** 5 (chips inside controls), 7 (buttons, tooltips), 9–10 (cards, panels), 999 (pills).
- **Phone (390 px):** 16 px gutter, stacked panels, a 56 px app bar, and a 76 px bottom tab bar. Touch targets are ≥ 44 px.
- **Elevation:** none, except tooltips and popovers (`0 8px 24px rgba(0,0,0,.28)`).
- **Motion:** 150 ms ease-out on state changes only. Nothing animates on load. `prefers-reduced-motion` turns motion off.

## Components

| Component | Notes |
|---|---|
| **Sidebar** | Brand mark and name, collapse button, greeting (name, date and time), grouped nav (caps group labels, 36 px items, active item raised with an accent icon), Sources block pinned to the bottom |
| **Top bar** | Breadcrumb · page controls · "Updated HH:MM" (each source's own age is in the sidebar's Sources block) · refresh · theme |
| **Segmented control** | 2 px inset track. The selected segment is raised (`--panel2` with an inset hairline) and uses `aria-pressed`. |
| **Panel** | Title plus optional one-line subtitle, legend or controls on the right, and a Chart / Table toggle on every chart |
| **Stat block** | Caps label, then the value (mono), then a muted second line (percent or context) |
| **Book mark / money badge** | See *Money state* above |
| **Chip** | Pill with an optional mark or icon, 12 px text |
| **Institution tile** | 28–32 px rounded square leading an account row: the owner's own logo on `--logo-plate` with a `--line` hairline when their logo folder has one, else the institution's initials on a wash of the category colour. Decorative (`aria-hidden`): the row names the institution in words. A holding row puts a 20 px logo beside its symbol only when one exists. Logos are never fetched or committed. |
| **Attention item** | 32 px icon tile in the status colour, caps level label, title, one line of detail, and a link to the page that resolves it |
| **Timeline row** | Time (mono), done/due icon, title and detail. The *now* line is a 1 px accent rule with a "NOW" label. |
| **Progress bar** | 8 px track (`--panel2` + inset hairline) with an accent fill, and a label with "n / target" |
| **Month calendar** | A real table with `role="grid"`: seven weekday columns, one row per week, a button per day of the month (the neighbouring months' days muted and inert). A day shows its number (mono; today ringed in the accent) and up to three events as a 14 px letter mark (E, F, I, D, O for the kind; filled when held, outlined when not) beside the symbol, then "+n". The selected day is raised (`--panel2` + inset `--line2`). One tab stop; arrows, Home/End and PageUp/PageDown walk it. Under 640 px the symbols drop and the marks sit in a row; cells stay 44 px tall. |
| **Milestone timeline** | A hairline from today to the furthest dated goal, months on a log scale (`ln(1 + months)`) so the next year has room and 2064 still fits, year ticks thinned to stay readable, a 12 px dot per goal (accent; `--good` once reached; `--warn` with the word "overdue" at today's end). One tab stop; ← → walk the dots; a tooltip carries the figures. Its table view lists every goal. |
| **Progress ring** | 64 px, a 6 px track (`--panel2` + hairline) and an accent arc for the share reached; the percent sits inside in the sans at 600. A reached goal's ring is full in `--good` with the check; the word beside the ring, never the colour, says reached or overdue. |
| **Allocation bar** | Two 20 px bars per account: what is held, as segments in the account's category hue split by 2 px of panel with the remainder in `--s3` as Other, and under it the aims as dotted outlines (the *expected* convention). A segment under 12 % carries its label in the legend only. Status words stay in the legend. |
| **Runway ruler** | A 10 px track from 0 to at least 12 months with a tick every three, the runway as a 12 px accent dot; a runway target's band shaded in `--line2` with its aim as a 2 px tick, the same marks as the Plan band bars. The hero figure above it is the months in the sans at 600, the pace under it in words. |
| **In / out bars** | A pair of bars per month: money in solid in `--s3`, money out the same hue washed to 45 % with a hairline, the figures above the bars in mono, the month under them. One series hue: in and out differ by fill, and the legend says which is which. |
| **Day line** | A hairline for the day in the profile's zone with ticks every six hours, each run as its status icon at its time (the Today panel's icons and colours), and the *now* rule: a 1 px accent line with the time above it. One tab stop; ← → walk the runs; a tooltip carries the run and its detail. Its table is the list beneath it. |
| **Week grid** | A real table: one row per job, one column per day from a week ago to today, the status icon with its word for screen readers in each cell, a middle dot and "no run" where the job didn't run. The worst status of a day's runs is the cell's. |
| **Source card** | A hairline card: the label, the kind as a chip, the status icon with its word, what the source reads (never a machine path) and its token variable's name (never its value), "updated 2 minutes ago · stale after 36h", the last success day and time in the profile's zone, and the detail. Three abreast, stacked on a phone. |
| **Room-to-stop bar** | 56 × 6 px track. The fill is proportional to the distance to the stop; it is `--warn` under 8 % and `--ink3` otherwise. |

## Charts

The rules follow the data-viz method (form first, colour last, validated palette):

- **Marks:**
  - Lines are 2 px with round joins. Reference lines are dotted.
  - Bars are ≤ 24 px wide, with a 4 px rounded data end and a square baseline.
  - Markers are ≥ 8 px with a 2 px ring in the panel colour.
  - Area washes are the series hue at 4–10 % opacity.
- **Grid:**
  - Horizontal gridlines only, as 1 px `--line` hairlines. The zero baseline uses `--line2`.
  - Value axes sit on the right in finance-style charts.
- **One y-axis per chart.** Two measures go in small multiples on a shared x-axis (for example, price over RSI).
- **Labels:**
  - A legend whenever there are two or more series.
  - Direct labels only where they don't collide, such as the endpoint or the one series the story is about.
  - Label text uses ink tokens, never the series colour.
- **Hover:**
  - A crosshair and tooltip on lines, and a per-mark tooltip on bars and cells.
  - The tooltip is a `--panel2` card with a date or bucket heading and one row per series (label on the left, mono value on the right).
- **Table view:** every chart has one, and it is the accessible path for anything the hover shows.
- **Expected bands** are 95 % ranges: expected ± 1.96 · sd / √n. They narrow as trades add up, which is what makes "is it behaving?" readable.

## Numbers and copy

- A true minus sign (−) is used for negatives. Deltas always carry a sign and ▲/▼.
- Currency shows cents in tables and heroes. Compact forms like `$118.2k` are used only in chart labels.
- A missing value is an em dash (—). A zero is written out (`$0.00`).
- Dates are `Fri 25 Sep` and times are 24-hour `17:08 ET`.
- Copy is in sentence case and names the book ("Mean reversion · real"). Panel titles are plain questions ("Is it behaving?", "Is it worth it?").
- A verdict states its sample size ("34 real trades so far — early evidence").

## Icons

- Stroke icons on a 24 px grid, stroke width 1.75, round caps and joins, `currentColor`.
- No emoji.
- Icon-only buttons carry an `aria-label`.

## Accessibility checklist

- AA contrast for all text, and ≥ 3:1 for all data marks against their surface.
- Real `<button>`, `<a href>` and `<table>` elements, with landmarks (`nav`, `main`, `aside`, `header`, `footer`) and an `aria-labelledby` on every panel.
- A visible focus ring (2 px accent, 2 px offset). The whole app is keyboard navigable.
- Meaning never rests on colour alone: marks, signs, icons and labels carry it.
- Every chart has a table view. Hidden status text is provided for icon-only table cells.
