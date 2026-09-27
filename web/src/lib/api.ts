// Types mirror src/kestrel/views/*.py, by hand. What keeps them honest:
// - the fixtures in src/test/fixtures are generated from the Python code, and a Python test fails when they drift;
// - src/test/renderApp.tsx checks the fixtures `satisfies` these types, so `tsc` fails when a field here is renamed,
//   missing from Python's output, or of another JSON type.
// Not checked: a field Python adds that is not declared here, and the members of string-literal unions (both sides
// are plain strings in JSON).
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
  total: number // everything owned less everything owed
  owed: number // what the debt accounts owe, already taken off total; 0 with none
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

// --- the Strategy pages (src/kestrel/views/strategy.py) ---------------------------------------------------------

export type Verdict = BookRow['verdict']

export interface BookChip {
  id: string
  name: string
  money: Money
  status: string
  open: number
  trades: number
}

export interface StrategyCard {
  id: string
  name: string
  summary: string
  books: BookChip[]
  book: Money | null
  trades: number
  per_trade_pct: number | null
  band_lo: number | null
  band_hi: number | null
  verdict: Verdict
}

export interface StrategiesView {
  strategies: StrategyCard[]
}

export interface Step {
  label: string
  title: string
  text: string
  params: string[]
}

export interface Expected {
  win_rate: number
  avg_trade_pct: number
  avg_win_pct: number
  avg_loss_pct: number
  trades_per_month: number
  sd_trade_pct: number
  distribution: number[]
  source: string
  window: string
  cagr_pct: number | null
  max_drawdown_pct: number | null
}

export interface Bucket {
  low: number
  count: number
  share: number
  expected: number | null
}

export interface ScoreRow {
  key: 'win_rate' | 'avg_trade' | 'avg_win' | 'avg_loss' | 'per_month'
  label: string
  actual: number | null
  expected: number | null
  status: 'ok' | 'above' | 'below' | 'early' | 'none'
}

export interface OtherBook {
  id: string
  money: Money
  trades: number
  per_trade_pct: number | null
  win_rate: number | null
}

export interface Behaving {
  trades: number
  buckets: Bucket[]
  scorecard: ScoreRow[]
  review_at: number | null
  other: OtherBook | null
}

export interface FunnelLine {
  book_id: string
  money: Money
  values: number[]
}

export interface Funnel {
  expected: number | null
  lines: FunnelLine[]
  lo: (number | null)[]
  hi: (number | null)[]
}

export interface WatchItem {
  symbol: string
  label: string
  value: number | null
  note: string
}

export interface Slots {
  book_id: string | null
  total: number | null
  days: string[]
  used: number[]
  avg_used: number | null
  working_pct: number | null
  idle: number
  watch: WatchItem[]
}

export interface RecentTrade {
  key: string
  symbol: string
  money: Money
  opened: string
  closed: string
  return_pct: number
  r_multiple: number | null
  exit_reason: string
  sessions: number
  chart: boolean
}

export interface Bar {
  date: string
  open: number
  high: number
  low: number
  close: number
}

export interface Indicator {
  label: string
  values: (number | null)[]
  lines: { value: number; label: string }[]
}

export interface AnatomyChart {
  key: string
  bars: Bar[]
  indicator: Indicator | null
  stop: number | null
  entry: number
  exit: number
  entry_price: number
  exit_price: number
}

export interface Anatomy {
  recent: RecentTrade[]
  charts: AnatomyChart[]
  selected: string | null
}

export interface WorthPoint {
  key: 'backtest' | 'book' | 'long_term' | 'benchmark'
  label: string
  period: string
  early: boolean
  return_pct: number
  drop_pct: number
}

export interface Month {
  month: string
  book: number | null
  long_term: number | null
  ahead: boolean | null
}

export interface Monthly {
  months: Month[]
  ahead: number
  compared: number
  best: { month: string; value: number } | null
  worst: { month: string; value: number } | null
}

export interface TradeRow {
  symbol: string
  money: Money
  opened: string
  closed: string
  days_held: number
  return_pct: number
  r_multiple: number | null
  pnl: number
  exit_reason: string
}

export interface StrategyView {
  id: string
  name: string
  summary: string
  books: BookChip[]
  book: Money | null
  primary: string | null
  toggle: boolean
  expected: Expected | null
  steps: Step[]
  sizing: string
  behaving: Behaving
  funnel: Funnel
  slots: Slots
  anatomy: Anatomy
  worth: { points: WorthPoint[] }
  monthly: Monthly
  trades: TradeRow[]
}

// --- the Books pages (src/kestrel/views/books.py) ---------------------------------------------------------------

export interface BooksRow extends BookRow {
  spark: number[] // the last 60 values of the book's history, oldest first
}

export interface BooksView {
  as_of: string
  real_value: number
  paper_value: number
  rows: BooksRow[] // every book, real first then paper
}

export interface EquitySeries {
  dates: string[]
  values: number[] // growth index (%) since the book's first point
  benchmark: (number | null)[] // the benchmark over the same dates, indexed from the same start day
  return_pct: number
  max_drop_pct: number
}

export interface DrawdownSeries {
  dates: string[]
  values: number[] // percent below the running peak, always <= 0
}

export interface BookScorecard {
  trades: number
  win_rate: number | null
  avg_trade_pct: number | null
  avg_win_pct: number | null
  avg_loss_pct: number | null
  total_pnl: number
  best_pct: number | null
  worst_pct: number | null
  band_lo: number | null
  band_hi: number | null
  verdict: Verdict
}

