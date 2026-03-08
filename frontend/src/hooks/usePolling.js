import { useState, useEffect, useCallback } from 'react'

export function usePolling(fetchFn, intervalMs = 30000, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const load = useCallback(async () => {
    try {
      const result = await fetchFn()
      setData(result)
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message || 'Failed to fetch')
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => {
    load()
    const interval = setInterval(load, intervalMs)
    return () => clearInterval(interval)
  }, [load, intervalMs])

  return { data, loading, error, refetch: load, lastUpdated }
}
