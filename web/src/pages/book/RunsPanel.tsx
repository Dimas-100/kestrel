import { Empty } from '../../charts/marks'
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { BookView } from '../../lib/api'
import { shortDate, timeHM } from '../../lib/format'
import { RUN_ICON } from '../home/TodayAndPositions'

/** This book's runs: next first, then newest. */
export function RunsPanel({ v, tz }: { v: BookView; tz: string }) {
  const runs = v.runs
  return (
    <Panel id="book-runs" title="Runs" subtitle="Next first, then newest" span={6} height={300}>
      {runs.length === 0 ? (
        <Empty>No runs recorded for this book yet.</Empty>
      ) : (
        <ul className="mt-1 overflow-y-auto" style={{ maxHeight: 230 }}>
          {runs.map((r, i) => {
            const icon = RUN_ICON[r.status]
            return (
              <li key={`${r.time}-${i}`}
                className="flex items-center gap-2.5 h-10 border-t border-line first:border-t-0">
                <span className="num w-24 text-xs text-ink2 flex-none">
                  {shortDate(r.time, tz).slice(0, 3)} {timeHM(r.time, tz)}
                </span>
                <Icon name={icon.name} size={16} style={{ color: icon.color }} />
                <span className="sr-only">{r.status}</span>
                <div className="min-w-0">
                  <div className="text-[13px] font-medium truncate">{r.label}</div>
                  <div className="text-[11px] text-ink3 truncate">{r.detail}</div>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}
