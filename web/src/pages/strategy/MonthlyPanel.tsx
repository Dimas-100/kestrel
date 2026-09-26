import { useState } from 'react'
import { MonthGrid, MonthTable } from '../../charts/MonthGrid'
import { Delta, Missing, Panel, Seg } from '../../components/bits'
import type { StrategyView } from '../../lib/api'
import { monthLabel, pct } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'

const VIEWS = ['Chart', 'Table'] as const

function Figure({ label, figure }: { label: string; figure: { month: string; value: number } | null }) {
  return (
    <div className="flex justify-between">
      <span className="text-ink2">{label}{figure && ` · ${monthLabel(`${figure.month}-01`)}`}</span>
      {figure ? <Delta value={figure.value} digits={1}>{pct(figure.value, 1)}</Delta> : <Missing />}
    </div>
  )
}

export function MonthlyPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const m = v.monthly
  const money = v.book ?? 'real'
  const word = MONEY_WORD[money]
  return (
    <Panel id="monthly" title="Month by month" subtitle={`${word} book against your long-term accounts`} span={5}
      height={380} actions={<Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      <div className="mt-4">
        {view === 'Chart'
          ? <MonthGrid months={m.months} bookLabel={word} money={money} ariaLabel="Monthly returns, book against long-term" />
          : <MonthTable months={m.months} bookLabel={word} />}
      </div>
      <div className="mt-auto border-t border-line pt-3.5 flex flex-col gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-ink2">Months ahead of long-term</span>
          <span className="num">{m.compared ? `${m.ahead} of ${m.compared}` : '—'}</span>
        </div>
        <Figure label="Best month" figure={m.best} />
        <Figure label="Worst month" figure={m.worst} />
      </div>
    </Panel>
  )
}
