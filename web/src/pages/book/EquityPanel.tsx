// The book's value since it started, against the named benchmark from the same day, with its drawdown as a small
// multiple sharing the same time axis underneath. Chart or table.
import { type CSSProperties, useState } from 'react'
import { LineChart, LineKey } from '../../charts/LineChart'
import { Empty } from '../../charts/marks'
import { Panel, Seg } from '../../components/bits'
import type { BookView } from '../../lib/api'
import { monthLabel, pct, shortDate } from '../../lib/format'

const VIEWS = ['Chart', 'Table'] as const

/** "Since 13 Aug · return +9.4% · worst drop −2.1% · measured on the whole account's net liq" */
export function equitySubtitle(v: BookView): string {
  const e = v.equity
  const basis = v.book.capital_basis ? ` · measured on ${v.book.capital_basis}` : ''
  return `Since ${monthLabel(e.dates[0], true)} · return ${pct(e.return_pct, 1)} · worst drop ${pct(e.max_drop_pct)}${basis}`
}

export function EquityPanel({ v }: { v: BookView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const { equity, drawdown } = v
  if (equity.dates.length < 2) {
    return (
      <Panel id="equity" title="Equity" subtitle="Value since the book started, against the benchmark" span={12}
        height={280}>
        <Empty>No history yet. The chart appears once this book has a few days of data.</Empty>
      </Panel>
    )
  }
  const short = equity.dates.length < 90
  const hasBenchmark = equity.benchmark.some((b) => b != null)
  const later = hasBenchmark && equity.benchmark_from != null && equity.benchmark_from !== equity.dates[0]
  return (
    <Panel id="equity" title="Equity" span={12} subtitle={equitySubtitle(v)}
      actions={<>
        <span className="inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--s2)" style="solid" />Book
        </span>
        {hasBenchmark && (
          <span className="inline-flex items-center gap-1.5 text-xs text-ink2">
            <LineKey color="var(--ref)" style="dotted" />{equity.benchmark_label}
          </span>
        )}
        <Seg label="View" options={VIEWS} value={view} onChange={setView} />
      </>}>
      {!hasBenchmark && <p className="text-xs text-ink3 mt-2">No benchmark history over these dates.</p>}
      {later && (
        <p className="text-xs text-ink3 mt-2">
          {equity.benchmark_label} is drawn from {monthLabel(equity.benchmark_from as string, true)}, where its history
          starts, and indexed from that day.
        </p>
      )}
      {view === 'Chart' ? (
        <>
          <div className="mt-3.5">
            <LineChart dates={equity.dates} height={190} zeroLine
              ariaLabel={`The book's return since it started, against ${equity.benchmark_label}`}
              series={[
                { key: 'book', label: 'Book', values: equity.values, color: 'var(--s2)', style: 'solid', area: true },
                ...(hasBenchmark ? [{ key: 'benchmark', label: equity.benchmark_label, values: equity.benchmark,
                  color: 'var(--ref)', style: 'dotted' as const }] : []),
              ]}
              yFormat={(n) => pct(n, 0)} valueFormat={(n) => pct(n)} xLabel={(d) => monthLabel(d, short)}
              tipTitle={(d) => shortDate(d)} />
          </div>
          <div className="mt-3">
            <div className="label mb-1">Drawdown</div>
            <LineChart dates={drawdown.dates} height={80} compact
              ariaLabel="Percent below the running peak"
              series={[
                { key: 'drawdown', label: 'Drawdown', values: drawdown.values, color: 'var(--down)', style: 'solid',
                  area: true },
              ]}
              yFormat={(n) => pct(n, 0)} valueFormat={(n) => pct(n)} xLabel={(d) => monthLabel(d, short)}
              tipTitle={(d) => shortDate(d)} />
          </div>
        </>
      ) : (
        <div className="table-scroll overflow-y-auto mt-3.5" style={{ maxHeight: 290 }}>
          <table className="tbl" style={{ '--row': '34px', minWidth: 420 } as CSSProperties}>
            <thead>
              <tr><th>Day</th><th className="r">Book</th>{hasBenchmark && <th className="r">{equity.benchmark_label}</th>}<th className="r">Drawdown</th></tr>
            </thead>
            <tbody>
              {equity.dates.map((d, i) => (
                <tr key={d}>
                  <td className="num">{shortDate(d)}</td>
                  <td className="r num">{pct(equity.values[i])}</td>
                  {hasBenchmark && <td className="r num">{equity.benchmark[i] == null ? '—' : pct(equity.benchmark[i] as number)}</td>}
                  <td className="r num">{pct(drawdown.values[i] ?? 0)}</td>
                </tr>
              )).reverse()}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
