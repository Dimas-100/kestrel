// Pure chart math, tested without a DOM.
import type { ValuePoint } from '../lib/api'

export type Range = '1M' | '3M' | 'YTD' | '1Y'
export const RANGES: readonly Range[] = ['1M', '3M', 'YTD', '1Y']

/** The UTC date `months` whole months before `date`, its day clamped to that month's last (31 Mar → 28 Feb). */
function monthsBefore(date: Date, months: number): Date {
  const year = date.getUTCFullYear()
  const month = date.getUTCMonth() - months // Date.UTC rolls a negative month back into the year before
  const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate()
  return new Date(Date.UTC(year, month, Math.min(date.getUTCDate(), lastDay), 12))
}

/** Points inside the range, counted back from the last point's date. */
export function windowPoints(points: ValuePoint[], range: Range): ValuePoint[] {
  if (points.length === 0) return points
  const last = new Date(`${points[points.length - 1].date}T12:00:00Z`)
  const start = range === 'YTD'
    ? new Date(Date.UTC(last.getUTCFullYear(), 0, 1, 12))
    : monthsBefore(last, { '1M': 1, '3M': 3, '1Y': 12 }[range])
  const from = start.toISOString().slice(0, 10)
  const inside = points.filter((p) => p.date >= from)
  return inside.length >= 2 ? inside : points.slice(-2)
}

/** The "starting value + deposits" line: what the account would hold if the market had not moved. */
export function baseline(points: ValuePoint[]): number[] {
  const out: number[] = []
  points.forEach((p, i) => out.push(i === 0 ? p.value : out[i - 1] + p.net_flow))
  return out
}

/** Index of the x closest to `x` (xs ascending). */
export function nearestIndex(xs: number[], x: number): number {
  if (xs.length === 0) return -1
  let lo = 0
  let hi = xs.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (xs[mid] <= x) lo = mid
    else hi = mid
  }
  return Math.abs(xs[lo] - x) <= Math.abs(xs[hi] - x) ? lo : hi
}

/** About `count` evenly spaced indices across n points, always including the first. */
export function tickIndices(n: number, count: number): number[] {
  if (n <= 0) return []
  if (n <= count) return Array.from({ length: n }, (_, i) => i)
  const step = (n - 1) / (count - 1)
  return Array.from({ length: count }, (_, i) => Math.round(i * step))
}
