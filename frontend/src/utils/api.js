import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({ baseURL: BASE, timeout: 15000 })

export const fetchDashboard = () => api.get('/dashboard').then(r => r.data)
export const fetchEvents = (limit = 50) => api.get(`/events?limit=${limit}`).then(r => r.data)
export const fetchAdvisories = (limit = 20) => api.get(`/advisories?limit=${limit}`).then(r => r.data)
export const fetchTradePartners = () => api.get('/trade/partners').then(r => r.data)
export const fetchCommodities = () => api.get('/trade/commodities').then(r => r.data)
export const fetchHealth = () => api.get('/health').then(r => r.data)
export const analyzeHeadline = (headline, source_url = null) =>
  api.post('/analyze', { headline, source_url }).then(r => r.data)
export const farmerChat = (question, state = null, crop = null, season = null) =>
  api.post('/farmer/chat', { question, state, crop, season }).then(r => r.data)

export default api
