// The Books list: every book, real money first then paper, with its sparkline and how it trades against expected.
import { Link } from '@tanstack/react-router'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Missing, MoneyBadge, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type BooksRow, useBooks, useShell } from '../../lib/api'
import { money, pct, shortDate, sinceLabel, timeHM } from '../../lib/format'
import { BandBar, VERDICT } from '../home/BooksPanel'

/** A tiny 60-point line, coloured by whether the book ended above or below where it started. */
export function Spark({ values }: { values: number[] }) {
  if (values.length < 2) return <Missing />
  const w = 68
  const h = 22
  const pad = 2
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const span = hi - lo || 1
  const x = (i: number) => (i / (values.length - 1)) * (w - pad * 2) + pad
  const y = (v: number) => h - pad - ((v - lo) / span) * (h - pad * 2)
  const d = values.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const up = values[values.length - 1] >= values[0]
  return (
    <svg width={w} height={h} aria-label={up ? 'trending up' : 'trending down'} role="img" style={{ display: 'block' }}>
      <path d={d} fill="none" stroke={up ? 'var(--up)' : 'var(--down)'} strokeWidth={1.5} strokeLinecap="round"
        strokeLinejoin="round" />
    </svg>
  )
}

function Row({ b, tz, now }: { b: BooksRow; tz: string; now: string }) {
  return (
    <tr>
      <td>
        <div className="flex items-center gap-3">
          <BookMark kind={b.money} size={14} />
          <div>
            <Link to="/books/$bookId" params={{ bookId: b.id }} className="font-medium" style={{ color: 'inherit' }}>
              {b.name}
            </Link>
            <div className="text-xs text-ink3 mt-0.5">{b.strategy} · since {sinceLabel(b.started, now)}</div>
          </div>
        </div>
      </td>
      <td><MoneyBadge money={b.money} /></td>
      <td>
        <div className="flex items-center gap-2 text-[13px] capitalize">
          <span className="w-2 h-2 rounded-full" style={b.status === 'running'
            ? { background: 'var(--good)' } : { boxShadow: 'inset 0 0 0 1.5px var(--ink3)' }} />
          {b.status}
        </div>
      </td>
      <td className="r num">{money(b.value)}</td>
      <td className="r">{b.since_pct == null ? <Missing /> : <Delta value={b.since_pct} digits={1}>{pct(b.since_pct)}</Delta>}</td>
      <td><Spark values={b.spark} /></td>
      <td className="r num">{b.trades}</td>
      <td style={{ paddingLeft: 28 }}>
        {b.band_lo != null && b.band_hi != null && b.per_trade_pct != null && (
          <BandBar lo={b.band_lo} hi={b.band_hi} actual={b.per_trade_pct} />
        )}
        <div className="text-[11px] mt-1.5 flex items-center gap-1.5 whitespace-nowrap"
          style={{ color: b.verdict === 'below' ? 'var(--ink1)' : 'var(--ink3)' }}>
          {b.verdict === 'below' && <Icon name="alert" size={12} style={{ color: 'var(--warn)' }} />}
          {VERDICT[b.verdict]}
          {b.verdict === 'early' && ` · ${b.trades} trades`}
        </div>
      </td>
      <td>
        {b.slots_total ? `${b.slots_used} of ${b.slots_total}` : <Missing />}
      </td>
      <td className="num text-[11px] text-ink3">
        {b.next_run ? `${shortDate(b.next_run, tz).slice(0, 3)} ${timeHM(b.next_run, tz)}` : <Missing />}
      </td>
    </tr>
  )
}

export function Books() {
  const list = useBooks()
  const shell = useShell()
  if (list.isPending) return <p className="text-ink3" role="status">Loading books…</p>
  if (!list.data) {
    return <div role="alert" className="panel">Books couldn&rsquo;t load: {list.error.message}</div>
  }
  const v = list.data
  const tz = shell.data?.app.timezone ?? 'UTC'
  return (
    <>
      <header className="mb-5">
        <h1 className="text-3xl font-semibold tracking-[-0.025em]">Books</h1>
        <p className="text-ink2 mt-1.5">Every book of money, real and paper, side by side.</p>
      </header>
      <Panel id="books-list" title="Books" span={12}
        subtitle={`Real ${money(v.real_value)} · Paper ${money(v.paper_value)}`}>
        {v.rows.length === 0 ? (
          <Empty>No books yet. A book appears once a trading feed reports one.</Empty>
        ) : (
          <div className="table-scroll mt-4">
            <table className="tbl" style={{ minWidth: 980 }}>
              <thead>
                <tr>
                  <th>Book</th><th>Money</th><th>Status</th><th className="r">Value</th>
                  <th className="r">Since start</th><th>60 days</th><th className="r">Trades</th>
                  <th style={{ paddingLeft: 28 }}>Per trade vs expected</th><th>Slots</th><th>Next run</th>
                </tr>
              </thead>
              <tbody>
                {v.rows.map((b) => <Row key={b.id} b={b} tz={tz} now={v.as_of} />)}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  )
}
