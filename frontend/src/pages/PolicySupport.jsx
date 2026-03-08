import React, { useMemo, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchAdvisories, fetchEvents } from '../utils/api'
import { Panel, PanelHeader, KpiCard, RiskPill, Spinner, Empty, fmtUSD } from '../components/ui'

const RISK_RANK = { LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 }

function isBedrock(advisory) {
  const model = String(advisory?.model_used || '').toLowerCase()
  return model.includes('nova') || model.includes('claude')
}

export default function PolicySupport() {
  const { data: advisories, loading: advLoading } = usePolling(fetchAdvisories, 30000)
  const { data: events } = usePolling(fetchEvents, 30000)

  const [riskFilter, setRiskFilter] = useState('ANY')
  const [countryFilter, setCountryFilter] = useState('ANY')

  const advisoryList = advisories || []
  const eventList = events || []
  const criticalEvents = eventList.filter((e) => e.risk_label === 'CRITICAL')

  const countryOptions = useMemo(() => {
    const set = new Set()
    advisoryList.forEach((a) => {
      if (a?.primary_country) set.add(a.primary_country)
    })
    return ['ANY', ...Array.from(set)]
  }, [advisoryList])

  const filtered = useMemo(() => {
    return advisoryList.filter((a) => {
      const okRisk = riskFilter === 'ANY' || String(a?.risk_label || '').toUpperCase() === riskFilter
      const okCountry = countryFilter === 'ANY' || String(a?.primary_country || '') === countryFilter
      return okRisk && okCountry
    })
  }, [advisoryList, riskFilter, countryFilter])

  const bedrockFiltered = filtered.filter(isBedrock)

  const latestAdv = useMemo(() => {
    const src = bedrockFiltered.length ? bedrockFiltered : filtered
    if (!src.length) return null
    const sorted = [...src].sort((a, b) => {
      const riskDelta = (RISK_RANK[b?.risk_label] || 0) - (RISK_RANK[a?.risk_label] || 0)
      if (riskDelta !== 0) return riskDelta
      const scoreDelta = (Number(b?.risk_score) || 0) - (Number(a?.risk_score) || 0)
      if (scoreDelta !== 0) return scoreDelta
      return String(b?.generated_at || '').localeCompare(String(a?.generated_at || ''))
    })
    return sorted[0]
  }, [filtered, bedrockFiltered])

  const advisorySource = !latestAdv
    ? 'Not available'
    : (isBedrock(latestAdv) ? 'Amazon Bedrock' : 'Rule-based fallback')

  const timeline = latestAdv
    ? [
        {
          period: '0-72 Hours',
          icon: '!!',
          color: 'rgba(255,61,90,.2)',
          borderColor: 'rgba(255,61,90,.4)',
          title: 'Immediate Actions',
          desc: latestAdv.policy_makers?.immediate_72h || 'Awaiting advisory generation',
        },
        {
          period: 'Week 1 to Week 4',
          icon: '->',
          color: 'rgba(255,107,53,.2)',
          borderColor: 'rgba(255,107,53,.4)',
          title: 'Short-term Response',
          desc: latestAdv.policy_makers?.week_1_4 || 'See advisory details',
        },
        {
          period: 'Month 1 to Month 3',
          icon: '[]',
          color: 'rgba(255,184,0,.2)',
          borderColor: 'rgba(255,184,0,.4)',
          title: 'Strategic Measures',
          desc: latestAdv.policy_makers?.medium_term || 'See advisory details',
        },
      ]
    : []

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[22px] mb-1" style={{ color: 'var(--text)' }}>
        Policy Decision Support
      </div>
      <div className="text-[14px] mb-2" style={{ color: 'var(--muted)' }}>
        Condition-based Government of India policy advisories from Bedrock, with rule fallback.
      </div>
      <div className="text-[13px] mb-5" style={{ color: 'var(--muted)' }}>
        Advisory source: <span style={{ color: 'var(--text)', fontWeight: 700 }}>{advisorySource}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        <KpiCard label="Critical Events" value={criticalEvents.length} color="red" sub="Require immediate policy action" />
        <KpiCard label="Policy Advisories" value={advisoryList.length} color="blue" sub="Generated since startup" />
        <KpiCard
          label="Total Trade at Risk"
          color="orange"
          value={fmtUSD(eventList.reduce((s, e) => s + (e.revenue_at_risk_usd || 0), 0))}
          sub="Across active events"
        />
      </div>

      <Panel>
        <div className="px-5 py-4 border-b flex flex-wrap items-center gap-3" style={{ borderColor: 'var(--border)' }}>
          <div className="text-[13px] font-semibold" style={{ color: 'var(--text)' }}>Conditions:</div>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border text-[13px] bg-transparent"
            style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
          >
            <option value="ANY">Any Risk</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <select
            value={countryFilter}
            onChange={(e) => setCountryFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border text-[13px] bg-transparent"
            style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
          >
            {countryOptions.map((c) => (
              <option key={c} value={c}>{c === 'ANY' ? 'Any Country' : c}</option>
            ))}
          </select>
          <div className="text-[12px] ml-auto" style={{ color: 'var(--muted)' }}>
            Showing {filtered.length} advisory record{filtered.length !== 1 ? 's' : ''}
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-5 items-start mt-5">
        <Panel>
          <PanelHeader
            title="Recommended Action Timeline"
            right={
              latestAdv && (
                <div className="flex items-center gap-2">
                  <RiskPill label={latestAdv.risk_label} />
                  <span className="text-[11px]" style={{ color: 'var(--muted)' }}>{latestAdv.primary_country}</span>
                </div>
              )
            }
          />
          {advLoading && !advisoryList.length ? (
            <Spinner />
          ) : !latestAdv ? (
            <Empty message="No advisory matched these conditions. Try changing risk/country filters." />
          ) : (
            <div className="p-5">
              {timeline.map((item, i) => (
                <div key={i} className="flex gap-4 mb-5 relative">
                  {i < timeline.length - 1 && (
                    <div className="absolute left-4 top-9 bottom-0 w-px" style={{ background: 'var(--border)' }} />
                  )}
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-[12px] font-semibold flex-shrink-0 border"
                    style={{ background: item.color, borderColor: item.borderColor }}
                  >
                    {item.icon}
                  </div>
                  <div>
                    <div className="text-[11px] uppercase tracking-wider mb-1" style={{ color: 'var(--muted)' }}>{item.period}</div>
                    <div className="text-[20px] font-semibold mb-1.5" style={{ color: 'var(--text)' }}>{item.title}</div>
                    <div className="text-[15px] leading-relaxed" style={{ color: 'var(--muted)' }}>{item.desc}</div>
                  </div>
                </div>
              ))}
              {latestAdv.summary && (
                <div className="mt-2 p-4 rounded-lg border text-[14px]" style={{ borderColor: 'var(--border)', color: 'var(--text)', background: 'var(--surface2)' }}>
                  <span style={{ color: 'var(--accent)', fontWeight: 700 }}>Summary:</span> {latestAdv.summary}
                </div>
              )}
            </div>
          )}
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel>
            <PanelHeader title="Active Events by Risk" />
            <div className="p-4">
              {eventList.slice(0, 6).map((ev, i) => (
                <div key={i} className="flex items-start gap-2 py-2 border-b" style={{ borderColor: 'rgba(26,45,69,.5)' }}>
                  <div className="mt-0.5"><RiskPill label={ev.risk_label} /></div>
                  <div>
                    <div className="text-[13px]" style={{ color: 'var(--text)' }}>{ev.headline?.slice(0, 70)}...</div>
                    <div className="text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>{ev.primary_country} · {fmtUSD(ev.revenue_at_risk_usd)}</div>
                  </div>
                </div>
              ))}
              {!eventList.length && <Empty message="Awaiting events..." />}
            </div>
          </Panel>

          {latestAdv && (
            <Panel>
              <PanelHeader title="Pending Actions" />
              <div className="p-4 text-[13px] leading-loose" style={{ color: 'var(--text)' }}>
                {[
                  `Buffer stock release - ${(latestAdv.affected_states || []).slice(0, 2).join(', ') || 'Nationwide'}`,
                  'WTO filing if applicable - deadline tracked',
                  'CEPA review - Commerce Ministry',
                  `MSP revision for ${(latestAdv.affected_commodities || []).slice(0, 1).join('') || 'priority crop'}`,
                ].map((action, i) => (
                  <div key={i} className="flex items-center gap-2 py-1.5 border-b" style={{ borderColor: 'rgba(26,45,69,.4)' }}>
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
