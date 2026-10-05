// The Settings page: who you are and how the app looks, with the look shown as what it is; the benchmark and the
// versions; every source as a card. Read-only: everything comes from profile.toml (spec 2026-10-05 system pages §3).
import type { ReactNode } from 'react'
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { SourceCard } from '../../components/SourceCard'
import { type SettingsSource, type SettingsView, useSettings } from '../../lib/api'
import { ago, timeHM } from '../../lib/format'

/** "green-red" -> "Green / Red", "system" -> "System": a configured value, shown as words. */
export function readable(value: string): string {
  return value.split('-').map((word) => word[0].toUpperCase() + word.slice(1)).join(' / ')
}

/** A 12 px swatch in a token colour, named for screen readers. */
function Swatch({ color, name }: { color: string; name: string }) {
  return (
    <span role="img" aria-label={name} className="inline-block w-3 h-3 rounded-full align-[-1px] flex-none"
      style={{ background: color, boxShadow: 'inset 0 0 0 1px var(--line2)' }} />
  )
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 text-sm border-b border-line last:border-0">
      <dt className="text-ink3">{label}</dt>
      <dd className="text-ink1 text-right inline-flex items-center gap-2 justify-end">{children}</dd>
    </div>
  )
}

function ThemeIcon({ theme }: { theme: string }) {
  if (theme === 'light') return <Icon name="sun" size={14} />
  if (theme === 'dark') return <Icon name="moon" size={14} />
  return <span className="inline-flex gap-0.5"><Icon name="sun" size={14} /><Icon name="moon" size={14} /></span>
}

function YouPanel({ view }: { view: SettingsView }) {
  const { you, app } = view
  return (
    <Panel id="you" title="You" subtitle="Change any of this in profile.toml" span={7}>
      <h3 className="text-[28px] font-semibold tracking-[-0.025em] mt-3">{you.name}</h3>
      <dl className="mt-3">
        <Row label="Theme"><span className="text-ink2"><ThemeIcon theme={app.theme} /></span>{readable(app.theme)}</Row>
        <Row label="Accent">{readable(app.accent)}<Swatch color="var(--acc)" name={`the ${app.accent} accent`} /></Row>
        <Row label="Gain / loss">
          {readable(app.gain_loss)}
          <Swatch color="var(--up)" name="the gain colour" /><Swatch color="var(--down)" name="the loss colour" />
        </Row>
        <Row label="Density">{readable(app.density)}</Row>
        <Row label="Currency">{app.currency}</Row>
        <Row label="Time zone">
          <span>{app.timezone}<span className="text-ink3"> · <span className="num">{timeHM(view.as_of, app.timezone)}</span> there now</span></span>
        </Row>
      </dl>
    </Panel>
  )
}

function AboutPanel({ view }: { view: SettingsView }) {
  return (
    <Panel id="about" title="About" subtitle="The benchmark, the profile and the versions" span={5}>
      <dl className="mt-3">
        <Row label="Benchmark">{view.benchmark.symbol} · {view.benchmark.label}</Row>
        <Row label="Profile">{view.profile}</Row>
        <Row label="Contract"><span className="num">{view.contract_version}</span></Row>
        <Row label="kestrel"><span className="num">{view.version}</span></Row>
      </dl>
    </Panel>
  )
}

export function timingText(source: SettingsSource): string {
  const parts = [`stale after ${source.stale_after}`]
  if (source.refresh) parts.push(`reuses for ${source.refresh}`)
  if (source.timeout != null) parts.push(`times out at ${source.timeout}s`)
  return parts.join(' · ')
}

function SourcesPanel({ sources, now, tz }: { sources: SettingsSource[]; now: Date; tz: string }) {
  return (
    <Panel id="sources" title="Sources" subtitle={sources.length > 0 ? 'What each one reads, and its live status' : undefined} span={12}>
      {sources.length === 0 ? (
        <p className="text-ink2 mt-3">No sources configured yet. Add one to profile.toml (see docs/connectors.md).</p>
      ) : (
        <div className="grid gap-3 mt-3.5 grid-cols-1 md:grid-cols-3">
          {sources.map((s) => (
            <SourceCard key={s.id} label={s.label} kind={s.kind} status={s.status} lastSuccess={s.last_success} tz={tz}
              ageText={s.last_success ? ago(s.last_success, now) : null} timing={timingText(s)}
              reads={s.reads || null} tokenEnv={s.token_env} detail={s.detail} />
          ))}
        </div>
      )}
    </Panel>
  )
}

export function Settings() {
  const query = useSettings()
  if (query.isPending) return <p className="text-ink3" role="status">Loading settings…</p>
  if (!query.data) {
    return <div role="alert" className="panel">Settings couldn&rsquo;t load: {query.error.message}</div>
  }
  const view = query.data
  const now = new Date(view.as_of)
  return (
    <>
      <header className="mb-5">
        <div className="label">System</div>
        <h1 className="text-3xl font-semibold tracking-[-0.025em] mt-1.5">Settings</h1>
        <p className="text-ink2 mt-1.5">Read-only: everything here comes from {view.profile}.</p>
      </header>
      <div className="grid12">
        <YouPanel view={view} />
        <AboutPanel view={view} />
        <SourcesPanel sources={view.sources} now={now} tz={view.app.timezone} />
      </div>
    </>
  )
}
