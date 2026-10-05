// An account's percent targets as the segments of two bars: what is held, and what is aimed for (spec 2026-10-05
// plan page §2.3). Pure: the panel only draws what this returns.
import type { TargetRow } from '../../lib/api'

export interface Segment {
  id: string
  label: string
  pct: number // the share of the account, 0..100
  status: TargetRow['status']
}

export interface AimSegment extends Segment {
  fromBand: boolean // true when the row has no aim and the middle of its band (or 0 with no band) stands in
}

export interface Allocation {
  actual: Segment[] // the rows' shares, scaled down together when they add past 100
  other: number // what the targets don't cover, 0..100
  aim: AimSegment[] // the same rows, the aims
}

/** Only the percent rows with a measured actual take part; a ratio row or an unknown one can't be a share. */
export function allocationSegments(rows: TargetRow[]): Allocation {
  const shares = rows.filter((r): r is TargetRow & { actual: number } => r.unit === '%' && r.actual != null)
  const sum = shares.reduce((acc, r) => acc + Math.max(0, r.actual), 0)
  const scale = sum > 100 ? 100 / sum : 1
  const actual = shares.map((r) => ({ id: r.id, label: r.label, pct: Math.max(0, r.actual) * scale, status: r.status }))
  const aim = shares.map((r) => {
    const fromBand = r.target == null
    const pct = r.target ?? (r.low != null && r.high != null ? (r.low + r.high) / 2 : (r.low ?? r.high ?? 0))
    return { id: r.id, label: r.label, pct: Math.max(0, pct), status: r.status, fromBand }
  })
  return { actual, other: Math.max(0, 100 - sum * scale), aim }
}
