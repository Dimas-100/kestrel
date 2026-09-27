// The book's value since it started, against the benchmark from the same day, with its drawdown as a small
// multiple sharing the same time axis underneath.
import { LineChart, LineKey } from '../../charts/LineChart'
import { Empty } from '../../charts/marks'
import { Panel } from '../../components/bits'
import type { BookView } from '../../lib/api'
import { monthLabel, pct, shortDate } from '../../lib/format'

export function EquityPanel({ v }: { v: BookView }) {
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
  return (
    <Panel id="equity" title="Equity" span={12}
      subtitle={`Since ${monthLabel(equity.dates[0], true)} · return ${pct(equity.return_pct, 1)} · worst drop ${pct(equity.max_drop_pct)}`}
      actions={<>
        <span className="inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--s2)" style="solid" />Book
        </span>
        <span className="inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ref)" style="dotted" />Benchmark
        </span>
      </>}>
      <div className="mt-3.5">
        <LineChart dates={equity.dates} height={190} zeroLine
          ariaLabel="The book's return since it started, against the benchmark"
          series={[
            { key: 'book', label: 'Book', values: equity.values, color: 'var(--s2)', style: 'solid', area: true },
            { key: 'benchmark', label: 'Benchmark', values: equity.benchmark, color: 'var(--ref)', style: 'dotted' },
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
    </Panel>
  )
}
