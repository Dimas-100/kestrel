// Cash and debt: balances, rates, utilization, and the spread between what you pay and what you earn.
import { useReserves } from '../../lib/api'
import { money } from '../../lib/format'
import { CashPanel } from './CashPanel'
import { DebtPanel } from './DebtPanel'
import { SpreadPanel } from './SpreadPanel'

export function Reserves() {
  const reserves = useReserves()
  if (reserves.isPending) return <p className="text-ink3" role="status">Loading your reserves…</p>
  if (!reserves.data) {
    return <div role="alert" className="panel">Reserves couldn&rsquo;t load: {reserves.error.message}</div>
  }
  const v = reserves.data
  const empty = v.cash.length === 0 && v.debts.length === 0
  return (
    <>
      <header className="mb-5">
        <div className="label">Money</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Reserves</h1>
        {!empty && <p className="text-ink2 mt-1.5">{money(v.totals.net)} in cash after debts.</p>}
      </header>
      {empty ? (
        <div className="panel text-ink2">
          No cash or debt yet. Add a feed with cash or debt accounts (see docs/connectors.md).
        </div>
      ) : (
        <div className="grid12">
          <SpreadPanel totals={v.totals} spread={v.spread} />
          <CashPanel cash={v.cash} />
          <DebtPanel debts={v.debts} />
        </div>
      )}
    </>
  )
}
