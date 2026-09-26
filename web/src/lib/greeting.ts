/** "Good morning" (05–11), "Good afternoon" (12–16), otherwise "Good evening" — in the profile's time zone. */
export function greeting(now: Date, timeZone: string): string {
  const hour = Number(new Intl.DateTimeFormat('en-US', { hour: 'numeric', hourCycle: 'h23', timeZone }).format(now))
  if (hour >= 5 && hour < 12) return 'Good morning'
  if (hour >= 12 && hour < 17) return 'Good afternoon'
  return 'Good evening'
}

/** "Fri 25 Sep · 17:08 ET" style line under the greeting */
export function clockLine(now: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    timeZone, timeZoneName: 'short',
  }).formatToParts(now)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('weekday')} ${get('day')} ${get('month')} · ${get('hour')}:${get('minute')} ${get('timeZoneName')}`
}
