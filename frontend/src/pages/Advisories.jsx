import React, { useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchAdvisories } from '../utils/api'
import { Panel, PanelHeader, RiskPill, Spinner, Empty, AdvCard, fmtUSD, timeAgo } from '../components/ui'

const TABS = [
  { id: 'policy_makers', label: '🏛 Policymakers' },
  { id: 'farmers', label: '🌾 Farmers' },
  { id: 'consumers', label: '🛒 Consumers' },
  { id: 'traders', label: '📦 Traders' },
]

function AdvisoryPanel({ advisory }) {
  const [activeTab, setActiveTab] = useState('policy_makers')

  const pm = advisory.policy_makers || {}
  const fa = advisory.farmers || {}
  const co = advisory.consumers || {}
  const tr = advisory.traders || {}

  const tabContent = {
    policy_makers: [
      { type: 'alert', title: '⚠ Immediate — 0 to 72 Hours', text: pm.immediate_72h, tags: ['URGENT', advisory.primary_country, advisory.event_type] },
      { type: 'warning', title: '◈ Short-term — 1 to 4 Weeks', text: pm.week_1_4, tags: ['POLICY'] },
      { type: 'action', title: '✦ Medium-term — 1 to 3 Months', text: pm.medium_term, tags: ['STRATEGIC'] },
    ],
    farmers: [
      { type: 'alert', title: `⚠ Immediate Action — ${(advisory.affected_states || []).slice(0, 2).join(', ')}`, text: fa.immediate_action, tags: (advisory.affected_commodities || []).slice(0, 3) },
      { type: 'warning', title: '◈ Crop Planning Advisory', text: fa.crop_advisory, tags: ['CROP PLAN'] },
      { type: 'action', title: '✦ Opportunity', text: fa.opportunity, tags: ['OPPORTUNITY'] },
    ],
    consumers: [
      { type: 'alert', title: '⚠ Price Alert', text: co.price_alert, tags: ['PRICE IMPACT'] },
      { type: 'warning', title: '◈ Consumer Advisory', text: co.advisory, tags: ['ADVISORY'] },
      { type: 'info', title: '◎ 30-Day Outlook', text: co.outlook_30d, tags: ['FORECAST'] },
    ],
    traders: [
      { type: 'alert', title: '⚠ Immediate — Trade Action', text: tr.immediate, tags: ['URGENT'] },
      { type: 'warning', title: '◈ Rerouting / Hedging', text: tr.rerouting, tags: ['REROUTE'] },
      { type: 'action', title: '✦ Trading Opportunity', text: tr.opportunity, tags: ['OPPORTUNITY'] },
    ],
  }

  return (
    <Panel className="mb-5">
      <PanelHeader
        title={`🤖 ${advisory.headline?.slice(0, 70) || 'Advisory'}…`}
        right={
          <div className="flex items-center gap-2">
            <RiskPill label={advisory.risk_label} />
            <span className="text-[9px]" style={{ color: 'var(--accent)' }}>
              {advisory.model_used?.includes('claude') ? 'Claude Sonnet' :
                advisory.model_used?.includes('nova') ? 'Nova Lite' : 'Rule-based'} · {timeAgo(advisory.generated_at)}
            </span>
          </div>
        }
      />

      {/* Summary */}
      {advisory.summary && (
        <div className="px-5 py-3 text-[12px] leading-relaxed font-serif border-b"
          style={{ borderColor: 'var(--border)', color: 'var(--muted)', background: 'rgba(0,0,0,.15)' }}>
          {advisory.summary}
        </div>
      )}

      {/* Meta row */}
      <div className="flex gap-4 px-5 py-2.5 border-b text-[10px]"
        style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
        <span>📍 {advisory.primary_country}</span>
        <span>🌾 {(advisory.affected_commodities || []).slice(0, 3).join(', ')}</span>
        <span>👨‍🌾 {advisory.farmers_at_risk_millions}M farmers</span>
        <span>💰 {fmtUSD(advisory.revenue_at_risk_usd)} at risk</span>
        <span>📍 {(advisory.affected_states || []).slice(0, 2).join(', ')}</span>
      </div>

      {/* Tabs */}
      <div className="flex border-b" style={{ borderColor: 'var(--border)' }}>
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className="px-4 py-2.5 text-[11px] uppercase tracking-wider border-b-2 transition-all cursor-pointer"
            style={{
              borderBottomColor: activeTab === tab.id ? 'var(--accent)' : 'transparent',
              color: activeTab === tab.id ? 'var(--accent)' : 'var(--muted)',
              background: 'none',
            }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-4">
        {(tabContent[activeTab] || []).filter(item => item.text).map((item, i) => (
          <AdvCard key={i} type={item.type} title={item.title} tags={item.tags?.filter(Boolean)}>
            {item.text}
          </AdvCard>
        ))}
        {!(tabContent[activeTab] || []).some(i => i.text) && (
          <Empty message="Advisory details loading…" />
        )}
      </div>
    </Panel>
  )
}

export default function Advisories() {
  const { data: advisories, loading } = usePolling(fetchAdvisories, 30000)

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[18px] mb-1" style={{ color: 'var(--text)' }}>
        AI-Generated Advisories
      </div>
      <div className="text-[11px] mb-5" style={{ color: 'var(--muted)' }}>
        Amazon Bedrock (Claude Sonnet / Nova Lite) — Actionable intelligence per stakeholder group
      </div>

      {loading && !advisories ? <Spinner /> :
        !advisories?.length ? <Empty message="Advisories are generated automatically when GDELT events are detected. Use Live Feed to trigger manual analysis." /> :
          advisories.map((adv, i) => <AdvisoryPanel key={i} advisory={adv} />)
      }
    </div>
  )
}
