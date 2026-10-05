// Company events ahead and behind: earnings, filings, insider trades and dividends, as a month or as lists,
// filterable by kind.
import { useState } from 'react'
import { Empty } from '../../charts/marks'
import { Panel, Seg } from '../../components/bits'
import { type CalendarView, type EventKind, type EventRow, useCalendar } from '../../lib/api'
import { shortDate } from '../../lib/format'
import { EventItem, eventKey, KIND_LABEL } from './EventItem'
import { allEvents, MonthView } from './MonthView'

export { eventKey, isHttpsUrl, KIND_LABEL } from './EventItem'

const KINDS: EventKind[] = ['earnings', 'filing', 'insider', 'dividend', 'other']
type Filter = 'all' | EventKind
const FILTER_OPTIONS = ['all', ...KINDS] as const
const FILTER_LABEL: Record<Filter, string> = { all: 'All', ...KIND_LABEL }
const VIEWS = ['Month', 'List'] as const

export function matches(kind: EventKind, filter: Filter): boolean {
  return filter === 'all' || filter === kind
}

function KindFilter({ value, onChange }: { value: Filter; onChange: (v: Filter) => void }) {
  return <Seg label="Kind" options={FILTER_OPTIONS} value={value} onChange={onChange} labels={FILTER_LABEL} />
}

function CountsRow({ counts }: { counts: CalendarView['counts'] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {KINDS.map((k) => <span key={k} className="chip">{KIND_LABEL[k]} {counts[k]}</span>)}
    </div>
  )
}

function UpcomingPanel({ view, filter }: { view: CalendarView; filter: Filter }) {
  const weeks = view.upcoming
    .map((w) => ({ ...w, items: w.items.filter((e) => matches(e.kind, filter)) }))
    .filter((w) => w.items.length > 0)
  return (
    <Panel id="calendar-upcoming" title="Upcoming" subtitle="By week, earliest first" span={12}>
      {weeks.length === 0 ? (
        <Empty>No events ahead within what your source sent.</Empty>
      ) : (
        <div className="flex flex-col gap-4 mt-3.5">
          {weeks.map((w) => (
            <div key={w.week_start}>
              <div className="label mb-1.5">Week of {shortDate(w.week_start)}</div>
              <ul>{w.items.map((e) => <EventItem key={eventKey(e)} e={e} />)}</ul>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}

function RecentPanel({ view, filter }: { view: CalendarView; filter: Filter }) {
  const items = view.recent.filter((e) => matches(e.kind, filter))
  return (
    <Panel id="calendar-recent" title="Recent" subtitle="The last 90 days, newest first" span={12}>
      {items.length === 0 ? <Empty>No events behind within what your source sent.</Empty> : (
        <ul className="mt-3.5">{items.map((e) => <EventItem key={eventKey(e)} e={e} />)}</ul>
      )}
    </Panel>
  )
}

/** The selected day's events, beside the month. Its title says the day, so the rows leave the date off. */
function DayPanel({ day, events }: { day: string; events: EventRow[] }) {
  const n = events.length
  return (
    <Panel id="calendar-day" title={shortDate(day)} subtitle={n === 0 ? 'No events' : n === 1 ? '1 event' : `${n} events`}
      span={4}>
      {n === 0 ? <Empty>Nothing on this day.</Empty> : (
        <ul className="mt-3.5">{events.map((e) => <EventItem key={eventKey(e)} e={e} date={false} />)}</ul>
      )}
    </Panel>
  )
}

export function Calendar() {
  const query = useCalendar()
  const [filter, setFilter] = useState<Filter>('all')
  const [mode, setMode] = useState<(typeof VIEWS)[number]>('Month')
  const [picked, setPicked] = useState<string | null>(null) // null: today, until a day is chosen
  if (query.isPending) return <p className="text-ink3" role="status">Loading the calendar…</p>
  if (!query.data) {
    return <div role="alert" className="panel">Calendar couldn&rsquo;t load: {query.error.message}</div>
  }
  const view = query.data
  const empty = view.upcoming.length === 0 && view.recent.length === 0
  const day = picked ?? view.today
  const events = allEvents(view).filter((e) => matches(e.kind, filter))
  return (
    <>
      <header className="mb-5">
        <div className="label">Research</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Calendar</h1>
        <p className="text-ink2 mt-1.5">Company events ahead and behind: earnings, filings, insider trades and dividends.</p>
      </header>
      {empty ? (
        <div className="panel text-ink2">
          No calendar events yet. They come from an investing feed that reports company events (earnings, filings,
          insider trades and dividends).
        </div>
      ) : (
        <div className="grid12">
          <div className="span-12 flex flex-wrap items-center justify-between gap-3">
            <CountsRow counts={view.counts} />
            <div className="flex flex-wrap items-center gap-3">
              <Seg label="View" options={VIEWS} value={mode} onChange={setMode} />
              <KindFilter value={filter} onChange={setFilter} />
            </div>
          </div>
          {mode === 'Month' ? (
            <>
              <MonthView events={events} today={view.today} selected={day} onSelect={setPicked} />
              <DayPanel day={day} events={events.filter((e) => e.date === day)} />
            </>
          ) : (
            <>
              <UpcomingPanel view={view} filter={filter} />
              <RecentPanel view={view} filter={filter} />
            </>
          )}
        </div>
      )}
    </>
  )
}
