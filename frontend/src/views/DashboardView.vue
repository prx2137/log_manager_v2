<template>
  <div class="min-h-screen bg-gray-900 text-white p-6">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Log Dashboard</h1>
      
      <div class="flex items-center gap-4">
        <!-- Auto-refresh toggle -->
        <label class="flex items-center gap-2 cursor-pointer">
          <span class="text-sm text-gray-400">Auto-refresh</span>
          <div class="relative">
            <input 
              type="checkbox" 
              v-model="autoRefresh"
              class="sr-only"
            >
            <div 
              :class="[
                'w-10 h-6 rounded-full transition-colors',
                autoRefresh ? 'bg-green-500' : 'bg-gray-600'
              ]"
              @click="autoRefresh = !autoRefresh"
            >
              <div 
                :class="[
                  'w-4 h-4 bg-white rounded-full absolute top-1 transition-transform',
                  autoRefresh ? 'translate-x-5' : 'translate-x-1'
                ]"
              ></div>
            </div>
          </div>
        </label>
        
        <!-- Manual refresh -->
        <button 
          @click="refreshLogs"
          :disabled="loading"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg flex items-center gap-2"
        >
          <svg 
            :class="['w-4 h-4', loading ? 'animate-spin' : '']" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
        
        <!-- Reset logs -->
        <button 
          @click="confirmResetLogs"
          class="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg"
        >
          Reset Logs
        </button>
      </div>
    </div>
    
    <!-- Stats Cards -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <div class="bg-gray-800 rounded-lg p-4">
        <div class="text-2xl font-bold">{{ stats.total }}</div>
        <div class="text-gray-400 text-sm">Total Logs</div>
      </div>
      <div class="bg-red-900/30 rounded-lg p-4">
        <div class="text-2xl font-bold text-red-400">{{ stats.errors }}</div>
        <div class="text-gray-400 text-sm">Errors</div>
      </div>
      <div class="bg-yellow-900/30 rounded-lg p-4">
        <div class="text-2xl font-bold text-yellow-400">{{ stats.warnings }}</div>
        <div class="text-gray-400 text-sm">Warnings</div>
      </div>
      <div class="bg-blue-900/30 rounded-lg p-4">
        <div class="text-2xl font-bold text-blue-400">{{ stats.info }}</div>
        <div class="text-gray-400 text-sm">Info</div>
      </div>
    </div>
    
    <!-- Filters -->
    <div class="bg-gray-800 rounded-lg p-4 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <input 
          v-model="filters.search"
          type="text"
          placeholder="Search logs..."
          class="bg-gray-700 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @keyup.enter="applyFilters"
        >
        
        <select 
          v-model="filters.severity"
          class="bg-gray-700 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="applyFilters"
        >
          <option value="">All Severities</option>
          <option value="ERROR">ERROR</option>
          <option value="WARNING">WARNING</option>
          <option value="WARN">WARN</option>
          <option value="INFO">INFO</option>
          <option value="DEBUG">DEBUG</option>
        </select>
        
        <select 
          v-model="filters.event_type"
          class="bg-gray-700 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="applyFilters"
        >
          <option value="">All Event Types</option>
          <option value="SELECT">SELECT</option>
          <option value="INSERT">INSERT</option>
          <option value="UPDATE">UPDATE</option>
          <option value="DELETE">DELETE</option>
          <option value="LOG">LOG</option>
          <option value="INITIAL_LOAD">INITIAL_LOAD</option>
        </select>
        
        <select 
          v-model="filters.source"
          class="bg-gray-700 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="applyFilters"
        >
          <option value="">All Sources</option>
          <option v-for="source in availableSources" :key="source" :value="source">{{ source }}</option>
        </select>
        
        <!-- Page size selector -->
        <select 
          v-model="pageSize"
          class="bg-gray-700 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          @change="changePageSize"
        >
          <option :value="25">25 per page</option>
          <option :value="50">50 per page</option>
          <option :value="100">100 per page</option>
          <option :value="200">200 per page</option>
        </select>
      </div>
    </div>
    
    <!-- Pagination Top -->
    <div class="flex justify-between items-center mb-4">
      <div class="text-gray-400 text-sm">
        Showing {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, totalLogs) }} of {{ totalLogs }} logs
        <span v-if="totalAllLogs !== totalLogs" class="ml-2">({{ totalAllLogs }} total)</span>
      </div>
      
      <div class="flex items-center gap-2">
        <button 
          @click="goToPage(1)"
          :disabled="currentPage === 1"
          class="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded"
        >
          First
        </button>
        <button 
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage === 1"
          class="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded"
        >
          Prev
        </button>
        
        <!-- Page numbers -->
        <template v-for="page in visiblePages" :key="page">
          <button 
            v-if="page !== '...'"
            @click="goToPage(page as number)"
            :class="[
              'px-3 py-1 rounded',
              page === currentPage ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
            ]"
          >
            {{ page }}
          </button>
          <span v-else class="px-2 text-gray-500">...</span>
        </template>
        
        <button 
          @click="goToPage(currentPage + 1)"
          :disabled="currentPage === totalPages"
          class="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded"
        >
          Next
        </button>
        <button 
          @click="goToPage(totalPages)"
          :disabled="currentPage === totalPages"
          class="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 rounded"
        >
          Last
        </button>
      </div>
    </div>
    
    <!-- Logs Table -->
    <div class="bg-gray-800 rounded-lg overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="bg-gray-700">
            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Time</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Severity</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Event Type</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Source</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Message</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="logItem in logs" 
            :key="logItem.id || logItem.timestamp"
            @click="showLogDetail(logItem)"
            class="border-t border-gray-700 hover:bg-gray-700/50 cursor-pointer"
          >
            <td class="px-4 py-3 text-sm text-gray-300 whitespace-nowrap">
              {{ formatTime(logItem.timestamp) }}
            </td>
            <td class="px-4 py-3">
              <span :class="getLevelClass(logItem.severity || logItem.level || '')">
                {{ (logItem.severity || logItem.level || 'INFO').toUpperCase() }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm text-gray-300">
              {{ logItem.event_type || logItem.operation || '-' }}
            </td>
            <td class="px-4 py-3 text-sm text-gray-300">
              {{ logItem.source || 'unknown' }}
            </td>
            <td class="px-4 py-3 text-sm text-gray-300 truncate max-w-md">
              {{ logItem.message || logItem.raw_line || '-' }}
            </td>
          </tr>
          <tr v-if="logs.length === 0">
            <td colspan="5" class="px-4 py-8 text-center text-gray-500">
              <div v-if="loading">Loading...</div>
              <div v-else>No logs found. Try adjusting filters or adding log sources.</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Pagination Bottom -->
    <div class="flex justify-between items-center mt-4">
      <div class="text-gray-400 text-sm">
        Page {{ currentPage }} of {{ totalPages }}
      </div>
      
      <div class="flex items-center gap-2">
        <span class="text-gray-400 text-sm mr-2">Go to page:</span>
        <input 
          type="number" 
          v-model.number="jumpToPage"
          @keyup.enter="goToPage(jumpToPage)"
          min="1"
          :max="totalPages"
          class="w-20 bg-gray-700 rounded px-3 py-1 text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
        <button 
          @click="goToPage(jumpToPage)"
          class="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded"
        >
          Go
        </button>
      </div>
    </div>
    
    <!-- Log Detail Modal -->
    <div v-if="selectedLog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="selectedLog = null">
      <div class="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Log Details</h2>
          <button @click="selectedLog = null" class="text-gray-400 hover:text-white">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div class="space-y-4">
          <div>
            <h3 class="text-sm font-semibold text-gray-400 mb-1">Timestamp</h3>
            <p class="text-white">{{ selectedLog.timestamp }}</p>
          </div>
          
          <div class="grid grid-cols-2 gap-4">
            <div>
              <h3 class="text-sm font-semibold text-gray-400 mb-1">Severity</h3>
              <span :class="getLevelClass(selectedLog.severity || selectedLog.level || '')">
                {{ (selectedLog.severity || selectedLog.level || 'INFO').toUpperCase() }}
              </span>
            </div>
            
            <div>
              <h3 class="text-sm font-semibold text-gray-400 mb-1">Source Type</h3>
              <p class="text-white">{{ selectedLog.source_type || 'unknown' }}</p>
            </div>
          </div>
          
          <div>
            <h3 class="text-sm font-semibold text-gray-400 mb-1">Source</h3>
            <p class="text-white">{{ selectedLog.source || 'unknown' }}</p>
          </div>
          
          <div v-if="selectedLog.event_type || selectedLog.operation">
            <h3 class="text-sm font-semibold text-gray-400 mb-1">Event Type</h3>
            <p class="text-white">{{ selectedLog.event_type || selectedLog.operation }}</p>
          </div>
          
          <div>
            <h3 class="text-sm font-semibold text-gray-400 mb-1">Message</h3>
            <p class="text-white whitespace-pre-wrap">{{ selectedLog.message }}</p>
          </div>
          
          <div v-if="selectedLog.raw_line">
            <h3 class="text-sm font-semibold text-gray-400 mb-1">Raw Data</h3>
            <pre class="bg-gray-900 p-3 rounded text-sm text-gray-300 overflow-x-auto">{{ selectedLog.raw_line }}</pre>
          </div>
          
          <div>
            <h3 class="text-sm font-semibold text-gray-400 mb-1">Full JSON</h3>
            <pre class="bg-gray-900 p-3 rounded text-sm text-gray-300 overflow-x-auto">{{ JSON.stringify(selectedLog, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Reset confirmation modal -->
    <div v-if="showResetConfirm" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
        <h2 class="text-xl font-bold mb-4">Reset All Logs?</h2>
        <p class="text-gray-400 mb-6">This will permanently delete all logs from memory and Elasticsearch. This action cannot be undone.</p>
        <div class="flex gap-4 justify-end">
          <button @click="showResetConfirm = false" class="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg">Cancel</button>
          <button @click="resetLogs" class="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg">Delete All</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useLogger } from '../services/logger'

// Logger dla tego komponentu
const log = useLogger('DashboardView')

interface Log {
  id: string
  timestamp: string
  severity?: string
  level?: string
  source?: string
  source_type?: string
  event_type?: string
  operation?: string
  message?: string
  raw_line?: string
  [key: string]: any
}

// Data
const logs = ref<Log[]>([])
const totalLogs = ref(0)
const totalAllLogs = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const totalPages = ref(1)
const loading = ref(false)
const autoRefresh = ref(false)
const selectedLog = ref<Log | null>(null)
const showResetConfirm = ref(false)
const availableSources = ref<string[]>([])
const jumpToPage = ref(1)

const filters = ref({
  search: '',
  severity: '',
  event_type: '',
  source: ''
})

let refreshInterval: number | null = null

// Computed
const stats = computed(() => {
  const total = totalAllLogs.value
  const errors = logs.value.filter(l => (l.severity || l.level)?.toUpperCase() === 'ERROR').length
  const warnings = logs.value.filter(l => ['WARN', 'WARNING'].includes((l.severity || l.level || '').toUpperCase())).length
  const info = logs.value.filter(l => (l.severity || l.level)?.toUpperCase() === 'INFO').length
  return { total, errors, warnings, info }
})

const visiblePages = computed(() => {
  const pages: (number | string)[] = []
  const total = totalPages.value
  const current = currentPage.value
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    
    if (current > 3) pages.push('...')
    
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
      pages.push(i)
    }
    
    if (current < total - 2) pages.push('...')
    
    pages.push(total)
  }
  
  return pages
})

// Methods
const formatTime = (timestamp: string) => {
  if (!timestamp) return '-'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('pl-PL', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      day: '2-digit',
      month: '2-digit'
    })
  } catch {
    return timestamp
  }
}

