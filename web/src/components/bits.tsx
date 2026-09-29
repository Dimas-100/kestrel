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

/** `labels` overrides an option's display word (the value passed to `onChange` is always the option itself). */
export function Seg<T extends string>({ label, options, value, onChange, labels }: {
  label: string; options: readonly T[]; value: T; onChange: (value: T) => void; labels?: Partial<Record<T, string>>
}) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((option) => (
        <button key={option} type="button" aria-pressed={option === value} onClick={() => onChange(option)}>
          {labels?.[option] ?? option}
        </button>
      ))}
    </div>
  )
}

/** Under a chart of every account together: how many accounts have no history of their own, and so are drawn flat
 *  at today's balance. Nothing when every account has a history. */
export function NoHistoryNote({ count }: { count: number }) {
  if (count <= 0) return null
  return (
    <p className="text-xs text-ink3 mt-2">
      {count === 1 ? '1 account has' : `${count} accounts have`} no history: counted at today's balance
    </p>
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
      {sub && <div className="prose text-xs text-ink3 mt-1">{sub}</div>}
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

/** Where an account's money is filed: long-term money is slate, trading rufous, cash neutral. What is owed takes no
 *  hue of its own: it is never a slice of the waffle. */
export const CATEGORY_COLOR: Record<string, string> = {
  long_term: 'var(--s1)', trading: 'var(--s2)', cash: 'var(--s3)', debt: 'var(--ink3)', other: 'var(--ink3)',
}
export const CATEGORY_WORD: Record<string, string> = {
  long_term: 'Long-term', trading: 'Trading', cash: 'Cash', debt: 'Debt', other: 'Other',
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

/** An institution's initials: "Capital One" -> "CO", "Fidelity" -> "F". */
export function initials(institution: string): string {
  const words = institution.replace(/[^A-Za-z0-9 ]/g, ' ').split(/\s+/).filter((w) => w && !/^(of|the|and)$/i.test(w))
  if (words.length === 0) return '?'
  return words.slice(0, 2).map((w) => w[0].toUpperCase()).join('')
}

/** A row's leading tile: the institution's initials on a wash of the account's category colour, so rows scan by
 *  institution without a logo fetched from anywhere. The text beside it names the institution in words. */
export function InstitutionTile({ institution, category, size = 28 }: {
  institution: string; category: string; size?: number
}) {
  const color = CATEGORY_COLOR[category] ?? 'var(--s3)'
  return (
    <span aria-hidden="true" className="flex-none inline-flex items-center justify-center font-semibold"
      style={{ width: size, height: size, borderRadius: 7, fontSize: Math.round(size * 0.38), letterSpacing: '-0.02em',
        color, background: `color-mix(in srgb, ${color} 16%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${color} 30%, transparent)` }}>
      {initials(institution)}
    </span>
  )
}
