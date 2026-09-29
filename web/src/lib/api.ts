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
  debt_accounts: number // how many accounts that owed comes from
  today: Delta
  month: Delta
  year: Delta
  year_flows: number
  points: ValuePoint[]
  no_history: number // accounts with no history, counted at today's balance on every date of points
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
  institution: string
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
  stop_resting: boolean | null // true: a stop rests but its level isn't reported
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
  win_rate: number | null
  avg_return_pct: number | null
  pnl: number
  last_closed: string | null
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
  spark: number[] // the last 60 values of the growth since the book started, in percent; the last is since_pct
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
  stop_resting: boolean | null // true: a stop rests but its level isn't reported
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
  growth: Record<Window, Growth | null> // "Now" is total
  no_history: number // accounts with no history, counted in the growth at today's balance
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

// --- the Calendar page (src/kestrel/views/calendar.py) -----------------------------------------------------------

export type EventKind = 'earnings' | 'filing' | 'insider' | 'dividend' | 'other'

export interface EventRow {
  date: string
  symbol: string
  kind: EventKind
  title: string
  detail: string
  url: string
  held: boolean
}

export interface WeekGroup {
  week_start: string
  items: EventRow[]
}

export interface CalendarView {
  as_of: string
  today: string
  upcoming: WeekGroup[]
  recent: EventRow[]
  counts: Record<EventKind, number>
}

// --- the Backtests page (src/kestrel/views/backtests.py) ---------------------------------------------------------

export type BacktestVerdict = 'pass' | 'fail' | 'refused' | 'pending'

export interface Backtest {
  id: string
  name: string
  family: string
  window: string
  verdict: BacktestVerdict
  at: string
  strategy_id: string | null
  trades: number | null
  avg_trade_pct: number | null
  t_stat: number | null
  calmar: number | null
  max_drawdown_pct: number | null
  note: string
}

export interface BacktestTotals {
  results: number
  candidates: number
  families: number
  passes_by_window: Record<string, number>
}

export interface FamilyRow {
  family: string
  candidates: number
  best: Backtest | null
  verdicts: Partial<Record<string, BacktestVerdict>> // only the windows this family has a result in
  last_at: string
}

export interface BacktestsView {
  as_of: string
  totals: BacktestTotals
  windows: string[]
  families: FamilyRow[]
  rows: Backtest[]
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

export function useCalendar() {
  return useQuery({
    queryKey: ['calendar'], queryFn: () => getJson<CalendarView>('/api/calendar'), refetchInterval: MINUTE,
  })
}

export function useBacktests() {
  return useQuery({
    queryKey: ['backtests'], queryFn: () => getJson<BacktestsView>('/api/backtests'), refetchInterval: MINUTE,
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

// --- the Settings page (src/kestrel/views/settings.py) ----------------------------------------------------------

export interface YouSettings {
  name: string
}

export interface BenchmarkConfig {
  symbol: string
  label: string
}

export interface SettingsSource {
  id: string
  label: string
  kind: string
  reads: string
  stale_after: string
  refresh: string | null
  timeout: number | null
  token_env: string | null
  status: Source['status']
  last_success: string | null
  detail: string
}

export interface SettingsView {
  as_of: string
  you: YouSettings
  app: AppSettings
  benchmark: BenchmarkConfig
  profile: string
  contract_version: string
  version: string
  sources: SettingsSource[]
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'], queryFn: () => getJson<SettingsView>('/api/settings'), refetchInterval: MINUTE,
  })
}

// --- the Plan page (src/kestrel/views/plan.py) -------------------------------------------------------------------

export type TargetStatus = 'on' | 'over' | 'under' | 'unknown'
export type Health = 'ok' | 'watch' | 'alert' | 'none'
export type GapUnit = 'money' | 'pts' | 'x'

export interface TargetRow {
  id: string
  label: string
  symbols: string[]
  unit: '%' | 'x'
  target: number | null
  low: number | null
  high: number | null
  actual: number | null
  status: TargetStatus
  gap: number | null // in gap_unit's unit; null when unknown or gap_unit is null
  gap_unit: GapUnit | null // what `gap` is measured in — never infer money from where the row is grouped
  gap_text: string // "under the low end" / "over the high end" / "on plan" / "" when unknown
  note: string
}

export interface AccountTargets {
  account_id: string
  name: string // the account's name, or its bare id when no source ever sent it (see `known`)
  known: boolean // false: this account_id names no account any source sent — never link to it
  rows: TargetRow[]
}

export interface ThesisRow {
  symbol: string
  name: string
  health: Health
  reasons: string[]
  conviction: string
  status: string
  opened: string | null
  last_reviewed: string | null
  days_since_review: number | null
  held: boolean
  held_value: number
  account_names: string[]
  wrong_if: string[]
}

export interface GoalRow {
  id: string
  label: string
  scope_text: string
  measure: 'value' | 'deposits' // a value today, or deposits since the goal's year began
  current: number | null // null when unknown: see missing_accounts and unknown_reason
  target: number
  progress_pct: number | null // null when current is unknown
  by: string | null
  months_left: number | null
  monthly_needed: number | null // a straight line: for a value goal, before any market growth
  reached: boolean
  overdue: boolean // by has passed and it isn't reached (the view's answer; a far placeholder date never is)
  missing_accounts: string[] // account id(s) this goal names that no source sent
  unknown_reason: string // why current is unknown when no account is missing ("" otherwise)
}

export interface PlanView {
  as_of: string
  accounts: AccountTargets[]
  unscoped: TargetRow[]
  theses: ThesisRow[]
  goals: GoalRow[]
  counts: { off_plan: number; theses_alert: number; theses_watch: number }
}

export function usePlan() {
  return useQuery({ queryKey: ['plan'], queryFn: () => getJson<PlanView>('/api/plan'), refetchInterval: MINUTE })
}

// --- the Reserves page (src/kestrel/views/reserves.py) -------------------------------------------------------------

export interface CashLine {
  id: string
  name: string
  institution: string
  value: number
  rate_pct: number | null
  as_of: string
}

export interface DebtLine {
  id: string
  name: string
  institution: string
  owed: number // a credit balance (paid past zero) is below zero
  limit: number | null
  utilization_pct: number | null
  rate_pct: number | null
  as_of: string
}

export interface Spread {
  owed_rate_pct: number
  owed_name: string // the debt that rate is on
  earned_rate_pct: number
  yearly_cost: number // a year of interest on every rated debt, shown apart from what cash earns (never netted)
  yearly_earned: number
  pay_down: number | null // paying the dearest debt from cash: the smaller of what it owes and all the cash
  pay_down_saves: number | null // a year's interest that would save, at the best cash rate given up
}

export interface ReservesView {
  as_of: string
  cash: CashLine[]
  debts: DebtLine[]
  totals: { cash: number; owed: number; net: number; utilization_pct: number | null }
  spread: Spread | null
}

export function useReserves() {
  return useQuery({
    queryKey: ['reserves'], queryFn: () => getJson<ReservesView>('/api/reserves'), refetchInterval: MINUTE,
  })
}
