// Each goal's current value, target, progress bar, the date, and the monthly amount that would reach it by then.
import { Empty } from '../../charts/marks'
import { Panel } from '../../components/bits'
import type { GoalRow } from '../../lib/api'
import { longDate, money, num } from '../../lib/format'

export function GoalsPanel({ goals, now }: { goals: GoalRow[]; now: string }) {
  const nowMs = new Date(now).getTime()
  return (
    <Panel id="goals" title="Goals" span={5}>
      {goals.length === 0 ? (
        <Empty>No goals yet. An investing feed sends what you&rsquo;re saving toward.</Empty>
      ) : (
        <ul>
          {goals.map((g) => {
            const missing = g.missing_accounts.length > 0
            const overdue = !missing && g.by != null && !g.reached && new Date(g.by).getTime() < nowMs
            return (
              <li key={g.id} className="py-3 border-t border-line">
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                  <span className="text-sm font-medium">{g.label}</span>
                  <span className="text-xs text-ink3">{g.scope_text}</span>
                </div>
                {missing ? (
                  <div className="text-xs text-ink3 mt-2">
                    <span className="num">—</span> · account not in any source: {g.missing_accounts.join(', ')}
                  </div>
                ) : (
                  <>
                    <div role="progressbar" aria-label={g.label} aria-valuemin={0} aria-valuemax={100}
                      aria-valuenow={g.progress_pct ?? 0} className="relative h-2 rounded mt-2 bg-panel2 overflow-hidden"
                      style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
                      <span className="absolute inset-y-0 left-0 rounded" style={{
                        width: `${g.progress_pct ?? 0}%`, background: g.reached ? 'var(--good)' : 'var(--acc)',
                      }} />
                    </div>
                    <div className="flex items-center justify-between text-xs text-ink3 mt-1.5 gap-3">
                      <span className="num">{money(g.current ?? 0, false)} / {money(g.target, false)}</span>
                      <span>
                        {g.reached ? 'Reached'
                          : overdue ? `was due ${longDate(g.by as string)}`
                            : g.by ? `by ${longDate(g.by)}`
                              : `${num(g.progress_pct ?? 0, 0)}%`}
                      </span>
                    </div>
                    {!g.reached && !overdue && g.monthly_needed != null && (
                      <p className="text-xs text-ink3 mt-1">{money(g.monthly_needed)} a month would reach it</p>
                    )}
                  </>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}
