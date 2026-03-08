import React, { useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchAdvisories, fetchEvents, farmerChat } from '../utils/api'
import { Panel, PanelHeader, RiskPill, Spinner, Empty, fmtUSD } from '../components/ui'

const CROP_DEFAULTS = [
  { crop: 'Soybean', region: 'Vidarbha, MP', risk: 'LOW', price: '↑ Stable', action: '✅ INCREASE', color: 'var(--accent)' },
  { crop: 'Pulses (Tur)', region: 'Karnataka, MH', risk: 'LOW', price: '↑ Strong', action: '✅ MAINTAIN', color: 'var(--accent)' },
  { crop: 'Cotton', region: 'Gujarat, Vidarbha', risk: 'CRITICAL', price: '↓ -20%', action: '⚠ REDUCE 20%', color: 'var(--danger)' },
  { crop: 'Paddy (Basmati)', region: 'Punjab, Haryana', risk: 'HIGH', price: '↓ -12%', action: '⚠ HOLD STOCK', color: 'var(--accent2)' },
  { crop: 'Maize', region: 'Bihar, UP, AP', risk: 'MEDIUM', price: '→ Flat', action: '→ WATCH', color: 'var(--warn)' },
  { crop: 'Spices', region: 'Kerala, AP, KA', risk: 'LOW', price: '↑ GCC strong', action: '✅ DIRECT EXPORT', color: 'var(--accent)' },
]

