// Totals for cash and debt, and the spread: the highest rate paid against the best rate earned (spec 2026-10-05
// reserves §2.5: the same words as Phase 5, at the foot of the page).
import { useState } from 'react'
import { Panel, Stat } from '../../components/bits'
import type { ReservesView } from '../../lib/api'
import { money, num } from '../../lib/format'

/** Try paying some of the dearest card from cash: what a year of its interest would save at the best cash rate given
 *  up, and what cash would be left. Arithmetic in the page from the view's figures; nothing is written anywhere. */
function PayDown({ spread, cash, max }: { spread: NonNullable<ReservesView['spread']>; cash: number; max: number }) {
  const [amount, setAmount] = useState(Math.round(max))
  const saves = amount * (spread.owed_rate_pct - spread.earned_rate_pct) / 100
  return (
    <div className="mt-3">
      <label className="flex items-center gap-3 text-xs text-ink3">
        <span className="whitespace-nowrap">Try an amount</span>
        <input type="range" min={0} max={Math.round(max)} step={1} value={amount} className="flex-1 min-w-0"
          style={{ accentColor: 'var(--acc)' }} aria-label={`Pay this much of the ${spread.owed_name} from cash`}
          onChange={(e) => setAmount(Number(e.target.value))} />
      </label>
      <p className="text-sm text-ink2 mt-1.5">
        Paying <span className="num text-ink1">{money(amount)}</span> saves about{' '}
        <span className="num text-ink1">{money(saves)}</span> a year and leaves{' '}
        <span className="num text-ink1">{money(cash - amount)}</span> in cash.
      </p>
    </div>
  )
}

export function SpreadPanel({ totals, spread }: { totals: ReservesView['totals']; spread: ReservesView['spread'] }) {
  return (
    <Panel id="reserves-summary" title="Earning against owing" span={12}
      subtitle="The totals, and the spread between the rate you pay and the rate you earn">
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
            <>
              <p className="mt-1.5">
                Paying <span className="num text-ink1">{money(spread.pay_down)}</span> of the {spread.owed_name} from
                cash would save about <span className="num text-ink1">{money(spread.pay_down_saves)}</span> a year.
              </p>
              <PayDown spread={spread} cash={totals.cash} max={spread.pay_down} />
            </>
          )}
        </div>
      )}
    </Panel>
  )
}
