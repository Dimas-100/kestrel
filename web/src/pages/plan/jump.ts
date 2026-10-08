// A priority's link to the place on the page that backs it (spec 2026-10-08 plan §4): the element named by its
// anchor, or the panel it lives in when that view isn't showing (a panel switched to its table), opened if it sits
// inside a closed disclosure, scrolled to and focused.
import type { PlanAction } from '../../lib/api'

const PANEL: Record<PlanAction['kind'], string> = {
  target: 'allocation-title', goal: 'milestones-title', thesis: 'theses-title',
}

export function jumpTarget(anchor: string, kind: PlanAction['kind']): HTMLElement | null {
  return document.getElementById(anchor) ?? document.getElementById(PANEL[kind])
}

export function jumpTo(anchor: string, kind: PlanAction['kind']): void {
  const el = jumpTarget(anchor, kind)
  if (!el) return
  for (let p = el.parentElement; p; p = p.parentElement) {
    if (p instanceof HTMLDetailsElement && !p.open) p.open = true
  }
  if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1')
  const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  el.scrollIntoView?.({ block: 'center', behavior: still ? 'auto' : 'smooth' })
  el.focus({ preventScroll: true })
}
