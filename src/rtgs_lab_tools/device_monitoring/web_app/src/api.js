const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function fetchAllEntries() {
  const res = await fetch(`${API_BASE_URL}/api/entries`);
  return res.json();
}

export async function fetchLoggerInfo() {
  const res = await fetch(`${API_BASE_URL}/api/logger-info`);
  return res.json();
}

export async function fetchConfig() {
  const res = await fetch(`${API_BASE_URL}/api/config`);
  return res.json();
}

export async function fetchProductConfig() {
  const res = await fetch(`${API_BASE_URL}/api/product-config`);
  return res.json();
}

// Apply config overrides to one or more products at once. Pass a value of null
// for a key to clear that override (revert the product(s) to the default).
export async function saveProductConfig(productNames, overrides) {
  const res = await fetch(`${API_BASE_URL}/api/product-config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_names: productNames, overrides }),
  });
  if (!res.ok) throw new Error("Failed to save product config");
  return res.json();
}

export async function fetchIgnoredProblems() {
  const res = await fetch(`${API_BASE_URL}/api/ignored-problems`);
  return res.json();
}

export async function ignoreProblem(nodeId, problemKey) {
  const res = await fetch(`${API_BASE_URL}/api/ignored-problems`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ node_id: nodeId, problem_key: problemKey }),
  });
  if (!res.ok) throw new Error("Failed to ignore problem");
  return res.json();
}

export async function unignoreProblem(nodeId, problemKey) {
  const res = await fetch(
    `${API_BASE_URL}/api/ignored-problems/${encodeURIComponent(nodeId)}/${encodeURIComponent(problemKey)}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error("Failed to un-ignore problem");
  return res.json();
}
