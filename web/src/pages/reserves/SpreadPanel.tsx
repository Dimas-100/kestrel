// Totals for cash and debt, and the spread: the highest rate paid against the best rate earned.
import { Panel, Stat } from '../../components/bits'
import type { ReservesView } from '../../lib/api'
import { money, num } from '../../lib/format'

export function SpreadPanel({ totals, spread }: { totals: ReservesView['totals']; spread: ReservesView['spread'] }) {
  return (
    <Panel id="reserves-summary" title="Cash and debt" span={12}>
      <div className="flex flex-wrap gap-x-9 gap-y-3 mt-3">
        <Stat label="Cash"><span className="num">{money(totals.cash)}</span></Stat>
        <Stat label="Owed"><span className="num">{money(totals.owed)}</span></Stat>
        <Stat label="Net"><span className="num">{money(totals.net)}</span></Stat>
        <Stat label="Utilization">
          <span className="num">{totals.utilization_pct == null ? '—' : `${num(totals.utilization_pct, 1)}%`}</span>
        </Stat>
      </div>
      {spread && (
        <p className="text-sm text-ink2 mt-4 pt-3.5 border-t border-line">
          The highest rate you pay is <span className="num text-ink1">{num(spread.owed_rate_pct, 1)}%</span>; the best
          rate you earn is <span className="num text-ink1">{num(spread.earned_rate_pct, 1)}%</span>.{' '}
          {spread.gap >= 0
            ? <>At today&rsquo;s balances, that leaves about{' '}
              <span className="num text-ink1">{money(spread.gap)}</span> a year in your favor.</>
            : <>At today&rsquo;s balances, closing that gap is worth about{' '}
              <span className="num text-ink1">{money(-spread.gap)}</span> a year.</>}
        </p>
      )}
    </Panel>
  )
}
