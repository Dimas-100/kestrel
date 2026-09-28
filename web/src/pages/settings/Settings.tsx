// The Settings page: the profile's own settings and every source, read-only.
import type { ReactNode } from 'react'
import { Icon } from '../../components/Icon'
import { Missing, Panel } from '../../components/bits'
import { type SettingsSource, type SettingsView, useSettings } from '../../lib/api'
import { ago, timeHM } from '../../lib/format'
import { STATUS_ICON } from '../../shell/Shell'

/** "green-red" -> "Green / red", "system" -> "System": a configured value, shown as words. */
export function readable(value: string): string {
  return value.split('-').map((word) => word[0].toUpperCase() + word.slice(1)).join(' / ')
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 text-sm border-b border-line last:border-0">
      <span className="text-ink3">{label}</span>
      <span className="text-ink1 text-right">{value}</span>
    </div>
  )
}

function YouPanel({ you, app }: { you: SettingsView['you']; app: SettingsView['app'] }) {
  return (
    <Panel id="you" title="You and the look" subtitle="Change any of this in profile.toml" span={6}>
      <div className="mt-2">
        <Row label="Name" value={you.name} />
        <Row label="Theme" value={readable(app.theme)} />
        <Row label="Accent" value={readable(app.accent)} />
        <Row label="Gain / loss colours" value={readable(app.gain_loss)} />
        <Row label="Density" value={readable(app.density)} />
        <Row label="Currency" value={app.currency} />
        <Row label="Time zone" value={app.timezone} />
      </div>
    </Panel>
  )
}

function AboutPanel({ view }: { view: SettingsView }) {
  return (
    <Panel id="about" title="Benchmark and version" span={6}>
      <div className="mt-2">
        <Row label="Benchmark" value={`${view.benchmark.symbol} · ${view.benchmark.label}`} />
        <Row label="Profile" value={view.profile} />
        <Row label="Contract version" value={view.contract_version} />
        <Row label="kestrel version" value={view.version} />
      </div>
    </Panel>
  )
}

function timingText(source: SettingsSource): string {
  const parts = [`stale after ${source.stale_after}`]
  if (source.refresh) parts.push(`reuses for ${source.refresh}`)
  if (source.timeout != null) parts.push(`times out at ${source.timeout}s`)
  return parts.join(' · ')
}

function SourcesPanel({ sources, now, tz }: { sources: SettingsSource[]; now: Date; tz: string }) {
  return (
    <Panel id="sources" title="Sources" subtitle="What each one reads, and its live status" span={12}>
      {sources.length === 0 ? (
        <p className="text-ink2 mt-3">No sources configured yet. Add one to profile.toml (see docs/connectors.md).</p>
      ) : (
        <div className="table-scroll mt-3.5">
          <table className="tbl" style={{ minWidth: 920 }}>
            <thead>
              <tr>
                <th>Source</th><th>Reads</th><th>Timing</th><th>Status</th><th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => {
                const status = STATUS_ICON[s.status]
                return (
                  <tr key={s.id}>
                    <td>
                      <div className="font-medium">{s.label}</div>
                      <div className="text-xs text-ink3 mt-0.5">{s.kind}</div>
                    </td>
                    <td className="text-sm" style={{ wordBreak: 'break-all' }}>
                      {s.reads || <Missing />}
                      {s.token_env && <div className="text-xs text-ink3 mt-0.5">token: {s.token_env}</div>}
                    </td>
                    <td className="text-xs text-ink2">{timingText(s)}</td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <Icon name={status.name} size={14} style={{ color: status.color }} />
                        <span>{status.text}</span>
                      </div>
                      <div className="num text-xs text-ink3 mt-0.5">
                        {s.last_success ? `${ago(s.last_success, now)} ago · ${timeHM(s.last_success, tz)}` : 'never'}
                      </div>
                    </td>
                    <td className="text-sm text-ink2">{s.detail || <Missing />}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
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
        <p className="text-ink2 mt-1.5">Read-only: everything here comes from profile.toml.</p>
      </header>
      <div className="grid12">
        <YouPanel you={view.you} app={view.app} />
        <AboutPanel view={view} />
        <SourcesPanel sources={view.sources} now={now} tz={view.app.timezone} />
      </div>
    </>
  )
}

