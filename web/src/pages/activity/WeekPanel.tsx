// The week as a grid: one row per job, one column per day from a week ago to today, the status icon with its
// word in each cell (spec 2026-10-05 system pages §2.2). A column of checks is a good week.
import { Empty } from '../../charts/marks'
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { WeekCell, WeekRow } from '../../lib/api'
import { RUN_ICON } from '../home/TodayAndPositions'

/** "Today" for today, else the weekday and the day: "Fri 18". */
export function dayHead(iso: string, today: string): string {
  if (iso === today) return 'Today'
  const d = new Date(`${iso}T12:00:00Z`)
  return `${d.toLocaleString('en-US', { weekday: 'short', timeZone: 'UTC' })} ${d.getUTCDate()}`
}

function Cell({ cell }: { cell: WeekCell }) {
  if (cell.status == null) {
    return <><span aria-hidden="true" className="text-ink3">·</span><span className="sr-only">no run</span></>
  }
  const icon = RUN_ICON[cell.status]
  return (
    <span className="inline-flex" style={{ color: icon.color }}>
      <Icon name={icon.name} size={16} /><span className="sr-only">{cell.status}</span>
    </span>
  )
}

export function WeekPanel({ week, today }: { week: WeekRow[]; today: string }) {
  return (
    <Panel id="week" title="The week" subtitle={week.length > 0 ? 'Each job, each day. A column of checks is a good week.' : undefined} span={7}>
      {week.length === 0 ? (
        <Empty>No runs recorded yet. They appear once a scheduled task reports in.</Empty>
      ) : (
        <div className="table-scroll mt-3.5">
          <table className="tbl" style={{ minWidth: 520 }}>
            <thead>
              <tr>
                <th>Job</th>
                {week[0].cells.map((c) => <th key={c.date} scope="col" className="r">{dayHead(c.date, today)}</th>)}
              </tr>
            </thead>
            <tbody>
              {week.map((row) => (
                <tr key={row.label}>
                  {/* a feed's job label can be a sentence: the column stays narrow and the full label is a title */}
                  <td className="font-medium whitespace-nowrap overflow-hidden text-ellipsis" style={{ maxWidth: 240 }}
                    title={row.label}>{row.label}</td>
                  {row.cells.map((c) => <td key={c.date} className="r"><Cell cell={c} /></td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
