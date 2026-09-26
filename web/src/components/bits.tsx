// Small shared pieces: the money-state mark and badge, deltas, panels, segmented controls.
import type { CSSProperties, ReactNode } from 'react'
import type { Money } from '../lib/api'

/** Real = solid, paper = hatched, expected = dotted. The one convention every page shares. */
export function BookMark({ kind, color, size = 12 }: { kind: Money | 'expected'; color?: string; size?: number }) {
  return (
    <span className={`mark ${kind}`} aria-hidden="true"
      style={{ width: size, height: size, ...(color ? ({ '--mc': color } as CSSProperties) : {}) }} />
  )
}

export function MoneyBadge({ money }: { money: Money }) {
  return <span className="badge"><BookMark kind={money} size={9} />{money === 'real' ? 'REAL' : 'PAPER'}</span>
}

/** A signed value with ▲/▼ so a gain or loss never rests on colour alone. */
export function Delta({ value, children }: { value: number; children: ReactNode }) {
  if (Math.abs(value) < 0.005) return <span className="num" style={{ color: 'var(--ink3)' }}>{children}</span>
  const up = value > 0
  return (
    <span className={`num ${up ? 'up' : 'down'}`}>
      <span aria-hidden="true">{up ? '▲' : '▼'} </span>
      <span className="sr-only">{up ? 'up ' : 'down '}</span>
      {children}
    </span>
  )
}

export function Panel({ id, title, subtitle, actions, span, height, children }: {
  id: string; title: string; subtitle?: string; actions?: ReactNode; span: 4 | 5 | 7 | 8 | 12; height?: number
  children: ReactNode
}) {
  return (
    <section className={`panel span-${span}`} aria-labelledby={`${id}-title`}
      style={height ? ({ '--h': `${height}px` } as CSSProperties) : undefined}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={`${id}-title`} className="panel-title">{title}</h2>
          {subtitle && <div className="panel-sub">{subtitle}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
      {children}
    </section>
  )
}

export function Seg<T extends string>({ label, options, value, onChange }: {
  label: string; options: readonly T[]; value: T; onChange: (value: T) => void
}) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((option) => (
        <button key={option} type="button" aria-pressed={option === value} onClick={() => onChange(option)}>
          {option}
        </button>
      ))}
    </div>
  )
}

/** "—" for a missing value (design-system rule), in muted ink */
export function Missing() {
  return <span style={{ color: 'var(--ink3)' }}>—</span>
}
