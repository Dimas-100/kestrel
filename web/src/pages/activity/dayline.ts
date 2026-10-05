// The day line: a time as minutes into the day in the profile's zone, its place on the line, and the ticks.
export const PAD = 8
export const MINUTES = 24 * 60

export interface DayTick {
  minutes: number
  label: string
}

export const DAY_TICKS: DayTick[] = [0, 6, 12, 18, 24].map((h) => ({ minutes: h * 60, label: `${String(h).padStart(2, '0')}:00` }))

/** Minutes since midnight in `tz` for an instant. */
export function minutesOfDay(iso: string, tz: string): number {
  const parts = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: tz })
    .formatToParts(new Date(iso))
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value ?? 0)
  return get('hour') * 60 + get('minute')
}

/** Where a minute of the day sits on a line `width` wide, inside the pads. */
export function dayX(minutes: number, width: number, pad = PAD): number {
  return pad + (Math.max(0, Math.min(MINUTES, minutes)) / MINUTES) * (width - 2 * pad)
}
