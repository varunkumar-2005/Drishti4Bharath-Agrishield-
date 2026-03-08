import React, { useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchEvents } from '../utils/api'
import { Panel, PanelHeader, RiskPill, LiveDot, Spinner, Empty, fmtUSD, timeAgo } from '../components/ui'

const FILTERS = ['All', 'TARIFF', 'CONFLICT', 'SANCTION', 'DIPLOMATIC', 'CLIMATE', 'ECONOMIC']

export default function Events() {
  const { data: events, loading } = usePolling(fetchEvents, 30000)
  const [filter, setFilter] = useState('All')
  const [search, setSearch] = useState('')

  const filtered = (events || []).filter(ev => {
    const matchFilter = filter === 'All' || ev.event_type === filter
    const matchSearch = !search ||
      ev.headline?.toLowerCase().includes(search.toLowerCase()) ||
      ev.primary_country?.toLowerCase().includes(search.toLowerCase())
    return matchFilter && matchSearch
  })

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[18px] mb-1" style={{ color: 'var(--text)' }}>
        Geopolitical Event Tracker
      </div>
      <div className="text-[11px] mb-5" style={{ color: 'var(--muted)' }}>
        Real-time monitoring of sanctions, tariffs, conflicts, and diplomatic shifts affecting Indian agri trade
      </div>

      {/* Search */}
      <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg mb-5"
        style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
        <span style={{ color: 'var(--muted)' }}>🔍</span>
        <input type="text" placeholder="Search by country, commodity, or event type…"
          value={search} onChange={e => setSearch(e.target.value)}
          className="bg-transparent border-none outline-none flex-1 text-[12px]"
          style={{ color: 'var(--text)', fontFamily: 'JetBrains Mono' }} />
        <span className="text-[10px]" style={{ color: 'var(--muted)' }}>{filtered.length} events</span>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className="px-3.5 py-1.5 rounded-full text-[10px] transition-all cursor-pointer border"
            style={{
              background: filter === f ? 'rgba(0,229,160,.1)' : 'var(--surface)',
              borderColor: filter === f ? 'rgba(0,229,160,.3)' : 'var(--border)',
              color: filter === f ? 'var(--accent)' : 'var(--muted)',
            }}>
            {f}
          </button>
        ))}
      </div>

      <Panel>
        <PanelHeader title="Live Events — GDELT sourced · Auto-refresh 30s" icon={<LiveDot />}
          right={<span className="text-[10px]" style={{ color: 'var(--muted)' }}>Sorted by impact</span>} />
        {/* Table head */}
        <div className="grid px-5 py-2.5 text-[9px] uppercase tracking-wider border-b"
          style={{ gridTemplateColumns: '85px 1fr 120px 80px 80px', color: 'var(--muted)', borderColor: 'var(--border)' }}>
          <span>Risk</span><span>Event</span><span>Sources</span><span>Goldstein</span><span>Impact</span>
        </div>
        {loading && !events ? <Spinner /> :
          filtered.length === 0 ? <Empty message="No events match this filter" /> :
            filtered.slice(0, 30).map((ev, i) => {
              const goldstein = ev.estimated_goldstein || 0
              const goldColor = goldstein < -5 ? 'var(--danger)' : goldstein < -2 ? 'var(--accent2)' : 'var(--accent)'
              return (
                <div key={i} className="grid items-center px-5 py-3 border-b cursor-pointer transition-colors hover:bg-white/[.015]"
                  style={{ gridTemplateColumns: '85px 1fr 120px 80px 80px', borderColor: 'rgba(26,45,69,.5)' }}>
                  <RiskPill label={ev.risk_label} />
                  <div>
                    <div className="text-[12px] font-semibold mb-0.5 leading-snug" style={{ color: 'var(--text)' }}>
                      {ev.headline}
                    </div>
                    <div className="text-[10px]" style={{ color: 'var(--muted)' }}>
                      {ev.primary_country} · {ev.event_type} · {timeAgo(ev.timestamp)}
                    </div>
                  </div>
                  <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
                    {ev.all_countries?.length || 1} countries
                  </span>
                  <span className="font-semibold text-[11px]" style={{ color: goldColor }}>
                    {goldstein.toFixed(1)}
                  </span>
                  <span className="font-bold text-[11px]" style={{ color: ev.is_positive ? 'var(--accent)' : 'var(--danger)' }}>
                    {fmtUSD(ev.revenue_at_risk_usd)}
                  </span>
                </div>
              )
            })
        }
      </Panel>
    </div>
  )
}
