<template>
  <div class="min-h-screen bg-gray-900 text-white p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Statistics</h1>
      
      <!-- Jedyny przycisk Kibana -->
      <a 
        href="http://localhost:5601" 
        target="_blank"
        class="px-6 py-3 bg-pink-600 hover:bg-pink-700 rounded-lg flex items-center gap-2 font-semibold"
      >
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
        Open Kibana for Advanced Analytics
      </a>
    </div>
    
    <!-- Info box -->
    <div class="bg-blue-900/30 border border-blue-500/50 rounded-lg p-4 mb-6">
      <p class="text-blue-300">
        For advanced visualizations, dashboards, and detailed analytics use Kibana. 
        Below are basic statistics from your logs.
      </p>
    </div>
    
    <!-- Stats cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-gray-800 rounded-lg p-6">
        <div class="text-4xl font-bold text-blue-400">{{ stats.total }}</div>
        <div class="text-gray-400 mt-2">Total Logs</div>
      </div>
      <div class="bg-gray-800 rounded-lg p-6">
        <div class="text-4xl font-bold text-red-400">{{ stats.errors }}</div>
        <div class="text-gray-400 mt-2">Errors</div>
      </div>
      <div class="bg-gray-800 rounded-lg p-6">
        <div class="text-4xl font-bold text-yellow-400">{{ stats.warnings }}</div>
        <div class="text-gray-400 mt-2">Warnings</div>
      </div>
      <div class="bg-gray-800 rounded-lg p-6">
        <div class="text-4xl font-bold text-green-400">{{ stats.info }}</div>
        <div class="text-gray-400 mt-2">Info</div>
      </div>
    </div>
    
    <!-- Level distribution -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <div class="bg-gray-800 rounded-lg p-6">
        <h2 class="text-xl font-semibold mb-4">Log Levels Distribution</h2>
        <div class="space-y-4">
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-red-400">ERROR</span>
              <span>{{ stats.errors }} ({{ getPercent(stats.errors) }}%)</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-3">
              <div class="bg-red-500 h-3 rounded-full" :style="{ width: getPercent(stats.errors) + '%' }"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-yellow-400">WARNING</span>
              <span>{{ stats.warnings }} ({{ getPercent(stats.warnings) }}%)</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-3">
              <div class="bg-yellow-500 h-3 rounded-full" :style="{ width: getPercent(stats.warnings) + '%' }"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-blue-400">INFO</span>
              <span>{{ stats.info }} ({{ getPercent(stats.info) }}%)</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-3">
              <div class="bg-blue-500 h-3 rounded-full" :style="{ width: getPercent(stats.info) + '%' }"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-gray-400">DEBUG</span>
              <span>{{ stats.debug }} ({{ getPercent(stats.debug) }}%)</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-3">
              <div class="bg-gray-500 h-3 rounded-full" :style="{ width: getPercent(stats.debug) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Operations distribution -->
      <div class="bg-gray-800 rounded-lg p-6">
        <h2 class="text-xl font-semibold mb-4">Database Operations</h2>
        <div class="space-y-4">
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-green-400">SELECT</span>
              <span>{{ operations.select }} ({{ getOpPercent(operations.select) }}%)</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-3">
              <div class="bg-green-500 h-3 rounded-full" :style="{ width: getOpPercent(operations.select) + '%' }"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-blue-400">INSERT</span>
              <span>{{ operations.insert }} ({{ getOpPercent(operations.insert) }}%)</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-3">
              <div class="bg-blue-500 h-3 rounded-full" :style="{ width: getOpPercent(operations.insert) + '%' }"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-yellow-400">UPDATE</span>
              <span>{{ operations.update }} ({{ getOpPercent(operations.update) }}%)</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-3">
              <div class="bg-yellow-500 h-3 rounded-full" :style="{ width: getOpPercent(operations.update) + '%' }"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-red-400">DELETE</span>
              <span>{{ operations.delete }} ({{ getOpPercent(operations.delete) }}%)</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-3">
              <div class="bg-red-500 h-3 rounded-full" :style="{ width: getOpPercent(operations.delete) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Sources -->
    <div class="bg-gray-800 rounded-lg p-6">
      <h2 class="text-xl font-semibold mb-4">Logs by Source</h2>
      <div v-if="Object.keys(sourceCounts).length === 0" class="text-gray-500 text-center py-4">
        No sources with logs yet
      </div>
      <div v-else class="space-y-4">
        <div v-for="(count, source) in sourceCounts" :key="source">
          <div class="flex justify-between text-sm mb-1">
            <span class="text-purple-400">{{ source }}</span>
            <span>{{ count }} logs ({{ getSourcePercent(count) }}%)</span>
          </div>
          <div class="w-full bg-gray-700 rounded-full h-3">
            <div class="bg-purple-500 h-3 rounded-full" :style="{ width: getSourcePercent(count) + '%' }"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

interface Log {
  severity?: string
  level?: string
  event_type?: string
  operation?: string
  source?: string
  [key: string]: any
}

const logs = ref<Log[]>([])
const totalFromBackend = ref(0)
const refreshInterval = ref<number | null>(null)

const stats = computed(() => {
  // Uzywamy total z backendu (moze byc wiecej niz zwroconych logow)
  const total = Math.max(totalFromBackend.value, logs.value.length)
  const errors = logs.value.filter(l => (l.severity || l.level)?.toUpperCase() === 'ERROR').length
  const warnings = logs.value.filter(l => {
    const lvl = (l.severity || l.level || '').toUpperCase()
    return lvl === 'WARN' || lvl === 'WARNING'
  }).length
  const info = logs.value.filter(l => (l.severity || l.level)?.toUpperCase() === 'INFO').length
  const debug = logs.value.filter(l => (l.severity || l.level)?.toUpperCase() === 'DEBUG').length
  return { total, errors, warnings, info, debug }
})

const operations = computed(() => {
  const select = logs.value.filter(l => (l.event_type || l.operation || '').toUpperCase() === 'SELECT').length
  const insert = logs.value.filter(l => (l.event_type || l.operation || '').toUpperCase() === 'INSERT').length
  const update = logs.value.filter(l => (l.event_type || l.operation || '').toUpperCase() === 'UPDATE').length
  const del = logs.value.filter(l => (l.event_type || l.operation || '').toUpperCase() === 'DELETE').length
  return { select, insert, update, delete: del }
})

const sourceCounts = computed(() => {
  const counts: Record<string, number> = {}
  logs.value.forEach(log => {
    const source = log.source || 'unknown'
    counts[source] = (counts[source] || 0) + 1
  })
  return counts
})

const getPercent = (count: number) => {
  if (stats.value.total === 0) return 0
  return Math.round((count / stats.value.total) * 100)
}

const getOpPercent = (count: number) => {
  const total = operations.value.select + operations.value.insert + operations.value.update + operations.value.delete
  if (total === 0) return 0
  return Math.round((count / total) * 100)
}

const getSourcePercent = (count: number) => {
  if (stats.value.total === 0) return 0
  return Math.round((count / stats.value.total) * 100)
}

const fetchLogs = async () => {
  try {
    // Pobieramy wiecej logow dla statystyk (10000)
    const response = await fetch('http://localhost:8000/api/logs?limit=10000')
    const data = await response.json()
    logs.value = data.logs || []
    totalFromBackend.value = data.total || logs.value.length
  } catch (error) {
    console.error('Failed to fetch logs:', error)
  }
}

onMounted(() => {
  fetchLogs()
  // Auto-refresh co 5 sekund
  refreshInterval.value = window.setInterval(fetchLogs, 5000)
})

// Cleanup
onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>
