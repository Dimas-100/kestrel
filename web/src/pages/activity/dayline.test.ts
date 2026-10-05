import { describe, expect, it } from 'vitest'
import { DAY_TICKS, dayX, minutesOfDay } from './dayline'

describe('the day line', () => {
  it('reads a time as minutes into the day in the profile’s zone', () => {
    expect(minutesOfDay('2026-09-25T13:31:00Z', 'America/New_York')).toBe(9 * 60 + 31)
    expect(minutesOfDay('2026-09-26T02:30:00Z', 'America/New_York')).toBe(22 * 60 + 30) // still the 25th there
    expect(minutesOfDay('2026-09-25T00:00:00Z', 'UTC')).toBe(0)
  })

  it('places a time on the line between the pads', () => {
    expect(dayX(0, 1000)).toBe(8)
    expect(dayX(1440, 1000)).toBe(992)
    expect(dayX(720, 1000)).toBe(500)
  })

  it('ticks every six hours, from midnight to midnight', () => {
    expect(DAY_TICKS.map((t) => t.label)).toEqual(['00:00', '06:00', '12:00', '18:00', '24:00'])
    expect(DAY_TICKS.map((t) => t.minutes)).toEqual([0, 360, 720, 1080, 1440])
  })
})
