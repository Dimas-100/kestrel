// What to do this month, worked out by the view from the targets, theses and goals: items like Home's Needs you,
// warnings first (spec 2026-10-05 plan page §2.2). No link: the page is the plan.
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Attention } from '../../lib/api'
import { LOOK } from '../home/AttentionPanel'

export function ThisMonthPanel({ actions }: { actions: Attention[] }) {
  const n = actions.length
  return (
    <Panel id="this-month" title="This month" span={5}
      subtitle={n > 0 ? `${n} thing${n === 1 ? '' : 's'} to do` : undefined}>
      {n === 0 ? (
        <div className="flex items-start gap-2 mt-6 text-ink2">
          <Icon name="checkCircle" size={18} style={{ color: 'var(--good)', marginTop: 1 }} />
          <span>Nothing to do this month: every target is on plan, every thesis holds, and no goal is due within the year.</span>
        </div>
      ) : (
        <ul className="mt-3">
          {actions.map((item, i) => {
            const look = LOOK[item.level]
            return (
              <li key={i} className="flex gap-3 py-3.5 border-t border-line">
                <span className="w-8 h-8 flex-none rounded-lg bg-panel2 border border-line flex items-center justify-center"
                  style={{ color: look.color }}>
                  <Icon name={look.icon} size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="label" style={{ color: look.color }}>{look.word}</div>
                  <div className="text-sm font-medium mt-0.5 [overflow-wrap:anywhere]">{item.title}</div>
                  {item.detail && <div className="text-xs text-ink3 mt-0.5 [overflow-wrap:anywhere]">{item.detail}</div>}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}
