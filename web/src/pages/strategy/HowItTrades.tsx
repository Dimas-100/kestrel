import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Rules, Step } from '../../lib/api'
import { Empty } from '../../charts/marks'
import { monthLabel } from '../../lib/format'

const COUNT = ['', 'one step', 'two steps', 'three steps', 'four steps', 'five steps', 'six steps']

/** "The whole rule, in four steps · 4 gates" */
export function rulesSubtitle(steps: Step[], gates: Step[]): string | undefined {
  if (steps.length === 0 && gates.length === 0) return undefined
  const flow = steps.length ? `The whole rule, in ${COUNT[steps.length] ?? `${steps.length} steps`}` : 'No flow described'
  return gates.length ? `${flow} · ${gates.length} gate${gates.length === 1 ? '' : 's'}` : flow
}

function Params({ params }: { params: string[] }) {
  if (params.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1.5 mt-3">
      {params.map((param, k) => (
        <span key={`${param}-${k}`} className="num text-2xs text-ink2 rounded-[5px] border border-line2 px-[7px] py-[3px]">
          {param}
        </span>
      ))}
    </div>
  )
}

/** The rule as numbered cards joined by arrows, then its gates and limits, then the sizing and the version. */
export function HowItTrades({ rules }: { rules: Rules }) {
  const { steps, gates } = rules
  const cols = Math.min(4, Math.max(1, steps.length))
  return (
    <Panel id="how" title="How it trades" span={12} subtitle={rulesSubtitle(steps, gates)}>
      {steps.length === 0 && gates.length === 0 ? (
        <Empty>This strategy hasn&rsquo;t described its rules.</Empty>
      ) : (
        <>
          {steps.length > 0 && (
            <ol className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3.5"
              style={{ gridTemplateColumns: undefined }} data-cols={cols}>
              {steps.map((step, i) => (
                <li key={`${i}-${step.label}`} className="flex min-w-0 min-[1180px]:[grid-column:auto]">
                  {i > 0 && (
                    <span aria-hidden="true" className="hidden min-[1180px]:flex w-8 flex-none items-center justify-center"
                      style={{ color: 'var(--ink3)' }}>
                      <Icon name="arrow" size={18} />
                    </span>
                  )}
                  <div className="flex-1 min-w-0 rounded-[9px] border border-line bg-panel2 p-4">
                    <div className="flex items-center gap-2">
                      <span className="num text-2xs" style={{ color: 'var(--acc-ink)' }}>{String(i + 1).padStart(2, '0')}</span>
                      <span className="label">{step.label}</span>
                    </div>
                    <div className="text-lg font-medium mt-2.5">{step.title}</div>
                    <div className="text-xs text-ink3 mt-1">{step.text}</div>
                    <Params params={step.params} />
                  </div>
                </li>
              ))}
            </ol>
          )}
          {gates.length > 0 && (
            <div className="mt-4">
              <div className="label">Gates and limits</div>
              <ul className="grid grid-cols-1 sm:grid-cols-2 min-[1180px]:grid-cols-4 gap-x-6 gap-y-2.5 mt-2">
                {gates.map((g, i) => (
                  <li key={`${i}-${g.label}`} className="flex gap-2.5 min-w-0">
                    <Icon name="shield" size={15} style={{ color: 'var(--ink3)', flex: 'none', marginTop: 2 }} />
                    <div className="min-w-0">
                      <div className="text-sm font-medium">{g.title}</div>
                      <div className="text-xs text-ink3">{g.text}</div>
                      <Params params={g.params} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      {(rules.sizing || rules.version) && (
        <div className="mt-auto pt-4 flex flex-wrap items-start justify-between gap-x-6 gap-y-2 text-xs text-ink2">
          {rules.sizing && (
            <span className="flex items-start gap-2">
              <Icon name="scale" size={15} style={{ color: 'var(--ink3)' }} />
              <span><span className="label mr-2">Sizing</span>{rules.sizing}</span>
            </span>
          )}
          {rules.version && (
            <span className="text-ink3">
              Rules {rules.version}{rules.effective && ` · since ${monthLabel(rules.effective, true)}`}
              {rules.history.length > 1 && ` · ${rules.history.length} versions`}
            </span>
          )}
        </div>
      )}
    </Panel>
  )
}
