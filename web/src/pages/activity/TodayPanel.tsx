// Today on the clock: a line for the day in the profile's zone with each run as its status icon at its time and the
// now rule, then the next run and today's list (spec 2026-10-05 system pages §2.1).
import type { PointerEvent } from 'react'
import { clampTip, nearestIndex } from '../../charts/geometry'
import { useIndex, useWidth } from '../../charts/hooks'
import { Tip } from '../../charts/marks'
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { DayRuns, RunRow } from '../../lib/api'
import { shortDate, timeHM } from '../../lib/format'
import { RUN_ICON } from '../home/TodayAndPositions'
import { DAY_TICKS, dayX, minutesOfDay } from './dayline'

const LINE_Y = 30
const HEIGHT = 64

export function RunLine({ r, tz }: { r: RunRow; tz: string }) {
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

function DayLine({ runs, now, tz }: { runs: RunRow[]; now: string; tz: string }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(900)
  const { index: hover, set: setHover, onKey } = useIndex(runs.length)
  const xs = runs.map((r) => dayX(minutesOfDay(r.time, tz), width))
  const nowX = dayX(minutesOfDay(now, tz), width)
  const onPointer = (event: PointerEvent<HTMLDivElement>) => {
    if (runs.length === 0) return
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, event.clientX - box.left))
  }
  const h = hover == null ? null : runs[hover]
  return (
    <div ref={wrapRef} className="relative mt-4 select-none" style={{ height: HEIGHT }} role="img"
      aria-label="Today’s runs on the clock" tabIndex={0} onKeyDown={onKey} onPointerMove={onPointer}
      onPointerLeave={() => setHover(null)} onBlur={() => setHover(null)}>
      <div className="absolute" style={{ left: dayX(0, width), right: dayX(0, width), top: LINE_Y, height: 1, background: 'var(--line2)' }} />
      {DAY_TICKS.map((t) => (
        <div key={t.label} className="absolute" style={{ left: dayX(t.minutes, width), top: LINE_Y - 4, transform: 'translateX(-50%)' }}>
          <div style={{ width: 1, height: 8, background: 'var(--line2)', margin: '0 auto' }} />
          <div className="text-[10px] text-ink3 mt-2" style={{ transform: t.minutes === 0 ? 'translateX(40%)' : t.minutes === 1440 ? 'translateX(-40%)' : undefined }}>
            {t.label}
          </div>
        </div>
      ))}
      <div className="absolute" style={{ left: nowX, top: 8, height: LINE_Y + 8 - 8, width: 1, background: 'var(--acc)' }} />
      <div className="absolute text-[10px] font-semibold whitespace-nowrap" style={{ left: nowX, top: -4, transform: 'translateX(-50%)', color: 'var(--acc-ink)' }}>
        now {timeHM(now, tz)}
      </div>
      {runs.map((r, i) => {
        const icon = RUN_ICON[r.status]
        return (
          <span key={`${r.time}-${i}`} className="absolute inline-flex rounded-full"
            style={{ left: xs[i], top: LINE_Y, transform: 'translate(-50%, -50%)', color: icon.color, background: 'var(--panel)',
              padding: 1, outline: hover === i ? '2px solid var(--line2)' : undefined }}>
            <Icon name={icon.name} size={16} />
          </span>
        )
      })}
      {h != null && hover != null && (
        <Tip left={clampTip(xs[hover], width)} top={-6} title={`${timeHM(h.time, tz)} · ${h.status}`} rows={[
          ['Run', h.label + (h.book_name ? ` · ${h.book_name}` : '')],
          ...(h.detail ? [['Detail', h.detail] as [string, string]] : []),
        ]} />
      )}
    </div>
  )
}

export function TodayPanel({ today, next, now, tz }: { today: DayRuns | null; next: RunRow | null; now: string; tz: string }) {
  const runs = [...(today?.runs ?? [])].sort((a, b) => minutesOfDay(a.time, tz) - minutesOfDay(b.time, tz))
  return (
    <Panel id="today" title="Today" subtitle={shortDate(now, tz)} span={12}>
      <DayLine runs={runs} now={now} tz={tz} />
      {next && (
        <p className="text-sm mt-3">
          <span className="text-ink3">Next:</span> {next.label} at <span className="num">{timeHM(next.time, tz)}</span>
          {next.book_name && <span className="text-ink3"> · {next.book_name}</span>}
        </p>
      )}
      {runs.length === 0 ? (
        <p className="text-ink2 mt-3">Nothing has run yet today.</p>
      ) : (
        <ul className="mt-3">{runs.map((r, i) => <RunLine key={`${r.time}-${i}`} r={r} tz={tz} />)}</ul>
      )}
    </Panel>
  )
}
