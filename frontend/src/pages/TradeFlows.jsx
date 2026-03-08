import React from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchTradePartners } from '../utils/api'
import { Panel, PanelHeader, KpiCard, RiskPill, Spinner, Empty, fmtUSD } from '../components/ui'

const ROUTES = [
  { name: 'Strait of Hormuz', risk: 'CRITICAL', desc: 'Iran rice, UAE spice lanes · 38% of India oil imports', pct: '68% closure risk' },
  { name: 'Suez Canal', risk: 'HIGH', desc: 'EU wheat, African commodity lanes · Houthi activity', pct: 'Elevated' },
  { name: 'Malacca Strait', risk: 'LOW', desc: 'Palm oil from Indonesia/Malaysia · Stable', pct: 'Normal' },
  { name: 'South China Sea', risk: 'MEDIUM', desc: 'ASEAN rice, soy lanes · China tension monitoring', pct: 'Watch' },
]

export default function TradeFlows() {
  const { data: partners, loading } = usePolling(fetchTradePartners, 60000)

  const totalTrade = (partners || []).reduce((s, p) => s + p.total_trade_usd, 0)
  const exportPartners = (partners || []).filter(p => p.trade_type === 'EXPORT')
  const importPartners = (partners || []).filter(p => p.trade_type === 'IMPORT')
  const maxTrade = Math.max(...(partners || []).map(p => p.total_trade_usd), 1)

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[18px] mb-1" style={{ color: 'var(--text)' }}>
        Trade Flow Analysis
      </div>
      <div className="text-[11px] mb-5" style={{ color: 'var(--muted)' }}>
        India's bilateral agricultural trade exposure — partner countries, corridors, and shipping routes
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <KpiCard label="Total Agri Trade" value={fmtUSD(totalTrade)} color="blue"
          sub="From S3 trade dataset" />
        <KpiCard label="Export Partners" value={exportPartners.length} color="green"
          sub="Countries India exports to" />
        <KpiCard label="Import Partners" value={importPartners.length} color="orange"
          sub="Countries India imports from" />
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Trade partners */}
        <Panel>
          <PanelHeader title="Trade Partners by Volume"
            right={<span className="text-[10px]" style={{ color: 'var(--muted)' }}>From S3 dataset</span>} />
          <div className="p-4">
            {loading && !partners ? <Spinner /> :
              !partners?.length ? <Empty message="Loading trade data from S3…" /> :
                (partners || []).slice(0, 12).map((p, i) => {
                  const barPct = (p.total_trade_usd / maxTrade) * 100
                  const color = p.avg_shock > 2 ? 'var(--danger)' :
                    p.avg_shock > 1 ? 'var(--accent2)' : 'var(--accent3)'
                  return (
                    <div key={i} className="flex items-center py-2 border-b text-[11px]"
                      style={{ borderColor: 'rgba(26,45,69,.5)' }}>
                      <span className="w-36 flex-shrink-0" style={{ color: 'var(--text)' }}>{p.country}</span>
                      <div className="flex-1 mx-3 h-1 rounded-sm overflow-hidden" style={{ background: 'var(--dim)' }}>
                        <div className="h-full rounded-sm" style={{ width: `${barPct}%`, background: color }} />
                      </div>
                      <span className="font-semibold w-20 text-right" style={{ color }}>
                        {fmtUSD(p.total_trade_usd)}
                      </span>
                    </div>
                  )
                })
            }
          </div>
        </Panel>

        {/* Shipping routes + commodity exposure */}
        <div className="flex flex-col gap-4">
          <Panel>
            <PanelHeader title="Shipping Route Risk"
              right={<span className="text-[10px]" style={{ color: 'var(--muted)' }}>Live status</span>} />
            <div className="p-4 flex flex-col gap-2.5">
              {ROUTES.map((r, i) => {
                const bg = r.risk === 'CRITICAL' ? 'rgba(255,61,90,.08)' :
                  r.risk === 'HIGH' ? 'rgba(255,107,53,.08)' :
                    r.risk === 'MEDIUM' ? 'rgba(255,184,0,.08)' : 'rgba(0,229,160,.06)'
                const border = r.risk === 'CRITICAL' ? 'rgba(255,61,90,.2)' :
                  r.risk === 'HIGH' ? 'rgba(255,107,53,.2)' :
                    r.risk === 'MEDIUM' ? 'rgba(255,184,0,.2)' : 'rgba(0,229,160,.15)'
                return (
                  <div key={i} className="p-3 rounded-lg border" style={{ background: bg, borderColor: border }}>
                    <div className="flex justify-between mb-1">
                      <span className="text-[12px] font-semibold" style={{ color: 'var(--text)' }}>🚢 {r.name}</span>
                      <RiskPill label={r.risk} />
                    </div>
                    <div className="text-[10px]" style={{ color: 'var(--muted)' }}>{r.desc}</div>
                  </div>
                )
              })}
            </div>
          </Panel>

          <Panel>
            <PanelHeader title="Top Commodities by Partner" />
            <div className="p-4">
              {(partners || []).slice(0, 5).map((p, i) => (
                <div key={i} className="flex items-start gap-2 py-2 border-b"
                  style={{ borderColor: 'rgba(26,45,69,.5)' }}>
                  <span className="text-[11px] w-24 flex-shrink-0" style={{ color: 'var(--muted)' }}>{p.country}</span>
                  <div className="flex flex-wrap gap-1">
                    {(p.top_commodities || []).slice(0, 3).map(c => (
                      <span key={c} className="text-[9px] px-1.5 py-0.5 rounded"
                        style={{ background: 'rgba(61,158,255,.1)', border: '1px solid rgba(61,158,255,.2)', color: 'var(--accent3)' }}>
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {(!partners || partners.length === 0) && <Empty message="Loading…" />}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
