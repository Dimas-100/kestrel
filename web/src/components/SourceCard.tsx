// A source as a card: its status with the word, the label, the kind, when it last succeeded and how long it is
// trusted, and whatever the page adds (Activity: the age and the detail; Settings: what it reads and its timing).
// Never a token's value, never a machine path: the views that feed this never send one.
import { STATUS_ICON } from '../shell/Shell'
import type { Source } from '../lib/api'
import { shortDate, timeHM } from '../lib/format'
import { Icon } from './Icon'

export function SourceCard({ label, kind, status, lastSuccess, tz, ageText, staleAfter, timing, reads, tokenEnv, detail }: {
  label: string; kind: string; status: Source['status']; lastSuccess: string | null; tz: string
  ageText?: string | null; staleAfter?: string | null; timing?: string | null; reads?: string | null
  tokenEnv?: string | null; detail?: string
}) {
  const look = STATUS_ICON[status]
  return (
    <article aria-label={label} className="rounded-lg border border-line p-3.5 flex flex-col gap-2 min-w-0 bg-panel">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold [overflow-wrap:anywhere]">{label}</div>
          <span className="chip mt-1.5" style={{ padding: '2px 8px' }}>{kind}</span>
        </div>
        <span className="inline-flex items-center gap-1.5 text-xs whitespace-nowrap flex-none" style={{ color: look.color }}>
          <Icon name={look.name} size={14} />{look.text}
        </span>
      </div>
      {reads && (
        <div className="text-xs text-ink2" style={{ wordBreak: 'break-all' }}>
          {reads}{tokenEnv && <span className="text-ink3"> · token: {tokenEnv}</span>}
        </div>
      )}
      <div className="text-xs text-ink3 flex flex-col gap-0.5">
        <div>
          {ageText ? `updated ${ageText} ago` : lastSuccess ? 'updated' : 'never updated'}
          {staleAfter && ` · stale after ${staleAfter}`}
        </div>
        {timing && <div>{timing}</div>}
        {lastSuccess && <div className="num">{shortDate(lastSuccess, tz)} · {timeHM(lastSuccess, tz)}</div>}
      </div>
      {detail && <div className="text-xs text-ink2 [overflow-wrap:anywhere]">{detail}</div>}
    </article>
  )
}
