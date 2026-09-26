import { useState } from 'react'
import { CandleChart, CandleTable } from '../../charts/CandleChart'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Panel, Seg } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { RecentTrade, StrategyView } from '../../lib/api'
import { monthLabel, num, pct, shortDate } from '../../lib/format'

const VIEWS = ['Chart', 'Table'] as const

export const reasonWord = (reason: string) => (reason ? reason[0].toUpperCase() + reason.slice(1) : '—')

/** "6 sessions" · "1 session" · "Same day" */
export function sessionsText(n: number): string {
  if (n === 0) return 'Same day'
  return `${n} session${n === 1 ? '' : 's'}`
}

function AnatomyPanel({ v, selected }: { v: StrategyView; selected: string | null }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const trade = v.anatomy.recent.find((r) => r.key === selected)
  const chart = v.anatomy.charts.find((c) => c.key === selected)
  return (
    <Panel id="anatomy" title="Trade anatomy" span={8} height={452}
      subtitle={trade && `${trade.symbol} · ${trade.money} · bought ${shortDate(trade.opened)}, sold ${shortDate(trade.closed)}`
        + ` · ${trade.exit_reason || 'closed'}`}
      actions={trade && chart && <>
        <span className="chip"><Delta value={trade.return_pct}>{pct(trade.return_pct, 2)}</Delta></span>
        {trade.r_multiple != null && <span className="chip num text-ink1">{num(trade.r_multiple, 2)} R</span>}
        <span className="chip num text-ink1">{sessionsText(trade.sessions)}</span>
        <Seg label="View" options={VIEWS} value={view} onChange={setView} />
      </>}>
      {v.anatomy.recent.length === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : !trade || !chart ? (
        <Empty>No chart for these trades.</Empty>
      ) : (
        <div className="mt-auto pt-3">
          {view === 'Chart' ? (
            <CandleChart bars={chart.bars} indicator={chart.indicator} stop={chart.stop} entry={chart.entry}
              exit={chart.exit} entryPrice={chart.entry_price} exitPrice={chart.exit_price}
              height={chart.indicator ? 216 : 300}
              ariaLabel={`${trade.symbol} daily bars with the buy, the sell${chart.stop != null ? ' and the stop' : ''}`} />
          ) : (
            <CandleTable bars={chart.bars} indicator={chart.indicator} entry={chart.entry} exit={chart.exit} />
          )}
        </div>
      )}
    </Panel>
  )
}

function RecentRow({ r, selected, onSelect }: { r: RecentTrade; selected: boolean; onSelect: () => void }) {
  const inner = (
    <>
      <BookMark kind={r.money} color="var(--s2)" />
      <span className="num font-semibold w-12 flex-none text-left">{r.symbol}</span>
      <span className="num text-xs text-ink3 w-14 flex-none whitespace-nowrap text-left">{monthLabel(r.closed, true)}</span>
      <span className="chip" style={{ padding: '3px 8px', fontSize: 11 }}>
        {r.exit_reason === 'stop' && <Icon name="shield" size={12} style={{ color: 'var(--serious)' }} />}
        {reasonWord(r.exit_reason)}
      </span>
      {!r.chart && <span className="text-2xs text-ink3">no chart</span>}
      <span className="ml-auto text-sm"><Delta value={r.return_pct} digits={1}>{pct(r.return_pct, 1)}</Delta></span>
    </>
  )
  const look = 'flex w-full items-center gap-2.5 h-11 px-2.5 rounded-[7px] text-left'
  return r.chart ? (
    <button type="button" className={`${look} ease`} aria-pressed={selected} onClick={onSelect}
      aria-label={`${r.symbol}, closed ${shortDate(r.closed)}`}
      style={selected ? { background: 'var(--panel2)', boxShadow: 'inset 0 0 0 1px var(--line2)' } : undefined}>
      {inner}
    </button>
  ) : (
    <div className={look}>{inner}</div>
  )
}

/** The anatomy chart and the recent trades that pick what it shows. */
export function AnatomySection({ v }: { v: StrategyView }) {
  const [selected, setSelected] = useState(v.anatomy.selected)
  return (
    <>
      <AnatomyPanel v={v} selected={selected} />
      <Panel id="recent" title="Recent trades" span={4} height={452}
        actions={v.trades.length > 0 && (
          <a href="#trades-title" className="text-xs">All {v.trades.length}</a>
        )}>
        {v.anatomy.recent.length === 0 ? (
          <Empty>No closed trades yet.</Empty>
        ) : (
          <ul className="mt-2 -mx-2.5">
            {v.anatomy.recent.map((r) => (
              <li key={r.key}>
                <RecentRow r={r} selected={r.key === selected} onSelect={() => setSelected(r.key)} />
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  )
}
