import { useEffect, useState } from 'react'

export type ThemePref = 'system' | 'dark' | 'light'
export type Theme = 'dark' | 'light'

const KEY = 'kestrel.theme' // a per-viewer convenience; the profile sets the default

export function resolveTheme(pref: ThemePref, prefersDark: boolean): Theme {
  if (pref === 'system') return prefersDark ? 'dark' : 'light'
  return pref
}

export function readOverride(): Theme | null {
  try {
    const value = window.localStorage.getItem(KEY)
    return value === 'dark' || value === 'light' ? value : null
  } catch {
    return null // private windows and blocked storage: fall back to the profile
  }
}

function saveOverride(theme: Theme): void {
  try {
    window.localStorage.setItem(KEY, theme)
  } catch {
    // not fatal: the toggle still works for this visit
  }
}

function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** The theme to render and a toggle. Order: the viewer's toggle, then the profile, then the system. */
export function useTheme(pref: ThemePref): [Theme, () => void] {
  const [prefersDark, setPrefersDark] = useState(systemPrefersDark)
  const [override, setOverride] = useState<Theme | null>(readOverride)
  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => setPrefersDark(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])
  const theme = override ?? resolveTheme(pref, prefersDark)
  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    saveOverride(next)
    setOverride(next)
  }
  return [theme, toggle]
}
