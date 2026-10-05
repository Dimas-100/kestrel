import { describe, expect, it } from 'vitest'
import type { TargetRow } from '../../lib/api'
import { allocationSegments } from './allocation'

const row = (over: Partial<TargetRow>): TargetRow => ({
  id: 'r', label: 'SPY', symbols: ['SPY'], unit: '%', target: 60, low: 55, high: 65, actual: 62, status: 'on',
  gap: 0, gap_unit: 'money', gap_text: 'on plan', note: '', ...over,
})

describe('allocation segments', () => {
  it('turns the percent rows into actual segments, the remainder as Other, and aim segments in the same order', () => {
    const out = allocationSegments([
      row({ id: 'xlp', label: 'XLP', actual: 16, target: 20, status: 'under' }),
      row({ id: 'xlv', label: 'XLV', actual: 21, target: 15, status: 'over' }),
      row({ id: 'spy', label: 'SPY', actual: 62, target: 60 }),
    ])
    expect(out.actual.map((s) => [s.id, s.pct, s.status])).toEqual([['xlp', 16, 'under'], ['xlv', 21, 'over'], ['spy', 62, 'on']])
    expect(out.other).toBeCloseTo(1)
    expect(out.aim.map((s) => [s.id, s.pct, s.fromBand])).toEqual([['xlp', 20, false], ['xlv', 15, false], ['spy', 60, false]])
  })

  it('scales actual shares that add past 100 and leaves no remainder', () => {
    const out = allocationSegments([row({ id: 'a', actual: 60 }), row({ id: 'b', actual: 60 })])
    expect(out.actual.map((s) => s.pct)).toEqual([50, 50])
    expect(out.other).toBe(0)
  })

  it('aims from the middle of a band when a row has none, and nothing when it has neither', () => {
    const out = allocationSegments([
      row({ id: 'stocks', label: 'Single stocks', target: null, low: 15, high: 25, actual: 22 }),
      row({ id: 'free', label: 'Free', target: null, low: null, high: null, actual: 5 }),
    ])
    expect(out.aim.map((s) => [s.id, s.pct, s.fromBand])).toEqual([['stocks', 20, true], ['free', 0, true]])
  })

  it('leaves out ratio rows and rows with no actual', () => {
    const out = allocationSegments([
      row({ id: 'ratio', unit: 'x', actual: 3, target: 6 }),
      row({ id: 'blind', actual: null, status: 'unknown' }),
      row({ id: 'spy' }),
    ])
    expect(out.actual.map((s) => s.id)).toEqual(['spy'])
    expect(out.other).toBeCloseTo(38)
  })
})
