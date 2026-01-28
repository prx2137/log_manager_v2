/**
 * Frontend Logger Service
 * Przechwytuje logi z Vue i wysyla je do backendu
 */

interface FrontendLog {
  level: 'debug' | 'info' | 'warn' | 'error'
  message: string
  context?: Record<string, any>
  component?: string
  stack?: string
}

class FrontendLogger {
  private apiUrl = 'http://localhost:8000/api/logs/frontend'
  private buffer: FrontendLog[] = []
  private flushInterval: number | null = null
  private enabled = true
  private consoleOriginals: {
    log: typeof console.log
    info: typeof console.info
    warn: typeof console.warn
    error: typeof console.error
  }

  constructor() {
    // Zachowaj oryginalne metody console
    this.consoleOriginals = {
      log: console.log.bind(console),
      info: console.info.bind(console),
      warn: console.warn.bind(console),
      error: console.error.bind(console)
    }
  }

  /**
   * Inicjalizuje logger - wywolaj w main.ts
   */
  init(options?: { 
    interceptConsole?: boolean
    flushIntervalMs?: number 
    enabled?: boolean
  }) {
    const { 
      interceptConsole = true, 
      flushIntervalMs = 3000,
      enabled = true 
    } = options || {}

    this.enabled = enabled

    if (!this.enabled) return

    // Przechwytuj console.* jesli wlaczone
    if (interceptConsole) {
      this.interceptConsoleMethods()
    }

    // Przechwytuj nieobsluzone bledy
    this.setupErrorHandlers()

    // Wysylaj bufor co X ms
    this.flushInterval = window.setInterval(() => {
      this.flush()
    }, flushIntervalMs)

    this.info('Frontend logger initialized', { component: 'Logger' })
  }

  /**
   * Zatrzymuje logger
   */
  destroy() {
    if (this.flushInterval) {
      clearInterval(this.flushInterval)
    }
    this.restoreConsoleMethods()
    this.flush()
  }

  /**
   * Metody logowania
   */
  debug(message: string, context?: Record<string, any>) {
    this.log('debug', message, context)
  }

  info(message: string, context?: Record<string, any>) {
    this.log('info', message, context)
  }

  warn(message: string, context?: Record<string, any>) {
    this.log('warn', message, context)
  }

  error(message: string, context?: Record<string, any>, error?: Error) {
    this.log('error', message, {
      ...context,
      stack: error?.stack
    })
  }

  /**
   * Logowanie z komponentu Vue (helper)
   */
  component(componentName: string) {
    return {
      debug: (msg: string, ctx?: Record<string, any>) => 
        this.log('debug', msg, { ...ctx, component: componentName }),
      info: (msg: string, ctx?: Record<string, any>) => 
        this.log('info', msg, { ...ctx, component: componentName }),
      warn: (msg: string, ctx?: Record<string, any>) => 
        this.log('warn', msg, { ...ctx, component: componentName }),
      error: (msg: string, ctx?: Record<string, any>, err?: Error) => 
        this.log('error', msg, { ...ctx, component: componentName, stack: err?.stack })
    }
  }

  /**
   * Glowna metoda logowania
   */
  private log(level: FrontendLog['level'], message: string, context?: Record<string, any>) {
    if (!this.enabled) return

    const logEntry: FrontendLog = {
      level,
      message,
      context,
      component: context?.component
    }

    // Dodaj do bufora
    this.buffer.push(logEntry)

    // Wyswietl w konsoli (uzywajac oryginalnych metod)
    const consoleMethod = this.consoleOriginals[level === 'debug' ? 'log' : level]
    consoleMethod(`[${level.toUpperCase()}]`, message, context || '')

    // Natychmiast wyslij bledy
    if (level === 'error') {
      this.flush()
    }
  }

