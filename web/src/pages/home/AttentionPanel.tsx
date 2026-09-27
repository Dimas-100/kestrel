import { Link } from '@tanstack/react-router'
import { Panel } from '../../components/bits'
import { Icon, type IconName } from '../../components/Icon'
import type { Attention, Level } from '../../lib/api'

export const LOOK: Record<Level, { icon: IconName; color: string; word: string }> = {
  serious: { icon: 'shield', color: 'var(--serious)', word: 'Serious' },
  warning: { icon: 'clock', color: 'var(--warn)', word: 'Warning' },
  note: { icon: 'info', color: 'var(--ink3)', word: 'Note' },
}
const SHOWN = 3

export function AttentionPanel({ items }: { items: Attention[] }) {
  const counts = (['serious', 'warning', 'note'] as const)
    .map((level) => [level, items.filter((i) => i.level === level).length] as const)
    .filter(([, n]) => n > 0)
    .map(([level, n]) => `${n} ${level}`)
  return (
    <Panel id="attention" title="Needs you" span={5} height={372}
      actions={counts.length > 0 && <span className="chip">{counts.join(' · ')}</span>}>
      {items.length === 0 ? (
        <div className="flex items-center gap-2 mt-6 text-ink2">
          <Icon name="checkCircle" size={18} style={{ color: 'var(--good)' }} />Nothing needs you right now.
        </div>
      ) : (
        <ul className="mt-3">
          {items.slice(0, SHOWN).map((item, i) => {
            const look = LOOK[item.level]
            return (
              <li key={i} className="flex gap-3 py-3.5 border-t border-line">
                <span className="w-8 h-8 flex-none rounded-lg bg-panel2 border border-line flex items-center justify-center"
                  style={{ color: look.color }}>
                  <Icon name={look.icon} size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="label" style={{ color: look.color }}>{look.word}</div>
                  <div className="text-sm font-medium mt-0.5">{item.title}</div>
                  {item.detail && <div className="text-xs text-ink3 mt-0.5">{item.detail}</div>}
                </div>
                {item.link && (
                  <Link to={item.link} className="self-center inline-flex items-center gap-1 text-xs whitespace-nowrap"
                    style={{ color: 'var(--acc-ink)' }}>
                    Open<Icon name="arrow" size={13} />
                  </Link>
                )}
              </li>
            )
          })}
        </ul>
      )}
      {items.length > SHOWN && (
        <Link to="/activity" className="mt-auto text-xs" style={{ color: 'var(--acc-ink)' }}>
          {items.length - SHOWN} more
        </Link>
      )}
    </Panel>
  )
}
