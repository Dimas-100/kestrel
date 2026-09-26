import { afterEach, describe, expect, it } from 'vitest'
import {
  ago, compactMoney, money, monthLabel, num, pct, setCurrency, shortDate, signedMoney, sinceLabel, splitCents, timeHM,
} from './format'

describe('money', () => {
  it('uses a true minus sign and cents', () => {
    expect(money(148392.18)).toBe('$148,392.18')
    expect(money(-12.3)).toBe('−$12.30')
    expect(money(118200, false)).toBe('$118,200')
  })
  it('signs deltas but never zero', () => {
    expect(signedMoney(412.3)).toBe('+$412.30')
    expect(signedMoney(-32.5)).toBe('−$32.50')
    expect(signedMoney(0)).toBe('$0.00')
    expect(signedMoney(-0.001)).toBe('$0.00')
  })
  it('splits the hero figure', () => {
    expect(splitCents(148392.18)).toEqual(['$148,392', '18'])
  })
  describe('in another currency', () => {
    afterEach(() => setCurrency('USD'))
    it('follows the profile', () => {
      setCurrency('EUR')
      expect(money(1234.5)).toBe('€1,234.50')
      expect(signedMoney(-2)).toBe('−€2.00')
      expect(splitCents(1234.5)).toEqual(['€1,234', '50'])
    })
  })
})

describe('numbers', () => {
  it('formats percents with a sign', () => {
    expect(pct(14.2)).toBe('+14.2%')
    expect(pct(-5.12)).toBe('−5.1%')
    expect(pct(0.04)).toBe('0.0%')
    expect(pct(0.279, 2)).toBe('+0.28%')
  })
  it('compacts chart labels', () => {
    expect(compactMoney(118200)).toBe('$118.2k')
    expect(compactMoney(1_250_000)).toBe('$1.3M')
    expect(compactMoney(-950)).toBe('−$950')
  })
  it('formats prices', () => {
    expect(num(508.2)).toBe('508.20')
    expect(num(-3)).toBe('−3.00')
  })
})

describe('dates', () => {
  it('formats short dates and axis labels', () => {
    expect(shortDate('2026-09-25')).toBe('Fri 25 Sep')
    expect(monthLabel('2026-09-25')).toBe('Sep')
    expect(monthLabel('2026-09-25', true)).toBe('25 Sep')
    expect(sinceLabel('2026-09-10', '2026-09-25T21:08:00Z')).toBe('10 Sep')
    expect(sinceLabel('2025-07-27', '2026-09-25T21:08:00Z')).toBe('Jul 2025')
  })
  it('formats times in the profile zone', () => {
    expect(timeHM('2026-09-25T21:08:00Z', 'America/New_York')).toBe('17:08')
  })
  it('says how long ago', () => {
    const now = new Date('2026-09-25T21:08:00Z')
    expect(ago('2026-09-25T21:06:00Z', now)).toBe('2m')
    expect(ago('2026-09-24T19:08:00Z', now)).toBe('26h')
    expect(ago('2026-09-20T21:08:00Z', now)).toBe('5d')
    expect(ago(null, now)).toBe('never')
  })
})
