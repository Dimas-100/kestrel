import { Empty } from '../../charts/marks'
import { Missing, Panel, Stat } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { BookView } from '../../lib/api'
import { money, pct } from '../../lib/format'
import { BandBar, VERDICT } from '../home/BooksPanel'

/** Trades, win rate, average trade/win/loss, total P/L, best and worst, and the expected band when the strategy
 *  has one — the same verdict Home and the Books list show for this book. */
export function ScorecardPanel({ v }: { v: BookView }) {
  const s = v.scorecard
  const band = s.band_lo != null && s.band_hi != null && s.avg_trade_pct != null
  return (
    <Panel id="scorecard" title="Scorecard" subtitle={`${s.trades} closed trade${s.trades === 1 ? '' : 's'}`} span={6}
      height={300}>
      {s.trades === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-4 mt-3.5">
            <Stat label="Win rate">{s.win_rate == null ? <Missing /> : pct(s.win_rate, 1)}</Stat>
            <Stat label="Avg trade">{s.avg_trade_pct == null ? <Missing /> : pct(s.avg_trade_pct, 2)}</Stat>
            <Stat label="Avg win">{s.avg_win_pct == null ? <Missing /> : pct(s.avg_win_pct, 2)}</Stat>
            <Stat label="Avg loss">{s.avg_loss_pct == null ? <Missing /> : pct(s.avg_loss_pct, 2)}</Stat>
            <Stat label="Total P/L">{money(s.total_pnl)}</Stat>
            <Stat label="Best trade">{s.best_pct == null ? <Missing /> : pct(s.best_pct, 2)}</Stat>
            <Stat label="Worst trade">{s.worst_pct == null ? <Missing /> : pct(s.worst_pct, 2)}</Stat>
          </div>
          {band && (
            <div className="mt-4">
              <div className="label">Per trade vs expected</div>
              <div className="flex items-center gap-3 mt-2">
                <BandBar lo={s.band_lo as number} hi={s.band_hi as number} actual={s.avg_trade_pct as number} />
                <span className="text-xs flex items-center gap-1.5"
                  style={{ color: s.verdict === 'below' ? 'var(--ink1)' : 'var(--ink2)' }}>
                  {s.verdict === 'below' && <Icon name="alert" size={12} style={{ color: 'var(--warn)' }} />}
                  {VERDICT[s.verdict]}
                  {s.verdict === 'early' && ` · ${s.trades} trades`}
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </Panel>
  )
}
