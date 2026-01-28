<template>
  <div class="min-h-screen bg-gray-900">
    <!-- Navigation -->
    <nav class="bg-gray-800 border-b border-gray-700">
      <div class="max-w-7xl mx-auto px-4">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-8">
            <div class="text-xl font-bold text-white flex items-center gap-2">
              <svg class="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              Log Manager
            </div>
            
            <div class="flex gap-1">
              <router-link to="/" 
                           class="px-4 py-2 rounded-lg transition"
                           :class="$route.path === '/' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'">
                <div class="flex items-center gap-2">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M4 6h16M4 10h16M4 14h16M4 18h16"/>
                  </svg>
                  Logs
                </div>
              </router-link>
              
              <router-link to="/stats" 
                           class="px-4 py-2 rounded-lg transition"
                           :class="$route.path === '/stats' ? 'bg-purple-600 text-white' : 'text-gray-300 hover:bg-gray-700'">
                <div class="flex items-center gap-2">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                  </svg>
                  Statistics
                </div>
              </router-link>
              
              <router-link to="/sources" 
                           class="px-4 py-2 rounded-lg transition"
                           :class="$route.path === '/sources' ? 'bg-green-600 text-white' : 'text-gray-300 hover:bg-gray-700'">
                <div class="flex items-center gap-2">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/>
                  </svg>
                  Sources
                </div>
              </router-link>
            </div>
          </div>
          
          <div class="flex items-center gap-4">
            <!-- ES Status indicator -->
            <div class="flex items-center gap-2 text-sm">
              <div :class="esConnected ? 'bg-green-500' : 'bg-red-500'" class="w-2 h-2 rounded-full"></div>
              <span class="text-gray-400">{{ esConnected ? 'Elasticsearch' : 'ES Offline' }}</span>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const API_URL = 'http://localhost:8000'
const esConnected = ref(false)

async function checkESStatus() {
  try {
    const response = await fetch(`${API_URL}/api/elasticsearch/status`)
    const data = await response.json()
    esConnected.value = data.connected
  } catch {
    esConnected.value = false
  }
}

onMounted(() => {
  checkESStatus()
  // Check every 10 seconds
  setInterval(checkESStatus, 10000)
})
</script>
