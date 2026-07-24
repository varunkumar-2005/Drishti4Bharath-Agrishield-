import React, { useEffect, useRef, useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchAdvisories, fetchEvents, farmerMultimodalChat } from '../utils/api'
import { Panel, PanelHeader, RiskPill, Empty } from '../components/ui'

const CROP_DEFAULTS = [
  { crop: 'Soybean', region: 'Vidarbha, MP', risk: 'LOW', price: 'Stable', action: 'Increase', color: 'var(--accent)' },
  { crop: 'Pulses (Tur)', region: 'Karnataka, MH', risk: 'LOW', price: 'Strong', action: 'Maintain', color: 'var(--accent)' },
  { crop: 'Cotton', region: 'Gujarat, Vidarbha', risk: 'CRITICAL', price: '-20%', action: 'Reduce 20%', color: 'var(--danger)' },
  { crop: 'Paddy (Basmati)', region: 'Punjab, Haryana', risk: 'HIGH', price: '-12%', action: 'Hold Stock', color: 'var(--accent2)' },
  { crop: 'Maize', region: 'Bihar, UP, AP', risk: 'MEDIUM', price: 'Flat', action: 'Watch', color: 'var(--warn)' },
  { crop: 'Spices', region: 'Kerala, AP, KA', risk: 'LOW', price: 'GCC strong', action: 'Direct Export', color: 'var(--accent)' },
]