export default function FarmerPortal() {
  const { data: advisories, loading } = usePolling(fetchAdvisories, 30000)
  const { data: events } = usePolling(fetchEvents, 30000)
  const [chatQuestion, setChatQuestion] = useState('')
  const [chatState, setChatState] = useState('')
  const [chatCrop, setChatCrop] = useState('')
  const [chatSeason, setChatSeason] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatResponse, setChatResponse] = useState('')
  const [chatModel, setChatModel] = useState('')
  const [chatOpen, setChatOpen] = useState(false)

  // Get farmer advisories from latest events
  const farmerAdvisories = (advisories || []).slice(0, 3).filter(adv => adv.farmers?.immediate_action)

  // Derive commodity risk from events
  const commodityRisks = {}
    ; (events || []).forEach(ev => {
      ; (ev.affected_commodities || []).forEach(c => {
        if (!commodityRisks[c] || RISK_ORDER[ev.risk_label] > RISK_ORDER[commodityRisks[c]]) {
          commodityRisks[c] = ev.risk_label
        }
      })
    })

  const handleChat = async () => {
    if (!chatQuestion.trim() || chatLoading) return
    setChatLoading(true)
    try {
      const res = await farmerChat(chatQuestion, chatState || null, chatCrop || null, chatSeason || null)
      setChatResponse(res?.answer || 'No response')
      setChatModel(res?.model_used || '')
    } catch (err) {
      setChatResponse(err?.message || 'Chat request failed')
      setChatModel('error')
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[18px] mb-1" style={{ color: 'var(--text)' }}>
        Farmer Intelligence Portal
      </div>
      <div className="text-[11px] mb-5" style={{ color: 'var(--muted)' }}>
        Smart cropping, income risk alerts, and market advisories for Indian farmers by region and crop
      </div>

      {/* Live farmer advisories from Bedrock */}
      {farmerAdvisories.length > 0 && (
        <div className="mb-6">
          <div className="font-syne font-bold text-[13px] mb-3" style={{ color: 'var(--text)' }}>
            🤖 AI Farmer Advisories — Bedrock Generated
          </div>
          <div className="grid grid-cols-3 gap-4">
            {farmerAdvisories.slice(0, 3).map((adv, i) => (
              <div key={i} className="rounded-xl border p-5" style={{ background: 'var(--surface2)', borderColor: 'var(--border)' }}>
                <div className="font-syne font-bold text-[13px] mb-1" style={{ color: 'var(--text)' }}>
                  🌾 {(adv.affected_commodities || ['Crops'])[0]} Farmers
                </div>
                <div className="text-[10px] mb-3" style={{ color: 'var(--muted)' }}>
                  {(adv.affected_states || []).slice(0, 2).join(' · ')}
                </div>
                <div className="mb-3">
                  <RiskPill label={adv.risk_label} />
                </div>
                <div className="text-[12px] font-serif leading-relaxed mb-3" style={{ color: 'var(--text)' }}>
                  {adv.farmers?.immediate_action?.slice(0, 180)}
                </div>
                <div className="pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
                  <div className="text-[9px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--accent)' }}>
                    Crop Recommendation
                  </div>
                  <div className="text-[11px]" style={{ color: 'var(--text)' }}>
                    {adv.farmers?.crop_advisory?.slice(0, 120)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Crop calendar */}
      <Panel>
        <PanelHeader title="Crop Calendar — Kharif 2025 Risk Advisory"
          right={<div className="flex items-center gap-1 text-[9px]" style={{ color: 'var(--accent)' }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot inline-block" style={{ background: 'var(--accent)' }} />
            AI-adjusted for current geopolitical risk
          </div>} />
        <div className="grid px-5 py-2.5 text-[9px] uppercase tracking-wider border-b"
          style={{ gridTemplateColumns: '130px 1fr 90px 130px 140px', color: 'var(--muted)', borderColor: 'var(--border)' }}>
          <span>Crop</span><span>Region</span><span>Risk</span><span>Price Forecast</span><span>AI Action</span>
        </div>
        {CROP_DEFAULTS.map((c, i) => {
          const evRisk = commodityRisks[c.crop]
          const displayRisk = evRisk || c.risk
          return (
            <div key={i} className="grid items-center px-5 py-3 border-b transition-colors hover:bg-white/[.015]"
              style={{ gridTemplateColumns: '130px 1fr 90px 130px 140px', borderColor: 'rgba(26,45,69,.5)' }}>
              <span className="text-[12px] font-semibold" style={{ color: 'var(--text)' }}>{c.crop}</span>
              <span className="text-[11px]" style={{ color: 'var(--muted)' }}>{c.region}</span>
              <RiskPill label={displayRisk} />
              <span className="text-[11px] font-semibold" style={{ color: c.color }}>{c.price}</span>
              <span className="text-[11px]" style={{ color: c.color }}>{c.action}</span>
            </div>
          )
        })}
      </Panel>

      {/* Opportunity panel */}
      <div className="grid grid-cols-2 gap-5 mt-5">
        <Panel>
          <PanelHeader title="🌾 Opportunities" />
          <div className="p-4">
            {(advisories || []).filter(a => a.farmers?.opportunity).slice(0, 3).map((adv, i) => (
              <div key={i} className="p-3 rounded-lg mb-2.5 border"
                style={{ background: 'rgba(0,229,160,.04)', borderColor: 'rgba(0,229,160,.15)' }}>
                <div className="text-[9px] uppercase tracking-widest mb-1 font-bold" style={{ color: 'var(--accent)' }}>
                  ✦ {(adv.affected_commodities || [''])[0]} Opportunity
                </div>
                <div className="text-[12px] font-serif leading-relaxed" style={{ color: 'var(--text)' }}>
                  {adv.farmers.opportunity}
                </div>
              </div>
            ))}
            {!(advisories || []).some(a => a.farmers?.opportunity) && (
              <Empty message="Opportunities will appear as advisories are generated" />
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="📊 State-wise Risk Summary" />
          <div className="p-4">
            {[
              'Punjab', 'Andhra Pradesh', 'Gujarat', 'Maharashtra (Vidarbha)',
              'Kerala', 'West Bengal', 'Madhya Pradesh',
            ].map(state => {
              // Count events affecting this state
              const affected = (events || []).filter(e =>
                (e.impact_affected_states || []).includes(state)
              )
              const maxRisk = affected.reduce((max, e) => {
                const order = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }
                return (order[e.risk_label] || 0) > (order[max] || 0) ? e.risk_label : max
              }, 'LOW')
              return (
                <div key={state} className="flex items-center gap-3 py-2 border-b text-[11px]"
                  style={{ borderColor: 'rgba(26,45,69,.5)' }}>
                  <span className="flex-1" style={{ color: 'var(--muted)' }}>{state}</span>
                  <RiskPill label={maxRisk} />
                  <span className="text-[10px]" style={{ color: 'var(--muted)' }}>
                    {affected.length} event{affected.length !== 1 ? 's' : ''}
                  </span>
                </div>
              )
            })}
          </div>
        </Panel>
      </div>

      <div className="fixed right-4 bottom-4 z-50">
        {chatOpen && (
          <div
            className="mb-3 rounded-2xl border shadow-2xl w-[calc(100vw-2rem)] sm:w-[420px] max-h-[78vh] overflow-y-auto"
            style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
              <div className="font-semibold text-[16px]" style={{ color: 'var(--text)' }}>Farmer Chat Assistant</div>
              <button
                onClick={() => setChatOpen(false)}
                className="text-[14px] px-2 py-1 rounded border"
                style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}
              >
                Close
              </button>
            </div>

            <div className="p-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
                <input
                  type="text"
                  value={chatState}
                  onChange={e => setChatState(e.target.value)}
                  placeholder="State"
                  className="px-3 py-2.5 rounded border text-[14px] bg-transparent"
                  style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
                />
                <input
                  type="text"
                  value={chatCrop}
                  onChange={e => setChatCrop(e.target.value)}
                  placeholder="Crop"
                  className="px-3 py-2.5 rounded border text-[14px] bg-transparent"
                  style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
                />
                <input
                  type="text"
                  value={chatSeason}
                  onChange={e => setChatSeason(e.target.value)}
                  placeholder="Season"
                  className="px-3 py-2.5 rounded border text-[14px] bg-transparent"
                  style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
                />
              </div>

              <textarea
                rows={4}
                value={chatQuestion}
                onChange={e => setChatQuestion(e.target.value)}
                placeholder="Ask: What crop should I plant this season? How will prices move?"
                className="w-full px-3 py-2.5 rounded border text-[15px] bg-transparent mb-3"
                style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
              />

              <button
                onClick={handleChat}
                disabled={chatLoading || !chatQuestion.trim()}
                className="w-full px-3 py-2.5 rounded text-[14px] font-semibold border disabled:opacity-50 mb-3"
                style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}
              >
                {chatLoading ? 'Asking...' : 'Ask AI'}
              </button>

              <div className="rounded border p-3 min-h-[120px]" style={{ borderColor: 'var(--border)', background: 'var(--surface2)' }}>
                {!chatResponse ? (
                  <div className="text-[14px] leading-relaxed" style={{ color: 'var(--muted)' }}>
                    Ask a question to get crop and risk guidance from latest events and advisories.
                  </div>
                ) : (
                  <>
                    <div className="text-[15px] leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--text)' }}>
                      {chatResponse}
                    </div>
                    <div className="mt-2 text-[12px]" style={{ color: 'var(--muted)' }}>
                      model: {chatModel || 'unknown'}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        <button
          onClick={() => setChatOpen(v => !v)}
          className="w-14 h-14 rounded-full border flex items-center justify-center shadow-lg transition-transform hover:scale-105"
          style={{ background: 'var(--accent)', borderColor: 'var(--accent2)', color: '#082014' }}
          aria-label="Toggle Farmer Chat"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 5.5a2.5 2.5 0 0 1 2.5-2.5h11A2.5 2.5 0 0 1 20 5.5v8A2.5 2.5 0 0 1 17.5 16H10l-4.5 4v-4H6.5A2.5 2.5 0 0 1 4 13.5v-8Z" stroke="currentColor" strokeWidth="1.8" />
            <circle cx="9" cy="9.5" r="1" fill="currentColor" />
            <circle cx="12" cy="9.5" r="1" fill="currentColor" />
            <circle cx="15" cy="9.5" r="1" fill="currentColor" />
          </svg>
        </button>
      </div>
    </div>
  )
}

const RISK_ORDER = { LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 }
