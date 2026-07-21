export function isFlagged(value) {
  return value === true || value === "true" || value === 1 || value === "1";
}

// The config fields the app understands. These fallbacks mirror config.py and
// are only used before the daily pipeline has populated /api/config; DB values
// (global defaults, then per-product overrides) always take precedence.
export const DEFAULT_CONFIG = {
  battery_voltage_min: 3.6,
  system_power_max: 0.364,
  inbox_humidity_max: 65,
  critical_errors: [
    "SD_ACCESS_FAIL",
    "FRAM_ACCESS_FAIL",
    "FIND_FAIL",
    "FRAM_SPACE_CRITICAL",
    "FRAM_SPACE_WARNING",
    "FRAM_OVERRUN",
  ],
};

// Merge global defaults with a product's overrides. Only keys the product
// actually overrides win; everything else falls back to the default.
export function resolveConfig(defaults = {}, productOverrides = {}) {
  return { ...DEFAULT_CONFIG, ...defaults, ...productOverrides };
}

// Derive the list of flagging "problems" for a monitoring entry, given the
// effective config for that node's product. Mirrors the flagging logic in the
// pipeline's data_analyzer.py. Each problem has a stable `key` used for ignores.
export function deriveProblems(entry, config = {}) {
  if (!entry) return [];
  const cfg = { ...DEFAULT_CONFIG, ...config };
  const critical = cfg.critical_errors || [];
  const problems = [];

  if (isFlagged(entry.is_missing)) {
    problems.push({
      key: "missing",
      label: "Node missing",
      detail: "Not heard from within threshold window",
      is_critical: true,
    });
  }
  if (entry.battery != null && entry.battery < cfg.battery_voltage_min) {
    problems.push({
      key: "battery",
      label: "Battery low",
      detail: `${entry.battery.toFixed(2)}V < ${cfg.battery_voltage_min}V`,
      is_critical: false,
    });
  }
  if (entry.system != null && entry.system > cfg.system_power_max) {
    problems.push({
      key: "system",
      label: "System power high",
      detail: `${entry.system.toFixed(3)}W > ${cfg.system_power_max}W`,
      is_critical: false,
    });
  }
  if (entry.humidity != null && entry.humidity > cfg.inbox_humidity_max) {
    problems.push({
      key: "humidity",
      label: "Inbox humidity high",
      detail: `${entry.humidity.toFixed(1)}% > ${cfg.inbox_humidity_max}%`,
      is_critical: false,
    });
  }

  let errorsObj = {};
  try {
    errorsObj = JSON.parse(entry.errors || "{}");
  } catch {
    errorsObj = {};
  }
  for (const [name, count] of Object.entries(errorsObj)) {
    if (critical.includes(name) && count > 0) {
      problems.push({
        key: `error:${name}`,
        label: `Critical error: ${name}`,
        detail: `${count} occurrence${count !== 1 ? "s" : ""}`,
        is_critical: true,
      });
    }
  }

  return problems;
}

// A device needs attention when it has at least one active problem that the
// user has NOT ignored. If every active problem is ignored (or there are none),
// the device is effectively OK.
export function computeEffectiveFlagged(problems, ignoredKeys = []) {
  if (!problems || problems.length === 0) return false;
  return problems.some(p => !ignoredKeys.includes(p.key));
}

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
