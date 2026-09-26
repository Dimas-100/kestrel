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

export const TIP_W = 190 // the tooltip card's width (.tip min-width 170 + padding)

/** A tooltip's left edge: beside the anchor, flipped to its left near the right edge, and never outside the chart
 *  (phones are narrow). */
export function clampTip(anchor: number, width: number, tip = TIP_W): number {
  const side = anchor + 12 + tip > width ? anchor - 12 - tip : anchor + 12
  return Math.min(Math.max(0, side), Math.max(0, width - tip))
}

/** n equal slots across `width`; each slot's mark is centred and `fill` of the slot wide, at most `max` px. */
export function bandLayout(n: number, width: number, max = 24, fill = 0.76) {
  const step = n > 0 ? width / n : width
  const mark = Math.min(max, step * fill)
  return {
    step,
    mark,
    left: (i: number) => i * step + (step - mark) / 2,
    center: (i: number) => i * step + step / 2,
  }
}

/** The slot under an x position, clamped to the ends; -1 when there are no slots. */
export function indexAt(x: number, n: number, width: number): number {
  if (n <= 0) return -1
  return Math.min(n - 1, Math.max(0, Math.floor(x / (width / n))))
}

/** Decimals that tell neighbouring axis ticks apart: 0 for a step of 1 or more, 1 for 0.5 or 0.2, 2 for 0.05. */
export function tickDecimals(ticks: number[]): number {
  if (ticks.length < 2) return 0
  const step = Math.abs(ticks[1] - ticks[0])
  return step > 0 ? Math.max(0, Math.ceil(-Math.log10(step) - 1e-6)) : 0
}

export interface OHLC { open: number; high: number; low: number; close: number }
export interface Candle { x: number; w: number; up: boolean; bodyTop: number; bodyH: number; wickTop: number;
  wickBottom: number }

/** Candle bodies and wicks for bars spread across `width`, with `y` mapping a price to a pixel. */
export function candleShapes(bars: OHLC[], width: number, y: (price: number) => number): Candle[] {
  const layout = bandLayout(bars.length, width, 12, 0.6)
  return bars.map((b, i) => {
    const top = y(Math.max(b.open, b.close))
    return {
      x: layout.center(i), w: layout.mark, up: b.close >= b.open,
      bodyTop: top, bodyH: Math.max(1, y(Math.min(b.open, b.close)) - top),
      wickTop: y(b.high), wickBottom: y(b.low),
    }
  })
}

export interface Placed { x: number; y: number; anchor: 'start' | 'middle' | 'end'; leader: boolean; clear: boolean }
interface Box { left: number; top: number; w: number; h: number }

/** How much two boxes overlap, in square pixels (0 when they are apart). */
const overlap = (a: Box, b: Box) =>
  Math.max(0, Math.min(a.left + a.w, b.left + b.w) - Math.max(a.left, b.left))
  * Math.max(0, Math.min(a.top + a.h, b.top + b.h) - Math.max(a.top, b.top))

/** Direct labels for points. Each tries the spots around its point (right, left, above, below), then slides to
 *  the right or left of it, up or down in 8 px steps; it takes the first spot that stays inside the chart and clear
 *  of every marker and of the labels placed before it, or else the inside spot that overlaps least (`clear` is
 *  false). A label slid away from its point gets a leader line. `x` is where the text is anchored, `y` the label
 *  box's top; `h` is its height (a name over a figure). */
export function placeLabels(points: { x: number; y: number; w: number }[], width: number, height: number, h = 28,
  gap = 10): Placed[] {
  const taken: Box[] = points.map((p) => ({ left: p.x - 8, top: p.y - 8, w: 16, h: 16 })) // the markers
  return points.map((p) => {
    const right = { left: p.x + gap, x: p.x + gap, anchor: 'start' as const }
    const left = { left: p.x - gap - p.w, x: p.x - gap, anchor: 'end' as const }
    const middle = { left: p.x - p.w / 2, x: p.x, anchor: 'middle' as const }
    const level = p.y - h / 2
    const spots = [
      { ...right, top: level, dy: 0 }, { ...left, top: level, dy: 0 },
      { ...middle, top: p.y - gap - h, dy: 0 }, { ...middle, top: p.y + gap, dy: 0 },
    ]
    for (let step = 8; step <= 64; step += 8) {
      for (const dy of [step, -step]) spots.push({ ...right, top: level + dy, dy }, { ...left, top: level + dy, dy })
    }
    const boxOf = (s: (typeof spots)[number]): Box => ({ left: s.left, top: s.top, w: p.w, h })
    const inside = spots.filter((s) => {
      const b = boxOf(s)
      return b.left >= 0 && b.left + b.w <= width && b.top >= 0 && b.top + b.h <= height
    })
    const crowding = (s: (typeof spots)[number]) => taken.reduce((sum, t) => sum + overlap(boxOf(s), t), 0)
    const pick = inside.find((s) => crowding(s) === 0)
      ?? [...inside].sort((a, b) => crowding(a) - crowding(b))[0] ?? spots[0]
    const clear = crowding(pick) === 0
    taken.push(boxOf(pick))
    return { x: pick.x, y: pick.top, anchor: pick.anchor, leader: Math.abs(pick.dy) >= h / 2, clear }
  })
}

/** How strongly a month cell is washed in the gain or loss colour, in percent; null for a small or missing move. */
export function cellWash(value: number | null): number | null {
  if (value == null || Math.abs(value) < 0.5) return null
  return Math.min(60, Math.round(10 + Math.abs(value) * 10))
}

/** Consecutive "YYYY-MM" months grouped under their year, for the label row above a month grid. */
export function yearSpans(months: string[]): { year: string; span: number }[] {
  const out: { year: string; span: number }[] = []
  for (const month of months) {
    const year = month.slice(0, 4)
    const last = out[out.length - 1]
    if (last && last.year === year) last.span += 1
    else out.push({ year, span: 1 })
  }
  return out
}
