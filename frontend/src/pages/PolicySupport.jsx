import React from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchAdvisories, fetchEvents } from '../utils/api'
import { Panel, PanelHeader, KpiCard, RiskPill, Spinner, Empty, fmtUSD, AdvCard } from '../components/ui'

export default function PolicySupport() {
  const { data: advisories, loading: advLoading } = usePolling(fetchAdvisories, 30000)
  const { data: events } = usePolling(fetchEvents, 30000)

  const criticalEvents = (events || []).filter(e => e.risk_label === 'CRITICAL')
  const latestAdv = (advisories || [])[0]

  const timeline = latestAdv ? [
    {
      period: '0–72 Hours', icon: '🚨', color: 'rgba(255,61,90,.2)', borderColor: 'rgba(255,61,90,.4)',
      title: 'Immediate Actions',
      desc: latestAdv.policy_makers?.immediate_72h || 'Awaiting advisory generation'
    },
    {
      period: 'Week 1 · 7 Days', icon: '⚡', color: 'rgba(255,107,53,.2)', borderColor: 'rgba(255,107,53,.4)',
      title: 'Short-term Response',
      desc: latestAdv.policy_makers?.week_1_4 || 'See advisory details'
    },
    {
      period: 'Month 1 · 30 Days', icon: '📋', color: 'rgba(255,184,0,.2)', borderColor: 'rgba(255,184,0,.4)',
      title: 'Strategic Measures',
      desc: latestAdv.policy_makers?.medium_term || 'See advisory details'
    },
    {
      period: 'Quarter · 90 Days', icon: '📈', color: 'rgba(0,229,160,.2)', borderColor: 'rgba(0,229,160,.4)',
      title: 'Long-term Diversification',
      desc: 'Commission APEDA to develop 5-year trade diversification roadmap targeting Middle East, Africa, and ASEAN.'
    },
  ] : []

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[18px] mb-1" style={{ color: 'var(--text)' }}>
        Policy Decision Support
      </div>
      <div className="text-[11px] mb-5" style={{ color: 'var(--muted)' }}>
        Early alerts for buffer stocking, trade diversification, and policy action for government stakeholders
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <KpiCard label="Critical Events" value={criticalEvents.length} color="red"
          sub="Require immediate policy action" />
        <KpiCard label="Policy Advisories" value={advisories?.length || 0} color="blue"
          sub="AI-generated since startup" />
        <KpiCard label="Total Trade at Risk" color="orange"
          value={fmtUSD((events || []).reduce((s, e) => s + (e.revenue_at_risk_usd || 0), 0))}
          sub="Across active events" />
      </div>

      <div className="grid grid-cols-[1fr_300px] gap-5">
        {/* Timeline */}
        <Panel>
          <PanelHeader title="Recommended Action Timeline"
            right={latestAdv && (
              <div className="flex items-center gap-1.5">
                <RiskPill label={latestAdv.risk_label} />
                <span className="text-[9px]" style={{ color: 'var(--muted)' }}>
                  {latestAdv.primary_country}
                </span>
              </div>
            )} />
          {advLoading && !advisories ? <Spinner /> :
            !latestAdv ? <Empty message="No advisory data yet — awaiting GDELT events" /> : (
              <div className="p-5">
                {timeline.map((item, i) => (
                  <div key={i} className="flex gap-4 mb-5 relative">
                    {i < timeline.length - 1 && (
                      <div className="absolute left-4 top-9 bottom-0 w-px" style={{ background: 'var(--border)' }} />
                    )}
                    <div className="w-8 h-8 rounded-full flex items-center justify-center text-[14px] flex-shrink-0 border"
                      style={{ background: item.color, borderColor: item.borderColor }}>
                      {item.icon}
                    </div>
                    <div>
                      <div className="text-[9px] uppercase tracking-wider mb-1" style={{ color: 'var(--muted)' }}>
                        {item.period}
                      </div>
                      <div className="text-[12px] font-semibold mb-1.5" style={{ color: 'var(--text)' }}>
                        {item.title}
                      </div>
                      <div className="text-[11px] leading-relaxed" style={{ color: 'var(--muted)' }}>
                        {item.desc}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
        </Panel>

        {/* Status + pending actions */}
        <div className="flex flex-col gap-4">
          <Panel>
            <PanelHeader title="Active Events by Risk" />
            <div className="p-4">
              {(events || []).slice(0, 6).map((ev, i) => (
                <div key={i} className="flex items-start gap-2 py-2 border-b"
                  style={{ borderColor: 'rgba(26,45,69,.5)' }}>
                  <div className="mt-0.5"><RiskPill label={ev.risk_label} /></div>
                  <div>
                    <div className="text-[11px]" style={{ color: 'var(--text)' }}>{ev.headline?.slice(0, 55)}…</div>
                    <div className="text-[9px] mt-0.5" style={{ color: 'var(--muted)' }}>
                      {ev.primary_country} · {fmtUSD(ev.revenue_at_risk_usd)}
                    </div>
                  </div>
                </div>
              ))}
              {(!events || events.length === 0) && <Empty message="Awaiting events…" />}
            </div>
          </Panel>

          {latestAdv && (
            <Panel>
              <PanelHeader title="⚠ Pending Actions" />
              <div className="p-4 text-[11px] leading-loose" style={{ color: 'var(--text)' }}>
                {[
                  `Buffer stock release — ${(latestAdv.affected_states || []).slice(0, 2).join(', ')}`,
                  `WTO filing if applicable — deadline tracked`,
                  `CEPA review — Commerce Ministry`,
                  `MSP revision for ${(latestAdv.affected_commodities || []).slice(0, 1).join('')}`,
                ].map((action, i) => (
                  <div key={i} className="flex items-center gap-2 py-1.5 border-b"
                    style={{ borderColor: 'rgba(26,45,69,.4)' }}>
                    <span style={{ color: 'var(--danger)' }}>•</span>
                    {action}
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  )
}
