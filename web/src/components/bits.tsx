// Small shared pieces: the money-state mark and badge, deltas, panels, segmented controls, stat blocks, sortable
// column headings and the category chip.
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

/** A signed value with ▲/▼ so a gain or loss never rests on colour alone. `digits` is the precision the value is
 *  shown at (pct() shows 1, money 2): what rounds to zero there is no change — muted, no arrow. */
export function Delta({ value, digits = 2, children }: { value: number; digits?: number; children: ReactNode }) {
  if (Math.abs(value) < 0.5 * 10 ** -digits) {
    return <span className="num" style={{ color: 'var(--ink3)' }}>{children}</span>
  }
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
  id: string; title: string; subtitle?: string; actions?: ReactNode; span: 4 | 5 | 6 | 7 | 8 | 12; height?: number
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

/** The stat block: a caps label, the value, and a muted second line. */
export function Stat({ label, children, sub }: { label: string; children: ReactNode; sub?: ReactNode }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="text-[13px] mt-1.5">{children}</div>
      {sub && <div className="text-xs text-ink3 mt-1">{sub}</div>}
    </div>
  )
}

export interface Sort<K extends string> { key: K; dir: 'desc' | 'asc' }

/** A column clicked again flips its order; another column starts largest first. */
export function toggleSort<K extends string>(sort: Sort<K>, key: K): Sort<K> {
  return sort.key === key ? { key, dir: sort.dir === 'desc' ? 'asc' : 'desc' } : { key, dir: 'desc' }
}

/** A sortable column heading: a real button, with the order announced on the heading cell. */
export function SortHeader<K extends string>({ label, k, sort, onSort, right = false }: {
  label: string; k: K; sort: Sort<K>; onSort: (key: K) => void; right?: boolean
}) {
  const active = sort.key === k
  return (
    <th className={right ? 'r' : undefined} aria-sort={active ? (sort.dir === 'desc' ? 'descending' : 'ascending') : 'none'}>
      <button type="button" onClick={() => onSort(k)} className="uppercase tracking-[0.08em] font-medium"
        style={{ color: active ? 'var(--ink1)' : 'inherit', background: 'none', border: 0, padding: 0, cursor: 'pointer',
          font: 'inherit' }}>
        {label}
      </button>
      {active && <span aria-hidden="true"> {sort.dir === 'desc' ? '↓' : '↑'}</span>}
    </th>
  )
}

/** Where an account's money is filed: long-term money is slate, trading rufous, cash neutral. */
export const CATEGORY_COLOR: Record<string, string> = {
  long_term: 'var(--s1)', trading: 'var(--s2)', cash: 'var(--s3)', other: 'var(--ink3)',
}
export const CATEGORY_WORD: Record<string, string> = {
  long_term: 'Long-term', trading: 'Trading', cash: 'Cash', other: 'Other',
}

/** The category as a word beside its dot, so the colour is never the only cue. */
export function CategoryChip({ category }: { category: string }) {
  return (
    <span className="chip">
      <span aria-hidden="true" className="w-2 h-2 rounded-full flex-none"
        style={{ background: CATEGORY_COLOR[category] ?? 'var(--ink3)' }} />
      {CATEGORY_WORD[category] ?? category}
    </span>
  )
}
