// Number and date formatting. Rules: docs/design-system.md → "Numbers and copy".
export const MINUS = '−'
export const DASH = '—'

let currency = 'USD'
/** Set once from the profile; every money value then uses it. */
export function setCurrency(code: string): void {
  currency = code
}

function currencyFormat(cents: boolean): Intl.NumberFormat {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: cents ? 2 : 0,
    maximumFractionDigits: cents ? 2 : 0,
  })
}

/** $1,234.56 · −$12.30 (a true minus sign) */
export function money(value: number, cents = true): string {
  const text = currencyFormat(cents).format(Math.abs(value))
  return value < 0 && text !== currencyFormat(cents).format(0) ? MINUS + text : text
}

/** +$412.30 · −$32.50 · $0.00 (zero carries no sign) */
export function signedMoney(value: number, cents = true): string {
  const text = money(Math.abs(value), cents)
  if (text === money(0, cents)) return text
  return (value > 0 ? '+' : MINUS) + text
}

/** +14.2% · −5.1% · 0.0% */
export function pct(value: number, digits = 1): string {
  const text = Math.abs(value).toFixed(digits)
  if (Number(text) === 0) return `${text}%`
  return `${value > 0 ? '+' : MINUS}${text}%`
}

/** $118.2k · $1.2M — chart labels only */
export function compactMoney(value: number): string {
  const abs = Math.abs(value)
  const sign = value < 0 ? MINUS : ''
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}k`
  return `${sign}$${abs.toFixed(0)}`
}

/** 508.20 — prices and quantities */
export function num(value: number, digits = 2): string {
  const text = Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
  return value < 0 ? MINUS + text : text
}

/** ["$148,392", "18"] — the hero figure dims its cents */
export function splitCents(value: number): [string, string] {
  const [whole, cents = '00'] = money(value).split('.')
  return [whole, cents]
}

/** "Fri 25 Sep" for an ISO date (YYYY-MM-DD) or timestamp, in the given zone */
export function shortDate(iso: string, timeZone = 'UTC'): string {
  const date = iso.length === 10 ? new Date(`${iso}T12:00:00Z`) : new Date(iso)
  const zone = iso.length === 10 ? 'UTC' : timeZone
  const parts = new Intl.DateTimeFormat('en-US', { weekday: 'short', day: 'numeric', month: 'short', timeZone: zone })
    .formatToParts(date)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('weekday')} ${get('day')} ${get('month')}`
}

/** "10 Sep" this year, "Sep 2025" before it — for "since" dates */
export function sinceLabel(iso: string, nowIso: string): string {
  const date = new Date(`${iso.slice(0, 10)}T12:00:00Z`)
  const month = date.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' })
  return date.getUTCFullYear() === new Date(nowIso).getUTCFullYear()
    ? `${date.getUTCDate()} ${month}`
    : `${month} ${date.getUTCFullYear()}`
}

/** "Sep" / "25 Sep" axis labels for an ISO date */
export function monthLabel(iso: string, withDay = false): string {
  const date = new Date(`${iso}T12:00:00Z`)
  const month = date.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' })
  return withDay ? `${date.getUTCDate()} ${month}` : month
}

/** 24-hour "17:08" in the given zone */
export function timeHM(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone })
    .format(new Date(iso))
}

/** "2 min ago" · "26 h ago" · "3 d ago" */
export function ago(iso: string | null, now: Date): string {
  if (!iso) return 'never'
  const minutes = Math.max(0, Math.floor((now.getTime() - new Date(iso).getTime()) / 60000))
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 48) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}
