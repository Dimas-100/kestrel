// Is each account on plan, does every thesis still hold, and how are the goals coming along?
import { usePlan } from '../../lib/api'
import { GoalsPanel } from './GoalsPanel'
import { TargetsPanel } from './TargetsPanel'
import { ThesesPanel } from './ThesesPanel'

export function Plan() {
  const plan = usePlan()
  if (plan.isPending) return <p className="text-ink3" role="status">Loading your plan…</p>
  if (!plan.data) {
    return <div role="alert" className="panel">Plan couldn&rsquo;t load: {plan.error.message}</div>
  }
  const v = plan.data
  const empty = v.accounts.length === 0 && v.unscoped.length === 0 && v.theses.length === 0 && v.goals.length === 0
  const needing = v.counts.theses_alert + v.counts.theses_watch
  return (
    <>
      <header className="mb-5">
        <div className="label">Money</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Plan</h1>
        {!empty && (
          <p className="text-ink2 mt-1.5">
            {v.counts.off_plan === 0 ? 'Every target sits on plan.'
              : `${v.counts.off_plan} target${v.counts.off_plan === 1 ? ' is' : 's are'} off plan.`}{' '}
            {needing > 0 && `${needing} thesis${needing === 1 ? '' : 'es'} need${needing === 1 ? 's' : ''} a look.`}
          </p>
        )}
      </header>
      {empty ? (
        <div className="panel text-ink2">
          No plan yet. Add an investing feed with targets, theses or goals (see docs/connectors.md).
        </div>
      ) : (
        <div className="grid12">
          <TargetsPanel accounts={v.accounts} unscoped={v.unscoped} />
          <ThesesPanel theses={v.theses} />
          <GoalsPanel goals={v.goals} />
        </div>
      )}
    </>
  )
}
