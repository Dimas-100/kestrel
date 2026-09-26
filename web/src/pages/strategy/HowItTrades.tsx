import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Step } from '../../lib/api'
import { Empty } from '../../charts/marks'

const COUNT = ['', 'one step', 'two steps', 'three steps', 'four steps']

/** The rule as up to four cards joined by arrows, each with its parameters, then the sizing line. */
export function HowItTrades({ steps, sizing }: { steps: Step[]; sizing: string }) {
  const shown = steps.slice(0, 4)
  const subtitle = steps.length > 4 ? `The first four of its ${steps.length} steps`
    : shown.length ? `The whole rule, in ${COUNT[shown.length]}` : undefined
  return (
    <Panel id="how" title="How it trades" span={12} height={252} subtitle={subtitle}>
      {shown.length === 0 ? (
        <Empty>This strategy hasn&rsquo;t described its rules.</Empty>
      ) : (
        <ol className="grid grid-cols-1 sm:grid-cols-2 min-[1180px]:flex gap-3 min-[1180px]:gap-0 mt-3.5">
          {shown.map((step, i) => (
            <li key={`${i}-${step.label}`} className="flex min-w-0 min-[1180px]:flex-1">
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
                {step.params.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {step.params.map((param, k) => (
                      <span key={`${param}-${k}`}
                        className="num text-2xs text-ink2 rounded-[5px] border border-line2 px-[7px] py-[3px]">
                        {param}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
      {sizing && (
        <div className="mt-auto pt-3 flex items-start gap-2 text-xs text-ink2">
          <Icon name="scale" size={15} style={{ color: 'var(--ink3)' }} />
          <span><span className="label mr-2">Sizing</span>{sizing}</span>
        </div>
      )}
    </Panel>
  )
}
