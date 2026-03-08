import React from 'react'

// â”€â”€ Risk pill â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function RiskPill({ label }) {
  const styles = {
    CRITICAL: 'bg-red-500/20 text-red-400 border border-red-500/40',
    HIGH: 'bg-orange-500/20 text-orange-400 border border-orange-500/40',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40',
    LOW: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  }
  return (
    <span className={`inline-block px-2.5 py-1 rounded text-[11px] font-bold tracking-widest uppercase whitespace-nowrap ${styles[label] || styles.LOW}`}>
      {label}
    </span>
  )
}

// â”€â”€ Panel wrapper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function Panel({ children, className = '' }) {
  return (
    <div className={`rounded-xl border overflow-hidden ${className}`}
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
      {children}
    </div>
  )
}

export function PanelHeader({ title, right, icon }) {
  return (
    <div className="flex items-center justify-between px-5 py-4 border-b"
      style={{ borderColor: 'var(--border)' }}>
      <div className="flex items-center gap-2 font-syne font-bold text-[18px] text-[var(--text)]">
        {icon && <span>{icon}</span>}
        {title}
      </div>
      {right && <div>{right}</div>}
    </div>
  )
}

// â”€â”€ KPI card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function KpiCard({ label, value, sub, badge, color = 'green', topLine = true }) {
  const colors = {
    green: { bar: 'var(--accent)', val: 'var(--accent)' },
    red: { bar: 'var(--danger)', val: 'var(--danger)' },
    orange: { bar: 'var(--accent2)', val: 'var(--accent2)' },
    blue: { bar: 'var(--accent3)', val: 'var(--accent3)' },
    yellow: { bar: 'var(--warn)', val: 'var(--warn)' },
  }
  const c = colors[color] || colors.green
  return (
    <div className="rounded-xl border relative overflow-hidden p-5"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
      {topLine && (
        <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: c.bar }} />
      )}
      <div className="text-[12px] uppercase tracking-widest mb-2" style={{ color: 'var(--muted)' }}>{label}</div>
      <div className="font-syne font-extrabold text-4xl leading-none mb-1.5" style={{ color: c.val }}>{value}</div>
      {sub && <div className="text-[12px]" style={{ color: 'var(--muted)' }}>{sub}</div>}
      {badge && (
        <span className="absolute top-3.5 right-3.5 text-[11px] px-2 py-0.5 rounded-full font-semibold"
          style={{ background: `${c.bar}22`, color: c.val }}>
          {badge}
        </span>
      )}
    </div>
  )
}

// â”€â”€ Live dot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function LiveDot({ color = 'var(--danger)' }) {
  return (
    <span className="inline-block w-[7px] h-[7px] rounded-full animate-pulse-dot"
      style={{ background: color }} />
  )
}

// â”€â”€ Loading spinner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function Spinner() {
  return (
    <div className="flex items-center justify-center p-12">
      <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
        style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
    </div>
  )
}

// â”€â”€ Empty state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function Empty({ message = 'No data yet' }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 gap-2">
      <div className="text-2xl opacity-40">â—ˆ</div>
      <div className="text-[14px]" style={{ color: 'var(--muted)' }}>{message}</div>
    </div>
  )
}

// â”€â”€ Advisory card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function AdvCard({ type = 'action', title, children, tags = [] }) {
  const styles = {
    action: { bar: 'var(--accent)', label: 'var(--accent)', bg: 'rgba(0,229,160,.04)' },
    warning: { bar: 'var(--warn)', label: 'var(--warn)', bg: 'rgba(255,184,0,.04)' },
    alert: { bar: 'var(--danger)', label: 'var(--danger)', bg: 'rgba(255,61,90,.04)' },
    info: { bar: 'var(--accent3)', label: 'var(--accent3)', bg: 'rgba(61,158,255,.04)' },
  }
  const s = styles[type] || styles.action
  return (
    <div className="relative rounded-lg border mb-3 p-4" style={{ background: s.bg, borderColor: 'var(--border)' }}>
      <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-lg" style={{ background: s.bar }} />
      <div className="text-[11px] uppercase tracking-widest font-bold mb-1.5 ml-1" style={{ color: s.label }}>{title}</div>
      <div className="text-[15px] leading-relaxed font-serif ml-1" style={{ color: 'var(--text)' }}>{children}</div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2 ml-1">
          {tags.map(t => (
            <span key={t} className="text-[11px] px-1.5 py-0.5 rounded border"
              style={{ background: 'rgba(61,158,255,.1)', borderColor: 'rgba(61,158,255,.3)', color: 'var(--accent3)' }}>
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// â”€â”€ Format USD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function fmtUSD(val) {
  if (!val) return '$0'
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`
  if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}

// â”€â”€ Format time ago â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function timeAgo(isoString) {
  if (!isoString) return ''
  const diff = (Date.now() - new Date(isoString).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
