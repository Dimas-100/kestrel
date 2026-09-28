// Stroke icons on a 24 px grid, 1.75 stroke, round caps (docs/design-system.md → Icons). Never emoji.
import type { CSSProperties, ReactElement } from 'react'

const PATHS: Record<string, ReactElement> = {
  home: <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1z" />,
  accounts: (<><rect x="3" y="6" width="18" height="14" rx="2" /><path d="M3 10h18" /><path d="M16 15h2" /></>),
  books: (<><path d="m12 3 9 5-9 5-9-5z" /><path d="m3 13 9 5 9-5" /></>),
  strategy: (<><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" />
    <path d="M8.5 6H15a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h6.5" /></>),
  backtests: (<><path d="M9 3h6" /><path d="M10 3v6L4.5 18.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3" />
    <path d="M7 15h10" /></>),
  activity: <path d="M3 12h4l2.5-6 5 12 2.5-6h4" />,
  settings: (<><path d="M4 7h10" /><path d="M18 7h2" /><path d="M4 17h4" /><path d="M12 17h8" />
    <circle cx="16" cy="7" r="2" /><circle cx="10" cy="17" r="2" /></>),
  refresh: (<><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 5v6h-6" /></>),
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />,
  sun: (<><circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>),
  chevron: <path d="m9 6 6 6-6 6" />,
  arrow: (<><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>),
  alert: (<><path d="M12 4 2.8 19.5a1 1 0 0 0 .9 1.5h16.6a1 1 0 0 0 .9-1.5z" /><path d="M12 10v4" /><path d="M12 17.5h.01" /></>),
  shield: (<><path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6z" /><path d="m9.5 9.5 5 5" /><path d="m14.5 9.5-5 5" /></>),
  clock: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  info: (<><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>),
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  checkCircle: (<><circle cx="12" cy="12" r="9" /><path d="m8 12.5 3 3 5-6" /></>),
  circle: <circle cx="12" cy="12" r="8" />,
  menu: (<><path d="M4 7h16" /><path d="M4 12h16" /><path d="M4 17h16" /></>),
  panel: (<><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /></>),
  more: (<><path d="M5 12h.01" /><path d="M12 12h.01" /><path d="M19 12h.01" /></>),
  scale: (<><path d="M12 4v16" /><path d="M5 8h14" /><path d="m5 8-2.5 6a3 3 0 0 0 5 0z" />
    <path d="m19 8-2.5 6a3 3 0 0 0 5 0z" /><path d="M8 20h8" /></>),
  calendar: (<><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18" /><path d="M8 3v4" />
    <path d="M16 3v4" /></>),
  target: (<><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" /></>),
}

export type IconName = keyof typeof PATHS

export function Icon({ name, size = 16, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flex: 'none', ...style }}>
      {PATHS[name]}
    </svg>
  )
}

/** The kestrel mark: a hovering bird, in the accent colour. */
export function Mark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" style={{ flex: 'none' }}>
      <path fill="var(--acc)" d="M1.5 10.2c3.2-.4 6.4.2 9.2 1.6L12 9.4l1.3 2.4c2.8-1.4 6-2 9.2-1.6-2.9 1.4-5.6 3-7.6 5.2l-.6 5.1h-4.6l-.6-5.1c-2-2.2-4.7-3.8-7.6-5.2z" />
    </svg>
  )
}