  /**
   * Wysyla bufor do backendu
   */
  private async flush() {
    if (this.buffer.length === 0) return

    const logsToSend = [...this.buffer]
    this.buffer = []

    try {
      await fetch(this.apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ logs: logsToSend })
      })
    } catch (err) {
      // Nie loguj bledu wysylania - unikamy petli
      this.consoleOriginals.error('Failed to send logs to backend:', err)
      // Zwroc logi do bufora
      this.buffer = [...logsToSend, ...this.buffer]
    }
  }

  /**
   * Przechwytuje metody console.*
   */
  private interceptConsoleMethods() {
    console.log = (...args: any[]) => {
      this.consoleOriginals.log(...args)
      if (this.shouldCapture(args)) {
        this.buffer.push({
          level: 'debug',
          message: this.formatArgs(args),
          context: { source: 'console.log' }
        })
      }
    }

    console.info = (...args: any[]) => {
      this.consoleOriginals.info(...args)
      if (this.shouldCapture(args)) {
        this.buffer.push({
          level: 'info',
          message: this.formatArgs(args),
          context: { source: 'console.info' }
        })
      }
    }

    console.warn = (...args: any[]) => {
      this.consoleOriginals.warn(...args)
      if (this.shouldCapture(args)) {
        this.buffer.push({
          level: 'warn',
          message: this.formatArgs(args),
          context: { source: 'console.warn' }
        })
      }
    }

    console.error = (...args: any[]) => {
      this.consoleOriginals.error(...args)
      if (this.shouldCapture(args)) {
        this.buffer.push({
          level: 'error',
          message: this.formatArgs(args),
          context: { source: 'console.error' }
        })
      }
    }
  }

  /**
   * Przywraca oryginalne metody console
   */
  private restoreConsoleMethods() {
    console.log = this.consoleOriginals.log
    console.info = this.consoleOriginals.info
    console.warn = this.consoleOriginals.warn
    console.error = this.consoleOriginals.error
  }

  /**
   * Czy przechwycic ten log (filtruje wlasne logi)
   */
  private shouldCapture(args: any[]): boolean {
    const firstArg = String(args[0] || '')
    // Nie przechwytuj logow z tego loggera
    if (firstArg.startsWith('[DEBUG]') || 
        firstArg.startsWith('[INFO]') || 
        firstArg.startsWith('[WARN]') || 
        firstArg.startsWith('[ERROR]')) {
      return false
    }
    return true
  }

  /**
   * Formatuje argumenty do stringa
   */
  private formatArgs(args: any[]): string {
    return args.map(arg => {
      if (typeof arg === 'object') {
        try {
          return JSON.stringify(arg)
        } catch {
          return String(arg)
        }
      }
      return String(arg)
    }).join(' ')
  }

  /**
   * Ustawia globalne handlery bledow
   */
  private setupErrorHandlers() {
    // Nieobsluzone bledy JS
    window.addEventListener('error', (event) => {
      this.buffer.push({
        level: 'error',
        message: event.message || 'Unknown error',
        context: {
          source: 'window.onerror',
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno
        },
        stack: event.error?.stack
      })
      this.flush()
    })

    // Nieobsluzone Promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.buffer.push({
        level: 'error',
        message: `Unhandled Promise Rejection: ${event.reason}`,
        context: {
          source: 'unhandledrejection',
          reason: String(event.reason)
        },
        stack: event.reason?.stack
      })
      this.flush()
    })
  }
}

// Singleton instance
export const logger = new FrontendLogger()

// Vue plugin
export const LoggerPlugin = {
  install(app: any) {
    // Globalny error handler Vue
    app.config.errorHandler = (err: Error, instance: any, info: string) => {
      logger.error(`Vue Error: ${err.message}`, {
        component: instance?.$options?.name || 'Unknown',
        info,
        source: 'vue.errorHandler'
      }, err)
    }

    // Warning handler (tylko dev)
    app.config.warnHandler = (msg: string, instance: any, trace: string) => {
      logger.warn(`Vue Warning: ${msg}`, {
        component: instance?.$options?.name || 'Unknown',
        trace,
        source: 'vue.warnHandler'
      })
    }

    // Udostepnij logger globalnie
    app.config.globalProperties.$logger = logger
    app.provide('logger', logger)
  }
}

// Composable do uzycia w komponentach
export function useLogger(componentName?: string) {
  if (componentName) {
    return logger.component(componentName)
  }
  return logger
}
