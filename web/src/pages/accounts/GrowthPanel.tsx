// How the money grew over a window: what it started at, what you put in, and what the market added.
import { type ReactNode, useState } from 'react'
import { GrowthBar, GrowthTable, PART_LABEL } from '../../charts/GrowthBar'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Missing, NoHistoryNote, Panel, Seg, Stat } from '../../components/bits'
import type { Growth, Window } from '../../lib/api'
import { money, signedMoney, sinceLabel } from '../../lib/format'

export const WINDOWS: readonly Window[] = ['ytd', '1y', 'all']
export const WINDOW_WORD: Record<Window, string> = { ytd: 'This year', '1y': '1 year', all: 'All' }
const WORDS = WINDOWS.map((w) => WINDOW_WORD[w])
const VIEWS = ['Chart', 'Table'] as const

/** This year · 1 year · All */
export function WindowSeg({ value, onChange }: { value: Window; onChange: (window: Window) => void }) {
  return (
    <Seg label="Window" options={WORDS} value={WINDOW_WORD[value]}
      onChange={(word) => onChange(WINDOWS.find((w) => WINDOW_WORD[w] === word) ?? value)} />
  )
}

function Tile({ label, sub, children }: { label: string; sub?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-line px-3 py-2.5 min-w-0 [overflow-wrap:anywhere]">
      <Stat label={label} sub={sub}>{children}</Stat>
    </div>
  )
}

/** The four figures. A window with fewer than two days of history has no growth: dashes. */
export function GrowthTiles({ g, asOf, className = 'grid-cols-2' }: { g: Growth | null; asOf: string; className?: string }) {
  const figure = (text: string) => <span className="num text-lg">{text}</span>
  return (
    <div className={`grid gap-3 ${className}`}>
      <Tile label={PART_LABEL.start} sub={g ? sinceLabel(g.start_date, asOf) : undefined}>
        {g ? figure(money(g.start)) : <Missing />}
      </Tile>
      <Tile label={PART_LABEL.deposits}>{g ? figure(money(g.deposits)) : <Missing />}</Tile>
      <Tile label={PART_LABEL.market}>
        {g ? <span className="text-lg"><Delta value={g.market}>{signedMoney(g.market)}</Delta></span> : <Missing />}
      </Tile>
      <Tile label="Now">{g ? figure(money(g.end)) : <Missing />}</Tile>
    </div>
  )
}

/** Every account together: the four figures for the window, then the same split as one bar. `noHistory` accounts
 *  have no history of their own and are in every figure at today's balance. */
export function GrowthPanel({ growth, asOf, noHistory = 0 }: {
  growth: Record<Window, Growth | null>; asOf: string; noHistory?: number
}) {
  const [period, setPeriod] = useState<Window>('ytd')
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const g = growth[period]
  return (
    <Panel id="growth" title="Growth" subtitle="How much of the change was what you put in, and how much the market"
      span={12} actions={<>
        <WindowSeg value={period} onChange={setPeriod} />
        {g && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}
      </>}>
      <div className="mt-4"><GrowthTiles g={g} asOf={asOf} className="grid-cols-2 lg:grid-cols-4" /></div>
      {g == null ? (
        <Empty>Not enough history for this window yet.</Empty>
      ) : view === 'Chart' ? (
        <div className="mt-5">
          <GrowthBar growth={g} ariaLabel={`${WINDOW_WORD[period]}: started at, you put in, the market added`} />
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 text-xs text-ink2">
            <span className="inline-flex items-center gap-1.5"><BookMark kind="real" color="var(--s3)" />{PART_LABEL.start}</span>
            <span className="inline-flex items-center gap-1.5"><BookMark kind="expected" />{PART_LABEL.deposits}</span>
            <span className="inline-flex items-center gap-1.5">
              <BookMark kind="real" color={g.market >= 0 ? 'var(--up)' : 'var(--down)'} />{PART_LABEL.market}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className="inline-block w-0.5 h-3 bg-ink1" />Now
            </span>
          </div>
        </div>
      ) : (
        <div className="mt-4"><GrowthTable growth={g} /></div>
      )}
      {g != null && <NoHistoryNote count={noHistory} />}
    </Panel>
  )
}
