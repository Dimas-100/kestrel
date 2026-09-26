// @vitest-environment node
// Design-system rules that code review keeps missing, pinned as tests (docs/design-system.md).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const SRC = fileURLToPath(new URL('..', import.meta.url))
const css = () => readFileSync(join(SRC, 'styles', 'tokens.css'), 'utf8')

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? files(path) : [path]
  })
}

describe('design rules', () => {
  it('components use tokens, never raw hex colours', () => {
    const offenders = files(SRC)
      .filter((f) => /\.tsx?$/.test(f) && !f.endsWith('.test.ts') && !f.endsWith('.test.tsx'))
      .filter((f) => /#[0-9a-fA-F]{3,8}\b/.test(readFileSync(f, 'utf8')))
    expect(offenders).toEqual([])
  })

  it('keeps screen-reader labels inside scrolling tables (no sideways page scroll on phones)', () => {
    expect(css()).toMatch(/\.table-scroll \{ position: relative;/)
    expect(css()).toMatch(/\.panel \{ position: relative;/)
  })

  it('sets the type scale in px, so the 14 px root never shrinks it', () => {
    const sizes = Object.fromEntries([...css().matchAll(/--text-(\w+): (\d+)px;/g)].map((m) => [m[1], Number(m[2])]))
    expect(sizes).toEqual({
      '2xs': 11, xs: 12, sm: 13, base: 14, lg: 15, xl: 20, '2xl': 24, '3xl': 28, '4xl': 38, '5xl': 48,
    })
  })

  it('gives the expected mark its dotted outline and a faint ink wash', () => {
    expect(css()).toContain('.mark.expected { border: 1.5px dotted var(--mc, var(--ref));'
      + ' background: color-mix(in srgb, var(--ink1) 5%, transparent); }')
  })
})
