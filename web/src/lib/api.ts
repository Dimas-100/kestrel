// Types mirror src/kestrel/views/*.py. The fixtures in src/test/fixtures are generated from the Python code and a
// Python test fails when they drift, so a renamed field shows up as a failing front-end test here.
import { useQuery } from '@tanstack/react-query'

export type Money = 'real' | 'paper'
export type Level = 'serious' | 'warning' | 'note'

export interface AppSettings {
  name: string
  accent: 'rufous' | 'slate' | 'mono'
  theme: 'system' | 'dark' | 'light'
  gain_loss: 'green-red' | 'blue-orange'
  density: 'comfortable' | 'compact'
  currency: string
  timezone: string
}

export interface Source {
  id: string
  label: string
  kind: string
  last_success: string | null
  status: 'ok' | 'stale' | 'error'
  detail: string
}

export interface ShellView {
  name: string
  app: AppSettings
  benchmark_label: string
  now: string
  sources: Source[]
  counts: { accounts: number; books: number; strategies: number }
}

export interface Delta {
  amount: number
  pct: number | null
}

export interface ValuePoint {
  date: string
  value: number
  net_flow: number
}

export interface NetWorth {
  total: number
  today: Delta
  month: Delta
  year: Delta
  year_flows: number
  points: ValuePoint[]
}

export interface Slice {
  category: string
  label: string
  value: number
  share: number
  cells: number
}

export interface AccountRow {
  id: string
  name: string
  category: string
  value: number
  day_pct: number | null
}

export interface Line {
  key: 'trading' | 'long_term' | 'benchmark'
  label: string
  return_pct: number
  max_drop_pct: number
  values: (number | null)[]
}

export interface Comparison {
  window: 'ytd' | '12m'
  start: string // the lines' shared first day
  dates: string[]
  lines: Line[]
  gap_pts: number | null
  shallower: boolean | null
  real_trades: number
  review_at: number | null
}

export interface Attention {
  level: Level
  title: string
  detail: string
  link: string
}

export interface BookRow {
  id: string
  name: string
  strategy: string
  money: Money
  status: string
  value: number
  day_change: number | null
  since_pct: number | null
  started: string
  trades: number
  per_trade_pct: number | null
  band_lo: number | null
  band_hi: number | null
  verdict: 'in_band' | 'below' | 'above' | 'early' | 'none'
  slots_used: number
  slots_total: number | null
  next_run: string | null
}

export interface TodayRun {
  time: string
  label: string
  status: 'done' | 'due' | 'late' | 'failed' | 'paused'
  detail: string
}

export interface PositionRow {
  book_id: string
  book: string
  symbol: string
  money: Money
  quantity: number
  entry_price: number
  last_price: number
  stop_price: number | null
  room_pct: number | null
  pnl: number
  note: string
}

export interface HomeView {
  as_of: string
  summary: { day_change: number; gap_pts: number | null; needs_you: number }
  net_worth: NetWorth
  allocation: Slice[]
  accounts: AccountRow[]
  comparison: Comparison
  attention: Attention[]
  books: BookRow[]
  today: TodayRun[]
  positions: PositionRow[]
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`${path} answered ${response.status}`)
  return (await response.json()) as T
}

const MINUTE = 60_000

export function useShell() {
  return useQuery({ queryKey: ['shell'], queryFn: () => getJson<ShellView>('/api/shell'), refetchInterval: MINUTE })
}

export function useHome() {
  return useQuery({ queryKey: ['home'], queryFn: () => getJson<HomeView>('/api/home'), refetchInterval: MINUTE })
}
