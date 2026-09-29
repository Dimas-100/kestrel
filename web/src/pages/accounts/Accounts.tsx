// Every account: what each holds, and how much of the growth was your deposits vs the market.
import { Link } from '@tanstack/react-router'
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { CategoryChip, Delta, InstitutionTile, Missing, Panel, SymbolLogo } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type AccountLine, type AccountsView, type CombinedHolding, useAccounts } from '../../lib/api'
import { money, num, pct, signedMoney } from '../../lib/format'
import { GrowthPanel } from './GrowthPanel'

const SHOWN = 12

/** The sentence under the title, from the data: how many accounts, how much, and this year in two figures. */
export function headline(v: AccountsView): { lead: string; moved: string | null } {
  const lead = `${v.count} account${v.count === 1 ? '' : 's'}, ${money(v.total)} in all.`
  const year = v.growth.ytd
  if (!year) return { lead, moved: null }
  const moved = year.deposits >= 0 ? `you deposited ${money(year.deposits)}` : `you withdrew ${money(-year.deposits)}`
  return { lead, moved }
}

/** "Brokerage A · Roth IRA", leaving out whichever is unknown */
export function kindText(a: { institution: string; account_type: string }): string {
  return [a.institution, a.account_type].filter(Boolean).join(' · ')
}

/** A share of a whole, in percent: no sign, since it is not a change. */
const shareCell = (value: number | null) => (value == null ? <Missing /> : `${num(value, 1)}%`)

function AccountsPanel({ accounts }: { accounts: AccountLine[] }) {
  return (
    <Panel id="accounts" title="Accounts" subtitle="Largest first · open one to see what it holds" span={12}>
      <div className="table-scroll mt-3.5">
        <table className="tbl" style={{ minWidth: 820 }}>
          <thead>
            <tr>
              <th>Account</th><th>Category</th><th className="r">Value</th><th className="r">Share</th>
              <th className="r">Last day</th><th className="r">Market this year</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              // an empty account stays listed (it is still open) but steps back so the ones holding money lead
              <tr key={a.id} style={a.value === 0 ? { opacity: 0.7 } : undefined}>
                <td>
                  <div className="flex items-center gap-3">
                  <InstitutionTile institution={a.institution} category={a.category} size={32} />
                  <div className="min-w-0">
                  <Link to="/accounts/$accountId" params={{ accountId: a.id }}
                    className="inline-flex items-center gap-1 font-medium">
                    <span className="text-ink1">{a.name}</span><Icon name="chevron" size={13} />
                  </Link>
                  {kindText(a) && <div className="text-xs text-ink3 mt-0.5">{kindText(a)}</div>}
                  </div>
                  </div>
                </td>
                <td><CategoryChip category={a.category} /></td>
                <td className="r num">{money(a.value)}</td>
                <td className="r num">{shareCell(a.share)}</td>
                <td className="r">
                  {a.day_change == null ? <Missing /> : <Delta value={a.day_change}>{signedMoney(a.day_change)}</Delta>}
                  {a.day_pct != null && <div className="num text-[11px] text-ink3 mt-0.5">{pct(a.day_pct, 2)}</div>}
                </td>
                <td className="r">
                  {a.year_market == null ? <Missing /> : <Delta value={a.year_market}>{signedMoney(a.year_market)}</Delta>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

/** Every holding added up by symbol across accounts, with all the cash as one row; the first twelve, then the rest. */
function EverythingPanel({ rows }: { rows: CombinedHolding[] }) {
  const [all, setAll] = useState(false)
  const shown = all ? rows : rows.slice(0, SHOWN)
  return (
    <Panel id="everything" title="Everything you hold" subtitle="Across every account, largest first" span={12}>
      {rows.length === 0 ? (
        <Empty>Nothing held yet.</Empty>
      ) : (
        <>
          <div className="table-scroll mt-3.5">
            <table className="tbl" style={{ minWidth: 640, '--row': '48px' } as CSSProperties}>
              <thead>
                <tr>
                  <th>Symbol</th><th>Name</th><th className="r">Value</th><th className="r">Share</th>
                  <th style={{ paddingLeft: 16 }}>Held in</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r, i) => (
                  <tr key={`${r.symbol}-${i}`}>
                    <td>
                      {r.cash ? <span className="font-medium">Cash</span> : (
                        <span className="inline-flex items-center gap-2">
                          <SymbolLogo symbol={r.symbol} /><span className="num font-semibold">{r.symbol}</span>
                        </span>
                      )}
                    </td>
                    <td className="text-ink2">{r.cash || !r.name ? <Missing /> : r.name}</td>
                    <td className="r num">{money(r.value)}</td>
                    <td className="r num">{shareCell(r.share)}</td>
                    <td className="text-sm text-ink2" style={{ paddingLeft: 16 }}>{r.accounts.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length > SHOWN && (
            <button type="button" onClick={() => setAll(!all)} className="self-start mt-3 text-xs"
              style={{ color: 'var(--acc-ink)', background: 'none', border: 0, padding: 0, cursor: 'pointer' }}>
              {all ? `Show the first ${SHOWN}` : `Show all ${rows.length}`}
            </button>
          )}
        </>
      )}
    </Panel>
  )
}

export function Accounts() {
  const list = useAccounts()
  if (list.isPending) return <p className="text-ink3" role="status">Loading your accounts…</p>
  if (!list.data) {
    return <div role="alert" className="panel">Accounts couldn&rsquo;t load: {list.error.message}</div>
  }
  const v = list.data
  const { lead, moved } = headline(v)
  const year = v.growth.ytd
  return (
    <>
      <header className="mb-5">
        <div className="label">Money</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Accounts</h1>
        {v.count > 0 && (
          <p className="text-ink2 mt-1.5">
            {lead}
            {year && moved && (
              <> This year the market added <Delta value={year.market}>{signedMoney(year.market)}</Delta> and {moved}.</>
            )}
          </p>
        )}
      </header>
      {v.count === 0 ? (
        <div className="panel text-ink2">
          No accounts yet. Add a source in profile.toml, or run <code>kestrel check</code> if one isn&rsquo;t reading
          (see docs/connectors.md).
        </div>
      ) : (
        <div className="grid12">
          <GrowthPanel growth={v.growth} asOf={v.as_of} noHistory={v.no_history} />
          <AccountsPanel accounts={v.accounts} />
          <EverythingPanel rows={v.holdings} />
        </div>
      )}
    </>
  )
}
