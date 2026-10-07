// One book: its equity against the benchmark, drawdown, scorecard, open positions, trades and runs.
import { Link } from '@tanstack/react-router'
import { MoneyBadge } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type BookView, HttpError, useBook, useShell } from '../../lib/api'
import { shortDate, sinceLabel, timeHM } from '../../lib/format'
import { LOOK } from '../home/AttentionPanel'
import { Soon } from '../Soon'
import { EquityPanel } from './EquityPanel'
import { PositionsPanel } from './PositionsPanel'
import { RunsPanel } from './RunsPanel'
import { ScorecardPanel } from './ScorecardPanel'
import { TradesPanel } from './TradesPanel'

function Header({ v, tz, now }: { v: BookView; tz: string; now: string }) {
  return (
    <header className="mb-5">
      <div className="label">Book</div>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">{v.book.name}</h1>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mt-2">
            <MoneyBadge money={v.book.money} />
            <span className="text-ink2 capitalize">{v.book.status}</span>
            <Link to="/strategies/$strategyId" params={{ strategyId: v.strategy_id }} className="text-xs"
              style={{ color: 'var(--acc-ink)' }}>
              {v.strategy_name}
            </Link>
            <span className="text-xs text-ink3">since {sinceLabel(v.book.started, now)}</span>
          </div>
        </div>
        <div className="text-xs text-ink3 whitespace-nowrap">
          {v.book.next_run
            ? <>Next run {shortDate(v.book.next_run, tz)} {timeHM(v.book.next_run, tz)}</>
            : 'No run scheduled'}
        </div>
      </div>
      {v.attention.length > 0 && (
        <ul className="mt-4 flex flex-col gap-1.5" aria-label="Needs you on this book">
          {v.attention.map((a, i) => {
            const look = LOOK[a.level]
            return (
              <li key={`${a.title}-${i}`} className="flex items-start gap-2 text-sm">
                <Icon name={look.icon} size={15} style={{ color: look.color, flex: 'none', marginTop: 2 }} />
                <span><span className="label mr-2" style={{ color: look.color }}>{look.word}</span>{a.title}
                  {a.detail && <span className="text-ink3"> · {a.detail}</span>}</span>
              </li>
            )
          })}
        </ul>
      )}
    </header>
  )
}

export function Book({ id }: { id: string }) {
  const book = useBook(id)
  const shell = useShell()
  if (book.isPending) return <p className="text-ink3" role="status">Loading the book…</p>
  if (!book.data) {
    if (book.error instanceof HttpError && book.error.status === 404) {
      return <Soon title="Not found" text="There is no page here. Pick one from the menu." />
    }
    return <div role="alert" className="panel">This book couldn&rsquo;t load: {book.error.message}</div>
  }
  const v = book.data
  const tz = shell.data?.app.timezone ?? 'UTC'
  return (
    <>
      <Header v={v} tz={tz} now={v.as_of} />
      <div className="grid12">
        <EquityPanel v={v} />
        <ScorecardPanel v={v} />
        <PositionsPanel v={v} />
        <TradesPanel v={v} />
        <RunsPanel v={v} tz={tz} />
      </div>
    </>
  )
}
