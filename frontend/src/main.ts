import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

// Frontend Logger
import { logger, LoggerPlugin } from './services/logger'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Zainstaluj logger plugin (przechwytuje bledy Vue)
app.use(LoggerPlugin)

// Inicjalizuj logger
logger.init({
  interceptConsole: true,  // Przechwytuj console.log/warn/error
  flushIntervalMs: 3000,   // Wysylaj co 3 sekundy
  enabled: true            // Wlacz/wylacz
})

app.mount('#app')

// Loguj starty aplikacji
logger.info('Application started', { 
  component: 'App',
  url: window.location.href,
  userAgent: navigator.userAgent
})
