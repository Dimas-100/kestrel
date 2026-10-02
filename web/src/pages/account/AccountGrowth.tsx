import { Panel } from '../../components/bits'
import type { AccountView, Window } from '../../lib/api'
import { money, monthLabel, shortDate } from '../../lib/format'
import { GrowthTiles, WINDOW_WORD } from '../accounts/GrowthPanel'

/** "Tue 1 Sep" this year, "1 Sep 2025" before it */
export function flowDay(iso: string, year: string): string {
  return iso.slice(0, 4) === year ? shortDate(iso) : `${monthLabel(iso, true)} ${iso.slice(0, 4)}`
}

const UNPOSTED =
  "The balance moved, but the account's records don't show why yet. Most often it's a deposit the broker hasn't " +
  'posted. It counts as money moved, not growth, and this note goes once the records catch up.'

/** The window's four figures, then the last eight times money moved in or out. */
export function AccountGrowthPanel({ v, period }: { v: AccountView; period: Window }) {
  const year = v.as_of.slice(0, 4)
  return (
    <Panel id="growth" title="Growth" subtitle={WINDOW_WORD[period]} span={4} height={372}>
      <div className="mt-3.5"><GrowthTiles g={v.growth[period]} asOf={v.as_of} /></div>
      <div className="label mt-4">Money in and out</div>
      {v.flows.length === 0 ? (
        <p className="text-xs text-ink3 mt-2">No money has moved in or out yet.</p>
      ) : (
        <ul className="mt-1">
          {v.flows.map((f, i) => (
            <li key={`${f.date}-${i}`} className="flex items-center gap-3 h-7 text-[13px]">
              <span className="num text-xs text-ink2 min-w-[92px]">{flowDay(f.date, year)}</span>
              <span className="text-xs text-ink2">
                <span aria-hidden="true">{f.amount > 0 ? '▲' : '▼'} </span>{f.amount > 0 ? 'in' : 'out'}
                {f.unexplained ? (
                  <>
                    {' · '}
                    <span className="text-ink3" title={UNPOSTED}>not posted yet</span>
                  </>
                ) : null}
              </span>
              <span className="num ml-auto">{money(Math.abs(f.amount))}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}
