export async function fetchAllEntries() {
  const res = await fetch("http://localhost:5000/api/entries");
  return res.json();
}

export async function fetchLoggerInfo() {
  const res = await fetch("http://localhost:5000/api/logger-info");
  return res.json();
}