export default function FarmerPortal() {
  const { data: advisories } = usePolling(fetchAdvisories, 30000)
  const { data: events } = usePolling(fetchEvents, 30000)
  const [chatQuestion, setChatQuestion] = useState('')
  const [chatState, setChatState] = useState('')
  const [chatCrop, setChatCrop] = useState('')
  const [chatSeason, setChatSeason] = useState('')
  const [chatLanguage, setChatLanguage] = useState('en')
  const [chatImage, setChatImage] = useState(null)
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState(null)
  const [chatLoading, setChatLoading] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const fileInputRef = useRef(null)
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hello. Ask me about crop planning, mandi prices, and geopolitical risk for your state.',
      model: '',
    },
  ])
  const messageEndRef = useRef(null)

  const farmerAdvisoriesRaw = (advisories || []).filter(adv => adv.farmers?.immediate_action)
  const seenFarmerCrops = new Set()
  const farmerAdvisories = farmerAdvisoriesRaw.filter((adv) => {
    const key = String((adv.affected_commodities || ['Crops'])[0] || 'Crops').toLowerCase().trim()
    if (seenFarmerCrops.has(key)) return false
    seenFarmerCrops.add(key)
    return true
  }).slice(0, 3)

  const commodityRisks = {}
  ;(events || []).forEach(ev => {
    ;(ev.affected_commodities || []).forEach(c => {
      if (!commodityRisks[c] || RISK_ORDER[ev.risk_label] > RISK_ORDER[commodityRisks[c]]) {
        commodityRisks[c] = ev.risk_label
      }
    })
  })

  useEffect(() => {
    if (chatOpen) {
      messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, chatOpen])

  const handleSend = async (e) => {
    e?.preventDefault()
    e?.preventDefault()
    const question = chatQuestion.trim()
    if ((!question && !audioBlob && !chatImage) || chatLoading) return

    const newMessage = { role: 'user', text: question || (audioBlob ? '[Voice Message]' : ''), image: chatImage ? URL.createObjectURL(chatImage) : null }
    setMessages(prev => [...prev, newMessage])
    setChatQuestion('')
    setChatLoading(true)

    const formData = new FormData()
    if (question) formData.append('text', question)
    if (chatState) formData.append('state', chatState)
    if (chatCrop) formData.append('crop', chatCrop)
    if (chatSeason) formData.append('season', chatSeason)
    if (chatLanguage) formData.append('language', chatLanguage)
    if (chatImage) formData.append('image', chatImage)
    if (audioBlob) formData.append('audio', audioBlob, 'voice.webm')

    try {
      const res = await farmerMultimodalChat(formData)
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: res?.advisory_text || 'No response received',
          audio: res?.audio_response || null,
          model: res?.models_used?.join(', ') || '',
        },
      ])
      setChatImage(null)
      setAudioBlob(null)
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: err?.message || 'Chat request failed',
          model: 'error',
        },
      ])
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[20px] mb-1" style={{ color: 'var(--text)' }}>
        Farmer Intelligence Portal
      </div>
      <div className="text-[14px] mb-5" style={{ color: 'var(--muted)' }}>
        Smart cropping, income risk alerts, and market advisories for Indian farmers by region and crop
      </div>

      {farmerAdvisories.length > 0 && (
        <div className="mb-6">
          <div className="font-syne font-bold text-[15px] mb-3" style={{ color: 'var(--text)' }}>
            AI Farmer Advisories - Bedrock Generated
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {farmerAdvisories.slice(0, 3).map((adv, i) => (
              <div key={i} className="rounded-xl border p-5" style={{ background: 'var(--surface2)', borderColor: 'var(--border)' }}>
                <div className="font-syne font-bold text-[15px] mb-1" style={{ color: 'var(--text)' }}>
                  {(adv.affected_commodities || ['Crops'])[0]} Farmers
                </div>
                <div className="text-[12px] mb-3" style={{ color: 'var(--muted)' }}>
                  {(adv.affected_states || []).slice(0, 2).join(' · ')}
                </div>
                <div className="mb-3">
                  <RiskPill label={adv.risk_label} />
                </div>
                <div className="text-[14px] leading-relaxed mb-3" style={{ color: 'var(--text)' }}>
                  {adv.farmers?.immediate_action?.slice(0, 180)}
                </div>
                <div className="pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
                  <div className="text-[12px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--accent)' }}>
                    Crop Recommendation
                  </div>
                  <div className="text-[13px]" style={{ color: 'var(--text)' }}>
                    {adv.farmers?.crop_advisory?.slice(0, 120)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Panel>
        <PanelHeader
          title="Crop Calendar - Kharif 2025 Risk Advisory"
          right={
            <div className="flex items-center gap-1 text-[12px]" style={{ color: 'var(--accent)' }}>
              <span className="w-1.5 h-1.5 rounded-full animate-pulse-dot inline-block" style={{ background: 'var(--accent)' }} />
              AI-adjusted for current geopolitical risk
            </div>
          }
        />
        <div
          className="grid px-5 py-2.5 text-[12px] uppercase tracking-wider border-b"
          style={{ gridTemplateColumns: '130px 1fr 90px 130px 140px', color: 'var(--muted)', borderColor: 'var(--border)' }}
        >
          <span>Crop</span><span>Region</span><span>Risk</span><span>Price Forecast</span><span>AI Action</span>
        </div>
        {CROP_DEFAULTS.map((c, i) => {
          const evRisk = commodityRisks[c.crop]
          const displayRisk = evRisk || c.risk
          return (
            <div
              key={i}
              className="grid items-center px-5 py-3 border-b transition-colors hover:bg-white/[.015]"
              style={{ gridTemplateColumns: '130px 1fr 90px 130px 140px', borderColor: 'rgba(26,45,69,.5)' }}
            >
              <span className="text-[14px] font-semibold" style={{ color: 'var(--text)' }}>{c.crop}</span>
              <span className="text-[13px]" style={{ color: 'var(--muted)' }}>{c.region}</span>
              <RiskPill label={displayRisk} />
              <span className="text-[13px] font-semibold" style={{ color: c.color }}>{c.price}</span>
              <span className="text-[13px]" style={{ color: c.color }}>{c.action}</span>
            </div>
          )
        })}
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-5">
        <Panel>
          <PanelHeader title="Opportunities" />
          <div className="p-4">
            {(advisories || [])
              .filter(a => a.farmers?.opportunity)
              .filter((adv, idx, arr) => {
                const key = String((adv.affected_commodities || [''])[0] || '').toLowerCase().trim()
                return arr.findIndex((x) =>
                  String((x.affected_commodities || [''])[0] || '').toLowerCase().trim() === key
                ) === idx
              })
              .slice(0, 3)
              .map((adv, i) => (
              <div
                key={i}
                className="p-3 rounded-lg mb-2.5 border"
                style={{ background: 'rgba(0,229,160,.04)', borderColor: 'rgba(0,229,160,.15)' }}
              >
                <div className="text-[11px] uppercase tracking-widest mb-1 font-bold" style={{ color: 'var(--accent)' }}>
                  {(adv.affected_commodities || [''])[0]} Opportunity
                </div>
                <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text)' }}>
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
          <PanelHeader title="State-wise Risk Summary" />
          <div className="p-4">
            {[
              'Punjab', 'Andhra Pradesh', 'Gujarat', 'Maharashtra (Vidarbha)',
              'Kerala', 'West Bengal', 'Madhya Pradesh',
            ].map(state => {
              const affected = (events || []).filter(e => (e.impact_affected_states || []).includes(state))
              const maxRisk = affected.reduce((max, e) => {
                const order = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 }
                return (order[e.risk_label] || 0) > (order[max] || 0) ? e.risk_label : max
              }, 'LOW')
              return (
                <div
                  key={state}
                  className="flex items-center gap-3 py-2 border-b text-[13px]"
                  style={{ borderColor: 'rgba(26,45,69,.5)' }}
                >
                  <span className="flex-1" style={{ color: 'var(--muted)' }}>{state}</span>
                  <RiskPill label={maxRisk} />
                  <span className="text-[12px]" style={{ color: 'var(--muted)' }}>
                    {affected.length} event{affected.length !== 1 ? 's' : ''}
                  </span>
                </div>
              )
            })}
          </div>
        </Panel>
      </div>

      <div className="fixed right-4 bottom-4 z-[120] pointer-events-none">
        {chatOpen && (
          <div
            className="pointer-events-auto mb-3 rounded-2xl border shadow-[0_8px_32px_rgba(0,0,0,0.5)] w-[calc(100vw-2rem)] sm:w-[500px] max-h-[82vh] overflow-hidden backdrop-blur-md"
            style={{ borderColor: 'var(--border)', background: 'rgba(13, 21, 32, 0.95)' }}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
              <div className="font-semibold text-[18px] tracking-wide" style={{ color: 'var(--text)' }}>Farmer AI Assistant</div>
              <button
                onClick={() => setChatOpen(false)}
                className="text-[14px] px-3 py-1.5 rounded border transition-colors hover:bg-white/[0.05]"
                style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}
                type="button"
              >
                Close
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-3 px-5 py-3 border-b" style={{ borderColor: 'var(--border)', background: 'rgba(0,0,0,0.2)' }}>
              <select
                value={chatLanguage}
                onChange={e => setChatLanguage(e.target.value)}
                className="px-3 py-2 rounded-lg border text-[14px] bg-[var(--surface2)] focus:outline-none focus:border-[var(--accent)] transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
              >
                <option value="en">English</option>
                <option value="hi">हिंदी (Hindi)</option>
                <option value="pa">ਪੰਜਾਬੀ (Punjabi)</option>
                <option value="mr">मराठी (Marathi)</option>
              </select>
              <input
                type="text"
                value={chatState}
                onChange={e => setChatState(e.target.value)}
                placeholder="State"
                className="px-3 py-2.5 rounded-lg border text-[15px] bg-transparent focus:outline-none focus:border-[var(--accent)] transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
              />
              <input
                type="text"
                value={chatCrop}
                onChange={e => setChatCrop(e.target.value)}
                placeholder="Crop"
                className="px-3 py-2.5 rounded-lg border text-[15px] bg-transparent focus:outline-none focus:border-[var(--accent)] transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
              />
              <input
                type="text"
                value={chatSeason}
                onChange={e => setChatSeason(e.target.value)}
                placeholder="Season"
                className="px-3 py-2.5 rounded-lg border text-[15px] bg-transparent focus:outline-none focus:border-[var(--accent)] transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
              />
            </div>

            <div className="h-[380px] overflow-y-auto px-5 py-5 space-y-4" style={{ background: 'var(--surface2)' }}>
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className="max-w-[88%] rounded-2xl px-5 py-3.5 text-[16px] leading-relaxed whitespace-pre-wrap shadow-sm"
                    style={{
                      background: msg.role === 'user' ? 'var(--accent3)' : 'rgba(255,255,255,.09)',
                      color: msg.role === 'user' ? '#06111f' : 'var(--text)',
                      border: '1px solid',
                      borderColor: msg.role === 'user' ? 'rgba(61,158,255,.6)' : 'var(--border)',
                    }}
                  >
                    {msg.image && (
                      <img src={msg.image} alt="Upload" className="w-full max-w-[200px] rounded-lg mb-3 object-cover border border-white/20" />
                    )}
                    {msg.text}
                    {msg.audio && (
                      <audio controls src={msg.audio} className="mt-3 w-full max-w-[250px] h-8 rounded-lg outline-none" style={{ filter: 'invert(0.9) hue-rotate(180deg) opacity(0.8)' }} />
                    )}
                    {msg.model && msg.role === 'assistant' && (
                      <div className="mt-2.5 text-[12px] opacity-70">
                        models: {msg.model}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div
                    className="max-w-[80%] rounded-2xl px-5 py-3.5 text-[15px] shadow-sm animate-pulse"
                    style={{ background: 'rgba(255,255,255,.06)', border: '1px solid var(--border)', color: 'var(--muted)' }}
                  >
                    Thinking...
                  </div>
                </div>
              )}
              <div ref={messageEndRef} />
            </div>

            <form onSubmit={handleSend} className="p-4 border-t flex items-end gap-3 bg-[var(--surface)]" style={{ borderColor: 'var(--border)' }}>
              <input 
                type="file" 
                accept="image/*" 
                className="hidden" 
                ref={fileInputRef} 
                onChange={(e) => { if(e.target.files[0]) setChatImage(e.target.files[0]) }}
              />
              <button 
                type="button" 
                onClick={() => fileInputRef.current?.click()}
                className={`p-3 rounded-xl border transition-colors ${chatImage ? 'bg-[var(--accent)] text-[#082014]' : 'bg-transparent text-[var(--accent)]'}`}
                style={{ borderColor: 'var(--accent)' }}
                aria-label="Upload Image"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              </button>
              
              <button
                type="button"
                onClick={() => {
                  if (isRecording) {
                    setIsRecording(false)
                    // Mock recording stop and generate empty blob for demo
                    setAudioBlob(new Blob(['mock-audio'], { type: 'audio/webm' }))
                  } else {
                    setIsRecording(true)
                    setAudioBlob(null)
                  }
                }}
                className={`p-3 rounded-xl border transition-colors ${isRecording ? 'bg-[var(--danger)] text-white' : audioBlob ? 'bg-[var(--accent2)] text-[#082014]' : 'bg-transparent text-[var(--accent)]'}`}
                style={{ borderColor: isRecording ? 'var(--danger)' : audioBlob ? 'var(--accent2)' : 'var(--accent)' }}
                aria-label="Record Voice"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
              </button>

              <textarea
                rows={2}
                value={chatQuestion}
                onChange={e => setChatQuestion(e.target.value)}
                placeholder="Ask your question..."
                className="flex-1 px-4 py-3 rounded-xl border text-[16px] bg-transparent resize-none focus:outline-none focus:border-[var(--accent)] transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text)' }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend(e)
                  }
                }}
              />
              <button
                type="submit"
                disabled={chatLoading || (!chatQuestion.trim() && !audioBlob && !chatImage)}
                className="px-6 py-3.5 rounded-xl text-[15px] font-bold border transition-all hover:bg-[var(--accent)] hover:text-[#082014] disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-[var(--accent)] bg-transparent"
                style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}
              >
                Send
              </button>
            </form>
          </div>
        )}

        <button
          onClick={() => setChatOpen(v => !v)}
          className="pointer-events-auto w-14 h-14 rounded-full border flex items-center justify-center shadow-lg transition-transform hover:scale-105"
          style={{ background: 'var(--accent)', borderColor: 'var(--accent2)', color: '#082014' }}
          aria-label="Toggle Farmer Chat"
          type="button"
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
