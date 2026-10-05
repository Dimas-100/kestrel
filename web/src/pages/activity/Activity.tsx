// The Activity page: today on the clock, the week as a grid, every alert, every source (spec 2026-10-05 system
// pages §2).
import { useActivity, useShell } from '../../lib/api'
import { AlertsPanel } from './AlertsPanel'
import { SourcesPanel } from './SourcesPanel'
import { TodayPanel } from './TodayPanel'
import { WeekPanel } from './WeekPanel'

export function Activity() {
  const activity = useActivity()
  const shell = useShell()
  if (activity.isPending) return <p className="text-ink3" role="status">Loading activity…</p>
  if (!activity.data) {
    return <div role="alert" className="panel">Activity couldn&rsquo;t load: {activity.error.message}</div>
  }
  const v = activity.data
  const tz = shell.data?.app.timezone ?? 'UTC'
  const today = v.days.find((d) => d.label === 'Today') ?? null
  const todayIso = new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(new Date(v.as_of)) // "YYYY-MM-DD" there
  return (
    <>
      <header className="mb-5">
        <div className="label">System</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Activity</h1>
        <p className="text-ink2 mt-1.5 max-w-[70ch]">{v.summary || 'What ran, what is due, and what failed.'}</p>
      </header>
      <div className="grid12">
        <TodayPanel today={today} next={v.next_run} now={v.as_of} tz={tz} />
        <WeekPanel week={v.week} today={todayIso} />
        <AlertsPanel alerts={v.alerts} />
        <SourcesPanel sources={v.sources} tz={tz} />
      </div>
    </>
  )
}
