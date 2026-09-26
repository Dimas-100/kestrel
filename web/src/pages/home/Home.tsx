import { Delta } from '../../components/bits'
import { type HomeView, useHome, useShell } from '../../lib/api'
import { signedMoney } from '../../lib/format'
import { AllocationPanel } from './AllocationPanel'
import { AttentionPanel } from './AttentionPanel'
import { BooksPanel } from './BooksPanel'
import { ComparisonPanel, period } from './ComparisonPanel'
import { NetWorthPanel } from './NetWorthPanel'
import { PositionsPanel, TodayPanel } from './TodayAndPositions'

/** The sentence under the page title, written from the data. */
export function summaryParts(h: HomeView): { trading: string | null; needs: string } {
  const gap = h.summary.gap_pts
  const { phrase } = period(h.comparison)
  const trading = gap == null ? null : Math.abs(gap) < 0.05
    ? `Trading is level with your index money ${phrase}.`
    : `Trading is ${gap > 0 ? 'ahead of' : 'behind'} your index money by ${Math.abs(gap).toFixed(1)} pts ${phrase}.`
  const n = h.summary.needs_you
  const needs = n === 0 ? 'Nothing needs you.' : n === 1 ? 'One item needs you.' : `${n} items need you.`
  return { trading, needs }
}

export function Home() {
  const home = useHome()
  const shell = useShell()
  if (home.isPending) {
    return <p className="text-ink3" role="status">Loading your money…</p>
  }
  if (home.isError) {
    return <div role="alert" className="panel">Home couldn&rsquo;t load: {home.error.message}</div>
  }
  const h = home.data
  const tz = shell.data?.app.timezone ?? 'UTC'
  const { trading, needs } = summaryParts(h)
  return (
    <>
      <header className="mb-5">
        <h1 className="text-[28px] font-semibold tracking-[-0.025em]">Home</h1>
        <p className="text-ink2 mt-1.5">
          All your money is <Delta value={h.summary.day_change}>{signedMoney(h.summary.day_change)}</Delta> today.{' '}
          {trading && <>{trading} </>}{needs}
        </p>
      </header>
      <div className="grid12">
        <NetWorthPanel nw={h.net_worth} />
        <AllocationPanel slices={h.allocation} accounts={h.accounts} />
        <ComparisonPanel c={h.comparison} />
        <AttentionPanel items={h.attention} />
        <BooksPanel books={h.books} tz={tz} now={h.as_of} />
        <TodayPanel runs={h.today} now={h.as_of} tz={tz} />
        <PositionsPanel positions={h.positions} />
      </div>
    </>
  )
}

