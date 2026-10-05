// One event as a row: date, symbol, title, kind chip, Held, detail and a Source link. The lists and the Selected
// day panel render the same row, so an event reads the same wherever it shows.
import { Icon } from '../../components/Icon'
import type { EventKind, EventRow } from '../../lib/api'
import { shortDate } from '../../lib/format'

export const KIND_LABEL: Record<EventKind, string> = {
  earnings: 'Earnings', filing: 'Filing', insider: 'Insider', dividend: 'Dividend', other: 'Other',
}

/** https only: the contract already refuses anything else, but a link is never built from an unchecked string. */
export function isHttpsUrl(url: string): boolean {
  return url.startsWith('https://')
}

/** A stable key for an event row: it carries no id of its own, so date+kind+symbol+title identifies it. */
export function eventKey(e: EventRow): string {
  return `${e.date}|${e.kind}|${e.symbol}|${e.title}`
}

/** `date` false leaves the date column off, for a panel whose title already says the day. */
export function EventItem({ e, date = true }: { e: EventRow; date?: boolean }) {
  return (
    <li className="flex items-start gap-3 py-2.5 border-b border-line last:border-0">
      {date && <div className="num text-xs text-ink3 pt-0.5 w-16 shrink-0">{shortDate(e.date)}</div>}
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
