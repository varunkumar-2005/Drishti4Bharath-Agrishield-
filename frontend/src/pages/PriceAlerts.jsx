import React from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchEvents } from '../utils/api'
import { Panel, PanelHeader, KpiCard, RiskPill, Spinner, Empty } from '../components/ui'

export default function PriceAlerts() {
  const { data: events, loading } = usePolling(fetchEvents, 30000)

  const allPriceImpacts = (events || []).flatMap((ev) =>
    (ev.impact_price_impacts || []).map((p) => ({
      ...p,
      event_headline: ev.headline,
      risk_label: ev.risk_label,
      event_type: ev.event_type,
    }))
  ).slice(0, 15)

  const upAlerts = allPriceImpacts.filter((p) => p.direction === 'up')
  const downAlerts = allPriceImpacts.filter((p) => p.direction === 'down')
  const maxCPI = Math.max(...allPriceImpacts.map((p) => p.change_pct || 0), 0)

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[20px] mb-1" style={{ color: 'var(--text)' }}>
        Price Shock Alerts
      </div>
      <div className="text-[12px] mb-5" style={{ color: 'var(--muted)' }}>
        AI-detected import/export risks that may trigger food price spikes in Indian domestic markets
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <KpiCard label="Active Alerts" value={upAlerts.length} color="red" sub="Price rise predictions" badge="URGENT" />
        <KpiCard label="Price Falls" value={downAlerts.length} color="green" sub="Opportunities for consumers" />
        <KpiCard label="Max Price Impact" value={`${maxCPI.toFixed(1)}%`} color="yellow" sub="Largest single commodity swing" />
        <KpiCard label="Events Tracked" value={events?.length || 0} color="blue" sub="Active geopolitical events" />
      </div>

      <Panel>
        <PanelHeader title="Price Impact Feed - Real-time from ML predictions" />
        {loading && !events ? <Spinner /> :
          allPriceImpacts.length === 0 ? <Empty message="Price impact data loading - awaiting events from GDELT..." /> :
            allPriceImpacts.map((p, i) => {
              const isUp = p.direction === 'up'
              const circleStyle = isUp
                ? { background: 'rgba(255,61,90,.15)', color: 'var(--danger)', border: '1px solid rgba(255,61,90,.3)' }
                : { background: 'rgba(0,229,160,.15)', color: 'var(--accent)', border: '1px solid rgba(0,229,160,.3)' }
              return (
                <div key={i} className="flex items-center gap-3.5 px-5 py-3.5 border-b cursor-pointer transition-colors hover:bg-white/[.015]"
                  style={{ borderColor: 'rgba(26,45,69,.5)' }}>
                  <div className="w-11 h-11 rounded-full flex items-center justify-center font-syne font-extrabold text-[12px] flex-shrink-0" style={circleStyle}>
                    {isUp ? `+${p.change_pct}%` : `-${p.change_pct}%`}
                  </div>
                  <div className="flex-1">
                    <div className="text-[12px] font-semibold mb-1" style={{ color: 'var(--text)' }}>
                      {p.commodity} - {isUp ? 'Predicted Price Rise' : 'Predicted Price Fall'}
                    </div>
                    <div className="text-[11px] mb-1.5" style={{ color: 'var(--muted)' }}>
                      {p.event_headline?.slice(0, 90)}
                    </div>
                    <div className="flex gap-1.5 flex-wrap">
                      <span className="text-[9px] px-1.5 py-0.5 rounded border"
                        style={{ background: 'rgba(61,158,255,.1)', borderColor: 'rgba(61,158,255,.2)', color: 'var(--accent3)' }}>
                        {p.event_type}
                      </span>
                      <RiskPill label={p.risk_label} />
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-[12px] font-bold" style={{ color: isUp ? 'var(--danger)' : 'var(--accent)' }}>
                      ${p.current_usd_kg?.toFixed(2)}/kg -> ${p.forecast_usd_kg?.toFixed(2)}/kg
                    </div>
                    <div className="text-[9px] uppercase" style={{ color: 'var(--muted)' }}>Predicted 30d</div>
                  </div>
                </div>
              )
            })
        }
      </Panel>
    </div>
  )
}
