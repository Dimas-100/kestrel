// A caveat beside the figure it qualifies (spec 2026-10-08 reserves estimates §2): a raised note with the alert icon
// in the warn colour and a hidden "Warning:" when the figure may mislead (an old balance, a part of the debt without a
// rate), or the info icon in muted ink when it only says what a figure leaves out. The icon's shape and the words
// carry the meaning, never the colour alone.
import type { ReactNode } from 'react'
import { Icon } from '../../components/Icon'

export function Caveat({ warn = false, children }: { warn?: boolean; children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 text-xs text-ink2 mt-3 rounded-[7px] px-2.5 py-2"
      style={{ background: 'var(--panel2)', boxShadow: `inset 0 0 0 1px ${warn ? 'var(--warn)' : 'var(--line)'}` }}>
      <Icon name={warn ? 'alert' : 'info'} size={14} style={{ color: warn ? 'var(--warn)' : 'var(--ink3)', marginTop: 1 }} />
      <p className="prose min-w-0">{warn && <span className="sr-only">Warning: </span>}{children}</p>
    </div>
  )
}
