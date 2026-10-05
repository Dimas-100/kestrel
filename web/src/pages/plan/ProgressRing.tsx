// A ring whose arc is the share reached, the percent inside; a reached goal's ring is full with a check. The accent
// is the fill, as every progress fill is; the word beside the ring, never its colour, says reached or overdue.

export function ProgressRing({ pct, label, reached = false, size = 64 }: {
  pct: number; label: string; reached?: boolean; size?: number
}) {
  const stroke = 6
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const share = reached ? 1 : Math.max(0, Math.min(100, pct)) / 100
  const mid = size / 2
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img"
      aria-label={`${label}: ${Math.round(reached ? 100 : pct)}% there`} style={{ flex: 'none' }}>
      <circle cx={mid} cy={mid} r={r} fill="none" stroke="var(--panel2)" strokeWidth={stroke} />
      <circle cx={mid} cy={mid} r={r + stroke / 2} fill="none" stroke="var(--line)" strokeWidth={1} />
      <circle cx={mid} cy={mid} r={r} fill="none" stroke={reached ? 'var(--good)' : 'var(--acc)'} strokeWidth={stroke}
        strokeDasharray={`${c * share} ${c}`} strokeLinecap={share > 0 && share < 1 ? 'round' : 'butt'}
        transform={`rotate(-90 ${mid} ${mid})`} />
      {reached ? (
        <g transform={`translate(${mid - 12} ${mid - 12})`}>
          <path d="m5 12.5 4.5 4.5L19 7.5" fill="none" stroke="var(--good)" strokeWidth={2} strokeLinecap="round"
            strokeLinejoin="round" />
        </g>
      ) : (
        <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" fontSize={size * 0.24} fontWeight={600}
          fill="var(--ink1)" style={{ fontFamily: 'var(--k-sans)', letterSpacing: '-0.02em' }}>
          {Math.round(pct)}%
        </text>
      )}
    </svg>
  )
}
