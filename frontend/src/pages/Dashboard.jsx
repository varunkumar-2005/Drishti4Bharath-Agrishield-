import React from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchDashboard } from '../utils/api'
import { KpiCard, Panel, PanelHeader, RiskPill, LiveDot, Spinner, Empty, fmtUSD, timeAgo, AdvCard } from '../components/ui'

export default function Dashboard() {
  const { data, loading } = usePolling(fetchDashboard, 30000)

  if (loading && !data) return <Spinner />

  const d = data || {}
  const topEvents = d.top_events || []
  const latestAdv = d.latest_advisories || []

  const riskScore = Math.round(d.avg_risk_score || 0)
  const gaugeRotation = -180 + (riskScore / 100) * 180

  return (
    <div className="p-7 animate-fadeIn">
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KpiCard
          label="Active Threats"
          value={d.active_threats || 0}
          color="red"
          sub={`${d.critical_count || 0} critical · ${d.high_count || 0} high · ${d.medium_count || 0} medium`}
          badge={'up today'}
        />
        <KpiCard label="Trade at Risk" value={fmtUSD(d.trade_at_risk_usd || 0)} color="orange" sub="Across active threats" badge="up" />
        <KpiCard label="Advisories Issued" value={d.advisories_count || 0} color="blue" sub="AI-generated · multi-stakeholder" badge="Active" />
        <KpiCard
          label="System Risk Score"
          value={riskScore}
          color="green"
          sub={'Avg across top events'}
          badge={riskScore >= 75 ? 'CRITICAL' : riskScore >= 55 ? 'HIGH' : riskScore >= 35 ? 'MEDIUM' : 'LOW'}
        />
      </div>

      <div className="grid grid-cols-[1fr_340px] gap-5">
        <div>
          <Panel className="mb-5">
            <PanelHeader
              title="Global Threat Map"
              icon={<LiveDot />}
              right={<span className="text-[10px]" style={{ color: 'var(--muted)' }}>Static view</span>}
            />
            <div className="relative h-[220px] overflow-hidden" style={{ background: 'var(--surface2)' }}>
              <svg width="100%" height="100%" viewBox="0 0 800 220">
                <rect width="800" height="220" fill="#0a1628" />
                <path d="M80,25 L180,20 L200,50 L190,105 L160,125 L130,155 L100,158 L80,138 L60,105 L70,65 Z" fill="#0d1f35" stroke="#1a3050" strokeWidth="1" />
                <path d="M310,20 L380,15 L400,40 L390,70 L360,75 L330,67 L310,50 Z" fill="#0d1f35" stroke="#1a3050" strokeWidth="1" />
                <path d="M320,85 L390,80 L410,115 L400,168 L370,185 L330,180 L310,152 L300,115 Z" fill="#0d1f35" stroke="#1a3050" strokeWidth="1" />
                <path d="M430,25 L580,23 L620,60 L610,115 L570,138 L520,148 L480,125 L450,90 L440,55 Z" fill="#0d1f35" stroke="#1a3050" strokeWidth="1" />
                <path d="M490,85 L530,81 L545,110 L530,148 L505,161 L488,141 L480,115 Z" fill="#112035" stroke="#1a4060" strokeWidth="1.5" />
                {[
                  { name: 'USA', x: 160, y: 53, lx: 160, ly: 36, col: '#ff6b35' },
                  { name: 'IRAN', x: 490, y: 98, lx: 455, ly: 82, col: '#ff3d5a' },
                  { name: 'ISRAEL', x: 518, y: 92, lx: 548, ly: 74, col: '#ff3d5a' },
                  { name: 'CHINA', x: 585, y: 90, lx: 624, ly: 72, col: '#ff6b35' },
                  { name: 'HORMUZ', x: 472, y: 112, lx: 434, ly: 130, col: '#ff3d5a' },
                ].map((m) => (
                  <g key={m.name}>
                    <circle cx={m.x} cy={m.y} r="1" fill={m.col}>
                      <animate attributeName="r" from="4" to="14" dur="1.8s" repeatCount="indefinite" />
                      <animate attributeName="opacity" from=".9" to="0" dur="1.8s" repeatCount="indefinite" />
                    </circle>
                    <circle cx={m.x} cy={m.y} r="5" fill={m.col} />
                    <line x1={m.x} y1={m.y} x2={m.lx} y2={m.ly + 2} stroke={m.col} strokeOpacity="0.8" strokeWidth="1" />
                    <rect x={m.lx - 20} y={m.ly - 8} rx="4" ry="4" width="40" height="14" fill="#0f1b2a" stroke={m.col} strokeWidth="0.8" />
                    <text x={m.lx} y={m.ly + 2} textAnchor="middle" fill={m.col} fontSize="8" fontFamily="Sora" fontWeight="700">
                      {m.name}
                    </text>
                  </g>
                ))}
                <circle cx="510" cy="115" r="7" fill="#00e5a0" />
                <text x="510" y="107" textAnchor="middle" fill="#00e5a0" fontSize="8" fontFamily="Sora" fontWeight="bold">INDIA</text>
              </svg>
            </div>
          </Panel>

          <Panel>
            <PanelHeader title="Top Active Events" icon={<LiveDot />} />
            {topEvents.length === 0 ? (
              <Empty message="Waiting for events..." />
            ) : (
              topEvents.slice(0, 5).map((ev, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 px-5 py-3.5 border-b cursor-pointer transition-colors hover:bg-white/[.02]"
                  style={{ borderColor: 'rgba(26,45,69,.6)' }}
                >
                  <div className="mt-0.5"><RiskPill label={ev.risk_label} /></div>
                  <div className="flex-1">
                    <div className="text-[12px] font-medium mb-1 leading-snug" style={{ color: 'var(--text)' }}>
                      {ev.headline}
                    </div>
                    <div className="flex gap-2.5 text-[10px] flex-wrap" style={{ color: 'var(--muted)' }}>
                      <span>{ev.primary_country || ev.impact_primary_country}</span>
                      <span>time {timeAgo(ev.timestamp)}</span>
                      <span>{ev.event_type}</span>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="font-syne font-bold text-sm" style={{ color: 'var(--danger)' }}>
                      {fmtUSD(ev.revenue_at_risk_usd)}
                    </div>
                    <div className="text-[9px] uppercase" style={{ color: 'var(--muted)' }}>at risk</div>
                  </div>
                </div>
              ))
            )}
          </Panel>
        </div>

        <div className="flex flex-col gap-4">
          <Panel>
            <PanelHeader
              title="System Risk Level"
              right={<span className="text-[11px] font-bold" style={{ color: 'var(--accent2)' }}>{riskScore >= 75 ? 'CRITICAL' : riskScore >= 55 ? 'HIGH ALERT' : riskScore >= 35 ? 'MEDIUM' : 'NORMAL'}</span>}
            />
            <div className="p-5">
              <svg viewBox="0 0 180 100" width="180" height="100" style={{ display: 'block', margin: '0 auto' }}>
                <path d="M 20 90 A 70 70 0 0 1 160 90" fill="none" stroke="#1a2d45" strokeWidth="10" strokeLinecap="round" />
                <path d="M 20 90 A 70 70 0 0 1 160 90" fill="none" stroke="url(#gg)" strokeWidth="10" strokeLinecap="round" strokeDasharray="220" strokeDashoffset={220 - (riskScore / 100) * 220} />
                <defs>
                  <linearGradient id="gg" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#00e5a0" />
                    <stop offset="50%" stopColor="#ffb800" />
                    <stop offset="100%" stopColor="#ff3d5a" />
                  </linearGradient>
                </defs>
                <line x1="90" y1="90" x2={90 + 68 * Math.cos((gaugeRotation * Math.PI) / 180)} y2={90 + 68 * Math.sin((gaugeRotation * Math.PI) / 180)} stroke="#ff6b35" strokeWidth="2.5" strokeLinecap="round" />
                <circle cx="90" cy="90" r="5" fill="#ff6b35" />
                <text x="14" y="102" fill="#5a7a94" fontSize="9" fontFamily="JetBrains Mono">LOW</text>
                <text x="77" y="22" fill="#5a7a94" fontSize="9" fontFamily="JetBrains Mono">MED</text>
                <text x="145" y="102" fill="#5a7a94" fontSize="9" fontFamily="JetBrains Mono">CRIT</text>
              </svg>
              <div className="text-center mb-4">
                <div className="font-syne font-extrabold text-3xl" style={{ color: 'var(--accent2)' }}>{riskScore}</div>
                <div className="text-[11px] uppercase tracking-widest" style={{ color: 'var(--muted)' }}>Overall Risk Score</div>
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader
              title="Quick Advisory"
              right={<div className="flex items-center gap-1 text-[9px]" style={{ color: 'var(--accent)' }}><span className="w-1.5 h-1.5 rounded-full animate-pulse-dot inline-block" style={{ background: 'var(--accent)' }} />Bedrock</div>}
            />
            <div className="p-4">
              {latestAdv.length === 0 ? (
                <Empty message="Advisories being generated..." />
              ) : (
                latestAdv.slice(0, 2).map((adv, i) => (
                  <AdvCard key={i} type={i === 0 ? 'alert' : 'warning'} title={`${i === 0 ? 'Policy' : 'Farmer'} · ${adv.risk_label || 'Advisory'}`}>
                    {adv.summary || `${(adv.policy_makers?.immediate_72h || 'Advisory generated').slice(0, 150)}...`}
                  </AdvCard>
                ))
              )}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
