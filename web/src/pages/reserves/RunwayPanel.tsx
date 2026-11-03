// Coverage: how long the cash would last at the pace money has left it, moves between your own accounts left out —
// in days under sixty, in months from there. Under the figure, a scale in the same unit with the coverage as an accent
// fill: a short scale in weeks when it is days (so "4 days" fills a visible part of a two-week bar instead of a dot at
// the start of a year), quarters when it is months, with a plan's runway band when it fits. How it is worked out
// opens beneath (spec 2026-10-08 reserves estimates §2, §3.3).
import type { ReactNode } from 'react'
import { useWidth } from '../../charts/hooks'
import { Icon } from '../../components/Icon'
import { Panel, Stat } from '../../components/bits'
import type { ReservesView, Runway } from '../../lib/api'
import { money, monthLabel, num, shortDate } from '../../lib/format'
import { Caveat } from './Caveat'

const PAD = 8
const HEIGHT = 58
const TRACK_Y = 20 // room above the track for the figure at the fill's end
const TRACK_H = 12
export const SHORT_DAYS = 60 // the view's rule: under this many days the figure reads in days
const MONTH_DAYS = 30.4375

type Cover = Pick<Runway, 'unit' | 'days_cover' | 'months'>

/** "4 days", "1 day", "6.3 months" */
export function coverageText(c: Cover): string {
  return c.unit === 'months' ? `${num(c.months, 1)} months` : `${c.days_cover} day${c.days_cover === 1 ? '' : 's'}`
}

/** The coverage some other amount of cash would give at the same pace (the pay-down's after), by the view's rules:
 *  whole days rounded down, never below zero. */
export function coverFor(cash: number, r: Runway): Cover {
  const left = Math.max(0, cash)
  const days = Math.floor(left / r.daily_out)
  return { unit: days < SHORT_DAYS ? 'days' : 'months', days_cover: days, months: Math.round(left / r.daily_out / MONTH_DAYS * 10) / 10 }
}

/** The months scale's end: at least a year, further when the runway or the band reaches past it, in whole quarters. */
export function rulerEnd(r: Runway): number {
  const need = Math.max(12, Math.ceil(r.months) + 1, (r.high ?? 0) + 2, (r.aim ?? 0) + 2)
  return Math.ceil(need / 3) * 3
}

/** The days scale's end: whole weeks, two at least, with room past the figure. */
export function dayScaleEnd(days: number): number {
  return Math.max(2, Math.ceil((days + 1) / 7)) * 7
}

/** "4–8", "from 4", "up to 8", or null without a band. */
export function bandText(r: Pick<Runway, 'low' | 'high'>): string | null {
  const short = (v: number) => num(v, Number.isInteger(v) ? 0 : 1)
  if (r.low != null && r.high != null) return `${short(r.low)}–${short(r.high)}`
  if (r.low != null) return `from ${short(r.low)}`
  if (r.high != null) return `up to ${short(r.high)}`
  return null
}

const aimText = (aim: number) => `${num(aim, Number.isInteger(aim) ? 0 : 1)} months`

/** The scale's unit, end, ticks and the coverage on it, in that unit. */
export function scaleOf(r: Runway) {
  if (r.unit === 'days') {
    const end = dayScaleEnd(r.days_cover)
    const every = end > 42 ? 14 : 7
    const ticks = Array.from({ length: end / every + 1 }, (_, i) => i * every)
    // a band or aim is in months: it is drawn only when it lands on this short scale, else said in words
    const toDays = (m: number | null) => (m == null ? null : m * MONTH_DAYS)
    const fits = (v: number | null) => v != null && v <= end
    return {
      unit: 'days' as const, end, value: r.days_cover, ticks, minor: end <= 21 ? 1 : 0,
      tickText: (t: number) => (t === 0 ? 'today' : `${t / 7} wk`),
      aim: fits(toDays(r.aim)) ? toDays(r.aim) : null,
      low: fits(toDays(r.low)) ? toDays(r.low) : null, high: fits(toDays(r.high)) ? toDays(r.high) : null,
      offScale: r.aim != null && !fits(toDays(r.aim)),
    }
  }
  const end = rulerEnd(r)
  return {
    unit: 'months' as const, end, value: r.months, ticks: Array.from({ length: end / 3 + 1 }, (_, i) => i * 3), minor: 0,
    tickText: (t: number) => (t === 0 ? 'today' : `${t} mo`), aim: r.aim, low: r.low, high: r.high, offScale: false,
  }
}

