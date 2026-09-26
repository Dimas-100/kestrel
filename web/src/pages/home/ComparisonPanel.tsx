import { useState } from 'react'
import { type ChartSeries, LineChart, LineKey } from '../../charts/LineChart'
import { Panel, Seg } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Comparison, Line } from '../../lib/api'
import { monthLabel, pct, shortDate } from '../../lib/format'

const STYLE: Record<Line['key'], Pick<ChartSeries, 'color' | 'style'>> = {
  trading: { color: 'var(--s2)', style: 'solid' },
  long_term: { color: 'var(--s1)', style: 'solid' },
  benchmark: { color: 'var(--ref)', style: 'dotted' },
}

export function verdict(c: Comparison): { headline: string; caveat: string } | null {
  if (c.gap_pts == null) return null
  const period = c.window === 'ytd' ? 'this year' : 'over the past 12 months'
  const gap = Math.abs(c.gap_pts).toFixed(1)
  const trading = c.lines.find((l) => l.key === 'trading')
  const longTerm = c.lines.find((l) => l.key === 'long_term')
  const drops = trading && longTerm ? ` (${pct(trading.max_drop_pct)} vs ${pct(longTerm.max_drop_pct)})` : ''
  const headline = Math.abs(c.gap_pts) < 0.05
    ? `Trading is level with your index money ${period}.`
    : `Trading is ${c.gap_pts > 0 ? 'ahead' : 'behind'} by ${gap} pts ${period}, with a ${c.shallower ? 'shallower' : 'deeper'} worst drop${drops}.`
  const early = c.review_at != null && c.real_trades < c.review_at
  const caveat = early
    ? `${c.real_trades} real trades so far — early evidence. The strategy is reviewed at ${c.review_at}.`
    : `${c.real_trades} real trades so far.`
  return { headline, caveat }
}

export function ComparisonPanel({ c }: { c: Comparison }) {
  const [view, setView] = useState<'Chart' | 'Table'>('Chart')
  const v = verdict(c)
  const series: ChartSeries[] = c.lines.map((l) => ({ key: l.key, label: l.label, values: l.values, ...STYLE[l.key] }))
  return (
    <Panel id="comparison" title="Trading vs your index money" span={7} height={372}
      subtitle={`${c.window === 'ytd' ? 'Year to date' : 'Past 12 months'} · real money only · all start at 0%`}
      actions={<Seg label="View" options={['Chart', 'Table'] as const} value={view} onChange={setView} />}>
      {c.lines.length === 0 ? (
        <p className="text-ink3 mt-6">No history yet. The comparison appears once your accounts have a few days of data.</p>
      ) : (
        <div className="flex flex-col sm:flex-row gap-4 sm:gap-6 mt-3.5 min-h-0">
          <div className="flex-1 min-w-0">
            {view === 'Chart' ? (
              <LineChart dates={c.dates} series={series} height={190} zeroLine
                ariaLabel="Return since the start of the window: trading, long-term and the benchmark"
                yFormat={(n) => pct(n, 0)} valueFormat={(n) => pct(n)} xLabel={(d) => monthLabel(d)}
                tipTitle={(d) => shortDate(d)} />
            ) : (
              <table className="tbl">
                <thead><tr><th>Line</th><th className="r">Return</th><th className="r">Worst drop</th></tr></thead>
                <tbody>
                  {c.lines.map((l) => (
                    <tr key={l.key}><td>{l.label}</td><td className="r num">{pct(l.return_pct)}</td>
                      <td className="r num">{pct(l.max_drop_pct)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="grid grid-cols-3 gap-2.5 sm:flex sm:flex-col sm:w-[150px] flex-none">
            {c.lines.map((l) => (
              <div key={l.key}>
                <div className="flex items-center gap-2 text-xs text-ink2">
                  <LineKey {...STYLE[l.key]} />{l.label}
                </div>
                <div className="num text-xl font-medium mt-1">{pct(l.return_pct)}</div>
                <div className="num text-[11px] text-ink3">max drop {pct(l.max_drop_pct)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {v && (
        <div className="mt-auto flex gap-3 items-start rounded-lg border border-line bg-panel2 px-3.5 py-3">
          <Icon name="scale" size={18} style={{ color: 'var(--ink2)', marginTop: 1 }} />
          <div>
            <div className="text-[13px] font-medium">{v.headline}</div>
            <div className="text-xs text-ink3 mt-0.5">{v.caveat}</div>
          </div>
        </div>
      )}
    </Panel>
  )
}
