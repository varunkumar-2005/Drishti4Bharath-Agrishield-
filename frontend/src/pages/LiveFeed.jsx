import React, { useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { fetchEvents, analyzeHeadline } from '../utils/api'
import { Panel, PanelHeader, RiskPill, LiveDot, KpiCard, Spinner, timeAgo } from '../components/ui'

export default function LiveFeed() {
  const { data: events, loading } = usePolling(fetchEvents, 20000)
  const [headline, setHeadline] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleAnalyze = async () => {
    if (!headline.trim()) return
    setSubmitting(true)
    try {
      await analyzeHeadline(headline)
      setSubmitted(true)
      setHeadline('')
      setTimeout(() => setSubmitted(false), 4000)
    } catch (e) {
      alert('Analysis queued (backend may be starting up)')
    } finally {
      setSubmitting(false)
    }
  }

  const avgTone = events?.length
    ? (events.reduce((s, e) => s + (e.avg_tone || 0), 0) / events.length).toFixed(1)
    : '0.0'

  return (
    <div className="p-7 animate-fadeIn">
      <div className="font-syne font-extrabold text-[18px] mb-1" style={{ color: 'var(--text)' }}>
        Live GDELT Feed
      </div>
      <div className="text-[11px] mb-5" style={{ color: 'var(--muted)' }}>
        Real-time geopolitical event stream — filtered for India agricultural trade relevance
      </div>

      {/* Analyze Box */}
      <Panel className="mb-5">
        <PanelHeader title="🔍 Analyze Custom Headline" right={
          <span className="text-[9px] px-2 py-0.5 rounded" style={{ background: 'rgba(0,229,160,.1)', border: '1px solid rgba(0,229,160,.2)', color: 'var(--accent)' }}>
            Bedrock · Claude
          </span>
        } />
        <div className="p-4">
          <div className="text-[10px] mb-2" style={{ color: 'var(--muted)' }}>
            Enter any geopolitical headline — our agents will analyze its impact on India's agri trade
          </div>
          <div className="flex gap-2">
            <input type="text" value={headline} onChange={e => setHeadline(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
              placeholder="e.g. USA imposes 50% tariff on Indian agricultural exports…"
              className="flex-1 px-4 py-2.5 rounded-lg text-[12px] bg-transparent border outline-none"
              style={{ borderColor: 'var(--border)', color: 'var(--text)', fontFamily: 'JetBrains Mono' }} />
            <button onClick={handleAnalyze} disabled={submitting || !headline.trim()}
              className="px-5 py-2.5 rounded-lg text-[12px] font-bold transition-all"
              style={{ background: submitting ? 'var(--dim)' : 'var(--accent)', color: 'var(--bg)', cursor: submitting ? 'not-allowed' : 'pointer' }}>
              {submitting ? 'Analyzing…' : 'Analyze →'}
            </button>
          </div>
          {submitted && (
            <div className="mt-2 text-[11px] font-medium" style={{ color: 'var(--accent)' }}>
              ✓ Analysis queued — results will appear in Events & Advisories within 30s
            </div>
          )}
          <div className="flex flex-wrap gap-2 mt-3">
            {[
              'USA imposes 50% tariff on Indian rice exports',
              'Iran fires missiles near Strait of Hormuz',
              'China bans fertilizer exports',
              'Bangladesh floods damage 40% of Boro rice crop',
            ].map(ex => (
              <button key={ex} onClick={() => setHeadline(ex)}
                className="text-[9px] px-2.5 py-1 rounded border transition-colors cursor-pointer"
                style={{ borderColor: 'var(--border)', color: 'var(--muted)', background: 'var(--surface2)' }}>
                {ex.slice(0, 45)}…
              </button>
            ))}
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-2 gap-4 mb-5">
        <KpiCard label="Events Today" value={events?.length || 0} color="blue"
          sub="Agri-relevant filtered from GDELT" />
        <KpiCard label="Avg Tone (India)" value={avgTone} color="red"
          sub="Negative = hostile geopolitical environment" />
      </div>

      <Panel>
        <PanelHeader title="Live Stream — New events appear automatically" icon={<LiveDot color="var(--danger)" />}
          right={<span className="text-[9px] px-2 py-0.5 rounded"
            style={{ background: 'rgba(0,229,160,.1)', border: '1px solid rgba(0,229,160,.2)', color: 'var(--accent)' }}>
            GDELT API
          </span>} />
        {loading && !events ? <Spinner /> :
          (events || []).slice(0, 20).map((ev, i) => (
            <div key={i} className="flex items-start gap-3 px-5 py-3.5 border-b transition-colors hover:bg-white/[.015]"
              style={{ borderColor: 'rgba(26,45,69,.5)', animation: i === 0 ? 'slideUp .4s ease' : '' }}>
              <div className="mt-0.5"><RiskPill label={ev.risk_label} /></div>
              <div className="flex-1">
                <div className="text-[12px] font-medium mb-1 leading-snug" style={{ color: 'var(--text)' }}>
                  {i === 0 && <span className="mr-1.5">📡</span>}{ev.headline}
                </div>
                <div className="flex gap-3 text-[10px]" style={{ color: 'var(--muted)' }}>
                  <span>{ev.primary_country}</span>
                  <span>⏱ {timeAgo(ev.timestamp)}</span>
                  <span>Goldstein: {(ev.estimated_goldstein || 0).toFixed(1)}</span>
                  {ev.avg_tone && <span>Tone: {ev.avg_tone.toFixed(1)}</span>}
                </div>
              </div>
              <div>
                {i === 0 && <div className="text-[11px] font-bold" style={{ color: 'var(--danger)' }}>NEW</div>}
              </div>
            </div>
          ))
        }
      </Panel>
    </div>
  )
}
