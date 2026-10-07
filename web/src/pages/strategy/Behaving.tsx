import { type CSSProperties, useState } from 'react'
import { Histogram, HistogramTable } from '../../charts/Histogram'
import { Empty } from '../../charts/marks'
import { BookMark, Panel, Seg } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { ScoreRow, StrategyView } from '../../lib/api'
import { num, pct } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'

const VIEWS = ['Chart', 'Table'] as const

/** Under 30 trades a histogram is a sketch: the panel says so and draws it smaller. */
export const sparse = (evidence: StrategyView['behaving']['evidence']) => evidence === 'early' || evidence === 'limited'

export function BehavingPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const money = v.book ?? 'real'
  const word = MONEY_WORD[money]
  const backtest = v.behaving.buckets.some((b) => b.expected != null)
  const thin = sparse(v.behaving.evidence)
  return (
    <Panel id="behaving" title="Is it behaving?" span={7} height={thin ? 372 : 412}
      subtitle={v.primary == null ? undefined
        : thin ? `${v.behaving.evidence_text} — a sketch, not a verdict`
          : `Where each ${money} trade landed${backtest ? ', against the spread of outcomes in the backtest' : ''}`}
      actions={v.primary != null && <>
        <span className="inline-flex items-center gap-1.5 text-xs text-ink2 whitespace-nowrap">
          <BookMark kind={money} color="var(--s2)" />{word} trades ({v.behaving.trades})
        </span>
        {backtest && (
          <span className="inline-flex items-center gap-1.5 text-xs text-ink2 whitespace-nowrap">
            <BookMark kind="expected" />Backtest
          </span>
        )}
        <Seg label="View" options={VIEWS} value={view} onChange={setView} />
      </>}>
      {v.primary == null ? (
        <Empty>No book trades this strategy yet.</Empty>
      ) : (
        <>
          <div className="mt-auto pt-3">
            {view === 'Chart'
              ? <Histogram buckets={v.behaving.buckets} money={money} ariaLabel={`${word} trade returns against the backtest`} />
              : <HistogramTable buckets={v.behaving.buckets} money={money} />}
          </div>
          <p className="text-xs text-ink3 mt-2">
            Return per trade, in 1-point buckets. Bars show the share of trades in each bucket.
            {thin && ' Too few trades to read a shape yet.'}
          </p>
        </>
      )}
    </Panel>
  )
}

function figure(row: ScoreRow, value: number | null): string {
  if (value == null) return '—'
  if (row.key === 'win_rate') return `${num(value, 1)}%`
  if (row.key === 'per_month') return num(value, 1)
  return pct(value, 2)
}

const STATUS: Record<'ok' | 'above' | 'below', { icon: 'check' | 'alert'; color: string; text: string }> = {
  ok: { icon: 'check', color: 'var(--good)', text: 'as expected' },
  above: { icon: 'alert', color: 'var(--warn)', text: 'higher than expected' },
  below: { icon: 'alert', color: 'var(--warn)', text: 'lower than expected' },
}

function Status({ status }: { status: ScoreRow['status'] }) {
  if (status === 'none') return null
  if (status === 'early') return <span className="text-2xs text-ink3 whitespace-nowrap">too early</span>
  const look = STATUS[status]
  return (
    <span className="inline-flex" style={{ color: look.color }}>
      <Icon name={look.icon} size={15} /><span className="sr-only">{look.text}</span>
    </span>
  )
}

export function ScorecardPanel({ v }: { v: StrategyView }) {
  const b = v.behaving
  const word = MONEY_WORD[v.book ?? 'real']
  const early = b.scorecard.some((r) => r.status === 'early')
  return (
    <Panel id="scorecard" title="Scorecard" span={5} height={452}
      subtitle={v.primary == null ? undefined : v.expected ? `${word} book against the backtest` : `${word} book`}>
      {v.primary == null ? (
        <Empty>No book trades this strategy yet.</Empty>
      ) : (
        <>
          <table className="tbl mt-3" style={{ '--row': '40px', tableLayout: 'fixed' } as CSSProperties}>
            <colgroup><col /><col style={{ width: 74 }} /><col style={{ width: 74 }} /><col style={{ width: early ? 58 : 28 }} /></colgroup>
            <thead>
              <tr>
                <th>Measure</th><th className="r">{word}</th><th className="r">Expected</th>
                <th className="r"><span className="sr-only">Status</span></th>
              </tr>
            </thead>
            <tbody>
              {b.scorecard.map((row) => (
                <tr key={row.key}>
                  <td className="text-sm text-ink2">{row.label}</td>
                  <td className="r"><span className="num font-medium">{figure(row, row.actual)}</span></td>
                  <td className="r"><span className="num text-ink3">{figure(row, row.expected)}</span></td>
                  <td className="r" style={{ paddingRight: 0 }}><Status status={row.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!v.expected && <p className="text-xs text-ink3 mt-3">No backtest to compare with.</p>}
          <p className="text-xs mt-3" style={{ color: sparse(b.evidence) || b.evidence === 'none' ? 'var(--ink2)' : 'var(--ink3)' }}>
            {b.evidence_text}
          </p>
          {b.other && (
            <div className="mt-auto border-t border-line pt-3.5 flex items-center gap-2.5 text-xs text-ink2">
              <BookMark kind={b.other.money} color="var(--s2)" />
              <span>
                {MONEY_WORD[b.other.money]}, same rules: <span className="num text-ink1">{b.other.trades}</span> trades
                {' · '}<span className="num text-ink1">{b.other.per_trade_pct == null ? '—' : pct(b.other.per_trade_pct, 2)}</span>
                {' · '}<span className="num text-ink1">{b.other.win_rate == null ? '—' : `${num(b.other.win_rate, 1)}%`}</span> wins
              </span>
            </div>
          )}
        </>
      )}
    </Panel>
  )
}
