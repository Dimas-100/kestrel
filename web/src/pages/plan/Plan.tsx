// Your plan: the goals in time, what to do this month, how each account sits against its plan, and why each
// holding is owned (spec 2026-10-05 plan page).
import { usePlan } from '../../lib/api'
import { AllocationPanel } from './AllocationPanel'
import { MilestonesPanel } from './MilestonesPanel'
import { ThesesPanel } from './ThesesPanel'
import { ThisMonthPanel } from './ThisMonthPanel'

export function Plan() {
  const plan = usePlan()
  if (plan.isPending) return <p className="text-ink3" role="status">Loading your plan…</p>
  if (!plan.data) {
    return <div role="alert" className="panel">Plan couldn&rsquo;t load: {plan.error.message}</div>
  }
  const v = plan.data
  const empty = v.accounts.length === 0 && v.unscoped.length === 0 && v.theses.length === 0 && v.goals.length === 0
  return (
    <>
      <header className="mb-5">
        <div className="label">Money</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Plan</h1>
        {!empty && v.summary && <p className="text-ink2 mt-1.5 max-w-[70ch]">{v.summary}</p>}
      </header>
      {empty ? (
        <div className="panel text-ink2">
          No plan yet. Add an investing feed with targets, theses or goals (see docs/connectors.md).
        </div>
      ) : (
        <div className="grid12">
          <MilestonesPanel goals={v.goals} today={v.as_of.slice(0, 10)} />
          <ThisMonthPanel actions={v.actions} />
          <AllocationPanel accounts={v.accounts} unscoped={v.unscoped} />
          <ThesesPanel theses={v.theses} />
        </div>
      )}
    </>
  )
}
