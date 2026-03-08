import React from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchEvents, fetchCommodities } from '../utils/api'
import { Panel, PanelHeader, KpiCard, RiskPill, Spinner, Empty, fmtUSD } from '../components/ui'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function RiskAnalyzer() {
  const { data: events, loading: evLoading } = usePolling(fetchEvents, 30000)
  const { data: commodities, loading: comLoading } = usePolling(fetchCommodities, 60000)

  const loading = evLoading && comLoading && !events && !commodities

  // Aggregate risk stats
  const criticalEvents = (events || []).filter(e => e.risk_label === 'CRITICAL')
  const highEvents = (events || []).filter(e => e.risk_label === 'HIGH')
  const avgScore = events?.length
    ? Math.round((events || []).reduce((s, e) => s + (e.risk_score || 0), 0) / events.length)
    : 0

  const totalRevAtRisk = (events || []).reduce((s, e) => s + (e.revenue_at_risk_usd || 0), 0)

  // Chart data - shock trend from events
  const chartData = (events || []).slice(0, 12).reverse().map((ev, i) => ({
    name: `E${i + 1}`,
    score: ev.risk_score || 0,
    label: ev.risk_label,
  }))

  const barColor = (score) => {
    if (score >= 75) return '#ff3d5a'
    if (score >= 55) return '#ff6b35'
    if (score >= 35) return '#ffb800'
    return '#00e5a0'
  }

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[20px] mb-1" style={{ color: 'var(--text)' }}>
        Export-Import Risk Analyzer
      </div>
      <div className="text-[12px] mb-5" style={{ color: 'var(--muted)' }}>
        XGBoost ML model - Trained on India bilateral trade dataset - Rule-based fallback
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <KpiCard label="Critical Events" value={criticalEvents.length} color="red"
          sub="Require immediate action" badge="CRITICAL" />
        <KpiCard label="High Risk Events" value={highEvents.length} color="orange"
          sub="Elevated monitoring needed" badge="HIGH" />
        <KpiCard label="Total Revenue at Risk" value={fmtUSD(totalRevAtRisk)} color="yellow"
          sub="Across all active events" />
        <KpiCard label="Avg Risk Score" value={avgScore} color="blue"
          sub="Across all tracked events" />
      </div>

      <div className="grid grid-cols-[1fr_320px] gap-5">
        <div>
          {/* Commodity risk matrix */}
          <Panel className="mb-5">
            <PanelHeader title="Commodity Risk Matrix"
              right={<span className="text-[10px]" style={{ color: 'var(--muted)' }}>Shock Ã— Trade Share</span>} />
            <div className="grid px-5 py-2.5 text-[9px] uppercase tracking-wider border-b"
              style={{ gridTemplateColumns: '1fr 90px 80px 80px 80px', color: 'var(--muted)', borderColor: 'var(--border)' }}>
              <span>Commodity</span><span>Trade Share</span><span>Avg Shock</span><span>MoM Chg</span><span>Risk</span>
            </div>
            {comLoading && !commodities ? <Spinner /> :
              (commodities || []).slice(0, 10).map((c, i) => {
                const shockScore = c.avg_shock || 0
                const riskLabel = shockScore > 3 ? 'CRITICAL' : shockScore > 2 ? 'HIGH' : shockScore > 1 ? 'MEDIUM' : 'LOW'
                const momChg = (c.avg_mom_change || 0) * 100
                return (
                  <div key={i} className="grid items-center px-5 py-3 border-b transition-colors hover:bg-white/[.015]"
                    style={{ gridTemplateColumns: '1fr 90px 80px 80px 80px', borderColor: 'rgba(26,45,69,.5)' }}>
                    <div>
                      <div className="text-[12px] font-semibold" style={{ color: 'var(--text)' }}>{c.commodity}</div>
                      <div className="text-[10px]" style={{ color: 'var(--muted)' }}>{c.top_countries?.join(' · ')}</div>
                    </div>
                    <span className="text-[11px]" style={{ color: 'var(--accent3)' }}>
                      {c.hs4 ? `HS ${c.hs4}` : 'N/A'}
                    </span>
                    <span className="font-semibold text-[11px]"
                      style={{ color: shockScore > 2 ? 'var(--danger)' : 'var(--warn)' }}>
                      {shockScore.toFixed(1)}
                    </span>
                    <span className="font-semibold text-[11px]"
                      style={{ color: momChg < 0 ? 'var(--danger)' : 'var(--accent)' }}>
                      {momChg > 0 ? '+' : ''}{momChg.toFixed(1)}%
                    </span>
                    <RiskPill label={riskLabel} />
                  </div>
                )
              })
            }
          </Panel>

          {/* ML predictions list */}
          <Panel>
            <PanelHeader title="ML Predictions - Recent Events"
              right={<span className="text-[9px]" style={{ color: 'var(--accent)' }}>XGBoost · rule-based fallback</span>} />
            {(events || []).slice(0, 8).map((ev, i) => (
              <div key={i} className="flex items-start gap-3 px-5 py-3.5 border-b"
                style={{ borderColor: 'rgba(26,45,69,.5)' }}>
                <RiskPill label={ev.risk_label} />
                <div className="flex-1">
                  <div className="text-[11px] font-medium mb-1" style={{ color: 'var(--text)' }}>
                    {ev.headline?.slice(0, 80)}
                  </div>
                  <div className="flex gap-3 text-[10px]" style={{ color: 'var(--muted)' }}>
                    <span>Score: <strong style={{ color: 'var(--accent3)' }}>{ev.risk_score}/100</strong></span>
                    <span>Confidence: <strong>{Math.round((ev.confidence || 0) * 100)}%</strong></span>
                    <span>Model: <strong style={{ color: 'var(--accent)' }}>{ev.model || 'rule_based'}</strong></span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="font-syne font-bold text-[14px]"
                    style={{ color: ev.is_positive ? 'var(--accent)' : 'var(--danger)' }}>
                    {fmtUSD(ev.revenue_at_risk_usd)}
                  </div>
                </div>
              </div>
            ))}
            {(!events || events.length === 0) && <Empty message="No predictions yet" />}
          </Panel>
        </div>

        <div className="flex flex-col gap-4">
          {/* Risk score chart */}
          <Panel>
            <PanelHeader title="Risk Score Trend" />
            <div className="p-4">
              {chartData.length === 0
                ? <Empty message="Awaiting events..." />
                : (
                  <ResponsiveContainer width="100%" height={140}>
                    <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
                      <XAxis dataKey="name" tick={{ fill: '#5a7a94', fontSize: 9 }} />
                      <YAxis tick={{ fill: '#5a7a94', fontSize: 9 }} domain={[0, 100]} />
                      <Tooltip
                        contentStyle={{ background: '#0d1520', border: '1px solid #1a2d45', borderRadius: 6 }}
                        labelStyle={{ color: '#e8f4f8', fontSize: 11 }}
                        itemStyle={{ color: '#5a7a94', fontSize: 10 }}
                      />
                      <Bar dataKey="score" radius={[2, 2, 0, 0]}>
                        {chartData.map((entry, i) => (
                          <Cell key={i} fill={barColor(entry.score)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )
              }
            </div>
          </Panel>

          {/* Probability breakdown */}
          {(events || []).slice(0, 1).map((ev, i) => (
            <Panel key={i}>
              <PanelHeader title="Latest Prediction Detail" />
              <div className="p-4">
                <div className="text-[10px] mb-3" style={{ color: 'var(--muted)' }}>
                  {ev.headline?.slice(0, 60)}...
                </div>
                {Object.entries(ev.probabilities || {}).map(([label, prob]) => (
                  <div key={label} className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] w-16" style={{ color: 'var(--muted)' }}>{label}</span>
                    <div className="flex-1 h-1 rounded-sm overflow-hidden" style={{ background: 'var(--dim)' }}>
                      <div className="h-full rounded-sm transition-all"
                        style={{
                          width: `${prob * 100}%`,
                          background: label === 'CRITICAL' ? 'var(--danger)' :
                            label === 'HIGH' ? 'var(--accent2)' :
                              label === 'MEDIUM' ? 'var(--warn)' : 'var(--accent)',
                        }} />
                    </div>
                    <span className="text-[10px] font-bold w-10 text-right"
                      style={{ color: label === 'CRITICAL' ? 'var(--danger)' : 'var(--muted)' }}>
                      {Math.round(prob * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </Panel>
          ))}
        </div>
      </div>
    </div>
  )
}
