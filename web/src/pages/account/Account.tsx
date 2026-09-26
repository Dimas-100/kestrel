// One account: its value over time against what went in, how it grew, and what it holds.
import { useState } from 'react'
import { CategoryChip } from '../../components/bits'
import { HttpError, useAccount, useShell, type Window } from '../../lib/api'
import { kindText } from '../accounts/Accounts'
import { Soon } from '../Soon'
import { AccountGrowthPanel, flowDay } from './AccountGrowth'
import { HoldingsPanel } from './HoldingsPanel'
import { ValuePanel } from './ValuePanel'

export function Account({ id }: { id: string }) {
  const account = useAccount(id)
  const shell = useShell()
  const [period, setPeriod] = useState<Window>('1y') // the Value panel's window, which the Growth panel follows
  if (account.isPending) return <p className="text-ink3" role="status">Loading the account…</p>
  if (!account.data) {
    if (account.error instanceof HttpError && account.error.status === 404) {
      return <Soon title="Not found" text="There is no page here. Pick one from the menu." />
    }
    return <div role="alert" className="panel">This account couldn&rsquo;t load: {account.error.message}</div>
  }
  const v = account.data
  const year = String(new Date(shell.data?.now ?? Date.now()).getUTCFullYear()) // this year: its dates need no year
  return (
    <>
      <header className="mb-5">
        <div className="label">Account</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">{v.name}</h1>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mt-2">
          {kindText(v) && <span className="text-ink2">{kindText(v)}</span>}
          <CategoryChip category={v.category} />
          <span className="text-xs text-ink3">as of {flowDay(v.as_of, year)}</span>
        </div>
      </header>
      <div className="grid12">
        <ValuePanel v={v} period={period} onPeriod={setPeriod} />
        <AccountGrowthPanel v={v} period={period} />
        <HoldingsPanel v={v} year={year} />
      </div>
    </>
  )
}
