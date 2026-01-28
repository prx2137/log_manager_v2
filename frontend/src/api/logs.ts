/**
 * Types - Typy dla Log Managera z Smart Parser
 */

// =====================================================
// LOG ENTRY
// =====================================================

export interface LogEntry {
  id: string;
  source: string;
  message: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  
  // Smart Parser fields
  event_type: string;
  event_category: string;
  severity: number;
  
  // Database operations
  table_name?: string;
  query?: string;
  affected_rows?: number;
  
  // HTTP
  http_method?: string;
  http_path?: string;
  http_status?: number;
  
  // Metadata
  user_id?: string;
  ip_address?: string;
  duration_ms?: number;
  
  // Extra
  extra_data?: Record<string, any>;
  raw_data?: Record<string, any>;
}

// =====================================================
// SOURCE
// =====================================================

export interface SourceStats {
  total: number;
  by_type: Record<string, number>;
  by_category: Record<string, number>;
  by_severity: {
    info: number;
    warning: number;
    error: number;
    critical: number;
  };
  by_table: Record<string, number>;
  summary: {
    errors: number;
    warnings: number;
    inserts: number;
    updates: number;
    deletes: number;
    selects: number;
  };
}

export interface Source {
  name: string;
  type: 'file' | 'mysql' | 'mongodb' | 'command';
  enabled: boolean;
  last_read?: string;
  logs_count?: number;
  stats?: SourceStats;
  config?: Record<string, any>;
}

// =====================================================
// GLOBAL STATS
// =====================================================

export interface GlobalStats {
  total: number;
  by_source: Record<string, number>;
  by_event_type: Record<string, number>;
  by_category: Record<string, number>;
  by_level: Record<string, number>;
  by_table: Record<string, number>;
  by_severity: {
    info: number;
    warning: number;
    error: number;
    critical: number;
  };
  summary: {
    errors: number;
    warnings: number;
    inserts: number;
    updates: number;
    deletes: number;
  };
  cache_size: number;
}

// =====================================================
// TIMELINE
// =====================================================

export interface TimelinePoint {
  timestamp: string;
  total: number;
  errors: number;
  warnings: number;
  inserts: number;
  updates: number;
  deletes: number;
}

export interface TimelineData {
  hours: number;
  source?: string;
  timeline: TimelinePoint[];
}

// =====================================================
// AGENT
// =====================================================

export interface AgentStatus {
  running: boolean;
  sources_count: number;
  sources_enabled: number;
  logs_in_cache: number;
  check_interval: number;
}

// =====================================================
// ELASTICSEARCH
// =====================================================

export interface ElasticsearchStatus {
  enabled: boolean;
  connected: boolean;
  details?: {
    cluster_name?: string;
    status?: string;
    number_of_nodes?: number;
    indices_count?: number;
    total_documents?: number;
  };
}

export interface ElasticsearchStats {
  total: number;
  by_event_type: Record<string, number>;
  by_category: Record<string, number>;
  by_source: Record<string, number>;
  by_level: Record<string, number>;
  by_table: Record<string, number>;
  by_severity: Record<string, number>;
  by_http_status: Record<string, number>;
  timeline: Array<{
    timestamp: string;
    count: number;
    by_type: Record<string, number>;
  }>;
  avg_duration_ms?: number;
  top_users: Record<string, number>;
  top_ips: Record<string, number>;
}

// =====================================================
// API RESPONSES
// =====================================================

export interface LogsResponse {
  logs: LogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourcesResponse {
  sources: Source[];
}

// =====================================================
// EVENT TYPE HELPERS
// =====================================================

export const EVENT_TYPE_COLORS: Record<string, string> = {
  error: 'bg-red-500',
  warning: 'bg-yellow-500',
  info: 'bg-blue-500',
  debug: 'bg-gray-500',
  insert: 'bg-green-500',
  update: 'bg-orange-500',
  delete: 'bg-red-400',
  select: 'bg-purple-500',
  http_get: 'bg-cyan-500',
  http_post: 'bg-emerald-500',
  http_put: 'bg-amber-500',
  http_delete: 'bg-rose-500',
  startup: 'bg-teal-500',
  shutdown: 'bg-slate-500',
  connection: 'bg-indigo-500',
  authentication: 'bg-violet-500',
  unknown: 'bg-gray-400',
};

export const EVENT_TYPE_LABELS: Record<string, string> = {
  error: 'Błąd',
  warning: 'Ostrzeżenie',
  info: 'Info',
  debug: 'Debug',
  insert: 'INSERT',
  update: 'UPDATE',
  delete: 'DELETE',
  select: 'SELECT',
  http_get: 'GET',
  http_post: 'POST',
  http_put: 'PUT',
  http_delete: 'DELETE',
  startup: 'Start',
  shutdown: 'Stop',
  connection: 'Połączenie',
  authentication: 'Auth',
  unknown: 'Nieznany',
};

export const CATEGORY_LABELS: Record<string, string> = {
  log_level: 'Poziom logowania',
  database: 'Baza danych',
  http: 'HTTP',
  system: 'System',
  unknown: 'Inne',
};
