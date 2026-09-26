import { Link } from '@tanstack/react-router'
import { Delta, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { AccountRow, Slice } from '../../lib/api'
import { money, pct } from '../../lib/format'

const COLOR: Record<string, string> = {
  long_term: 'var(--s1)', trading: 'var(--s2)', cash: 'var(--s3)', other: 'var(--ink3)',
}
const KIND: Record<string, string> = { long_term: 'Long-term', trading: 'Trading', cash: 'Cash', other: 'Other' }

/** 100 cells, filled column by column, so the waffle reads like one proportional bar. */
export function Waffle({ slices }: { slices: Slice[] }) {
  const cells = slices.flatMap((s) => Array.from({ length: s.cells }, () => s.category))
  return (
    <div role="img" aria-label={slices.map((s) => `${s.label} ${s.share.toFixed(1)} percent`).join(', ')}
      style={{ display: 'grid', gridTemplateColumns: 'repeat(20, minmax(0, 1fr))',
        gridTemplateRows: 'repeat(5, auto)', gridAutoFlow: 'column', gap: 4 }}>
      {cells.map((category, i) => (
        <span key={i} style={{ aspectRatio: '1', borderRadius: 2, background: COLOR[category] }} />
      ))}
    </div>
  )
}

export function AllocationPanel({ slices, accounts }: { slices: Slice[]; accounts: AccountRow[] }) {
  return (
    <Panel id="allocation" title="Where it sits" span={4} height={372}
      actions={<Link to="/accounts" className="text-xs inline-flex items-center gap-1">
        {accounts.length} accounts<Icon name="chevron" size={13} />
      </Link>}>
      <div className="mt-4"><Waffle slices={slices} /></div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-3">
        {slices.map((s) => (
          <span key={s.category} className="inline-flex items-center gap-1.5 text-[11.5px] text-ink2 whitespace-nowrap">
            <span className="mark real" style={{ '--mc': COLOR[s.category], width: 10, height: 10 } as React.CSSProperties} />
            {s.label} <span className="num text-ink1">{s.share.toFixed(1)}%</span>
          </span>
        ))}
      </div>
      <div className="mt-3.5 overflow-y-auto">
        {accounts.map((a) => (
          <div key={a.id} className="flex items-center gap-2.5 h-[42px] border-t border-line">
            <span className="w-2 h-2 rounded-full flex-none" style={{ background: COLOR[a.category] }} />
            <span className="text-[13px] font-medium truncate">{a.name}</span>
            <span className="text-[11px] text-ink3 hidden sm:inline">{KIND[a.category]}</span>
            <div className="ml-auto text-right">
              <div className="num text-[13px]">{money(a.value)}</div>
              <div className="text-[11px]">
                {a.day_pct == null ? <span className="text-ink3">—</span> : <Delta value={a.day_pct}>{pct(a.day_pct, 2)}</Delta>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}