export function scaleLabel(r: Runway): string {
  const s = scaleOf(r)
  if (s.unit === 'days') {
    const aim = r.aim == null ? '' : `; aim ${aimText(r.aim)}${s.offScale ? ', past the end of the scale' : ''}`
    return `Coverage: ${coverageText(r)} on a scale of ${s.end} days${aim}`
  }
  const parts = [r.aim != null ? `aim ${num(r.aim, Number.isInteger(r.aim) ? 0 : 1)}` : null,
    bandText(r) ? `band ${bandText(r)}` : null].filter(Boolean)
  return `Coverage: ${num(r.months, 1)} months${parts.length ? `; ${parts.join(', ')}` : ''}`
}

function Scale({ r }: { r: Runway }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(560)
  const s = scaleOf(r)
  const x = (v: number) => PAD + Math.max(0, Math.min(s.end, v)) / s.end * (width - 2 * PAD)
  const bandLo = s.low ?? (s.high != null ? 0 : null)
  const bandHi = s.high ?? (s.low != null ? s.end : null)
  const fillEnd = x(s.value)
  const figureAnchor = fillEnd < 60 ? 'start' : fillEnd > width - 60 ? 'end' : 'middle'
  return (
    <div ref={wrapRef} style={{ width: '100%' }}>
      <svg width={width} height={HEIGHT} role="img" aria-label={scaleLabel(r)} style={{ display: 'block', overflow: 'visible' }}>
        <rect x={PAD} y={TRACK_Y} width={width - 2 * PAD} height={TRACK_H} rx={6} fill="var(--panel2)" stroke="var(--line)" />
        {bandLo != null && bandHi != null && (
          <rect x={x(bandLo)} y={TRACK_Y} width={Math.max(0, x(bandHi) - x(bandLo))} height={TRACK_H} rx={6} fill="var(--line2)" />
        )}
        {s.minor > 0 && Array.from({ length: s.end - 1 }, (_, i) => i + 1).filter((d) => d % 7 !== 0).map((d) => (
          <line key={`m${d}`} x1={x(d)} x2={x(d)} y1={TRACK_Y + 3} y2={TRACK_Y + TRACK_H - 3} stroke="var(--line)" />
        ))}
        {s.value > 0 && (
          <rect x={PAD} y={TRACK_Y} width={Math.max(TRACK_H, fillEnd - PAD)} height={TRACK_H} rx={6} fill="var(--acc)" />
        )}
        {s.aim != null && (
          <rect x={x(s.aim) - 1} y={TRACK_Y - 4} width={2} height={TRACK_H + 8} rx={1} fill="var(--ink2)" />
        )}
        <text x={fillEnd} y={TRACK_Y - 7} fontSize={11} fontWeight={600} fill="var(--ink1)" textAnchor={figureAnchor}>
          {coverageText(r)}
        </text>
        {s.ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={TRACK_Y + TRACK_H + 2} y2={TRACK_Y + TRACK_H + 6} stroke="var(--line2)" />
            <text x={x(t)} y={HEIGHT - 2} fontSize={10} fill="var(--ink3)"
              textAnchor={t === 0 ? 'start' : t === s.end ? 'end' : 'middle'}>{s.tickText(t)}</text>
          </g>
        ))}
      </svg>
      {(r.aim != null || bandText(r)) && (
        <div className="text-[11px] text-ink3 mt-1.5">
          {s.unit === 'days'
            ? r.aim != null && <>Your plan aims for {aimText(r.aim)}{s.offScale ? ', past the end of this scale' : ', the tick'}</>
            : <>{r.aim != null && <>aim {num(r.aim, Number.isInteger(r.aim) ? 0 : 1)} months</>}
              {r.aim != null && bandText(r) && ' · '}{bandText(r) && <>band {bandText(r)}, shaded</>}</>}
        </div>
      )}
    </div>
  )
}

function Line({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="py-1.5 border-t border-line first:border-t-0">
      <dt className="text-[11px] text-ink3">{term}</dt>
      <dd className="text-xs text-ink2 mt-0.5">{children}</dd>
    </div>
  )
}

