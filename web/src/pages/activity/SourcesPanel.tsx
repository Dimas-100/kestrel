// Every source as a card: status, kind, age against its stale-after, last success in the profile's zone, detail.
import { Empty } from '../../charts/marks'
import { Panel } from '../../components/bits'
import { SourceCard } from '../../components/SourceCard'
import type { ActivitySource } from '../../lib/api'

export function SourcesPanel({ sources, tz }: { sources: ActivitySource[]; tz: string }) {
  return (
    <Panel id="sources" title="Sources" subtitle={sources.length > 0 ? 'Every place your money data comes from' : undefined} span={12}>
      {sources.length === 0 ? (
        <Empty>No sources configured yet.</Empty>
      ) : (
        <div className="grid gap-3 mt-3.5 grid-cols-1 md:grid-cols-3">
          {sources.map((s) => (
            <SourceCard key={s.id} label={s.label} kind={s.kind} status={s.status} lastSuccess={s.last_success} tz={tz}
              ageText={s.age_text} staleAfter={s.stale_after} detail={s.detail} />
          ))}
        </div>
      )}
    </Panel>
  )
}
