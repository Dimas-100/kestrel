// What to do this month, ranked by the view (spec 2026-10-08 plan §4.1): the first three as numbered priority cards,
// each with why it is on the list, the figures and a link to the place on the page that backs it; the rest behind
// "Also this month", closed. With nothing to do, one line that names what kestrel can't measure rather than
// calling it on plan.
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { PlanAction, PlanView } from '../../lib/api'
import { LOOK } from '../home/AttentionPanel'
import { jumpTo } from './jump'

export const PRIORITIES = 3

const WHERE: Record<PlanAction['kind'], string> = {
  target: 'See it in Allocation', goal: 'See it in Milestones', thesis: 'See it in Theses',
}

function JumpLink({ item }: { item: PlanAction }) {
  return (
    <a href={`#${item.anchor}`} className="inline-flex items-center gap-1 text-xs font-medium"
      style={{ color: 'var(--acc-ink)' }}
      onClick={(e) => { e.preventDefault(); jumpTo(item.anchor, item.kind) }}>
      {WHERE[item.kind]}<Icon name="arrow" size={13} />
    </a>
  )
}

function Level({ item }: { item: PlanAction }) {
  const look = LOOK[item.level]
  return (
    <span className="inline-flex items-center gap-1.5 label" style={{ color: look.color }}>
      <Icon name={look.icon} size={14} />{look.word}
    </span>
  )
}

function PriorityCard({ item, rank }: { item: PlanAction; rank: number }) {
  return (
    <li className="priority">
      <div className="flex items-center justify-between gap-3">
        <span className="priority-rank num" aria-hidden="true">{rank}</span>
        <Level item={item} />
      </div>
      <h3 className="text-[15px] font-semibold leading-snug mt-2.5 [overflow-wrap:anywhere]">{item.title}</h3>
      {item.why && <p className="text-[13px] text-ink2 mt-1.5 [overflow-wrap:anywhere]">{item.why}</p>}
      {item.detail && <p className="num text-xs text-ink3 mt-1.5 [overflow-wrap:anywhere]">{item.detail}</p>}
      <div className="mt-auto pt-3"><JumpLink item={item} /></div>
    </li>
  )
}

function emptyLine(counts: PlanView['counts']): string {
  const unknown = counts.unknown
  if (unknown === 0) return 'Nothing to do this month: every measured target is on plan, every thesis holds, and no goal is due within the year.'
  const n = `${unknown} target${unknown === 1 ? '' : 's'}`
  return `Nothing to do this month that kestrel can see. ${n} can’t be measured yet, so ${unknown === 1 ? 'it isn’t' : 'they aren’t'} counted as on plan.`
}

export function ThisMonthPanel({ actions, counts }: { actions: PlanAction[]; counts: PlanView['counts'] }) {
  const top = actions.slice(0, PRIORITIES)
  const rest = actions.slice(PRIORITIES)
  const n = actions.length
  return (
    <Panel id="this-month" title="This month" span={12}
      subtitle={n === 0 ? undefined : n <= PRIORITIES ? `${n} thing${n === 1 ? '' : 's'} to do, most pressing first`
        : `${n} things to do: the ${PRIORITIES} most pressing first`}>
      {n === 0 ? (
        <div className="flex items-start gap-2 mt-4 text-ink2">
          <Icon name="checkCircle" size={18} style={{ color: 'var(--good)', marginTop: 1 }} />
          <span>{emptyLine(counts)}</span>
        </div>
      ) : (
        <>
          <ol className="priorities mt-4" aria-label="This month’s priorities">
            {top.map((item, i) => <PriorityCard key={`${item.anchor}-${i}`} item={item} rank={i + 1} />)}
          </ol>
          {rest.length > 0 && (
            <details className="mt-4 also">
              <summary className="text-sm font-medium cursor-pointer">Also this month ({rest.length})</summary>
              <ul className="mt-1">
                {rest.map((item, i) => (
                  <li key={`${item.anchor}-${i}`} className="flex gap-3 py-3 border-t border-line first:border-t-0">
                    <span className="w-8 h-8 flex-none rounded-lg bg-panel2 border border-line flex items-center justify-center"
                      style={{ color: LOOK[item.level].color }}>
                      <Icon name={LOOK[item.level].icon} size={16} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="label" style={{ color: LOOK[item.level].color }}>{LOOK[item.level].word}</div>
                      <div className="text-sm font-medium mt-0.5 [overflow-wrap:anywhere]">{item.title}</div>
                      {item.why && <div className="text-xs text-ink2 mt-0.5 [overflow-wrap:anywhere]">{item.why}</div>}
                      {item.detail && <div className="num text-xs text-ink3 mt-0.5 [overflow-wrap:anywhere]">{item.detail}</div>}
                      <div className="mt-1"><JumpLink item={item} /></div>
                    </div>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </Panel>
  )
}
