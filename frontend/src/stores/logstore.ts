/**
 * Log Store - Prosty i działający
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ===== TYPY =====

export interface LogEntry {
  raw: string
  timestamp: string
  source: string
  event_type: 'SELECT' | 'INSERT' | 'UPDATE' | 'DELETE' | 'ERROR' | 'OTHER'
  severity: 'INFO' | 'WARNING' | 'ERROR'
  table_name?: string
  affected_rows?: number
  message: string
  user?: string
}

export interface SourceStatus {
  name: string
  type: 'file' | 'mysql' | 'mongodb'
  enabled: boolean
  running: boolean
  last_check: string | null
  logs_collected: number
  last_error: string | null
}

export interface AgentStatus {
  running: boolean
  sources_count: number
  active_sources: number
  logs_in_cache: number
  elasticsearch: {
    enabled: boolean
    connected: boolean
  }
}

export interface Stats {
  total_logs: number
  by_event_type: Record<string, number>
  by_source: Record<string, number>
  by_severity: Record<string, number>
}

// ===== STORE =====

export const useLogStore = defineStore('logs', () => {
  // State
  const logs = ref<LogEntry[]>([])
  const sources = ref<SourceStatus[]>([])
  const agentStatus = ref<AgentStatus | null>(null)
  const stats = ref<Stats | null>(null)
  
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  // Filters
  const filterSource = ref<string | null>(null)
  const filterEventType = ref<string | null>(null)
  
  // Computed
  const filteredLogs = computed(() => {
    let result = logs.value
    
    if (filterSource.value) {
      result = result.filter(l => l.source === filterSource.value)
    }
    if (filterEventType.value) {
      result = result.filter(l => l.event_type === filterEventType.value)
    }
    
    return result
  })
  
  const activeSources = computed(() => {
    if (!Array.isArray(sources.value)) return []
    return sources.value.filter(s => s.enabled)
  })
  
  // ===== API CALLS =====
  
  async function api<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      }
    })
    
    if (!response.ok) {
      const err = await response.text()
      throw new Error(err || `HTTP ${response.status}`)
    }
    
    return response.json()
  }
  
  // Logi
  async function fetchLogs() {
    try {
      const data = await api<LogEntry[]>('/api/logs?limit=200')
      logs.value = Array.isArray(data) ? data : []
    } catch (e: any) {
      console.warn('fetchLogs error:', e.message)
    }
  }
  
  async function clearLogs() {
    loading.value = true
    try {
      await api('/api/logs', { method: 'DELETE' })
      logs.value = []
      await fetchStats()
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }
  
  // Źródła
  async function fetchSources() {
    try {
      const data = await api<SourceStatus[]>('/api/sources')
      sources.value = Array.isArray(data) ? data : []
    } catch (e: any) {
      console.warn('fetchSources error:', e.message)
    }
  }
  
  async function toggleSource(name: string) {
    try {
      const updated = await api<SourceStatus>(`/api/sources/${name}/toggle`, {
        method: 'POST'
      })
      
      // Aktualizuj w liście
      const idx = sources.value.findIndex(s => s.name === name)
      if (idx !== -1) {
        sources.value[idx] = updated
      }
      
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }
  
  async function testSource(name: string) {
    try {
      const result = await api<{ success: boolean; error?: string; message?: string }>(
        `/api/sources/${name}/test`,
        { method: 'POST' }
      )
      return result
    } catch (e: any) {
      return { success: false, error: e.message }
    }
  }
  
  async function deleteSource(name: string) {
    try {
      await api(`/api/sources/${name}`, { method: 'DELETE' })
      sources.value = sources.value.filter(s => s.name !== name)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }
  
  async function addSource(name: string, config: any) {
    try {
      // Backend oczekuje pełnego obiektu z polem 'name'
      const payload = {
        name: name,
        ...config
      }
      
      const newSource = await api<SourceStatus>('/api/sources', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
      
      // Dodaj do listy
      sources.value.push(newSource)
      return true
    } catch (e: any) {
      error.value = e.message
      console.error('addSource error:', e)
      return false
    }
  }
  
  // Agent
  async function fetchAgentStatus() {
    try {
      agentStatus.value = await api<AgentStatus>('/api/agent/status')
    } catch (e: any) {
      console.warn('fetchAgentStatus error:', e.message)
    }
  }
  
  async function restartAgent() {
    try {
      await api('/api/agent/restart', { method: 'POST' })
      await fetchAgentStatus()
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }
  
  // Statystyki
  async function fetchStats() {
    try {
      stats.value = await api<Stats>('/api/stats')
    } catch (e: any) {
      console.warn('fetchStats error:', e.message)
    }
  }
  
  // ===== POLLING =====
  
  let pollInterval: number | null = null
  
  function startPolling(interval = 3000) {
    if (pollInterval) return
    
    // Pierwsze pobranie
    fetchLogs()
    fetchSources()
    fetchAgentStatus()
    fetchStats()
    
    pollInterval = window.setInterval(() => {
      fetchLogs()
      fetchSources()
      fetchAgentStatus()
      fetchStats()
    }, interval)
  }
  
  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }
  
  return {
    // State
    logs,
    sources,
    agentStatus,
    stats,
    loading,
    error,
    
    // Filters
    filterSource,
    filterEventType,
    filteredLogs,
    activeSources,
    
    // Actions
    fetchLogs,
    clearLogs,
    fetchSources,
    toggleSource,
    testSource,
    deleteSource,
    addSource,
    fetchAgentStatus,
    restartAgent,
    fetchStats,
    
    // Polling
    startPolling,
    stopPolling
  }
})
