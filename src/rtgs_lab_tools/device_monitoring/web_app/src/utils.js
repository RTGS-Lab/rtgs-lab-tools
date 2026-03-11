export function formatTimestamp(ts) {
  if (!ts) return "—";
  return ts.replace("T", " ").slice(0, 23);
}

export function getBatteryColor(val) {
  if (val >= 3.6) return "#4ade80";
  if (val >= 3.4) return "#facc15";
  return "#ff0000";
}

export function getSystemColor(val) {
  if (val > 0.2) return "#facc15";
  if (val >= 0.364) return "#ff0000";
  return "#4ade80";
}

export function getHumidityColor(val) {
  if (val > 65) return "#facc15";
  return "#4ade80";
}