const getLevelClass = (level: string) => {
  const l = (level || '').toUpperCase()
  switch (l) {
    case 'ERROR': 
    case 'CRITICAL':
      return 'px-2 py-1 rounded text-xs font-semibold bg-red-500/20 text-red-400'
    case 'WARN':
    case 'WARNING': 
      return 'px-2 py-1 rounded text-xs font-semibold bg-yellow-500/20 text-yellow-400'
    case 'INFO': 
      return 'px-2 py-1 rounded text-xs font-semibold bg-blue-500/20 text-blue-400'
    case 'DEBUG': 
      return 'px-2 py-1 rounded text-xs font-semibold bg-gray-500/20 text-gray-400'
    default: 
      return 'px-2 py-1 rounded text-xs font-semibold bg-gray-500/20 text-gray-400'
  }
}

const buildApiUrl = () => {
  const params = new URLSearchParams()
  params.append('page', currentPage.value.toString())
  params.append('page_size', pageSize.value.toString())
  
  if (filters.value.search) params.append('query', filters.value.search)
  if (filters.value.severity) params.append('severity', filters.value.severity)
  if (filters.value.event_type) params.append('event_type', filters.value.event_type)
  if (filters.value.source) params.append('source', filters.value.source)
  
  return `http://localhost:8000/api/logs?${params.toString()}`
}

