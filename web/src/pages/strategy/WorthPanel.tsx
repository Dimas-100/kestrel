import { useState } from 'react'
import { Scatter, type ScatterPoint, ScatterTable } from '../../charts/Scatter'
import { Panel, Seg } from '../../components/bits'
import type { StrategyView, WorthPoint } from '../../lib/api'
import { pct } from '../../lib/format'

const VIEWS = ['Chart', 'Table'] as const

/** Real is solid, paper hatched, and the backtest and the benchmark dotted; long-term money is slate. */
function look(p: WorthPoint, book: StrategyView['book']): Pick<ScatterPoint, 'color' | 'style'> {
  if (p.key === 'backtest') return { color: 'var(--s2)', style: 'dotted' }
  if (p.key === 'book') return { color: 'var(--s2)', style: book === 'paper' ? 'hatched' : 'solid' }
  if (p.key === 'long_term') return { color: 'var(--s1)', style: 'solid' }
  return { color: 'var(--ref)', style: 'dotted' }
}

export function WorthPanel({ v }: { v: StrategyView }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const points: ScatterPoint[] = v.worth.points.map((p) => ({
    key: p.key, label: p.label, period: p.period, x: p.drop_pct, y: p.return_pct, ...look(p, v.book),
    sub: `${pct(p.return_pct, 1)}/yr · ${p.period}${p.early ? ' · early' : ''}`,
  }))
  return (
    <Panel id="worth" title="Is it worth it?" subtitle="Yearly return against the worst drop along the way" span={7}
      height={380} actions={points.length > 0 && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      <div className="mt-auto pt-3">
        {view === 'Chart' || points.length === 0
          ? <Scatter points={points} ariaLabel="Yearly return against worst drop" />
          : <ScatterTable points={points} />}
      </div>
    </Panel>
  )
}
