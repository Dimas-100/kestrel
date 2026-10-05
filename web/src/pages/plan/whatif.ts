// What-if arithmetic for a goal, in the page and read-only (spec 2026-10-05 milestones §3.2): the months a monthly
// amount takes to close the gap, and the day that lands on.

/** Months to reach `target` from `current` at `monthly`, rounded up; 0 when already there; null at zero a month. */
export function monthsToReach(current: number, target: number, monthly: number): number | null {
  if (current >= target) return 0
  if (monthly <= 0) return null
  return Math.ceil((target - current) / monthly)
}

/** `months` after `todayIso`, on the same day of the month, clamped to the shorter month's last day. */
export function reachDate(todayIso: string, months: number): string {
  const [y, m, d] = todayIso.slice(0, 10).split('-').map(Number)
  const first = new Date(Date.UTC(y, m - 1 + months, 1))
  const lastDay = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate()
  const day = Math.min(d, lastDay)
  return `${first.getUTCFullYear()}-${String(first.getUTCMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}
