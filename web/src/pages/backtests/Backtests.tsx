// The research record: every family tried, its best result, and the newest 200 individual runs.
import { useMemo, useState } from 'react'
import { Empty } from '../../charts/marks'
import { Missing, Panel, Stat } from '../../components/bits'
import { type Backtest, type BacktestsView, type BacktestVerdict, type FamilyRow, useBacktests } from '../../lib/api'
import { num, pct, shortDate } from '../../lib/format'

const SHOWN_FAMILIES = 25

export const VERDICT_WORD: Record<BacktestVerdict, string> = {
  pass: 'Pass', fail: 'Fail', refused: 'Refused', pending: 'Pending',
}
const VERDICT_COLOR: Record<BacktestVerdict, string> = {
  pass: 'var(--good)', fail: 'var(--serious)', refused: 'var(--ink3)', pending: 'var(--warn)',
}

type RowFilter = 'all' | 'passed' | 'failed'

export function VerdictChip({ verdict }: { verdict: BacktestVerdict }) {
  return (
    <span className="chip">
      <span aria-hidden="true" className="w-2 h-2 rounded-full flex-none" style={{ background: VERDICT_COLOR[verdict] }} />
      {VERDICT_WORD[verdict]}
    </span>
  )
}

/** Whether a row belongs under the all/passed/failed filter. */
export function matchesRowFilter(verdict: BacktestVerdict, filter: RowFilter): boolean {
  if (filter === 'passed') return verdict === 'pass'
  if (filter === 'failed') return verdict === 'fail'
  return true
}

/** Whether a result matches a free-text search of its family or its own name. */
export function matchesSearch(b: Backtest, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return b.family.toLowerCase().includes(q) || b.name.toLowerCase().includes(q)
}

function BestCell({ best }: { best: Backtest | null }) {
  if (!best) return <Missing />
  return (
    <div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-medium">{best.name}</span>
        <VerdictChip verdict={best.verdict} />
      </div>
      <div className="text-xs text-ink3 mt-0.5">
        {best.trades == null ? <Missing /> : `${num(best.trades, 0)} trades`}
        {best.avg_trade_pct != null && <> · {pct(best.avg_trade_pct, 2)} / trade</>}
        {best.t_stat != null && <> · t {num(best.t_stat, 2)}</>}
      </div>
    </div>
  )
}

function FamiliesPanel({ families, windows }: { families: FamilyRow[]; windows: string[] }) {
  const [all, setAll] = useState(false)
  const shown = all ? families : families.slice(0, SHOWN_FAMILIES)
  return (
    <Panel id="backtests-families" title="Families" subtitle="A pass first, then the most recently run" span={12}>
      {families.length === 0 ? <Empty>No families yet.</Empty> : (
        <>
          <div className="table-scroll mt-3.5">
            <table className="tbl" style={{ minWidth: 640 }}>
              <thead>
                <tr>
                  <th>Family</th><th className="r">Candidates</th><th>Best result</th>
                  {windows.map((w) => <th key={w} className="capitalize">{w}</th>)}
                  <th>Last ran</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((f) => (
                  <tr key={f.family}>
                    <td className="font-medium">{f.family || <Missing />}</td>
                    <td className="r num">{num(f.candidates, 0)}</td>
                    <td><BestCell best={f.best} /></td>
                    {windows.map((w) => (
                      <td key={w}>{f.verdicts[w] ? <VerdictChip verdict={f.verdicts[w]} /> : <Missing />}</td>
                    ))}
                    <td className="text-sm text-ink2">{shortDate(f.last_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {families.length > SHOWN_FAMILIES && (
            <button type="button" onClick={() => setAll(!all)} className="self-start mt-3 text-xs"
              style={{ color: 'var(--acc-ink)', background: 'none', border: 0, padding: 0, cursor: 'pointer' }}>
              {all ? `Show the first ${SHOWN_FAMILIES}` : `Show all ${families.length}`}
            </button>
          )}
        </>
      )}
    </Panel>
  )
}

function ResultsPanel({ rows }: { rows: Backtest[] }) {
  const [filter, setFilter] = useState<RowFilter>('all')
  const [query, setQuery] = useState('')
  const shown = useMemo(
    () => rows.filter((b) => matchesRowFilter(b.verdict, filter) && matchesSearch(b, query)),
    [rows, filter, query],
  )
  return (
    <Panel id="backtests-rows" title="Results" subtitle="The newest 200 results" span={12}
      actions={(
        <div className="flex flex-wrap items-center gap-3">
          <div className="seg" role="group" aria-label="Verdict">
            {(['all', 'passed', 'failed'] as const).map((f) => (
              <button key={f} type="button" aria-pressed={f === filter} onClick={() => setFilter(f)}
                className="capitalize">
                {f}
              </button>
            ))}
          </div>
          <input type="search" className="search" placeholder="Search family or name" value={query}
            onChange={(e) => setQuery(e.target.value)} aria-label="Search family or name" />
        </div>
      )}>
      {shown.length === 0 ? <Empty>No results match.</Empty> : (
        <div className="table-scroll mt-3.5">
          <table className="tbl" style={{ minWidth: 760 }}>
            <thead>
              <tr>
                <th>Name</th><th>Family</th><th>Window</th><th>Verdict</th><th className="r">Trades</th>
                <th className="r">Avg / trade</th><th className="r">t</th><th>At</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((b) => (
                <tr key={b.id}>
                  <td className="font-medium">{b.name}</td>
                  <td className="text-ink2">{b.family || <Missing />}</td>
                  <td className="capitalize text-ink2">{b.window || <Missing />}</td>
                  <td><VerdictChip verdict={b.verdict} /></td>
                  <td className="r num">{b.trades == null ? <Missing /> : num(b.trades, 0)}</td>
                  <td className="r num">{b.avg_trade_pct == null ? <Missing /> : pct(b.avg_trade_pct, 2)}</td>
                  <td className="r num">{b.t_stat == null ? <Missing /> : num(b.t_stat, 2)}</td>
                  <td className="text-sm text-ink2">{shortDate(b.at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}

function TotalsRow({ totals }: { totals: BacktestsView['totals'] }) {
  const passes = Object.entries(totals.passes_by_window)
  return (
    <div className="panel span-12" id="backtests-totals">
      <div className="flex flex-wrap gap-8">
        <Stat label="Total results">{num(totals.results, 0)}</Stat>
        <Stat label="Candidates">{num(totals.candidates, 0)}</Stat>
        <Stat label="Families">{num(totals.families, 0)}</Stat>
        <Stat label="Passes by window">
          {passes.length === 0 ? <Missing /> : passes.map(([w, n]) => `${w} ${n}`).join(' · ')}
        </Stat>
      </div>
    </div>
  )
}

export function Backtests() {
  const query = useBacktests()
  if (query.isPending) return <p className="text-ink3" role="status">Loading the research record…</p>
  if (!query.data) {
    return <div role="alert" className="panel">Backtests couldn&rsquo;t load: {query.error.message}</div>
  }
  const view = query.data
  return (
    <>
      <header className="mb-5">
        <div className="label">Research</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Backtests</h1>
        <p className="text-ink2 mt-1.5">What has been tested, and what passed.</p>
      </header>
      {view.totals.results === 0 ? (
        <div className="panel text-ink2">
          No backtests yet. They come from a feed that reports the research record: what was tried, in which window,
          and whether it passed.
        </div>
      ) : (
        <div className="grid12">
          <TotalsRow totals={view.totals} />
          <FamiliesPanel families={view.families} windows={view.windows} />
          <ResultsPanel rows={view.rows} />
        </div>
      )}
    </>
  )
}
