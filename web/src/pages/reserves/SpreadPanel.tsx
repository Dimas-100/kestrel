// Earning against owing: first how much of the debt and the cash has a rate on record (every interest figure covers
// that part only), then the highest rate on record against the best your cash earns, a year of each apart, and paying
// the dearest rated debt from cash as Now → After blocks (cash, coverage, the interest saved) over the exact table
// (spec 2026-10-08 reserves estimates §2, §3.7).
import { type CSSProperties, useState } from 'react'
import { Icon } from '../../components/Icon'
import { Panel } from '../../components/bits'
import type { DebtLine, Rates, ReservesView, Runway } from '../../lib/api'
import { money, num } from '../../lib/format'
import { Caveat } from './Caveat'
import { coverageText, coverFor } from './RunwayPanel'

/** "Store card", "Store card and Visa", "A, B and C" */
const names = (list: string[]) => (list.length < 2 ? list.join('') : `${list.slice(0, -1).join(', ')} and ${list[list.length - 1]}`)

/** The rate-coverage note: a warning when some of what is owed has no APR on record, null when all of it has one. */
function RatesNote({ rates }: { rates: Rates }) {
  if (rates.owed <= 0 || rates.rated_owed_pct == null || rates.rated_owed_pct >= 100) return null
  const none = rates.unrated.length === 1 ? 'has none' : 'have none'
  if (rates.rated_owed <= 0) {
    return (
      <Caveat warn>
        No APR is on record for any of the <span className="num">{money(rates.owed)}</span> you owe, so a year of interest
        can&rsquo;t be estimated. Add each card&rsquo;s rate to its feed to see it.
      </Caveat>
    )
  }
  return (
    <Caveat warn>
      Rates are on record for <span className="num">{money(rates.rated_owed)}</span> of the{' '}
      <span className="num">{money(rates.owed)}</span> you owe (<span className="num">{num(rates.rated_owed_pct, 1)}%</span>).{' '}
      {names(rates.unrated)} {none}, so the interest below covers the rated part only; the cost of the rest is unknown.
    </Caveat>
  )
}

