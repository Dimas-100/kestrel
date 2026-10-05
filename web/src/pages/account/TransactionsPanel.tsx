// What moved through the account, as its bank posted it: newest first, with the totals in and out, a Show filter
// and a search. Only for an account whose source sends rows; a brokerage account shows nothing here.
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { Missing, Panel, Seg } from '../../components/bits'
import type { AccountView, TransactionRow } from '../../lib/api'
import { money, signedMoney } from '../../lib/format'
import { flowDay } from './AccountGrowth'

const SHOW = ['All', 'In', 'Out'] as const
type Show = (typeof SHOW)[number]
const STICKY: CSSProperties = { position: 'sticky', top: 0, background: 'var(--panel)' }

export function matchesShow(t: TransactionRow, show: Show): boolean {
  return show === 'All' || (show === 'In' ? t.amount > 0 : t.amount < 0)
}

/** Case-insensitive, against the description, the counterparty and the category; an empty query matches all. */
export function matchesQuery(t: TransactionRow, query: string): boolean {
  const q = query.trim().toLowerCase()
  return !q || [t.description, t.counterparty, t.category].some((s) => s.toLowerCase().includes(q))
}

/** The counterparty is worth a second line only when the description doesn't already say it. */
export function showsCounterparty(t: TransactionRow): boolean {
  return t.counterparty !== '' && !t.description.toLowerCase().includes(t.counterparty.toLowerCase())
}

export function TransactionsPanel({ v, year }: { v: AccountView; year: string }) {
  const [show, setShow] = useState<Show>('All')
  const [query, setQuery] = useState('')
  const t = v.transactions
  if (!t) return null
  const shown = t.rows.filter((r) => matchesShow(r, show) && matchesQuery(r, query))
  return (
    <Panel id="transactions" title="Transactions" span={12}
      subtitle={`${t.count} since ${flowDay(t.since, year)} · in ${money(t.money_in)} · out ${money(t.money_out)}`}
      actions={(
        <>
          <Seg label="Show" options={SHOW} value={show} onChange={setShow} />
          <input type="search" className="search" placeholder="Search transactions" value={query}
            onChange={(e) => setQuery(e.target.value)} aria-label="Search transactions" />
        </>
      )}>
      {shown.length === 0 ? <Empty>No transactions match.</Empty> : (
        <div className="table-scroll overflow-y-auto mt-3.5" style={{ maxHeight: 520 }}>
          <table className="tbl" style={{ minWidth: 640, '--row': '44px' } as CSSProperties}>
            <thead>
              <tr>
                <th style={STICKY}>Date</th><th style={STICKY}>Description</th><th style={STICKY}>Category</th>
                <th className="r" style={STICKY}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r, i) => (
                <tr key={`${r.date}-${i}`}>
                  <td className="num text-xs text-ink3 whitespace-nowrap">{flowDay(r.date, year)}</td>
                  <td>
                    <div className="text-ink1">{r.description}</div>
                    {showsCounterparty(r) && <div className="text-xs text-ink3">{r.counterparty}</div>}
                  </td>
                  <td>
                    {r.category ? <span className="chip" style={{ padding: '2px 8px' }}>{r.category}</span> : <Missing />}
                  </td>
                  <td className="r num whitespace-nowrap">{signedMoney(r.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
