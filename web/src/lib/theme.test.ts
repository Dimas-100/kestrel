import { afterEach, describe, expect, it, vi } from 'vitest'
import { readOverride, resolveTheme } from './theme'

describe('theme', () => {
  afterEach(() => vi.restoreAllMocks())

  it('resolves system against the OS setting', () => {
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
    expect(resolveTheme('light', true)).toBe('light')
  })

  it('ignores junk and survives blocked storage', () => {
    window.localStorage.setItem('kestrel.theme', 'neon')
    expect(readOverride()).toBeNull()
    window.localStorage.setItem('kestrel.theme', 'light')
    expect(readOverride()).toBe('light')
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(readOverride()).toBeNull()
  })
})
