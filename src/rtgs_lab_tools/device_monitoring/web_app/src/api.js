const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function fetchAllEntries() {
  const res = await fetch(`${API_BASE_URL}/api/entries`);
  return res.json();
}

export async function fetchLoggerInfo() {
  const res = await fetch(`${API_BASE_URL}/api/logger-info`);
  return res.json();
}
