// The goals in time: months between days, a log scale that gives the next years room while 2064 still fits, the
// year ticks, the next few dated goals, and the monthly line said for what it is (spec 2026-10-05 plan page §2.1).
import type { GoalRow } from '../../lib/api'
import { money } from '../../lib/format'

const DAY_MS = 86_400_000
const MONTH_DAYS = 30.4375
const MIN_TICK_GAP = 0.05 // of the line: ticks closer than this to the previous kept one are thinned out

const at = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00Z`).getTime()

/** Months from one day to a later one, fractional; 0 when the second day isn't later. */
export function monthsBetween(fromIso: string, toIso: string): number {
  return Math.max(0, (at(toIso) - at(fromIso)) / DAY_MS / MONTH_DAYS)
}

/** Where `months` from today sits on the line, 0..1: ln(1 + months) / ln(1 + furthest), so three months get a
 *  visible stretch against forty years. */
export function timelinePosition(months: number, furthest: number): number {
  if (furthest <= 0) return 0
  return Math.min(1, Math.max(0, Math.log1p(Math.max(0, months)) / Math.log1p(furthest)))
}

/** The 1 January after today, then each year after it, each at its place on the line; a year that would sit within
 *  MIN_TICK_GAP of the previous kept tick is left out, so the far, crowded end keeps a few readable years. */
export function yearTicks(todayIso: string, furthestIso: string): { label: string; pos: number }[] {
  const furthest = monthsBetween(todayIso, furthestIso)
  const firstYear = Number(todayIso.slice(0, 4)) + 1
  const lastYear = Number(furthestIso.slice(0, 4))
  const ticks: { label: string; pos: number }[] = []
  for (let year = firstYear; year <= lastYear; year++) {
    const pos = timelinePosition(monthsBetween(todayIso, `${year}-01-01`), furthest)
    if (pos >= 1) break
    if (ticks.length === 0 || pos - ticks[ticks.length - 1].pos >= MIN_TICK_GAP) ticks.push({ label: String(year), pos })
  }
  return ticks
}

/** The nearest `n` dated goals that aren't reached and that kestrel can measure, earliest first (an overdue one is
 *  the earliest of all); one it can't see keeps to the table, with its reason. */
export function nextDated(goals: GoalRow[], n: number): GoalRow[] {
  return goals
    .filter((g): g is GoalRow & { by: string } => g.by != null && !g.reached && g.current != null)
    .sort((a, b) => (a.by < b.by ? -1 : a.by > b.by ? 1 : 0))
    .slice(0, n)
}

/** The straight-line monthly amount, said for what it is: deposits for a deposits goal; for a value goal, a figure
 *  that leaves out any market growth (over decades that is most of the story, so it must never read as a plan). */
export function monthlyText(g: Pick<GoalRow, 'measure' | 'monthly_needed'>): string | null {
  if (g.monthly_needed == null) return null
  return g.measure === 'deposits'
    ? `about ${money(g.monthly_needed)} a month in deposits`
    : `about ${money(g.monthly_needed)} a month, before any market growth`
}