function BeforeAfter({ spread, cash, owedNow, runway, amount }: {
  spread: NonNullable<ReservesView['spread']>; cash: number; owedNow: number; runway: Runway | null; amount: number
}) {
  const rate = spread.owed_rate_pct / 100
  const rows: [string, string, string][] = [
    ['Cash', money(cash), money(cash - amount)],
    ['Coverage', runway ? coverageText(runway) : '—', runway ? coverageText(coverFor(cash - amount, runway)) : '—'],
    [`Owed on the ${spread.owed_name}`, money(owedNow), money(owedNow - amount)],
    ['Interest a year, rates on record', money(spread.yearly_cost), money(spread.yearly_cost - amount * rate)],
  ]
  return (
    <div className="table-scroll mt-3.5">
      <table className="tbl" style={{ maxWidth: 560, '--row': '34px' } as CSSProperties}>
        <caption className="sr-only">Before and after paying {money(amount)} from cash</caption>
        <thead><tr><th>&nbsp;</th><th className="r">Now</th><th className="r">After paying {money(amount)}</th></tr></thead>
        <tbody>
          {rows.map(([label, now, after]) => (
            <tr key={label}><td>{label}</td><td className="r num">{now}</td><td className="r num">{after}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** One Now → After block: the label, today's figure muted, an arrow, the after figure large, and what changed. */
function Shift({ label, now, after, change }: { label: string; now: string; after: string; change: string }) {
  return (
    <div className="rounded-[10px] p-3.5 min-w-0" style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
      <div className="label">{label}</div>
      <div className="flex items-baseline flex-wrap gap-x-2 gap-y-1 mt-2">
        <span className="num text-[15px] text-ink3"><span className="sr-only">now </span>{now}</span>
        <Icon name="arrow" size={14} style={{ color: 'var(--ink3)', alignSelf: 'center' }} />
        <span className="num text-[22px] font-semibold tracking-[-0.02em] text-ink1"><span className="sr-only">after </span>{after}</span>
      </div>
      <div className="text-xs text-ink3 mt-1.5">{change}</div>
    </div>
  )
}

/** "1 day less", "0.2 months less", "no change" */
export function coverageChange(now: ReturnType<typeof coverFor>, after: ReturnType<typeof coverFor>): string {
  if (now.unit === 'days' && after.unit === 'days') {
    const d = now.days_cover - after.days_cover
    return d === 0 ? 'no change' : `${d} day${d === 1 ? '' : 's'} less`
  }
  const m = Math.round((now.months - after.months) * 10) / 10
  return m === 0 ? 'no change' : `${num(m, 1)} months less`
}

/** Try paying some of the dearest rated debt from cash: Now → After blocks for cash and coverage beside the year's
 *  interest saved (at the best cash rate given up), all moving with the slider, and the exact figures in a table under
 *  them. Arithmetic in the page from the view's figures; nothing is written anywhere. */
function PayDown({ spread, cash, owedNow, runway, max }: {
  spread: NonNullable<ReservesView['spread']>; cash: number; owedNow: number; runway: Runway | null; max: number
}) {
  // whole dollars on the slider, its top stop the exact amount: never more than the card owes or the cash there is
  const [step, setStep] = useState(Math.ceil(max))
  const amount = Math.min(step, max)
  const saves = amount * (spread.owed_rate_pct - spread.earned_rate_pct) / 100
  const coverNow = runway ? { unit: runway.unit, days_cover: runway.days_cover, months: runway.months } : null
  const coverAfter = runway ? coverFor(cash - amount, runway) : null
  return (
    <div className="mt-5 pt-4 border-t border-line">
      <div className="text-[13px] font-medium text-ink1">Try paying the {spread.owed_name} from cash</div>
      <label className="flex items-center gap-3 text-xs text-ink3 mt-2">
        <span className="whitespace-nowrap">Amount</span>
        <input type="range" min={0} max={Math.ceil(max)} step={1} value={step} className="flex-1 min-w-0"
          style={{ accentColor: 'var(--acc)', maxWidth: 420 }} aria-label={`Pay this much of the ${spread.owed_name} from cash`}
          onChange={(e) => setStep(Number(e.target.value))} />
        <span className="num text-[13px] text-ink1 min-w-[84px] text-right" aria-live="polite">{money(amount)}</span>
      </label>
      <div className="grid gap-3 mt-3.5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <Shift label="Cash" now={money(cash)} after={money(cash - amount)}
          change={amount > 0 ? `${money(amount)} to the card` : 'no change'} />
        <Shift label="Coverage" now={coverNow ? coverageText(coverNow) : '—'} after={coverAfter ? coverageText(coverAfter) : '—'}
          change={coverNow && coverAfter ? coverageChange(coverNow, coverAfter) : 'no bank rows to measure the pace'} />
        <Shift label="Interest saved a year" now={money(0)} after={money(saves)}
          change="net of what that cash would have earned" />
      </div>
      <BeforeAfter spread={spread} cash={cash} owedNow={owedNow} runway={runway} amount={amount} />
    </div>
  )
}

export function SpreadPanel({ totals, spread, rates, runway, debts }: {
  totals: ReservesView['totals']; spread: ReservesView['spread']; rates: Rates | null; runway: Runway | null
  debts: DebtLine[]
}) {
  const owedNow = spread ? debts.find((d) => d.name === spread.owed_name)?.owed ?? spread.pay_down ?? 0 : 0
  const allOwedRated = rates == null || rates.rated_owed_pct == null || rates.rated_owed_pct >= 100
  const allCashRated = rates == null || rates.rated_cash >= rates.cash
  return (
    <Panel id="reserves-summary" title="Earning against owing" span={12}
      subtitle="Interest paid and earned, on the balances with a rate on record">
      {rates && <RatesNote rates={rates} />}
      {spread ? (
        // a year of interest paid and a year earned, apart: they are different money, so they are never netted
        <div className="text-sm text-ink2 mt-3.5">
          <p>
            The highest rate on record is <span className="num text-ink1">{num(spread.owed_rate_pct, 1)}%</span>, on{' '}
            {spread.owed_name}; the best your cash earns on record is{' '}
            <span className="num text-ink1">{num(spread.earned_rate_pct, 1)}%</span>. At today&rsquo;s balances, a
            year of interest costs about <span className="num text-ink1">{money(spread.yearly_cost)}</span> on{' '}
            {allOwedRated ? 'what you owe' : <>the <span className="num">{money(rates!.rated_owed)}</span> with a rate</>}{' '}
            and earns about <span className="num text-ink1">{money(spread.yearly_earned)}</span> on{' '}
            {allCashRated ? 'your cash' : <>the <span className="num">{money(rates!.rated_cash)}</span> of your cash with a rate</>}.
          </p>
          {spread.pay_down != null && spread.pay_down_saves != null && (
            <PayDown spread={spread} cash={totals.cash} owedNow={owedNow} runway={runway} max={spread.pay_down} />
          )}
        </div>
      ) : (
        rates && rates.owed > 0 && rates.rated_owed > 0 && (
          <p className="text-sm text-ink2 mt-3.5">No cash with a rate on record to compare against.</p>
        )
      )}
      {!spread && (rates == null || rates.owed <= 0) && <p className="text-sm text-ink3 mt-3.5">Nothing owed.</p>}
    </Panel>
  )
}
