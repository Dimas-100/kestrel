import { useState } from 'react'
import { baseline, RANGES, type Range, windowPoints } from '../../charts/geometry'
import { LineChart, LineKey } from '../../charts/LineChart'
import { Delta, Panel, Seg, Stat } from '../../components/bits'
import type { NetWorth } from '../../lib/api'
import { compactMoney, monthLabel, money, pct, shortDate, signedMoney, splitCents } from '../../lib/format'

export function NetWorthPanel({ nw }: { nw: NetWorth }) {
  const [range, setRange] = useState<Range>('1Y')
  const [view, setView] = useState<'Chart' | 'Table'>('Chart')
  const points = windowPoints(nw.points, range)
  const base = baseline(points)
  const growth = points.length ? points[points.length - 1].value - base[base.length - 1] : 0
  const [whole, cents] = splitCents(nw.total)
  return (
    <Panel id="net-worth" title="Net worth" span={8} height={372}
      actions={<>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ink1)" style="solid" />Net worth
        </span>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ref)" style="dotted" />Start + deposits
        </span>
        <Seg label="Range" options={RANGES} value={range} onChange={setRange} />
        <Seg label="View" options={['Chart', 'Table'] as const} value={view} onChange={setView} />
      </>}>
      <div className="flex flex-wrap items-end gap-x-9 gap-y-3 mt-3.5">
        <div className="text-[38px] sm:text-5xl font-semibold tracking-[-0.035em] leading-none">
          {whole}<span className="text-ink3">.{cents}</span>
        </div>
        <div className="flex flex-wrap gap-x-7 gap-y-3 pb-1">
          <Stat label="Today" sub={nw.today.pct != null && pct(nw.today.pct, 2)}>
            <Delta value={nw.today.amount}>{signedMoney(nw.today.amount)}</Delta>
          </Stat>
          <Stat label="Month" sub={nw.month.pct != null && pct(nw.month.pct, 2)}>
            <Delta value={nw.month.amount}>{signedMoney(nw.month.amount)}</Delta>
          </Stat>
          <Stat label="Year" sub={<>incl. <span className="num">{money(nw.year_flows, false)}</span> deposited</>}>
            <Delta value={nw.year.amount}>{signedMoney(nw.year.amount)}</Delta>
          </Stat>
          <Stat label="Market" sub={`over ${range}`}>
            <Delta value={growth} digits={0}>{signedMoney(growth, false)}</Delta>
          </Stat>
        </div>
      </div>
      <div className="mt-auto pt-3">
        {points.length === 0 ? (
          <p className="text-ink3">No history yet. The chart appears once your accounts have a few days of data.</p>
        ) : view === 'Chart' ? (
          <LineChart dates={points.map((p) => p.date)} height={196}
            ariaLabel="Net worth against your starting value plus deposits"
            series={[
              { key: 'nw', label: 'Net worth', values: points.map((p) => p.value), color: 'var(--ink1)', style: 'solid',
                area: true },
              { key: 'base', label: 'Start + deposits', values: base, color: 'var(--ref)', style: 'dotted', step: true },
            ]}
            yFormat={compactMoney} valueFormat={(v) => money(v, false)}
            xLabel={(d) => monthLabel(d, range === '1M' || range === '3M')} tipTitle={(d) => shortDate(d)} />
        ) : (
          <div className="overflow-y-auto" style={{ maxHeight: 196 }}>
            <table className="tbl">
              <thead><tr><th>Date</th><th className="r">Net worth</th><th className="r">Start + deposits</th></tr></thead>
              <tbody>
                {points.map((p, i) => (
                  <tr key={p.date}>
                    <td>{shortDate(p.date)}</td>
                    <td className="r num">{money(p.value)}</td>
                    <td className="r num">{money(base[i])}</td>
                  </tr>
                )).reverse()}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Panel>
  )
}
