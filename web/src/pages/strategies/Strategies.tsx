// The strategy list: one card per strategy with its books and how its primary book is doing against the backtest.
import { Link } from '@tanstack/react-router'
import { BookMark, Delta } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type BookChip, type StrategyCard, useStrategies } from '../../lib/api'
import { pct } from '../../lib/format'
import { BandBar, VERDICT } from '../home/BooksPanel'

export const MONEY_WORD = { real: 'Real', paper: 'Paper' } as const

/** "Real · running · 4 open" */
export function chipText(book: BookChip): string {
  return `${MONEY_WORD[book.money]} · ${book.status} · ${book.open} open`
}

export function BookChips({ books }: { books: BookChip[] }) {
  return (
    <>
      {books.map((b) => (
        <span key={b.id} className="chip"><BookMark kind={b.money} color="var(--s2)" />{chipText(b)}</span>
      ))}
    </>
  )
}

/** The verdict in Home's words, with the sample size when it is too early to judge. */
export function verdictText(s: StrategyCard): string {
  if (s.verdict === 'early') return `${VERDICT.early} · ${s.trades} trades`
  if (s.verdict === 'none') return s.trades === 0 ? 'No closed trades yet' : 'No backtest to compare with'
  return VERDICT[s.verdict]
}

function Card({ s }: { s: StrategyCard }) {
  const title = `strategy-${s.id}`
  const band = s.band_lo != null && s.band_hi != null && s.per_trade_pct != null
  return (
    <article className="panel gap-4" aria-labelledby={title}>
      <div>
        <h2 id={title} className="text-lg font-semibold tracking-[-0.01em]">{s.name}</h2>
        {s.summary && <p className="text-sm text-ink2 mt-1">{s.summary}</p>}
      </div>
      {s.books.length > 0 && <div className="flex flex-wrap gap-2"><BookChips books={s.books} /></div>}
      <div>
        <div className="label">Per trade vs expected{s.book ? ` · ${s.book} book` : ''}</div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mt-2">
          {band && <BandBar lo={s.band_lo as number} hi={s.band_hi as number} actual={s.per_trade_pct as number} />}
          <span className="text-xs whitespace-nowrap" style={{ color: s.verdict === 'below' ? 'var(--ink1)' : 'var(--ink2)' }}>
            {s.verdict === 'below' && (
              <Icon name="alert" size={12}
                style={{ color: 'var(--warn)', display: 'inline-block', verticalAlign: '-2px', marginRight: 6 }} />
            )}
            {verdictText(s)}
            {band && <> · <Delta value={s.per_trade_pct as number}>{pct(s.per_trade_pct as number, 2)}</Delta></>}
          </span>
        </div>
      </div>
      <div className="mt-auto flex items-center justify-between border-t border-line pt-3 text-xs">
        <span className="text-ink3">{s.trades} closed trades</span>
        <Link to="/strategies/$strategyId" params={{ strategyId: s.id }} aria-label={`Open ${s.name}`}
          className="inline-flex items-center gap-1" style={{ color: 'var(--acc-ink)' }}>
          Open<Icon name="arrow" size={13} />
        </Link>
      </div>
    </article>
  )
}

export function Strategies() {
  const list = useStrategies()
  if (list.isPending) return <p className="text-ink3" role="status">Loading strategies…</p>
  if (!list.data) {
    return <div role="alert" className="panel">Strategies couldn&rsquo;t load: {list.error.message}</div>
  }
  const cards = list.data.strategies
  return (
    <>
      <header className="mb-5">
        <h1 className="text-3xl font-semibold tracking-[-0.025em]">Strategies</h1>
        <p className="text-ink2 mt-1.5">How each strategy trades, and whether it is behaving the way its backtest said it would.</p>
      </header>
      {cards.length === 0 ? (
        <div className="panel text-ink2">No strategies yet.</div>
      ) : (
        <div className="grid grid-cols-1 min-[900px]:grid-cols-2 gap-4">
          {cards.map((s) => <Card key={s.id} s={s} />)}
        </div>
      )}
    </>
  )
}
