import { describe, expect, it } from 'vitest'
import type { GoalRow } from '../../lib/api'
import { monthlyText, monthsBetween, nextDated, timelinePosition, yearTicks } from './timeline'

const goal = (over: Partial<GoalRow>): GoalRow => ({
  id: 'g', label: 'Goal', scope_text: 'Roth IRA', measure: 'value', current: 500, target: 1000, progress_pct: 50,
  by: '2027-12-31', months_left: 15, monthly_needed: 33.33, reached: false, reached_on: null, overdue: false, missing_accounts: [],
  unknown_reason: '', ...over,
})

describe('the goal timeline', () => {
  it('counts months between two days, never below zero', () => {
    expect(monthsBetween('2026-09-25', '2026-12-31')).toBeCloseTo(3.19, 1)
    expect(monthsBetween('2026-09-25', '2064-05-07')).toBeCloseTo(451.7, 0)
    expect(monthsBetween('2026-09-25', '2026-01-01')).toBe(0)
  })

  it('places months on a log scale: 0 at today, 1 at the furthest, with room for the first years', () => {
    expect(timelinePosition(0, 452)).toBe(0)
    expect(timelinePosition(452, 452)).toBe(1)
    expect(timelinePosition(3, 452)).toBeGreaterThan(0.2) // three months get more than a fifth against forty years
    expect(timelinePosition(600, 452)).toBe(1) // past the end still sits at the end
    expect(timelinePosition(5, 0)).toBe(0) // no span at all: everything sits at today
  })

  it('ticks on 1 January of each year, thinned where the scale crowds them', () => {
    const ticks = yearTicks('2026-09-25', '2064-05-07')
    expect(ticks[0]).toEqual({ label: '2027', pos: timelinePosition(monthsBetween('2026-09-25', '2027-01-01'), monthsBetween('2026-09-25', '2064-05-07')) })
    expect(ticks.map((t) => t.label).slice(0, 4)).toEqual(['2027', '2028', '2029', '2030'])
    expect(ticks.length).toBeLessThan(18) // not one per year out to 2064
    for (let i = 1; i < ticks.length; i++) expect(ticks[i].pos - ticks[i - 1].pos).toBeGreaterThanOrEqual(0.05)
    expect(yearTicks('2026-09-25', '2026-12-31')).toEqual([]) // nothing before the first new year
    const narrow = yearTicks('2026-09-25', '2064-05-07', 36 / 300) // a 300 px line: labels need more of it
    expect(narrow.length).toBeLessThan(ticks.length)
    expect(narrow[0].label).toBe('2027')
    for (let i = 1; i < narrow.length; i++) expect(narrow[i].pos - narrow[i - 1].pos).toBeGreaterThanOrEqual(36 / 300)
  })

  it('the next dated goals are the nearest unreached ones, overdue first, reached and undated left out', () => {
    const goals = [
      goal({ id: 'far', by: '2040-01-01' }), goal({ id: 'done', by: '2027-01-01', reached: true, progress_pct: 100 }),
      goal({ id: 'late', by: '2026-01-01', overdue: true }), goal({ id: 'none', by: null }),
      goal({ id: 'near', by: '2027-07-25' }), goal({ id: 'mid', by: '2029-06-30' }),
      goal({ id: 'blind', by: '2027-03-01', current: null, progress_pct: null }), // can't be measured: table only
    ]
    expect(nextDated(goals, 3).map((g) => g.id)).toEqual(['late', 'near', 'mid'])
    expect(nextDated(goals, 10).map((g) => g.id)).toEqual(['late', 'near', 'mid', 'far'])
  })

  it('says the monthly amount for what it is', () => {
    expect(monthlyText(goal({ measure: 'value', monthly_needed: 100 }))).toBe('about $100.00 a month, before any market growth')
    expect(monthlyText(goal({ measure: 'deposits', monthly_needed: 100 }))).toBe('about $100.00 a month in deposits')
    expect(monthlyText(goal({ monthly_needed: null }))).toBeNull()
  })
})
