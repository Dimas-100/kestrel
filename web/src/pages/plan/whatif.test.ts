import { describe, expect, it } from 'vitest'
import { monthsToReach, reachDate } from './whatif'

describe('what-if arithmetic', () => {
  it('counts the months to reach a target at a monthly amount, rounded up; never at zero; none left when there', () => {
    expect(monthsToReach(1500, 1800, 150)).toBe(2)
    expect(monthsToReach(1500, 1800, 100)).toBe(3)
    expect(monthsToReach(1500, 1800, 0)).toBeNull()
    expect(monthsToReach(1800, 1800, 50)).toBe(0)
  })

  it('dates the reach from today, keeping the day of the month', () => {
    expect(reachDate('2026-09-25', 2)).toBe('2026-11-25')
    expect(reachDate('2026-09-25', 4)).toBe('2027-01-25')
    expect(reachDate('2026-01-31', 1)).toBe('2026-02-28') // a shorter month clamps the day
  })
})
