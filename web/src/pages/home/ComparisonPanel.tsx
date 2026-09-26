import { useState } from 'react'
import { type ChartSeries, LineChart, LineKey } from '../../charts/LineChart'
import { Delta, Panel, Seg } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Comparison, Line } from '../../lib/api'
import { monthLabel, pct, shortDate } from '../../lib/format'

const STYLE: Record<Line['key'], Pick<ChartSeries, 'color' | 'style'>> = {
  trading: { color: 'var(--s2)', style: 'solid' },
  long_term: { color: 'var(--s1)', style: 'solid' },
  benchmark: { color: 'var(--ref)', style: 'dotted' },
}

const DAY_MS = 86_400_000
const GRACE_DAYS = 7 // a year's first close can fall as late as 4 January (New Year's Day, then a weekend)

/** The comparison's period in words. Every line starts on the same day; when that day is later than the window's
 *  own start (say a book opened in July), the words name it: "since 1 Jul". */
export function period(c: Comparison): { phrase: string; title: string } {
  const last = c.dates[c.dates.length - 1] ?? c.start
  const opens = c.window === 'ytd' ? Date.parse(`${c.start.slice(0, 4)}-01-01`) : Date.parse(last) - 365 * DAY_MS
  if (Date.parse(c.start) - opens > GRACE_DAYS * DAY_MS) {
    const day = monthLabel(c.start, true)
    return { phrase: `since ${day}`, title: `Since ${day}` }
  }
  return c.window === 'ytd'
    ? { phrase: 'this year', title: 'Year to date' }
    : { phrase: 'over the past 12 months', title: 'Past 12 months' }
}

export function verdict(c: Comparison): { headline: string; caveat: string } | null {
  if (c.gap_pts == null) return null
  const { phrase } = period(c)
  const gap = Math.abs(c.gap_pts).toFixed(1)
  const trading = c.lines.find((l) => l.key === 'trading')
  const longTerm = c.lines.find((l) => l.key === 'long_term')
  const drops = trading && longTerm ? ` (${pct(trading.max_drop_pct)} vs ${pct(longTerm.max_drop_pct)})` : ''
  const equalDrop = trading && longTerm && Math.abs(trading.max_drop_pct - longTerm.max_drop_pct) < 0.05
  const drop = equalDrop ? 'an equal' : c.shallower ? 'a shallower' : 'a deeper'
  const headline = Math.abs(c.gap_pts) < 0.05
    ? `Trading is level with your index money ${phrase}.`
    : `Trading is ${c.gap_pts > 0 ? 'ahead' : 'behind'} by ${gap} pts ${phrase}, with ${drop} worst drop${drops}.`
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
      subtitle={`${period(c).title} · real money only · all start at 0%`}
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
                    <tr key={l.key}><td>{l.label}</td><td className="r"><Delta value={l.return_pct} digits={1}>{pct(l.return_pct)}</Delta></td>
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
                <div className="num text-xl font-medium mt-1"><Delta value={l.return_pct} digits={1}>{pct(l.return_pct)}</Delta></div>
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
