// An account's targets as one row each on a shared scale (spec 2026-10-08 plan §4.3): never stacked, summed or
// normalised, so a holding at 32 % of the account draws at 32 % of the scale whatever the other rows say. A sleeve's
// members sit indented under it. Pure: the panel only draws what this returns.
import { bandGeometry, type Band } from '../../charts/geometry'
import type { TargetRow } from '../../lib/api'

export interface Placed {
  row: TargetRow
  depth: 0 | 1 // 1: a member of the sleeve listed just above it
}

/** The rows in the view's order, each sleeve followed at once by its members; a member whose sleeve isn't in the
 *  list stays at the top level where it was. */
export function nestRows(rows: TargetRow[]): Placed[] {
  const ids = new Set(rows.map((r) => r.id))
  const kids = (id: string) => rows.filter((r) => r.parent === id)
  const out: Placed[] = []
  for (const row of rows) {
    if (row.parent != null && ids.has(row.parent)) continue
    out.push({ row, depth: 0 })
    for (const kid of kids(row.id)) out.push({ row: kid, depth: 1 })
  }
  return out
}

const STEP = 10

/** One scale for every "%" row of an account, 0 up to the next 10 above the largest band edge, aim or actual (with
 *  a tenth to spare), never past 100: the rows compare with each other, and a band reads at a useful width. */
export function percentDomain(rows: TargetRow[]): [number, number] {
  const values = rows.filter((r) => r.unit === '%')
    .flatMap((r) => [r.low, r.high, r.target, r.actual])
    .filter((v): v is number => v != null)
  const top = Math.max(STEP, ...values) * 1.1
  return [0, Math.min(100, Math.ceil(top / STEP) * STEP)]
}

/** A ratio ("x") row has no natural bound: its own scale, from 0 to a little past its largest figure. */
export function ratioDomain(row: TargetRow): [number, number] {
  const values = [row.low, row.high, row.target, row.actual].filter((v): v is number => v != null)
  const top = Math.max(1, ...values) * 1.15
  return [0, Math.ceil(top * 2) / 2]
}

export function domainFor(row: TargetRow, accountDomain: [number, number]): [number, number] {
  return row.unit === '%' ? accountDomain : ratioDomain(row)
}

/** The row's band, aim and actual as fractions of its scale. */
export function rowGeometry(row: TargetRow, domain: [number, number]): Band {
  return bandGeometry(row.low, row.high, row.target, row.actual, domain)
}

/** The axis labels under an account's rows: the ends and the middle. */
export function axisTicks(domain: [number, number]): number[] {
  const [lo, hi] = domain
  return [lo, (lo + hi) / 2, hi]
}
