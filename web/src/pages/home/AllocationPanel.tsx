import { Link } from '@tanstack/react-router'
import { CATEGORY_COLOR, CATEGORY_WORD, Delta, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { AccountRow, Slice } from '../../lib/api'
import { money, pct } from '../../lib/format'

/** An account's figure for the list: what a debt account owes says so in words (the category word beside it is
 *  hidden on a phone), and a card paid past zero is a credit balance, never a bare figure that reads as held. */
export function rowValue(a: Pick<AccountRow, 'category' | 'value'>): string {
  if (a.category !== 'debt') return money(a.value)
  return a.value < 0 ? `${money(-a.value)} credit balance` : `${money(a.value)} owed`
}

/** 100 cells, filled column by column, so the waffle reads like one proportional bar. */
export function Waffle({ slices }: { slices: Slice[] }) {
  const cells = slices.flatMap((s) => Array.from({ length: s.cells }, () => s.category))
  return (
    <div role="img" aria-label={slices.map((s) => `${s.label} ${s.share.toFixed(1)} percent`).join(', ')}
      style={{ display: 'grid', gridTemplateColumns: 'repeat(20, minmax(0, 1fr))',
        gridTemplateRows: 'repeat(5, auto)', gridAutoFlow: 'column', gap: 4 }}>
      {cells.map((category, i) => (
        <span key={i} style={{ aspectRatio: '1', borderRadius: 2, background: CATEGORY_COLOR[category] }} />
      ))}
    </div>
  )
}

export function AllocationPanel({ slices, accounts, owed, debtAccounts }: {
  slices: Slice[]; accounts: AccountRow[]; owed: number; debtAccounts: number
}) {
  return (
    <Panel id="allocation" title="Where it sits" span={4} height={372}
      actions={<Link to="/accounts" className="text-xs inline-flex items-center gap-1">
        {accounts.length} accounts<Icon name="chevron" size={13} />
      </Link>}>
      <div className="mt-4"><Waffle slices={slices} /></div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-3">
        {slices.map((s) => (
          <span key={s.category} className="inline-flex items-center gap-1.5 text-[11.5px] text-ink2 whitespace-nowrap">
            <span className="mark real" style={{ '--mc': CATEGORY_COLOR[s.category], width: 10, height: 10 } as React.CSSProperties} />
            {s.label} <span className="num text-ink1">{s.share.toFixed(1)}%</span>
          </span>
        ))}
      </div>
      <div className="mt-3.5 overflow-y-auto">
        {accounts.map((a) => (
          // each row opens the account; the text keeps its own ink, not the link colour
          <Link key={a.id} to="/accounts/$accountId" params={{ accountId: a.id }}
            className="flex items-center gap-2.5 h-[42px] border-t border-line">
            <span className="w-2 h-2 rounded-full flex-none" style={{ background: CATEGORY_COLOR[a.category] }} />
            {/* flex-1 min-w-0: the name is what identifies the row, so it claims space first and truncates last
                (screenshot pass, 2026-09-28) -- at 1200px, without this, the fixed-width category word and value
                left it almost no room at all */}
            <span className="text-[13px] font-medium truncate text-ink1 flex-1 min-w-0">{a.name}</span>
            <span className="text-[11px] text-ink3 hidden sm:inline flex-none">{CATEGORY_WORD[a.category]}</span>
            <div className="ml-auto text-right">
              <div className="num text-[13px] text-ink1">{rowValue(a)}</div>
              <div className="text-[11px]">
                {a.day_pct == null ? <span className="text-ink3">—</span> : <Delta value={a.day_pct}>{pct(a.day_pct, 2)}</Delta>}
              </div>
            </div>
          </Link>
        ))}
      </div>
      {owed > 0 && (
        <Link to="/reserves" className="mt-auto pt-2.5 text-xs" style={{ color: 'var(--acc-ink)' }}>
          Owed: <span className="num">{money(owed)}</span> across {debtAccounts} account{debtAccounts === 1 ? '' : 's'}
        </Link>
      )}
    </Panel>
  )
}
