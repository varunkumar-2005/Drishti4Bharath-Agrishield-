import React from 'react'
import { NavLink } from 'react-router-dom'
import { LiveDot } from './ui'

const NAV = [
  { section: 'Monitor' },
  { path: '/', label: 'Dashboard', icon: '◈' },
  { path: '/events', label: 'Event Tracker', icon: '⬡', badge: 'events' },
  { path: '/livefeed', label: 'Live Feed', icon: '◎', live: true },
  { section: 'Analyze' },
  { path: '/risk', label: 'Risk Analyzer', icon: '△' },
  { path: '/trade', label: 'Trade Flows', icon: '◇' },
  { path: '/price', label: 'Price Alerts', icon: '⊕', badge: 'alerts' },
  { section: 'Advise' },
  { path: '/advisories', label: 'Advisories', icon: '✦' },
  { path: '/policy', label: 'Policy Support', icon: '⊞' },
  { path: '/farmer', label: 'Farmer Portal', icon: '⊿' },
]

export default function Sidebar({ eventCount = 0, alertCount = 0, lastSync }) {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[220px] flex flex-col z-50"
      style={{ background: 'var(--surface)', borderRight: '1px solid var(--border)' }}>
      {/* Logo */}
      <div className="px-5 py-6 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2 font-syne font-extrabold text-xl" style={{ color: 'var(--accent)' }}>
          <div className="w-7 h-7 rounded-md flex items-center justify-center text-sm font-bold"
            style={{ background: 'var(--accent)', color: 'var(--bg)' }}>🌾</div>
          AgroShield
        </div>
        <div className="text-[9px] mt-1 tracking-[2px] uppercase" style={{ color: 'var(--muted)' }}>
          Trade Intelligence Platform
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {NAV.map((item, i) => {
          if (item.section) return (
            <div key={i} className="px-5 pt-2 pb-1 text-[9px] tracking-[2px] uppercase"
              style={{ color: 'var(--muted)' }}>{item.section}</div>
          )

          const badgeCount = item.badge === 'events' ? (eventCount || 0) :
            item.badge === 'alerts' ? (alertCount || 0) : 0

          return (
            <NavLink key={item.path} to={item.path} end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-5 py-2.5 text-[12px] transition-all duration-150 border-l-2 cursor-pointer ${isActive
                  ? 'border-l-[var(--accent)] bg-[rgba(0,229,160,.06)]'
                  : 'border-transparent hover:bg-white/[0.03]'
                }`
              }
              style={({ isActive }) => ({ color: isActive ? 'var(--accent)' : 'var(--muted)' })}
            >
              <span className="text-[11px]">{item.icon}</span>
              <span>{item.label}</span>
              {item.live && (
                <span className="ml-auto">
                  <LiveDot />
                </span>
              )}
              {badgeCount > 0 && (
                <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded-full font-bold"
                  style={{ background: item.badge === 'alerts' ? 'var(--warn)' : 'var(--danger)', color: '#000' }}>
                  {badgeCount}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t text-[10px]" style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full animate-pulse-dot" style={{ background: 'var(--accent)' }} />
          GDELT Live
        </div>
        <div className="mt-1 text-[9px]" style={{ color: 'var(--dim)' }}>
          {lastSync ? `Last sync: ${lastSync}` : 'Connecting…'}
        </div>
      </div>
    </aside>
  )
}
