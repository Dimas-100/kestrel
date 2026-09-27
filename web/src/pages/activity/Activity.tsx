// The Activity page: what ran today and what is due, then the last seven days; every alert; every source's status.
import { Link } from '@tanstack/react-router'
import { Empty } from '../../charts/marks'
import { Missing, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type ActivitySource, type ActivityView, type DayRuns, type RunRow, useActivity, useShell } from '../../lib/api'
import { shortDate, timeHM } from '../../lib/format'
import { LOOK } from '../home/AttentionPanel'
import { RUN_ICON } from '../home/TodayAndPositions'
import { STATUS_ICON } from '../../shell/Shell'

function RunLine({ r, tz }: { r: RunRow; tz: string }) {
  const icon = RUN_ICON[r.status]
  return (
    <li className="flex items-center gap-2.5 h-10 border-t border-line first:border-t-0">
      <span className="num w-14 text-xs text-ink2 flex-none">{timeHM(r.time, tz)}</span>
      <Icon name={icon.name} size={16} style={{ color: icon.color }} />
      <div className="min-w-0 flex-1">
        <div className="text-[13px] font-medium truncate">
          {r.label}{r.book_name && <span className="text-ink3"> · {r.book_name}</span>}
        </div>
        {r.detail && <div className="text-[11px] text-ink3 truncate">{r.detail}</div>}
      </div>
      <span className="text-[11px] capitalize flex-none" style={{ color: icon.color }}>{r.status}</span>
    </li>
  )
}

function DayBlock({ day, tz }: { day: DayRuns; tz: string }) {
  return (
    <div className="mb-5 last:mb-0">
      <div className="label mb-1.5">{day.label}</div>
      <ul>{day.runs.map((r, i) => <RunLine key={`${day.date}-${i}`} r={r} tz={tz} />)}</ul>
    </div>
  )
}

function RunsPanel({ days, counts, tz }: { days: DayRuns[]; counts: Record<string, number>; tz: string }) {
  const summary = Object.entries(counts).map(([status, n]) => `${n} ${status}`).join(' · ')
  return (
    <Panel id="runs" title="Runs" subtitle="Today, what's next, then the last seven days" span={12}
      actions={summary && <span className="chip">{summary}</span>}>
      {days.length === 0 ? (
        <Empty>No runs recorded yet. They appear once a scheduled task reports in.</Empty>
      ) : (
        <div className="mt-3.5">
          {days.map((day) => <DayBlock key={day.date} day={day} tz={tz} />)}
        </div>
      )}
    </Panel>
  )
}

function AlertsPanel({ alerts }: { alerts: ActivityView['alerts'] }) {
  return (
    <Panel id="activity-alerts" title="Alerts" span={12}
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
                  <div className="text-sm font-medium mt-0.5">{a.title}</div>
                  {a.detail && <div className="text-xs text-ink3 mt-0.5">{a.detail}</div>}
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

function SourcesPanel({ sources }: { sources: ActivitySource[] }) {
  return (
    <Panel id="sources" title="Sources" subtitle="Every place your money data comes from" span={12}>
      {sources.length === 0 ? (
        <Empty>No sources configured yet.</Empty>
      ) : (
        <div className="table-scroll mt-3.5">
          <table className="tbl" style={{ minWidth: 760 }}>
            <thead>
              <tr>
                <th>Source</th><th>Kind</th><th>Status</th><th>Last success</th><th className="r">Age</th>
                <th className="r">Stale after</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => {
                const status = STATUS_ICON[s.status]
                return (
                  <tr key={s.id}>
                    <td className="font-medium">{s.label}</td>
                    <td className="text-ink2">{s.kind}</td>
                    <td>
                      <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: status.color }}>
                        <Icon name={status.name} size={14} />{status.text}
                      </span>
                    </td>
                    <td className="text-ink2 text-xs">{s.last_success ? shortDate(s.last_success) : <Missing />}</td>
                    <td className="r num text-xs">{s.age_text ?? <Missing />}</td>
                    <td className="r num text-xs">{s.stale_after ?? <Missing />}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}

export function Activity() {
  const activity = useActivity()
  const shell = useShell()
  if (activity.isPending) return <p className="text-ink3" role="status">Loading activity…</p>
  if (!activity.data) {
    return <div role="alert" className="panel">Activity couldn&rsquo;t load: {activity.error.message}</div>
  }
  const v = activity.data
  const tz = shell.data?.app.timezone ?? 'UTC'
  return (
    <>
      <header className="mb-5">
        <h1 className="text-3xl font-semibold tracking-[-0.025em]">Activity</h1>
        <p className="text-ink2 mt-1.5">What ran, what is due, and what failed.</p>
      </header>
      <div className="grid12">
        <RunsPanel days={v.days} counts={v.counts} tz={tz} />
        <AlertsPanel alerts={v.alerts} />
        <SourcesPanel sources={v.sources} />
      </div>
    </>
  )
}
