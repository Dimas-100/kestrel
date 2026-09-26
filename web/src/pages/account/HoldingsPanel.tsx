import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { CATEGORY_COLOR, Delta, Missing, Panel, type Sort, SortHeader, toggleSort } from '../../components/bits'
import type { AccountView, HoldingRow } from '../../lib/api'
import { MINUS, money, num, pct, signedMoney } from '../../lib/format'

type SortKey = 'value' | 'gain'
const SORT_VALUE: Record<SortKey, (h: HoldingRow) => number | null> = { value: (h) => h.value, gain: (h) => h.gain }

/** Sorted by value or gain; a holding with no gain (its cost is unknown) goes last either way. */
export function sortHoldings(rows: HoldingRow[], sort: Sort<SortKey>): HoldingRow[] {
  return [...rows].sort((a, b) => {
    const [x, y] = [SORT_VALUE[sort.key](a), SORT_VALUE[sort.key](b)]
    if (x == null || y == null) return x == null && y == null ? 0 : x == null ? 1 : -1
    return sort.dir === 'desc' ? y - x : x - y
  })
}

/** 63.66 · 1,200 · 0.000123: whole shares plainly, fractions to four places (six under one) */
export function quantityText(value: number): string {
  const text = Math.abs(value).toLocaleString('en-US', { maximumFractionDigits: Math.abs(value) >= 1 ? 4 : 6 })
  return value < 0 && text !== '0' ? MINUS + text : text
}

/** A thin bar and the percent; the bar stays inside its track for a weight over 100% or under zero. */
function Weight({ value, color }: { value: number | null; color: string }) {
  if (value == null) return <Missing />
  return (
    <div className="flex items-center justify-end gap-2">
      <span className="relative w-14 h-1.5 rounded-full overflow-hidden bg-panel2"
        style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
        <span className="absolute inset-y-0 left-0"
          style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }} />
      </span>
      <span className="num text-xs min-w-[46px] text-right">{num(value, 1)}%</span>
    </div>
  )
}

function Gain({ gain, pctValue }: { gain: number | null; pctValue: number | null }) {
  if (gain == null) return <Missing />
  return (
    <>
      <Delta value={gain}>{signedMoney(gain)}</Delta>
      {pctValue != null && <div className="text-[11px] mt-0.5"><Delta value={pctValue}>{pct(pctValue, 2)}</Delta></div>}
    </>
  )
}

/** What the account holds, then its cash and the totals. */
export function HoldingsPanel({ v }: { v: AccountView }) {
  const [sort, setSort] = useState<Sort<SortKey>>({ key: 'value', dir: 'desc' })
  const onSort = (key: SortKey) => setSort((s) => toggleSort(s, key))
  const color = CATEGORY_COLOR[v.category] ?? 'var(--ink3)'
  const t = v.totals
  const n = v.holdings.length
  return (
    <Panel id="holdings" title="Holdings" span={12}
      subtitle={`${n} holding${n === 1 ? '' : 's'} and cash · weights are shares of the account`}>
      {n === 0 && v.cash === 0 ? (
        <Empty>This account holds nothing right now.</Empty>
      ) : (
        <>
          <div className="table-scroll mt-3.5">
            <table className="tbl" style={{ minWidth: 900, '--row': '52px' } as CSSProperties}>
              <thead>
                <tr>
                  <th>Symbol</th><th>Name</th><th className="r">Quantity</th><th className="r">Price</th>
                  <SortHeader label="Value" k="value" sort={sort} onSort={onSort} right />
                  <th className="r">Weight</th><th className="r">Cost basis</th>
                  <SortHeader label="Gain" k="gain" sort={sort} onSort={onSort} right />
                </tr>
              </thead>
              <tbody>
                {sortHoldings(v.holdings, sort).map((h, i) => (
                  <tr key={`${h.symbol}-${i}`}>
                    <td><span className="num font-semibold">{h.symbol}</span></td>
                    <td className="text-ink2">{h.name || <Missing />}</td>
                    <td className="r num">{quantityText(h.quantity)}</td>
                    <td className="r num">{num(h.price, Math.abs(h.price) < 1 ? 4 : 2)}</td>
                    <td className="r num">{money(h.value)}</td>
                    <td className="r"><Weight value={h.weight} color={color} /></td>
                    <td className="r num">{h.cost_basis == null ? <Missing /> : money(h.cost_basis)}</td>
                    <td className="r"><Gain gain={h.gain} pctValue={h.gain_pct} /></td>
                  </tr>
                ))}
                <tr>
                  <td><span className="font-medium">Cash</span></td>
                  <td><Missing /></td><td className="r"><Missing /></td><td className="r"><Missing /></td>
                  <td className="r num">{money(v.cash)}</td>
                  <td className="r"><Weight value={v.cash_weight} color="var(--s3)" /></td>
                  <td className="r"><Missing /></td><td className="r"><Missing /></td>
                </tr>
              </tbody>
              <tfoot>
                <tr style={{ borderTop: '1px solid var(--line2)' }}>
                  <td className="font-medium">Total</td><td /><td /><td />
                  <td className="r num font-medium">{money(t.value)}</td>
                  <td className="r num text-xs">{t.value > 0 ? '100.0%' : <Missing />}</td>
                  <td className="r num">{t.cost_basis == null ? <Missing /> : money(t.cost_basis)}</td>
                  <td className="r"><Gain gain={t.gain} pctValue={t.gain_pct} /></td>
                </tr>
              </tfoot>
            </table>
          </div>
          {t.unknown_cost > 0 && (
            <p className="text-xs text-ink3 mt-2">
              The cost and gain totals leave out {t.unknown_cost} holding{t.unknown_cost === 1 ? '' : 's'} with no cost
              basis.
            </p>
          )}
        </>
      )}
    </Panel>
  )
}
