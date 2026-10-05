// How long the cash would last: the months as the page's hero, the pace in words, and a ruler with the runway as
// a dot and, when the plan has a runway target, its band and aim (spec 2026-10-05 reserves §2.1).
import { useWidth } from '../../charts/hooks'
import { Panel } from '../../components/bits'
import type { ReservesView, Runway } from '../../lib/api'
import { money, num } from '../../lib/format'

const PAD = 8
const HEIGHT = 40
const TRACK_Y = 12
const TRACK_H = 8

/** The ruler's end: at least a year, further when the runway or the band reaches past it, in whole quarters. */
export function rulerEnd(r: Runway): number {
  const need = Math.max(12, Math.ceil(r.months) + 1, (r.high ?? 0) + 2, (r.aim ?? 0) + 2)
  return Math.ceil(need / 3) * 3
}

/** "4–8", "from 4", "up to 8", or null without a band. */
export function bandText(r: Pick<Runway, 'low' | 'high'>): string | null {
  const short = (v: number) => num(v, Number.isInteger(v) ? 0 : 1)
  if (r.low != null && r.high != null) return `${short(r.low)}–${short(r.high)}`
  if (r.low != null) return `from ${short(r.low)}`
  if (r.high != null) return `up to ${short(r.high)}`
  return null
}

export function rulerLabel(r: Runway): string {
  const parts = [r.aim != null ? `aim ${num(r.aim, Number.isInteger(r.aim) ? 0 : 1)}` : null,
    bandText(r) ? `band ${bandText(r)}` : null].filter(Boolean)
  return `Runway: ${num(r.months, 1)} months${parts.length ? `; ${parts.join(', ')}` : ''}`
}

function Ruler({ r }: { r: Runway }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(560)
  const end = rulerEnd(r)
  const x = (months: number) => PAD + Math.max(0, Math.min(end, months)) / end * (width - 2 * PAD)
  const ticks = Array.from({ length: end / 3 + 1 }, (_, i) => i * 3)
  const bandLo = r.low ?? (r.high != null ? 0 : null)
  const bandHi = r.high ?? (r.low != null ? end : null)
  return (
    <div ref={wrapRef} style={{ width: '100%' }}>
      <svg width={width} height={HEIGHT} role="img" aria-label={rulerLabel(r)} style={{ display: 'block', overflow: 'visible' }}>
        <rect x={PAD} y={TRACK_Y} width={width - 2 * PAD} height={TRACK_H} rx={4} fill="var(--panel2)"
          stroke="var(--line)" />
        {bandLo != null && bandHi != null && (
          <rect x={x(bandLo)} y={TRACK_Y} width={Math.max(0, x(bandHi) - x(bandLo))} height={TRACK_H} rx={4}
            fill="var(--line2)" />
        )}
        {r.aim != null && (
          <rect x={x(r.aim) - 1} y={TRACK_Y - 3} width={2} height={TRACK_H + 6} rx={1} fill="var(--ink2)" />
        )}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={TRACK_Y + TRACK_H + 2} y2={TRACK_Y + TRACK_H + 6} stroke="var(--line2)" />
            <text x={x(t)} y={HEIGHT - 2} fontSize={10} fill="var(--ink3)" textAnchor={t === 0 ? 'start' : t === end ? 'end' : 'middle'}>
              {t}
            </text>
          </g>
        ))}
        <circle cx={x(r.months)} cy={TRACK_Y + TRACK_H / 2} r={6} fill="var(--acc)" stroke="var(--panel)" strokeWidth={2} />
      </svg>
      {(r.aim != null || bandText(r)) && (
        <div className="text-[11px] text-ink3 mt-1">
          {r.aim != null && <>aim {num(r.aim, Number.isInteger(r.aim) ? 0 : 1)} months</>}
          {r.aim != null && bandText(r) && ' · '}
          {bandText(r) && <>band {bandText(r)}, shaded</>}
        </div>
      )}
    </div>
  )
}

export function RunwayPanel({ runway, totals, accounts }: {
  runway: Runway | null; totals: ReservesView['totals']; accounts: number
}) {
  const cashLine = `${money(totals.cash)} across ${accounts} account${accounts === 1 ? '' : 's'}`
  return (
    <Panel id="runway" title="Runway" subtitle="How long your cash would last" span={7}>
      {runway == null ? (
        <>
          <p className="text-ink2 mt-5">No bank transactions yet to measure the pace.</p>
          <div className="text-xs text-ink3 mt-3">{cashLine}</div>
        </>
      ) : (
        <>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-[36px] font-semibold tracking-[-0.03em] leading-none">{num(runway.months, 1)}</span>
            {' '}
            <span className="text-base font-medium text-ink2">months</span>
          </div>
          <p className="text-sm text-ink2 mt-2 max-w-[60ch]">
            at the pace money has left your cash these {runway.days} days,{' '}
            <span className="num text-ink1">{money(runway.monthly_out)}</span> a month
          </p>
          <div className="mt-4"><Ruler r={runway} /></div>
          <div className="text-xs text-ink3 mt-3">{cashLine}</div>
        </>
      )}
    </Panel>
  )
}
