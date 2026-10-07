import { type ReactNode, useState } from 'react'
import { Empty } from '../../charts/marks'
import { SlotsStrip, SlotsTable } from '../../charts/SlotsStrip'
import { Panel, Seg } from '../../components/bits'
import type { StrategyView } from '../../lib/api'
import { money, num } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'

const VIEWS = ['Chart', 'Table'] as const

function Tile({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-line px-3 py-2.5 min-w-0">
      <div className="label">{label}</div>
      <div className="num text-lg mt-1">{children}</div>
    </div>
  )
}

/** Slots in use over the last sessions, the money that is actually deployed (not the same thing), and the names
 *  close to a signal. */
export function SlotsPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const s = v.slots
  const money_ = v.book ?? 'real'
  const reported = s.total != null && s.days.length > 0
  return (
    <Panel id="slots" title="Where the money works" span={5} height={452}
      subtitle={reported ? `${MONEY_WORD[money_]} book · slots in use, last ${s.days.length} sessions · ${s.total} slots`
        : undefined}
      actions={reported && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      {s.book_id == null ? (
        <Empty>No book trades this strategy yet.</Empty>
      ) : !reported || s.total == null ? (
        <Empty>This book doesn&rsquo;t report slots.</Empty>
      ) : (
        <>
          <div className="mt-4">
            {view === 'Chart'
              ? <SlotsStrip days={s.days} used={s.used} total={s.total} money={money_} ariaLabel="Slots in use each session" />
              : <SlotsTable days={s.days} used={s.used} total={s.total} />}
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3.5">
            <Tile label="Slots in use">
              {s.avg_used == null ? '—' : num(s.avg_used, 1)} <span className="text-xs text-ink3">of {s.total} on average · {s.working_pct == null ? '—' : `${Math.round(s.working_pct)}%`}</span>
            </Tile>
            <Tile label="Money deployed">
              {s.deployed == null ? '—' : money(s.deployed, false)}
              <span className="text-xs text-ink3">
                {s.deployed_pct != null && s.capital != null ? ` · ${Math.round(s.deployed_pct)}% of ${money(s.capital, false)}` : ' · capital not reported'}
              </span>
            </Tile>
            <Tile label="Idle sessions">
              {s.idle} <span className="text-xs text-ink3">of {s.days.length}</span>
            </Tile>
          </div>
          {s.note && <p className="text-xs text-ink3 mt-2.5">{s.note}</p>}
        </>
      )}
      {s.watch.length > 0 && (
        <div className="mt-auto border-t border-line pt-3">
          <div className="label">Close to a signal</div>
          <div className="flex flex-wrap gap-2 mt-2">
            {s.watch.map((w, i) => (
              <span key={`${w.symbol}-${i}`} className="chip max-w-full">
                <span className="num font-semibold text-ink1">{w.symbol}</span>
                <span className="num">{w.label} {w.value == null ? '—' : num(w.value, 1)}</span>
                {w.note && <span className="text-ink3 min-w-0" style={{ whiteSpace: 'normal' }}>{w.note}</span>}
              </span>
            ))}
          </div>
        </div>
      )}
    </Panel>
  )
}
