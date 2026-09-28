// Each goal's current value, target, progress bar, the date, and the straight-line monthly amount to reach it by then.
import { Empty } from '../../charts/marks'
import { Panel } from '../../components/bits'
import type { GoalRow } from '../../lib/api'
import { longDate, money, num } from '../../lib/format'

/** The straight-line monthly amount, said for what it is: deposits for a deposits goal; for a value goal, a figure
 *  that leaves out any market growth (over decades that is most of the story, so it must never read as a plan). */
export function monthlyText(g: Pick<GoalRow, 'measure' | 'monthly_needed'>): string | null {
  if (g.monthly_needed == null) return null
  return g.measure === 'deposits'
    ? `about ${money(g.monthly_needed)} a month in deposits`
    : `about ${money(g.monthly_needed)} a month, before any market growth`
}

export function GoalsPanel({ goals }: { goals: GoalRow[] }) {
  return (
    <Panel id="goals" title="Goals" span={5}>
      {goals.length === 0 ? (
        <Empty>No goals yet. An investing feed sends what you&rsquo;re saving toward.</Empty>
      ) : (
        <ul>
          {goals.map((g) => {
            const missing = g.missing_accounts.length > 0
            const monthly = monthlyText(g)
            return (
              <li key={g.id} className="py-3 border-t border-line">
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                  <span className="text-sm font-medium">{g.label}</span>
                  <span className="text-xs text-ink3">{g.scope_text}</span>
                </div>
                {missing || g.current == null ? (
                  <div className="text-xs text-ink3 mt-2">
                    <span className="num">—</span> ·{' '}
                    {missing ? `account not in any source: ${g.missing_accounts.join(', ')}`
                      : g.unknown_reason || 'not known yet'}
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
                      <span className="num">{money(g.current, false)} / {money(g.target, false)}</span>
                      <span>
                        {g.reached ? 'Reached'
                          : g.overdue && g.by ? `was due ${longDate(g.by)}`
                            : g.by ? `by ${longDate(g.by)}`
                              : `${num(g.progress_pct ?? 0, 0)}%`}
                      </span>
                    </div>
                    {!g.reached && !g.overdue && monthly && <p className="text-xs text-ink3 mt-1">{monthly}</p>}
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
