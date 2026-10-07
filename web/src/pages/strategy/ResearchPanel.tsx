// What the expected figures rest on — stage, configuration, sizing, costs, sample, caveats — and this strategy's
// rows in the research record. Text only: a backtest is evidence with conditions, not a promise.
import type { CSSProperties } from 'react'
import { Empty } from '../../charts/marks'
import { Missing, Panel } from '../../components/bits'
import type { Research } from '../../lib/api'
import { num, pct, shortDate } from '../../lib/format'
import { VerdictChip } from '../backtests/Backtests'

const BASIS: [keyof Pick<NonNullable<Research['expected']>, 'stage' | 'config' | 'sizing' | 'costs' | 'sample'>, string][] = [
  ['stage', 'Stage'], ['config', 'Configuration'], ['sizing', 'Sizing'], ['costs', 'Costs modelled'], ['sample', 'Sample'],
]

export function ResearchPanel({ r, tz }: { r: Research; tz: string }) {
  const e = r.expected
  const lines = e ? BASIS.filter(([key]) => e[key]) : []
  return (
    <Panel id="research" title="What the expectation rests on" span={12}
      subtitle={e ? `${e.source || 'Backtest'}${e.window ? ` · ${e.window}` : ''}` : undefined}>
      {!e && r.backtests.length === 0 ? (
        <Empty>No backtest to compare with.</Empty>
      ) : (
        <>
          {e && (
            <dl className="grid grid-cols-1 sm:grid-cols-2 min-[1180px]:grid-cols-5 gap-x-6 gap-y-3 mt-3.5">
              {lines.map(([key, label]) => (
                <div key={key} className="min-w-0">
                  <dt className="label">{label}</dt>
                  <dd className="text-xs text-ink2 mt-1 [overflow-wrap:anywhere]">{e[key]}</dd>
                </div>
              ))}
              {lines.length === 0 && (
                <div className="sm:col-span-2 min-[1180px]:col-span-5 text-xs text-ink3">
                  The source doesn&rsquo;t say how this backtest was configured, sized or costed.
                </div>
              )}
            </dl>
          )}
          {e && e.caveats.length > 0 && (
            <div className="mt-3.5">
              <div className="label">Caveats</div>
              <ul className="mt-1.5 flex flex-col gap-1 text-xs text-ink2 list-disc pl-4">
                {e.caveats.map((c) => <li key={c}>{c}</li>)}
              </ul>
            </div>
          )}
          {r.backtests.length > 0 && (
            <div className="table-scroll mt-4">
              <table className="tbl" style={{ minWidth: 720, '--row': '44px' } as CSSProperties}>
                <thead>
                  <tr>
                    <th>Result</th><th>Stage</th><th>Verdict</th><th className="r">Trades</th>
                    <th className="r">Avg / trade</th><th className="r">Yearly</th><th className="r">Worst drop</th><th>At</th>
                  </tr>
                </thead>
                <tbody>
                  {r.backtests.map((b) => (
                    <tr key={b.id}>
                      <td>
                        <div className="text-sm font-medium">{b.name}</div>
                        {(b.config || b.sizing || b.costs || b.sample) && (
                          <div className="text-[11px] text-ink3 [overflow-wrap:anywhere]">
                            {[b.config, b.sizing, b.costs, b.sample].filter(Boolean).join(' · ')}
                          </div>
                        )}
                        {b.caveats.length > 0 && (
                          <div className="text-[11px] text-ink3 [overflow-wrap:anywhere]">Caveats: {b.caveats.join('; ')}</div>
                        )}
                      </td>
                      <td className="capitalize text-xs text-ink2">{b.window || <Missing />}</td>
                      <td><VerdictChip verdict={b.verdict} /></td>
                      <td className="r num">{b.trades == null ? <Missing /> : num(b.trades, 0)}</td>
                      <td className="r num">{b.avg_trade_pct == null ? <Missing /> : pct(b.avg_trade_pct, 2)}</td>
                      <td className="r num">{b.cagr_pct == null ? <Missing /> : pct(b.cagr_pct, 1)}</td>
                      <td className="r num">{b.max_drawdown_pct == null ? <Missing /> : pct(b.max_drawdown_pct, 1)}</td>
                      <td className="text-xs text-ink2 whitespace-nowrap">{shortDate(b.at, tz)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </Panel>
  )
}
