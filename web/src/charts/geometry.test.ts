import { describe, expect, it } from 'vitest'
import type { ValuePoint } from '../lib/api'
import {
  bandLayout, baseline, candleShapes, cellWash, clampTip, indexAt, nearestIndex, placeLabels, tickIndices, windowPoints,
  yearSpans,
} from './geometry'

const p = (date: string, value: number, net_flow = 0): ValuePoint => ({ date, value, net_flow })

describe('chart geometry', () => {
  it('keeps the points inside a range', () => {
    const pts = [p('2025-12-31', 1), p('2026-01-02', 2), p('2026-08-24', 3), p('2026-09-25', 4)]
    expect(windowPoints(pts, 'YTD').map((x) => x.date)).toEqual(['2026-01-02', '2026-08-24', '2026-09-25'])
    expect(windowPoints(pts, '1M').map((x) => x.date)).toEqual(['2026-08-24', '2026-09-25']) // 25 Aug is outside
    expect(windowPoints([p('2026-09-25', 4)], '1M')).toHaveLength(1)
    expect(windowPoints([], '1Y')).toEqual([])
  })
  it('counts months back from the end of a month without skipping the shorter month', () => {
    const march = [p('2026-02-27', 1), p('2026-02-28', 2), p('2026-03-02', 3), p('2026-03-31', 4)]
    expect(windowPoints(march, '1M').map((x) => x.date)).toEqual(['2026-02-28', '2026-03-02', '2026-03-31'])
    const leap = [p('2027-02-26', 1), p('2027-02-28', 2), p('2027-03-01', 3), p('2028-02-29', 4)]
    expect(windowPoints(leap, '1Y').map((x) => x.date)).toEqual(['2027-02-28', '2027-03-01', '2028-02-29'])
  })
  it('never returns fewer than two points when it has them', () => {
    const pts = [p('2026-01-02', 1), p('2026-09-24', 2), p('2026-09-25', 3)]
    expect(windowPoints(pts, '1M')).toHaveLength(2)
  })
  it('adds deposits onto the starting value', () => {
    expect(baseline([p('a', 100), p('b', 130, 20), p('c', 90, -10)])).toEqual([100, 120, 110])
  })
  it('finds the nearest x', () => {
    expect(nearestIndex([0, 10, 20], 14)).toBe(1)
    expect(nearestIndex([0, 10, 20], 16)).toBe(2)
    expect(nearestIndex([0, 10, 20], -5)).toBe(0)
    expect(nearestIndex([], 3)).toBe(-1)
  })
  it('spreads ticks', () => {
    expect(tickIndices(262, 6)).toEqual([0, 52, 104, 157, 209, 261])
    expect(tickIndices(3, 6)).toEqual([0, 1, 2])
  })
  it('keeps a tooltip beside its anchor and inside the chart', () => {
    expect(clampTip(100, 640)).toBe(112)
    expect(clampTip(600, 640)).toBe(600 - 12 - 190) // flipped to the left near the right edge
    expect(clampTip(150, 200)).toBe(0) // flipped would start off the chart
    expect(clampTip(10, 100)).toBe(0) // a chart narrower than the tooltip
  })
  it('lays out a row of evenly spaced marks and finds the one under the pointer', () => {
    const b = bandLayout(20, 660)
    expect([b.step, b.mark]).toEqual([33, 24]) // bars are at most 24 px wide
    expect(b.left(0)).toBe(4.5)
    expect(b.center(19)).toBe(643.5)
    expect(bandLayout(40, 200, Infinity, 0.8).mark).toBe(4)
    expect([indexAt(-5, 20, 660), indexAt(34, 20, 660), indexAt(9999, 20, 660)]).toEqual([0, 1, 19])
    expect(indexAt(10, 0, 660)).toBe(-1)
  })
  it('shapes candles, with a hairline body for a bar that did not move', () => {
    const y = (v: number) => 100 - v
    const [up, down, flat] = candleShapes([
      { open: 10, high: 20, low: 5, close: 15 },
      { open: 15, high: 16, low: 8, close: 9 },
      { open: 9, high: 9, low: 9, close: 9 },
    ], 30, y)
    expect(up).toMatchObject({ x: 5, up: true, bodyTop: 85, bodyH: 5, wickTop: 80, wickBottom: 95 })
    expect(down).toMatchObject({ up: false, bodyTop: 85, bodyH: 6 })
    expect(flat.bodyH).toBe(1)
  })
  it('places labels beside their points, clear of each other, the markers and the edges', () => {
    const placed = placeLabels([{ x: 100, y: 100, w: 80 }, { x: 100, y: 120, w: 80 }, { x: 290, y: 20, w: 80 }],
      300, 200)
    expect(placed[0]).toEqual({ x: 110, y: 86, anchor: 'start', leader: false, clear: true }) // right of its point
    expect(placed[1]).toEqual({ x: 90, y: 106, anchor: 'end', leader: false, clear: true }) // the right is taken
    expect(placed[2]).toEqual({ x: 280, y: 6, anchor: 'end', leader: false, clear: true }) // no room on the right
    // three points close together near the right edge: the third label slides clear and gets a leader line
    const stack = placeLabels([{ x: 160, y: 100, w: 80 }, { x: 160, y: 110, w: 80 }, { x: 160, y: 120, w: 80 }],
      200, 200)
    expect(stack[2]).toEqual({ x: 150, y: 154, anchor: 'end', leader: true, clear: true })
    // twenty labels on one point can't all be clear (the chart then uses a key), but each one stays inside it
    const crowd = placeLabels(Array.from({ length: 20 }, () => ({ x: 150, y: 100, w: 100 })), 300, 200)
    expect(crowd.some((l) => !l.clear)).toBe(true)
    for (const l of crowd) {
      const left = l.anchor === 'start' ? l.x : l.anchor === 'end' ? l.x - 100 : l.x - 50
      expect(left >= 0 && left + 100 <= 300 && l.y >= 0 && l.y + 28 <= 200).toBe(true)
    }
  })
  it('washes a month cell by the size of its move and leaves a small one neutral', () => {
    expect([cellWash(1.2), cellWash(-0.8), cellWash(9)]).toEqual([22, 18, 60])
    expect([cellWash(0.3), cellWash(null)]).toEqual([null, null])
  })
  it('groups months under their year', () => {
    expect(yearSpans(['2025-10', '2025-11', '2025-12', '2026-01'])).toEqual([
      { year: '2025', span: 3 }, { year: '2026', span: 1 },
    ])
  })
})