/** How the figure is worked out: the pace, the window, what was left out and what wasn't. */
function Workings({ r, cash, accounts }: { r: Runway; cash: number; accounts: number }) {
  const span = `${monthLabel(r.since, true)} – ${monthLabel(r.through, true)}`
  return (
    <details className="disclosure mt-4">
      <summary className="inline-flex items-center gap-1.5 text-xs text-ink2 cursor-pointer select-none">
        <Icon name="chevron" size={13} />
        How it&rsquo;s worked out
      </summary>
      <dl aria-label="How coverage is worked out" className="prose min-w-0 mt-2 grid gap-x-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <Line term="Pace">
          <span className="num text-ink1">{money(r.daily_out)}</span> a day · <span className="num">{money(r.monthly_out)}</span> a month
        </Line>
        <Line term="Window">{r.days} days of bank rows, {span}</Line>
        <Line term="Left out">
          {r.moved_count > 0
            ? <><span className="num">{money(r.moved)}</span> moved between your own accounts ({r.moved_count} transfer{r.moved_count === 1 ? '' : 's'})</>
            : 'Nothing: no moves between your own accounts found'}
        </Line>
        <Line term="Counted">Everything else that left your cash: card payments, investing, people, bills</Line>
        <Line term="Assumes">No money comes in, and today&rsquo;s <span className="num">{money(cash)}</span> across {accounts}{' '}
          account{accounts === 1 ? '' : 's'}</Line>
      </dl>
    </details>
  )
}

/** The day the cash would run out at this pace: the view's day plus the whole days covered. */
export function runsOut(today: string, days: number): string {
  const d = new Date(`${today}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return shortDate(d.toISOString().slice(0, 10))
}

export function RunwayPanel({ runway, totals, accounts, today }: {
  runway: Runway | null; totals: ReservesView['totals']; accounts: number; today: string
}) {
  const cashLine = `${money(totals.cash)} across ${accounts} account${accounts === 1 ? '' : 's'}`
  return (
    <Panel id="coverage" title="Coverage" subtitle="How long your cash would last at the recent pace" span={7}>
      {runway == null ? (
        <>
          <p className="text-ink2 mt-5">No bank transactions yet to measure the pace.</p>
          <div className="text-xs text-ink3 mt-3">{cashLine}</div>
        </>
      ) : (
        <>
          <div className="flex items-baseline gap-2 mt-4">
            <span className="text-[36px] font-semibold tracking-[-0.03em] leading-none">
              {runway.unit === 'months' ? num(runway.months, 1) : runway.days_cover}
            </span>
            <span className="text-base font-medium text-ink2">
              {runway.unit === 'months' ? 'months' : runway.days_cover === 1 ? 'day' : 'days'}
            </span>
          </div>
          <p className="text-sm text-ink2 mt-2">
            At <span className="num text-ink1">{money(runway.daily_out)}</span> a day, the pace of the last {runway.days}{' '}
            days,{' '}
            {runway.days_cover === 0
              ? 'your cash would not cover a day.'
              : runway.unit === 'days'
                ? <>your cash would run out around <span className="text-ink1">{runsOut(today, runway.days_cover)}</span>.</>
                : 'with nothing coming in.'}
          </p>
          <div className="mt-4"><Scale r={runway} /></div>
          {/* the assumptions that move the figure most, always in view; the rest open beneath */}
          <div className="flex flex-wrap gap-x-8 gap-y-3 mt-5 pt-3.5 border-t border-line" aria-label="Key assumptions" role="group">
            <Stat label="Pace"><span className="num">{money(runway.daily_out)}</span><span className="text-ink3"> a day</span></Stat>
            <Stat label="Window"><span className="num">{runway.days}</span><span className="text-ink3"> days of bank rows</span></Stat>
            <Stat label="Left out"><span className="num">{money(runway.moved)}</span><span className="text-ink3"> moved between your accounts</span></Stat>
          </div>
          <Workings r={runway} cash={totals.cash} accounts={accounts} />
          {runway.stale && (
            <Caveat warn>
              No bank rows since {monthLabel(runway.through, true)}: the pace may be out of date.
            </Caveat>
          )}
        </>
      )}
    </Panel>
  )
}
