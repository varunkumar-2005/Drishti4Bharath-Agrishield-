import React, { useState, useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import { Ticker, Topbar } from './components/Topbar'
import { usePolling } from './hooks/usePolling'
import { fetchDashboard, fetchHealth } from './utils/api'

import Dashboard    from './pages/Dashboard'
import Events       from './pages/Events'
import LiveFeed     from './pages/LiveFeed'
import RiskAnalyzer from './pages/RiskAnalyzer'
import TradeFlows   from './pages/TradeFlows'
import PriceAlerts  from './pages/PriceAlerts'
import Advisories   from './pages/Advisories'
import PolicySupport from './pages/PolicySupport'
import FarmerPortal  from './pages/FarmerPortal'

const PAGE_META = {
  '/':            { title: 'Intelligence Dashboard',    crumb: 'AgroShield / Overview' },
  '/events':      { title: 'Event Tracker',             crumb: 'AgroShield / Events' },
  '/livefeed':    { title: 'Live GDELT Feed',           crumb: 'AgroShield / Live Feed' },
  '/risk':        { title: 'Risk Analyzer',             crumb: 'AgroShield / Risk' },
  '/trade':       { title: 'Trade Flow Analysis',       crumb: 'AgroShield / Trade' },
  '/price':       { title: 'Price Shock Alerts',        crumb: 'AgroShield / Alerts' },
  '/advisories':  { title: 'AI Advisories',             crumb: 'AgroShield / Advisories' },
  '/policy':      { title: 'Policy Decision Support',   crumb: 'AgroShield / Policy' },
  '/farmer':      { title: 'Farmer Intelligence Portal', crumb: 'AgroShield / Farmer' },
}

export default function App() {
  const location = useLocation()
  const [clock, setClock] = useState('')
  const [lastSync, setLastSync] = useState(null)

  const { data: dashboard } = usePolling(fetchDashboard, 30000)
  const { data: health }    = usePolling(fetchHealth, 60000)

  // IST clock
  useEffect(() => {
    const tick = () => {
      const ist = new Date(Date.now() + 5.5 * 3600000)
      const p = n => String(n).padStart(2, '0')
      setClock(`${p(ist.getUTCHours())}:${p(ist.getUTCMinutes())}:${p(ist.getUTCSeconds())} IST`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (health) setLastSync('just now')
  }, [health])

  const meta = PAGE_META[location.pathname] || PAGE_META['/']
  const ticker = dashboard?.ticker || []
  const criticalCount = dashboard?.critical_count || 0
  const eventCount = dashboard?.active_threats || 0

  return (
    <div style={{ position: 'relative', zIndex: 1 }}>
      <Sidebar eventCount={eventCount} lastSync={lastSync} />
      <main style={{ marginLeft: 220, minHeight: '100vh' }}>
        <Ticker items={ticker} />
        <Topbar title={meta.title} crumb={meta.crumb} criticalCount={criticalCount} clock={clock} />
        <Routes>
          <Route path="/"            element={<Dashboard />} />
          <Route path="/events"      element={<Events />} />
          <Route path="/livefeed"    element={<LiveFeed />} />
          <Route path="/risk"        element={<RiskAnalyzer />} />
          <Route path="/trade"       element={<TradeFlows />} />
          <Route path="/price"       element={<PriceAlerts />} />
          <Route path="/advisories"  element={<Advisories />} />
          <Route path="/policy"      element={<PolicySupport />} />
          <Route path="/farmer"      element={<FarmerPortal />} />
        </Routes>
      </main>
    </div>
  )
}