export interface BookPosition {
  symbol: string
  quantity: number
  entry_price: number
  last_price: number
  stop_price: number | null
  room_pct: number | null
  pnl: number
  pnl_pct: number | null
  opened: string
  days: number
  flag: 'no_stop' | null
}

export interface BookTrade {
  book_id: string
  symbol: string
  opened: string
  closed: string
  entry_price: number
  exit_price: number
  quantity: number
  pnl: number
  return_pct: number
  r_multiple: number | null
  exit_reason: string
}

export interface BookRun {
  time: string
  label: string
  book_id: string | null
  status: 'done' | 'due' | 'late' | 'failed' | 'paused'
  detail: string
}

export interface BookView {
  as_of: string
  book: BooksRow
  strategy_id: string
  strategy_name: string
  account_id: string | null
  equity: EquitySeries
  drawdown: DrawdownSeries
  scorecard: BookScorecard
  positions: BookPosition[]
  trades: BookTrade[] // newest first
  runs: BookRun[] // this book's, next first then newest
}

// --- the Activity page (src/kestrel/views/activity.py) ------------------------------------------------------------

export interface RunRow {
  time: string
  label: string
  book_id: string | null
  book_name: string | null
  status: 'done' | 'due' | 'late' | 'failed' | 'paused'
  detail: string
}

export interface DayRuns {
  date: string
  label: string // 'Today' | 'Tomorrow' | a weekday date, e.g. 'Fri 25 Sep'
  runs: RunRow[]
}

export interface ActivitySource {
  id: string
  label: string
  kind: string
  status: 'ok' | 'stale' | 'error'
  last_success: string | null
  age_text: string | null
  stale_after: string | null
  detail: string
}

export interface ActivityView {
  as_of: string
  days: DayRuns[]
  counts: Record<string, number>
  alerts: Attention[] // serious, warning, note
  sources: ActivitySource[]
}

// --- the Accounts pages (src/kestrel/views/accounts.py) ---------------------------------------------------------

export type Window = 'ytd' | '1y' | 'all'
export type Category = 'long_term' | 'trading' | 'cash' | 'debt' | 'other' // debt: money owed

export interface Growth {
  start_date: string // the day the starting value is from
  start: number
  deposits: number // deposits minus withdrawals
  market: number
  end: number
}

export interface AccountLine {
  id: string
  name: string
  institution: string
  account_type: string
  category: Category
  value: number
  share: number | null
  day_change: number | null
  day_pct: number | null
  year_market: number | null
}

export interface CombinedHolding {
  symbol: string // empty on the cash row
  name: string
  cash: boolean
  value: number
  share: number | null
  accounts: string[]
}

export interface AccountsView {
  as_of: string
  count: number
  total: number
  growth: Record<Window, Growth | null>
  accounts: AccountLine[]
  holdings: CombinedHolding[]
}

export interface Flow {
  date: string
  amount: number // positive in, negative out
}

export interface HoldingRow {
  symbol: string
  name: string
  quantity: number
  price: number
  value: number
  weight: number | null
  cost_basis: number | null
  gain: number | null
  gain_pct: number | null
}

export interface Totals {
  value: number
  cost_basis: number | null
  gain: number | null
  gain_pct: number | null
  unknown_cost: number
}

export interface AccountView {
  id: string
  name: string
  institution: string
  account_type: string
  category: Category
  value: number
  as_of: string
  points: ValuePoint[]
  growth: Record<Window, Growth | null>
  flows: Flow[]
  holdings: HoldingRow[]
  holdings_as_of: string | null // the latest day the holdings were reported; null when the source doesn't say
  cash: number
  cash_weight: number | null
  totals: Totals
}

/** A non-2xx answer, with its status, so a page can tell "not found" from "the server is down". */
export class HttpError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new HttpError(response.status, `${path} answered ${response.status}`)
  return (await response.json()) as T
}

const MINUTE = 60_000

export function useShell() {
  return useQuery({ queryKey: ['shell'], queryFn: () => getJson<ShellView>('/api/shell'), refetchInterval: MINUTE })
}

export function useHome() {
  return useQuery({ queryKey: ['home'], queryFn: () => getJson<HomeView>('/api/home'), refetchInterval: MINUTE })
}

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'], queryFn: () => getJson<AccountsView>('/api/accounts'), refetchInterval: MINUTE,
  })
}

export function useAccount(id: string) {
  return useQuery({
    queryKey: ['account', id],
    queryFn: () => getJson<AccountView>(`/api/accounts/${encodeURIComponent(id)}`),
    refetchInterval: MINUTE,
  })
}

export function useBooks() {
  return useQuery({ queryKey: ['books'], queryFn: () => getJson<BooksView>('/api/books'), refetchInterval: MINUTE })
}

export function useBook(id: string) {
  return useQuery({
    queryKey: ['book', id],
    queryFn: () => getJson<BookView>(`/api/books/${encodeURIComponent(id)}`),
    refetchInterval: MINUTE,
  })
}

export function useActivity() {
  return useQuery({
    queryKey: ['activity'], queryFn: () => getJson<ActivityView>('/api/activity'), refetchInterval: MINUTE,
  })
}

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'], queryFn: () => getJson<StrategiesView>('/api/strategies'), refetchInterval: MINUTE,
  })
}

export function useStrategy(id: string, book: Money) {
  return useQuery({
    queryKey: ['strategy', id, book],
    queryFn: () => getJson<StrategyView>(`/api/strategies/${encodeURIComponent(id)}?book=${book}`),
    refetchInterval: MINUTE,
    // switching Real | Paper keeps the page up until the other book arrives; another strategy starts clean
    placeholderData: (previous, query) => (query?.queryKey[1] === id ? previous : undefined),
  })
}
