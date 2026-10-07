// One strategy: how it trades and whether it is behaving the way its backtest said it would.
import { BookMark, Seg } from '../../components/bits'
import { type Expected, HttpError, type Money, type StrategyView, useShell, useStrategy } from '../../lib/api'
import { monthLabel } from '../../lib/format'
import { Soon } from '../Soon'
import { BookChips, MONEY_WORD } from '../strategies/Strategies'
import { AdherencePanel } from './AdherencePanel'
import { AnatomySection } from './Anatomy'
import { StrategyAttentionPanel } from './AttentionPanel'
import { BehavingPanel, ScorecardPanel } from './Behaving'
import { CyclePanel } from './CyclePanel'
import { FunnelPanel } from './FunnelPanel'
import { HowItTrades } from './HowItTrades'
import { MonthlyPanel } from './MonthlyPanel'
import { PerformancePanel } from './PerformancePanel'
import { ResearchPanel } from './ResearchPanel'
import { ReviewPanel } from './ReviewPanel'
import { SlotsPanel } from './SlotsPanel'
import { TradesPanel } from './TradesPanel'
import { WorthPanel } from './WorthPanel'

const BOOKS = ['Real', 'Paper'] as const

/** "Backtest 2006–2020" */
export function backtestText(expected: Expected): string {
  const source = expected.source || 'backtest'
  return `${source[0].toUpperCase()}${source.slice(1)}${expected.window ? ` ${expected.window}` : ''}`
}

function Header({ v, onBook }: { v: StrategyView; onBook: (book: Money) => void }) {
  return (
    <header className="mb-5">
      <div className="label">Strategy</div>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">{v.name}</h1>
          {v.summary && <p className="text-ink2 mt-1.5 max-w-[680px]">{v.summary}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <BookChips books={v.books} />
          {v.expected && <span className="chip"><BookMark kind="expected" />{backtestText(v.expected)}</span>}
          {v.rules.version && (
            <span className="chip">Rules {v.rules.version}{v.rules.effective && ` · since ${monthLabel(v.rules.effective, true)}`}</span>
          )}
        </div>
      </div>
      {v.toggle && v.book && (
        <div className="mt-4">
          <Seg label="Book" options={BOOKS} value={MONEY_WORD[v.book]}
            onChange={(word) => onBook(word === 'Real' ? 'real' : 'paper')} />
        </div>
      )}
    </header>
  )
}

export function Strategy({ id, book, onBook }: { id: string; book: Money; onBook: (book: Money) => void }) {
  const strategy = useStrategy(id, book)
  const shell = useShell()
  const tz = shell.data?.app.timezone ?? 'UTC'
  if (strategy.isPending) return <p className="text-ink3" role="status">Loading the strategy…</p>
  if (!strategy.data) {
    if (strategy.error instanceof HttpError && strategy.error.status === 404) {
      return <Soon title="Not found" text="There is no page here. Pick one from the menu." />
    }
    return <div role="alert" className="panel">This strategy couldn&rsquo;t load: {strategy.error.message}</div>
  }
  const v = strategy.data
  return (
    <>
      <Header v={v} onBook={onBook} />
      <div className="grid12">
        <StrategyAttentionPanel items={v.attention} />
        <ReviewPanel review={v.review} />
        <PerformancePanel p={v.performance} />
        <HowItTrades rules={v.rules} />
        <CyclePanel c={v.cycle} tz={tz} />
        <ScorecardPanel v={v} />
        <BehavingPanel v={v} />
        <FunnelPanel v={v} />
        <SlotsPanel v={v} />
        {/* keyed by book: switching Real | Paper starts again from that book's newest charted trade */}
        <AnatomySection key={v.primary ?? 'none'} v={v} />
        <AdherencePanel a={v.adherence} />
        <ResearchPanel r={v.research} tz={tz} />
        <WorthPanel v={v} />
        <MonthlyPanel v={v} />
        <TradesPanel v={v} />
      </div>
    </>
  )
}
