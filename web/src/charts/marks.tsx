// Small SVG and tooltip pieces the charts share (docs/design-system.md → Charts).
import { type ReactNode, useId } from 'react'

/** A unique id that is safe inside url(#…): React's own ids carry characters a CSS url() would need escaped. */
export function useSvgId(prefix: string): string {
  return prefix + useId().replace(/[^a-zA-Z0-9_-]/g, '')
}

/** The paper hatch as an SVG pattern: 1.5 px of ink every 4 px, at 45°. Give each chart its own id (useSvgId). */
export function Hatch({ id, color }: { id: string; color: string }) {
  return (
    <defs>
      <pattern id={id} width={4} height={4} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width={1.5} height={4} fill={color} />
      </pattern>
    </defs>
  )
}

/** The tooltip card: a heading, then one row per series (label on the left, mono value on the right). */
export function Tip({ left, top = 4, title, rows }: {
  left: number; top?: number; title: string; rows: [label: string, value: ReactNode][]
}) {
  return (
    <div className="tip" style={{ left, top }} role="status">
      <div style={{ color: 'var(--ink3)', fontSize: 11 }}>{title}</div>
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between gap-4" style={{ marginTop: 4 }}>
          <span style={{ color: 'var(--ink2)' }}>{label}</span>
          <span className="num" style={{ fontWeight: 500 }}>{value}</span>
        </div>
      ))}
    </div>
  )
}

/** A chart with nothing to draw says so in plain words. */
export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-ink3 mt-6">{children}</p>
}