const refreshLogs = async () => {
  loading.value = true
  try {
    const url = buildApiUrl()
    const response = await fetch(url)
    const data = await response.json()
    
    logs.value = data.logs || []
    totalLogs.value = data.total || 0
    totalAllLogs.value = data.total_all || data.total || 0
    totalPages.value = data.total_pages || 1
    currentPage.value = data.page || 1
    
    // Extract unique sources from current logs AND fetch configured sources
    const uniqueSources = new Set<string>()
    
    // Add sources from current logs
    ;(data.logs || []).forEach((logItem: Log) => {
      if (logItem.source) uniqueSources.add(logItem.source)
    })
    
    // Also fetch configured sources from API
    try {
      const sourcesResponse = await fetch('http://localhost:8000/api/sources')
      const configuredSources = await sourcesResponse.json()
      ;(configuredSources || []).forEach((src: { name: string }) => {
        if (src.name) uniqueSources.add(src.name)
      })
    } catch (e) {
      // Ignore errors fetching sources
    }
    
    availableSources.value = Array.from(uniqueSources).sort()
    
    log.debug('Logs refreshed', { 
      count: logs.value.length, 
      total: totalLogs.value,
      page: currentPage.value,
      totalPages: totalPages.value
    })
  } catch (error) {
    log.error('Failed to fetch logs', { error: String(error) }, error as Error)
  } finally {
    loading.value = false
  }
}

const goToPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  jumpToPage.value = page
  refreshLogs()
}

const changePageSize = () => {
  currentPage.value = 1
  refreshLogs()
}

const applyFilters = () => {
  currentPage.value = 1
  refreshLogs()
}

const showLogDetail = (logItem: Log) => {
  selectedLog.value = logItem
}

const confirmResetLogs = () => {
  showResetConfirm.value = true
}

const resetLogs = async () => {
  try {
    log.info('Resetting all logs')
    await fetch('http://localhost:8000/api/logs', { method: 'DELETE' })
    logs.value = []
    totalLogs.value = 0
    totalAllLogs.value = 0
    currentPage.value = 1
    totalPages.value = 1
    showResetConfirm.value = false
    log.info('Logs reset complete')
  } catch (error) {
    log.error('Failed to reset logs', { error: String(error) }, error as Error)
  }
}

// Watchers
watch(autoRefresh, (enabled) => {
  if (enabled) {
    log.info('Auto-refresh enabled', { interval: 3000 })
    refreshInterval = window.setInterval(refreshLogs, 3000)
  } else if (refreshInterval) {
    log.info('Auto-refresh disabled')
    clearInterval(refreshInterval)
    refreshInterval = null
  }
})

// Lifecycle
onMounted(() => {
  log.info('Dashboard mounted')
  refreshLogs()
})

onUnmounted(() => {
  log.debug('Dashboard unmounted')
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>
