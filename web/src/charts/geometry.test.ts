import { describe, expect, it } from 'vitest'
import type { ValuePoint } from '../lib/api'
import { baseline, nearestIndex, tickIndices, windowPoints } from './geometry'

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
})
