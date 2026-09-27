// Company events ahead and behind: earnings, filings, insider trades and dividends, filterable by kind.
import { useState } from 'react'
import { Empty } from '../../charts/marks'
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type CalendarView, type EventKind, type EventRow, useCalendar } from '../../lib/api'
import { shortDate } from '../../lib/format'

export const KIND_LABEL: Record<EventKind, string> = {
  earnings: 'Earnings', filing: 'Filing', insider: 'Insider', dividend: 'Dividend', other: 'Other',
}
const KINDS: EventKind[] = ['earnings', 'filing', 'insider', 'dividend', 'other']
type Filter = 'all' | EventKind

/** https only: the contract already refuses anything else, but a link is never built from an unchecked string. */
export function isHttpsUrl(url: string): boolean {
  return url.startsWith('https://')
}

export function matches(kind: EventKind, filter: Filter): boolean {
  return filter === 'all' || filter === kind
}

function KindFilter({ value, onChange }: { value: Filter; onChange: (v: Filter) => void }) {
  return (
    <div className="seg" role="group" aria-label="Kind">
      {(['all', ...KINDS] as const).map((k) => (
        <button key={k} type="button" aria-pressed={k === value} onClick={() => onChange(k)}>
          {k === 'all' ? 'All' : KIND_LABEL[k]}
        </button>
      ))}
    </div>
  )
}

function CountsRow({ counts }: { counts: CalendarView['counts'] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {KINDS.map((k) => <span key={k} className="chip">{KIND_LABEL[k]} {counts[k]}</span>)}
    </div>
  )
}

function EventItem({ e }: { e: EventRow }) {
  return (
    <li className="flex items-start gap-3 py-2.5 border-b border-line last:border-0">
      <div className="num text-xs text-ink3 pt-0.5 w-16 shrink-0">{shortDate(e.date)}</div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          {e.symbol && <span className="num font-semibold">{e.symbol}</span>}
          <span className="text-ink1">{e.title}</span>
          <span className="chip" style={{ padding: '2px 8px' }}>{KIND_LABEL[e.kind]}</span>
          {e.held && <span className="chip" style={{ padding: '2px 8px' }}>Held</span>}
        </div>
        {e.detail && <div className="text-xs text-ink3 mt-0.5">{e.detail}</div>}
        {isHttpsUrl(e.url) && (
          <a href={e.url} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs mt-1" style={{ color: 'var(--acc-ink)' }}>
            Source<Icon name="arrow" size={11} />
          </a>
        )}
      </div>
    </li>
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
              <ul>{w.items.map((e, i) => <EventItem key={`${w.week_start}-${i}`} e={e} />)}</ul>
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
        <ul className="mt-3.5">{items.map((e, i) => <EventItem key={i} e={e} />)}</ul>
      )}
    </Panel>
  )
}

export function Calendar() {
  const query = useCalendar()
  const [filter, setFilter] = useState<Filter>('all')
  if (query.isPending) return <p className="text-ink3" role="status">Loading the calendar…</p>
  if (!query.data) {
    return <div role="alert" className="panel">Calendar couldn&rsquo;t load: {query.error.message}</div>
  }
  const view = query.data
  const empty = view.upcoming.length === 0 && view.recent.length === 0
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
            <KindFilter value={filter} onChange={setFilter} />
          </div>
          <UpcomingPanel view={view} filter={filter} />
          <RecentPanel view={view} filter={filter} />
        </div>
      )}
    </>
  )
}
