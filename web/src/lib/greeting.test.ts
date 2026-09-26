import { describe, expect, it } from 'vitest'
import { clockLine, greeting } from './greeting'

const NY = 'America/New_York'

describe('greeting', () => {
  it('follows the profile time zone, not the computer', () => {
    expect(greeting(new Date('2026-09-25T13:00:00Z'), NY)).toBe('Good morning') // 09:00 in New York
    expect(greeting(new Date('2026-09-25T17:00:00Z'), NY)).toBe('Good afternoon') // 13:00
    expect(greeting(new Date('2026-09-25T21:08:00Z'), NY)).toBe('Good evening') // 17:08
    expect(greeting(new Date('2026-09-25T07:00:00Z'), NY)).toBe('Good evening') // 03:00
    expect(greeting(new Date('2026-09-25T21:08:00Z'), 'Asia/Tokyo')).toBe('Good morning') // 06:08
  })
  it('writes the clock line', () => {
    expect(clockLine(new Date('2026-09-25T21:08:00Z'), NY)).toBe('Fri 25 Sep · 17:08 EDT')
  })
})
