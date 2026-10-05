// Every alert by level: the icon tile, the level word, the title, the detail and the link.
import { Link } from '@tanstack/react-router'
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { ActivityView } from '../../lib/api'
import { LOOK } from '../home/AttentionPanel'

export function AlertsPanel({ alerts }: { alerts: ActivityView['alerts'] }) {
  return (
    <Panel id="activity-alerts" title="Alerts" span={5}
      actions={alerts.length > 0 && <span className="chip">{alerts.length} total</span>}>
      {alerts.length === 0 ? (
        <div className="flex items-center gap-2 mt-3 text-ink2">
          <Icon name="checkCircle" size={18} style={{ color: 'var(--good)' }} />No alerts right now.
        </div>
      ) : (
        <ul className="mt-3">
          {alerts.map((a, i) => {
            const look = LOOK[a.level]
            return (
              <li key={i} className="flex gap-3 py-3 border-t border-line first:border-t-0">
                <span className="w-8 h-8 flex-none rounded-lg bg-panel2 border border-line flex items-center justify-center"
                  style={{ color: look.color }}>
                  <Icon name={look.icon} size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="label" style={{ color: look.color }}>{look.word}</div>
                  <div className="text-sm font-medium mt-0.5 [overflow-wrap:anywhere]">{a.title}</div>
                  {a.detail && <div className="text-xs text-ink3 mt-0.5 [overflow-wrap:anywhere]">{a.detail}</div>}
                </div>
                {a.link && (
                  <Link to={a.link} className="self-center inline-flex items-center gap-1 text-xs whitespace-nowrap"
                    style={{ color: 'var(--acc-ink)' }}>
                    Open<Icon name="arrow" size={13} />
                  </Link>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}
