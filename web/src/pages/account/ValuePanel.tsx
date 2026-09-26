import { type CSSProperties, useState } from 'react'
import { baseline } from '../../charts/geometry'
import { LineChart, LineKey } from '../../charts/LineChart'
import { Empty } from '../../charts/marks'
import { CATEGORY_COLOR, Missing, Panel, Seg } from '../../components/bits'
import type { AccountView, Growth, ValuePoint, Window } from '../../lib/api'
import { compactMoney, money, monthLabel, shortDate, signedMoney, splitCents } from '../../lib/format'
import { WINDOW_WORD, WindowSeg } from '../accounts/GrowthPanel'

const VIEWS = ['Chart', 'Table'] as const
const DAY_MS = 86_400_000

/** The window's points: from the day its starting value is from (all of them when it has no growth yet). */
export function pointsIn(points: ValuePoint[], growth: Growth | null): ValuePoint[] {
  return growth ? points.filter((p) => p.date >= growth.start_date) : points
}

/** The account's value over the window, with the dotted "start + deposits" line: the gap between them is what the
 *  market added. */
export function ValuePanel({ v, period, onPeriod }: { v: AccountView; period: Window; onPeriod: (w: Window) => void }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const points = pointsIn(v.points, v.growth[period])
  const base = baseline(points)
  const [whole, cents] = splitCents(v.value)
  const color = CATEGORY_COLOR[v.category] ?? 'var(--ink1)'
  // a window under about three months labels its days, not just its months
  const short = points.length > 1 && Date.parse(points[points.length - 1].date) - Date.parse(points[0].date) < 100 * DAY_MS
  return (
    <Panel id="value" title="Value" subtitle={`${WINDOW_WORD[period]} · the gap between the lines is the market`}
      span={8} height={372} actions={<>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color={color} style="solid" />Value
        </span>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ref)" style="dotted" />Start + deposits
        </span>
        <WindowSeg value={period} onChange={onPeriod} />
        <Seg label="View" options={VIEWS} value={view} onChange={setView} />
      </>}>
      <div className="text-[38px] sm:text-5xl font-semibold tracking-[-0.035em] leading-none mt-3.5">
        {whole}<span className="text-ink3">.{cents}</span>
      </div>
      <div className="mt-auto pt-3">
        {points.length < 2 ? (
          <Empty>No history yet. The chart appears once this account has a few days of data.</Empty>
        ) : view === 'Chart' ? (
          <LineChart dates={points.map((p) => p.date)} height={196}
            ariaLabel="The account’s value against its starting value plus deposits"
            series={[
              { key: 'value', label: 'Value', values: points.map((p) => p.value), color, style: 'solid', area: true },
              { key: 'base', label: 'Start + deposits', values: base, color: 'var(--ref)', style: 'dotted', step: true },
            ]}
            yFormat={compactMoney} valueFormat={(n) => money(n, false)} xLabel={(d) => monthLabel(d, short)}
            tipTitle={(d) => shortDate(d)} />
        ) : (
          <div className="table-scroll overflow-y-auto" style={{ maxHeight: 196 }}>
            <table className="tbl" style={{ minWidth: 480, '--row': '36px' } as CSSProperties}>
              <thead>
                <tr>
                  <th>Date</th><th className="r">Value</th><th className="r">Start + deposits</th>
                  <th className="r">In or out</th>
                </tr>
              </thead>
              <tbody>
                {points.map((p, i) => (
                  <tr key={p.date}>
                    <td>{shortDate(p.date)}</td>
                    <td className="r num">{money(p.value)}</td>
                    <td className="r num">{money(base[i])}</td>
                    <td className="r num">{i > 0 && p.net_flow !== 0 ? signedMoney(p.net_flow) : <Missing />}</td>
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
