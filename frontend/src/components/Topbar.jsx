import React, { useState, useEffect } from 'react'

export function Ticker({ items = [] }) {
  const doubled = [...items, ...items]
  if (!items.length) return null
  return (
    <div className="overflow-hidden border-b py-1.5"
      style={{ background: 'rgba(255,61,90,.06)', borderColor: 'rgba(255,61,90,.12)' }}>
      <div className="flex gap-10 animate-ticker whitespace-nowrap w-max">
        {doubled.map((item, i) => (
          <span key={i} className="text-[10px] flex-shrink-0" style={{ color: 'var(--muted)' }}>
            <span className="font-bold mr-1"
              style={{
                color: item.label === 'CRITICAL' ? 'var(--danger)' :
                  item.label === 'HIGH' ? 'var(--accent2)' :
                    item.label === 'MEDIUM' ? 'var(--warn)' : 'var(--accent)'
              }}>
              {item.label === 'CRITICAL' ? 'âš  CRITICAL' :
                item.label === 'HIGH' ? 'âš  HIGH' :
                  item.label === 'MEDIUM' ? 'â—ˆ MEDIUM' : 'âœ¦ LOW'}
            </span>
            Â· {item.text}
          </span>
        ))}
      </div>
    </div>
  )
}

export function Topbar({ title, crumb, criticalCount = 0, clock }) {
  return (
    <div className="h-[60px] flex items-center px-7 gap-4 sticky top-0 z-40"
      style={{ background: 'rgba(6,10,15,.92)', backdropFilter: 'blur(10px)', borderBottom: '1px solid var(--border)' }}>
      <div>
        <div className="font-syne font-bold text-[17px]" style={{ color: 'var(--text)' }}>{title}</div>
        <div className="text-[12px]" style={{ color: 'var(--muted)' }}>{crumb}</div>
      </div>
      {criticalCount > 0 && (
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px]"
          style={{ background: 'rgba(255,59,58,.10)', border: '1px solid rgba(255,59,58,.25)', color: '#ff6b6b' }}>
          âš  {criticalCount} critical event{criticalCount > 1 ? 's' : ''} require immediate attention
        </div>
      )}
      <div className="ml-auto flex items-center gap-3">
        <span className="text-[9px] px-2 py-0.5 rounded"
          style={{ background: 'rgba(0,229,160,.1)', border: '1px solid rgba(0,229,160,.2)', color: 'var(--accent)' }}>
          GDELT LIVE
        </span>
        <span className="text-[12px]" style={{ color: 'var(--muted)' }}>{clock}</span>
      </div>
    </div>
  )
}
