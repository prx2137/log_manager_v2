<template>
  <div class="min-h-screen bg-gray-900 text-white p-6">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-3xl font-bold text-green-400">Sources</h1>
        <p class="text-gray-400">Manage log sources</p>
      </div>
      <div class="flex gap-4">
        <a href="http://localhost:5601" target="_blank"
           class="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
          </svg>
          Open Kibana
        </a>
        <button @click="showAddModal = true" 
                class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Add Source
        </button>
      </div>
    </div>

    <!-- Sources List -->
    <div class="grid gap-4">
      <div v-for="source in sources" :key="source.name" 
           class="bg-gray-800 rounded-lg p-4 flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div :class="source.running ? 'bg-green-500' : 'bg-gray-500'" 
               class="w-3 h-3 rounded-full"></div>
          <div>
            <div class="font-semibold">{{ source.name }}</div>
            <div class="text-sm text-gray-400">{{ source.type }} | {{ source.logs_collected }} logs collected</div>
            <div v-if="source.last_error" class="text-sm text-red-400 mt-1">{{ source.last_error }}</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button @click="testSource(source.name)" 
                  class="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm">Test</button>
          <button @click="toggleSource(source.name)"
                  :class="source.running ? 'bg-yellow-600 hover:bg-yellow-700' : 'bg-green-600 hover:bg-green-700'"
                  class="px-3 py-1 rounded text-sm">
            {{ source.running ? 'Stop' : 'Start' }}
          </button>
          <button @click="deleteSource(source.name)"
                  class="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm">Delete</button>
        </div>
      </div>

      <div v-if="sources.length === 0" class="bg-gray-800 rounded-lg p-8 text-center text-gray-500">
        No sources configured. Click "Add Source" to get started.
      </div>
    </div>

    <!-- Add Source Modal -->
    <div v-if="showAddModal" class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <h2 class="text-xl font-bold mb-4">Add New Source</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-1">Name</label>
            <input v-model="newSource.name" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                   placeholder="my-source">
          </div>
          
          <div>
            <label class="block text-sm text-gray-400 mb-1">Type</label>
            <select v-model="newSource.type" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              <option value="file">File</option>
              <option value="mysql">MySQL</option>
              <option value="mongodb">MongoDB Atlas</option>
            </select>
          </div>

          <!-- File fields -->
          <div v-if="newSource.type === 'file'" class="space-y-4">
            <div>
              <label class="block text-sm text-gray-400 mb-1">File Path</label>
              <div class="flex gap-2">
                <input v-model="newSource.path" 
                       placeholder="C:\Users\username\logs\app.log"
                       class="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 font-mono text-sm">
                <button @click="browseFile" 
                        class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded flex items-center gap-2">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                  </svg>
                  Browse
                </button>
              </div>
              <p class="text-xs text-gray-500 mt-1">
                Windows: Use full path like C:\Users\grac0\Desktop\new.log
              </p>
              <p class="text-xs text-yellow-500 mt-1">
                Note: You can also paste the path directly - backslashes are handled automatically.
              </p>
            </div>
            
            <!-- File browser dialog (hidden input) -->
            <input type="file" ref="fileInput" @change="onFileSelected" class="hidden">
          </div>

          <!-- MySQL fields -->
          <template v-if="newSource.type === 'mysql'">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">Host</label>
                <input v-model="newSource.host" placeholder="localhost"
                       class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">Port</label>
                <input v-model.number="newSource.port" type="number" placeholder="3306"
                       class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">User</label>
                <input v-model="newSource.user" placeholder="root"
                       class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">Password</label>
                <input v-model="newSource.password" type="password"
                       class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              </div>
            </div>
            <div>
              <label class="block text-sm text-gray-400 mb-1">Database</label>
              <input v-model="newSource.database" placeholder="laravel"
                     class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
            </div>
            <div class="bg-blue-900 bg-opacity-30 border border-blue-700 rounded p-3 text-sm">
              <p class="text-blue-300 font-medium mb-1">MySQL general_log must be enabled:</p>
              <code class="text-xs text-gray-300">SET GLOBAL general_log = 'ON';<br>SET GLOBAL log_output = 'TABLE';</code>
            </div>
          </template>

          <!-- MongoDB Atlas fields -->
          <template v-if="newSource.type === 'mongodb'">
            <div class="bg-green-900 bg-opacity-30 border border-green-700 rounded p-3 text-sm mb-4">
              <p class="text-green-300 font-medium">MongoDB Atlas Connection</p>
              <p class="text-gray-400 text-xs mt-1">Get your connection string from MongoDB Atlas dashboard</p>
            </div>
            
            <div>
              <label class="block text-sm text-gray-400 mb-1">Connection String (URI)</label>
              <input v-model="newSource.uri" 
                     placeholder="mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?appName=myapp"
                     class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 font-mono text-xs">
              <p class="text-xs text-gray-500 mt-1">Full connection string from Atlas (includes username and password)</p>
            </div>
            
            <div class="text-center text-gray-500 text-sm my-2">- OR enter separately -</div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">Username</label>
                <input v-model="newSource.mongoUser" placeholder="myuser"
                       class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">Password</label>
                <input v-model="newSource.mongoPassword" type="password"
                       class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              </div>
            </div>
            
            <div>
              <label class="block text-sm text-gray-400 mb-1">Cluster Host</label>
              <input v-model="newSource.clusterHost" placeholder="logmanager.nivuikh.mongodb.net"
                     class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              <p class="text-xs text-gray-500 mt-1">From Atlas: cluster-name.xxxxx.mongodb.net</p>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">Database</label>
                <input v-model="newSource.database" placeholder="logs"
                       class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">Collection (optional)</label>
                <input v-model="newSource.collection" placeholder="app_logs"
                       class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
              </div>
            </div>
            
            <div>
              <label class="block text-sm text-gray-400 mb-1">App Name (optional)</label>
              <input v-model="newSource.appName" placeholder="logmanager"
                     class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
            </div>
          </template>
        </div>

        <div v-if="addError" class="mt-4 bg-red-900 bg-opacity-50 border border-red-700 rounded p-3 text-red-300 text-sm">
          {{ addError }}
        </div>

        <div class="flex justify-end gap-4 mt-6">
          <button @click="closeModal" 
                  class="px-4 py-2 text-gray-400 hover:text-white">Cancel</button>
          <button @click="addSource" 
                  :disabled="isAdding"
                  class="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-4 py-2 rounded">
            {{ isAdding ? 'Adding...' : 'Add Source' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Test Result Toast -->
    <div v-if="testResult" 
         :class="testResult.success ? 'bg-green-600' : 'bg-red-600'"
         class="fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg max-w-md">
      {{ testResult.message || testResult.error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

interface Source {
  name: string
  type: string
  enabled: boolean
  running: boolean
  logs_collected: number
  last_error?: string
}

const API_URL = 'http://localhost:8000'

const sources = ref<Source[]>([])
const showAddModal = ref(false)
const testResult = ref<{ success: boolean; message?: string; error?: string } | null>(null)
const addError = ref('')
const isAdding = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const newSource = ref({
  name: '',
  type: 'mysql',
  path: '',
  host: 'localhost',
  port: 3306,
  user: 'root',
  password: '',
  database: '',
  uri: '',
  collection: '',
  mongoUser: '',
  mongoPassword: '',
  clusterHost: '',
  appName: ''
})

function resetNewSource() {
  newSource.value = {
    name: '',
    type: 'mysql',
    path: '',
    host: 'localhost',
    port: 3306,
    user: 'root',
    password: '',
    database: '',
    uri: '',
    collection: '',
    mongoUser: '',
    mongoPassword: '',
    clusterHost: '',
    appName: ''
  }
  addError.value = ''
}

function closeModal() {
  showAddModal.value = false
  resetNewSource()
}

async function loadSources() {
  try {
    const response = await fetch(`${API_URL}/api/sources`)
    sources.value = await response.json()
  } catch (error) {
    console.error('Error loading sources:', error)
  }
}

function browseFile() {
  // Trigger the hidden file input
  fileInput.value?.click()
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    // Browser security only gives us the filename, not full path
    // We need to inform the user to paste the full path manually
    const filename = input.files[0].name
    addError.value = `Browser security prevents getting full path. Please paste the full path manually (e.g., C:\\Users\\grac0\\Desktop\\${filename})`
  }
}

async function addSource() {
  addError.value = ''
  isAdding.value = true
  
  try {
    // Build the source config based on type
    const sourceConfig: any = {
      name: newSource.value.name,
      type: newSource.value.type
    }
    
    if (newSource.value.type === 'file') {
      if (!newSource.value.path) {
        addError.value = 'File path is required'
        isAdding.value = false
        return
      }
      sourceConfig.path = newSource.value.path
    } 
    else if (newSource.value.type === 'mysql') {
      sourceConfig.host = newSource.value.host
      sourceConfig.port = newSource.value.port
      sourceConfig.user = newSource.value.user
      sourceConfig.password = newSource.value.password
      sourceConfig.database = newSource.value.database
    } 
    else if (newSource.value.type === 'mongodb') {
      // Build URI if not provided directly
      if (newSource.value.uri) {
        sourceConfig.uri = newSource.value.uri
      } else if (newSource.value.mongoUser && newSource.value.mongoPassword && newSource.value.clusterHost) {
        // Build MongoDB Atlas SRV connection string
        let uri = `mongodb+srv://${encodeURIComponent(newSource.value.mongoUser)}:${encodeURIComponent(newSource.value.mongoPassword)}@${newSource.value.clusterHost}/`
        if (newSource.value.database) {
          uri += newSource.value.database
        }
        uri += '?retryWrites=true&w=majority'
        if (newSource.value.appName) {
          uri += `&appName=${newSource.value.appName}`
        }
        sourceConfig.uri = uri
      } else {
        addError.value = 'Please provide either full URI or username/password/cluster host'
        isAdding.value = false
        return
      }
      
      sourceConfig.database = newSource.value.database
      sourceConfig.collection = newSource.value.collection
    }
    
    const response = await fetch(`${API_URL}/api/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sourceConfig)
    })
    
    const result = await response.json()
    
    if (response.ok) {
      closeModal()
      loadSources()
    } else {
      addError.value = result.detail || result.error || 'Failed to add source'
    }
  } catch (error) {
    addError.value = `Connection error: ${error}`
  }
  
  isAdding.value = false
}

async function testSource(name: string) {
  try {
    const response = await fetch(`${API_URL}/api/sources/${name}/test`, { method: 'POST' })
    testResult.value = await response.json()
    setTimeout(() => { testResult.value = null }, 5000)
  } catch (error) {
    testResult.value = { success: false, error: 'Connection failed' }
    setTimeout(() => { testResult.value = null }, 5000)
  }
}

async function toggleSource(name: string) {
  try {
    await fetch(`${API_URL}/api/sources/${name}/toggle`, { method: 'POST' })
    loadSources()
  } catch (error) {
    console.error('Error toggling source:', error)
  }
}

async function deleteSource(name: string) {
  if (!confirm(`Delete source "${name}"?`)) return
  try {
    await fetch(`${API_URL}/api/sources/${name}`, { method: 'DELETE' })
    loadSources()
  } catch (error) {
    console.error('Error deleting source:', error)
  }
}

onMounted(loadSources)
</script>
