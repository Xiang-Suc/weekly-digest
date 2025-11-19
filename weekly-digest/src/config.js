// Unified config adapter for web/weekly-digest
// Reads window.CONFIG.API_BASE_URL if available, otherwise falls back to same-origin
export const API_BASE_URL = (window.CONFIG && window.CONFIG.API_BASE_URL) ? window.CONFIG.API_BASE_URL : 'http://127.0.0.1:8001';