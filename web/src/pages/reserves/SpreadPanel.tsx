// Totals for cash and debt, and the spread: the highest rate paid against the best rate earned.
import { Panel, Stat } from '../../components/bits'
import type { ReservesView } from '../../lib/api'
import { money, num } from '../../lib/format'

export function SpreadPanel({ totals, spread }: { totals: ReservesView['totals']; spread: ReservesView['spread'] }) {
  return (
    <Panel id="reserves-summary" title="Cash and debt" span={12}>
      <div className="flex flex-wrap gap-x-9 gap-y-3 mt-3">
        <Stat label="Cash"><span className="num">{money(totals.cash)}</span></Stat>
        <Stat label="Owed">
          {totals.owed < 0
            ? <span className="text-ink2">{money(Math.abs(totals.owed))} credit balance</span>
            : <span className="num">{money(totals.owed)}</span>}
        </Stat>
        <Stat label="Net"><span className="num">{money(totals.net)}</span></Stat>
        <Stat label="Utilization">
          <span className="num">{totals.utilization_pct == null ? '—' : `${num(totals.utilization_pct, 1)}%`}</span>
        </Stat>
      </div>
      {spread && (
        // a year of interest paid and a year earned, apart: they are different money, so they are never netted
        <div className="text-sm text-ink2 mt-4 pt-3.5 border-t border-line">
          <p>
            The highest rate you pay is <span className="num text-ink1">{num(spread.owed_rate_pct, 1)}%</span>, on{' '}
            {spread.owed_name}; the best rate you earn is{' '}
            <span className="num text-ink1">{num(spread.earned_rate_pct, 1)}%</span>. At today&rsquo;s balances, a
            year of interest costs about <span className="num text-ink1">{money(spread.yearly_cost)}</span> on what
            you owe and earns about <span className="num text-ink1">{money(spread.yearly_earned)}</span> on your cash.
          </p>
          {spread.pay_down != null && spread.pay_down_saves != null && (
            <p className="mt-1.5">
              Paying <span className="num text-ink1">{money(spread.pay_down)}</span> of the {spread.owed_name} from
              cash would save about <span className="num text-ink1">{money(spread.pay_down_saves)}</span> a year.
            </p>
          )}
        </div>
      )}
    </Panel>
  )
}
