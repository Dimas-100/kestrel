import { describe, expect, it } from 'vitest'
import type { TargetRow } from '../../lib/api'
import { axisTicks, nestRows, percentDomain, ratioDomain, rowGeometry } from './allocation'

function row(partial: Partial<TargetRow> & { id: string }): TargetRow {
  return {
    label: partial.id, symbols: [partial.id], unit: '%', target: null, low: null, high: null, actual: null,
    status: 'on', gap: null, gap_unit: null, gap_text: '', note: '', rebalance: 'trades', parent: null, ...partial,
  }
}

describe('allocation rows', () => {
  it('draws a share at its own width on the scale, never scaled down by the other rows', () => {
    // a sleeve (41 %) and its members (17 %, 14 %) beside a 32 % holding add past 100: none of them shrinks
    const rows = [row({ id: 'core', symbols: ['M', 'N', 'A'], low: 45, high: 50, actual: 41.1 }),
                  row({ id: 'schd', actual: 32, target: 15, low: 11.25, high: 18.75 }),
                  row({ id: 'm', actual: 17.3, target: 22, low: 16.5, high: 27.5, parent: 'core' }),
                  row({ id: 'n', actual: 13.6, target: 12, low: 9, high: 15, parent: 'core' })]
    const domain = percentDomain(rows)
    expect(domain).toEqual([0, 60])
    expect(rowGeometry(rows[1], domain).actual).toBeCloseTo(32 / 60)
    expect(rowGeometry(rows[0], domain).actual).toBeCloseTo(41.1 / 60)
  })

  it('nests a sleeve’s members under it, in the view’s order otherwise', () => {
    const rows = [row({ id: 'n', parent: 'core' }), row({ id: 'core', symbols: ['M', 'N'] }), row({ id: 'x' }),
                  row({ id: 'm', parent: 'core' }), row({ id: 'orphan', parent: 'gone' })]
    expect(nestRows(rows).map((p) => [p.row.id, p.depth])).toEqual(
      [['core', 0], ['n', 1], ['m', 1], ['x', 0], ['orphan', 0]])
  })

  it('keeps the scale between 10 and 100, in steps of ten', () => {
    expect(percentDomain([row({ id: 'a', actual: 2, high: 3 })])).toEqual([0, 20])
    expect(percentDomain([row({ id: 'a', actual: 95, high: 99 })])).toEqual([0, 100])
    expect(percentDomain([row({ id: 'r', unit: 'x', actual: 400 })])).toEqual([0, 20])
  })

  it('gives a ratio its own scale and the axis its ends and middle', () => {
    expect(ratioDomain(row({ id: 'r', unit: 'x', actual: 0.75, target: 1.75, low: 1.31, high: 2.19 }))).toEqual([0, 3])
    expect(axisTicks([0, 60])).toEqual([0, 30, 60])
  })
})
