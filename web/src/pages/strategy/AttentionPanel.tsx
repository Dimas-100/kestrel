// What needs you on this strategy: its positions without a stop, its alerts, its late runs, stale marks, a review
// that is due, a paused book, a thin sample. The same shape and look as Home's "Needs you".
import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Attention } from '../../lib/api'
import { LOOK } from '../home/AttentionPanel'

const SHOWN = 4

/** "2 serious · 1 warning · 3 notes", or "" */
export function attentionCounts(items: Attention[]): string {
  return (['serious', 'warning', 'note'] as const)
    .map((level) => [level, items.filter((i) => i.level === level).length] as const)
    .filter(([, n]) => n > 0)
    .map(([level, n]) => `${n} ${level}${n > 1 && level === 'note' ? 's' : ''}`)
    .join(' · ')
}

export function StrategyAttentionPanel({ items }: { items: Attention[] }) {
  const [all, setAll] = useState(false)
  const shown = all ? items : items.slice(0, SHOWN)
  const counts = attentionCounts(items)
  return (
    <Panel id="strategy-attention" title="Needs you" span={5} height={372}
      subtitle="On this strategy, most serious first"
      actions={counts && <span className="chip">{counts}</span>}>
      {items.length === 0 ? (
        <div className="flex items-center gap-2 mt-6 text-ink2">
          <Icon name="checkCircle" size={18} style={{ color: 'var(--good)' }} />Nothing needs you on this strategy.
        </div>
      ) : (
        <ul className="mt-2">
          {shown.map((item, i) => {
            const look = LOOK[item.level]
            return (
              <li key={`${item.title}-${i}`} className="flex gap-3 py-3 border-t border-line">
                <span className="w-8 h-8 flex-none rounded-lg bg-panel2 border border-line flex items-center justify-center"
                  style={{ color: look.color }}>
                  <Icon name={look.icon} size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="label" style={{ color: look.color }}>{look.word}</div>
                  <div className="text-sm font-medium mt-0.5 [overflow-wrap:anywhere]">{item.title}</div>
                  {item.detail && <div className="text-xs text-ink3 mt-0.5 [overflow-wrap:anywhere]">{item.detail}</div>}
                </div>
                {item.link && !item.link.startsWith('/strategies/') && (
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
        <button type="button" onClick={() => setAll(!all)} className="mt-auto text-xs self-start"
          style={{ color: 'var(--acc-ink)', background: 'none', border: 0, padding: 0, cursor: 'pointer' }}>
          {all ? 'Show fewer' : `Show all ${items.length}`}
        </button>
      )}
    </Panel>
  )
}
