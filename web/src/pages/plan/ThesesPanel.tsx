// Why each holding is owned: grouped alert, watch, ok, not rated, with a health strip up top; each row has the
// health (an icon plus the word), the reasons, conviction, whether and where it is held with its value, and what
// would prove it wrong behind a disclosure.
import { Empty } from '../../charts/marks'
import { Panel, SymbolLogo } from '../../components/bits'
import { Icon, type IconName } from '../../components/Icon'
import type { Health, ThesisRow } from '../../lib/api'
import { money } from '../../lib/format'

const HEALTH: Record<Health, { icon: IconName; color: string; word: string; chip: string }> = {
  alert: { icon: 'shield', color: 'var(--serious)', word: 'Alert', chip: 'alert' },
  watch: { icon: 'clock', color: 'var(--warn)', word: 'Watch', chip: 'watch' },
  ok: { icon: 'checkCircle', color: 'var(--good)', word: 'OK', chip: 'ok' },
  none: { icon: 'circle', color: 'var(--ink3)', word: 'Not rated', chip: 'not rated' },
}
const ORDER: Health[] = ['alert', 'watch', 'ok', 'none']

/** Alert first, then watch, ok and not rated; within a health, the order the view gave. */
export function sortByHealth(theses: ThesisRow[]): ThesisRow[] {
  return [...theses].sort((a, b) => ORDER.indexOf(a.health) - ORDER.indexOf(b.health))
}

export function healthStrip(theses: ThesisRow[]): string {
  return ORDER.map((h) => [h, theses.filter((t) => t.health === h).length] as const)
    .filter(([, n]) => n > 0)
    .map(([h, n]) => `${n} ${HEALTH[h].chip}`)
    .join(' · ')
}

export function ThesesPanel({ theses }: { theses: ThesisRow[] }) {
  return (
    <Panel id="theses" title="Theses" subtitle={theses.length > 0 ? 'Why each holding is owned' : undefined} span={12}
      actions={theses.length > 0 && <span className="chip">{healthStrip(theses)}</span>}>
      {theses.length === 0 ? (
        <Empty>No theses yet. An investing feed sends why each holding is owned.</Empty>
      ) : (
        <ul className="mt-2">
          {sortByHealth(theses).map((t) => {
            const look = HEALTH[t.health]
            return (
              <li key={t.symbol} className="flex gap-3 py-3 border-t border-line">
                <span className="w-8 h-8 flex-none rounded-lg bg-panel2 border border-line flex items-center justify-center"
                  style={{ color: look.color }}>
                  <Icon name={look.icon} size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="inline-flex items-center gap-2">
                      <SymbolLogo symbol={t.symbol} size={18} /><span className="num font-semibold">{t.symbol}</span>
                    </span>
                    {t.name && <span className="text-xs text-ink3 truncate">{t.name}</span>}
                    <span className="text-xs ml-auto whitespace-nowrap" style={{ color: look.color }}>{look.word}</span>
                  </div>
                  {t.reasons.length > 0 && (
                    <ul className="text-xs text-ink2 mt-1 pl-4" style={{ listStyle: 'disc' }}>
                      {t.reasons.map((r) => <li key={r}>{r}</li>)}
                    </ul>
                  )}
                  <div className="text-xs text-ink3 mt-1">
                    {t.conviction && <>{t.conviction} conviction · </>}
                    {t.held
                      ? <>held in {t.account_names.join(', ') || 'an account'}{t.held_value > 0 && <> · <span className="num">{money(t.held_value, false)}</span></>}</>
                      : 'not held'}
                    {t.days_since_review != null && <> · reviewed {t.days_since_review}d ago</>}
                  </div>
                  {t.wrong_if.length > 0 && (
                    <details className="mt-1.5">
                      <summary className="text-xs cursor-pointer inline-block" style={{ color: 'var(--acc-ink)' }}>
                        Wrong if…
                      </summary>
                      <ul className="text-xs text-ink2 mt-1 pl-4" style={{ listStyle: 'disc' }}>
                        {t.wrong_if.map((w) => <li key={w}>{w}</li>)}
                      </ul>
                    </details>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}
