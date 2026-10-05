// Your reserves: how long the cash would last, what has been coming in and going out, what cash sits where, what
// is owed, and the spread between what you pay and what you earn (spec 2026-10-05 reserves page).
import { useReserves } from '../../lib/api'
import { CashPanel } from './CashPanel'
import { DebtPanel } from './DebtPanel'
import { FlowsPanel } from './FlowsPanel'
import { RunwayPanel } from './RunwayPanel'
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
        {!empty && v.summary && <p className="text-ink2 mt-1.5 max-w-[70ch]">{v.summary}</p>}
      </header>
      {empty ? (
        <div className="panel text-ink2">
          No cash or debt yet. Add a feed with cash or debt accounts (see docs/connectors.md).
        </div>
      ) : (
        <div className="grid12">
          <RunwayPanel runway={v.runway} totals={v.totals} accounts={v.cash.length} />
          <FlowsPanel flows={v.flows} />
          <CashPanel cash={v.cash} viewDay={v.as_of} />
          <DebtPanel debts={v.debts} />
          <SpreadPanel totals={v.totals} spread={v.spread} />
        </div>
      )}
    </>
  )
}
