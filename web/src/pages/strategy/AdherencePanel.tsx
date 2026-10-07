// Did the trades follow the rules in force when they were entered? One row per rules version, the deviations
// listed under it, and the method in a sentence.
import type { CSSProperties } from 'react'
import { Empty } from '../../charts/marks'
import { Missing, Panel } from '../../components/bits'
import type { Adherence, AdherenceRow } from '../../lib/api'
import { monthLabel } from '../../lib/format'

/** "15 of 16 followed" · "not scored" */
export function followedText(r: AdherenceRow): string {
  const scored = r.followed + r.broken
  if (scored === 0) return r.trades ? 'not scored' : '—'
  return `${r.followed} of ${scored} followed${r.unscored ? ` · ${r.unscored} not scored` : ''}`
}

export function AdherencePanel({ a }: { a: Adherence }) {
  const rows = a.rows.filter((r) => r.trades > 0 || r.effective)
  return (
    <Panel id="adherence" title="Did it follow the rules?" span={12}
      subtitle="Each trade is judged against the rules in force when it was entered">
      {!a.reported || rows.length === 0 ? (
        <Empty>{a.reported ? 'No closed trades yet.' : a.note}</Empty>
      ) : (
        <>
          <div className="table-scroll mt-3.5">
            <table className="tbl" style={{ minWidth: 720, '--row': '44px' } as CSSProperties}>
              <thead>
                <tr>
                  <th>Rules</th><th>Since</th><th className="r">Trades</th><th className="r">Entries system / hand</th>
                  <th className="r">Exits system / hand</th><th>Plan followed</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.version}>
                    <td>
                      <div className="text-sm font-medium">{r.version}<span className="text-ink3 font-normal"> · {r.system_run ? 'system-run' : 'run by hand'}</span></div>
                      {r.summary && <div className="text-[11px] text-ink3 [overflow-wrap:anywhere]">{r.summary}</div>}
                    </td>
                    <td className="num text-xs text-ink2 whitespace-nowrap">{r.effective ? monthLabel(r.effective, true) : <Missing />}</td>
                    <td className="r num">{r.trades}</td>
                    <td className="r num">{r.system_entries} / {r.hand_entries}</td>
                    <td className="r num">{r.system_exits} / {r.hand_exits}</td>
                    <td className="text-xs">{followedText(r)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4">
            <div className="label">Deviations</div>
            {a.deviations.length === 0 ? (
              <p className="text-xs text-ink2 mt-1.5">None on record.</p>
            ) : (
              <ul className="mt-1.5 flex flex-col gap-1">
                {a.deviations.map((d, i) => (
                  <li key={`${d.symbol}-${d.closed}-${i}`} className="text-xs text-ink2">
                    <span className="num font-semibold text-ink1">{d.symbol}</span>
                    {' '}· {monthLabel(d.opened, true)} → {monthLabel(d.closed, true)} · {d.rules_version} · {d.what}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <p className="text-xs text-ink3 mt-3">{a.note}</p>
        </>
      )}
    </Panel>
  )
}
