// Where you stand: cash − recorded debt = the difference, as three figures with the operators between them, each with
// its count, and under them how fresh the balances are, naming any over a week old (spec 2026-10-08 reserves
// estimates §3.2). The arithmetic is the view's; the page only lays it out.
import type { ReactNode } from 'react'
import { Icon } from '../../components/Icon'
import { Panel } from '../../components/bits'
import type { CashLine, DebtLine, ReservesTotals } from '../../lib/api'
import { MINUS, money, monthLabel } from '../../lib/format'
import { Caveat } from './Caveat'

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

/** "7 Oct", or "6–7 Oct" / "30 Sep – 7 Oct" when the balances span days. */
export function balanceDays(oldest: string, newest: string): string {
  if (oldest === newest) return monthLabel(oldest, true)
  const [a, b] = [new Date(`${oldest}T12:00:00Z`), new Date(`${newest}T12:00:00Z`)]
  return a.getUTCMonth() === b.getUTCMonth()
    ? `${a.getUTCDate()}–${monthLabel(newest, true)}`
    : `${monthLabel(oldest, true)} – ${monthLabel(newest, true)}`
}

function Figure({ label, value, sub }: { label: string; value: ReactNode; sub: ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="label">{label}</div>
      <div className="text-[30px] sm:text-[34px] font-semibold tracking-[-0.03em] leading-none mt-2 num whitespace-nowrap">
        {value}
      </div>
      <div className="text-xs text-ink3 mt-2">{sub}</div>
    </div>
  )
}

const Op = ({ sign, word }: { sign: string; word: string }) => (
  <div className="text-[26px] leading-none text-ink3 font-light sm:self-center sm:pt-4 sm:px-2">
    <span aria-hidden="true">{sign}</span><span className="sr-only">{word}</span>
  </div>
)

export function StandingPanel({ totals, cash, debts }: { totals: ReservesTotals; cash: CashLine[]; debts: DebtLine[] }) {
  const lines = [...cash.map((c) => ({ name: c.name, as_of: c.as_of })), ...debts.map((d) => ({ name: d.name, as_of: d.as_of }))]
  const stale = totals.stale.map((name) => {
    const line = lines.find((l) => l.name === name)
    return line ? `${name} (balance from ${monthLabel(line.as_of.slice(0, 10), true)})` : name
  })
  return (
    <Panel id="standing" title="Where you stand" subtitle="Cash, recorded debt, and the difference" span={12} lead>
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr_auto_1fr] items-start gap-x-4 gap-y-2 mt-5">
        <Figure label="Cash" value={money(totals.cash)} sub={plural(totals.cash_count, 'account')} />
        <Op sign={MINUS} word="minus" />
        <Figure label="Recorded debt"
          value={totals.owed < 0 ? <span className="text-ink2 text-[20px]">{money(Math.abs(totals.owed))} credit balance</span>
            : money(totals.owed)}
          sub={`${plural(totals.debt_count, 'debt')} on record`} />
        <Op sign="=" word="equals" />
        <Figure label="Difference" value={money(totals.net)}
          sub={totals.net < 0 ? 'more owed than held in cash' : 'cash after recorded debt'} />
      </div>
      {totals.oldest_as_of && totals.newest_as_of && (
        <div className="flex items-center gap-1.5 text-xs text-ink3 mt-5 pt-3 border-t border-line">
          <Icon name="clock" size={13} />
          Balances from {balanceDays(totals.oldest_as_of, totals.newest_as_of)}
        </div>
      )}
      {stale.length > 0 && (
        <Caveat warn>
          Over a week old, so these figures may be off: {stale.join(', ')}.
        </Caveat>
      )}
    </Panel>
  )
}
