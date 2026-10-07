import { type CSSProperties, useState } from 'react'
import { type ChartSeries, LineChart, LineKey } from '../../charts/LineChart'
import { Empty } from '../../charts/marks'
import { Panel, Seg } from '../../components/bits'
import type { StrategyView } from '../../lib/api'
import { pct } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'
import { sparse } from './Behaving'

const VIEWS = ['Chart', 'Table'] as const

/** The running average per trade for each book (the primary one solid if real, a paper one dashed) inside the
 *  expected 95% range, which narrows as trades add up. */
export function FunnelPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const f = v.funnel
  const n = Math.max(0, ...f.lines.map((l) => l.values.length))
  const trades = Array.from({ length: n }, (_, i) => String(i + 1))
  const series: ChartSeries[] = f.lines.map((l) => ({
    key: l.book_id, label: MONEY_WORD[l.money], color: 'var(--s2)', style: l.money === 'real' ? 'solid' : 'dashed',
    values: trades.map((_, i) => l.values[i] ?? null),
    endLabel: `${MONEY_WORD[l.money]} ${pct(l.values[l.values.length - 1], 2)}`,
  }))
  const band = f.expected != null ? { lo: f.lo, hi: f.hi, label: 'Expected range' } : undefined
  const thin = sparse(v.behaving.evidence)
  return (
    <Panel id="funnel" title="Average per trade, as trades add up" span={5} height={thin ? 372 : 412}
      subtitle={thin ? `${n} trades: the funnel is still wide — early readings swing`
        : band ? 'If the edge is real, the line settles inside the funnel' : 'The running average of every closed trade'}
      actions={n > 0 && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      {n === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : (
        <>
          <div className="flex flex-wrap gap-x-3.5 gap-y-1 mt-3 text-xs text-ink2">
            {series.map((s) => (
              <span key={s.key} className="inline-flex items-center gap-1.5"><LineKey color={s.color} style={s.style} />{s.label}</span>
            ))}
            {band && (
              <span className="inline-flex items-center gap-1.5"><LineKey color="var(--ref)" style="dotted" />Expected range (95%)</span>
            )}
          </div>
          <div className="mt-auto pt-2">
            {view === 'Chart' ? (
              <>
                <LineChart dates={trades} series={series} band={band} height={214} zeroLine
                  ariaLabel="Running average return per trade, with the expected range"
                  yFormat={(value, d) => pct(value, d)} valueFormat={(value) => pct(value, 2)} xLabel={(t) => t}
                  tipTitle={(t) => `After trade ${t}`} />
                <div className="text-2xs text-ink3 text-center">trade number</div>
              </>
            ) : (
              <div className="table-scroll overflow-y-auto" style={{ maxHeight: 236 }}>
                <table className="tbl" style={{ '--row': '34px' } as CSSProperties}>
                  <thead>
                    <tr>
                      <th>Trade</th>{series.map((s) => <th key={s.key} className="r">{s.label}</th>)}
                      {band && <th className="r">Expected range</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t, i) => (
                      <tr key={t}>
                        <td className="num">{t}</td>
                        {series.map((s) => (
                          <td key={s.key} className="r num">{s.values[i] == null ? '—' : pct(s.values[i] as number, 2)}</td>
                        ))}
                        {band && (
                          <td className="r num">
                            {f.lo[i] == null || f.hi[i] == null ? '—'
                              : `${pct(f.lo[i] as number, 2)} to ${pct(f.hi[i] as number, 2)}`}
                          </td>
                        )}
                      </tr>
                    )).reverse()}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </Panel>
  )
}
