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

// Parse the raw `errors` column into a normalized list of records:
//   { device_type, device_position, error_name, count }
// The pipeline now stores a JSON array of these. Legacy rows stored a
// { error_name: count } object; we up-convert those so the UI never crashes
// before the DB is repopulated.
export function parseErrors(raw) {
  let parsed;
  try {
    parsed = JSON.parse(raw || "[]");
  } catch {
    return [];
  }
  if (Array.isArray(parsed)) return parsed;
  if (parsed && typeof parsed === "object") {
    return Object.entries(parsed).map(([error_name, count]) => ({
      device_type: "",
      device_position: "",
      error_name,
      count,
    }));
  }
  return [];
}

// Stable ignore key for one error record. Scoped to
// (device_type, device_position, error_name) so the same error on different
// sensors of a node can be ignored independently.
export function errorProblemKey(rec) {
  return `error:${rec.device_type || ""}:${rec.device_position || ""}:${rec.error_name}`;
}

// "device_type [device_position]" for display; falls back to just the type.
export function formatErrorLocation(rec) {
  const type = rec.device_type || "";
  const pos = rec.device_position || "";
  return pos ? `${type} [${pos}]`.trim() : type;
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

  for (const rec of parseErrors(entry.errors)) {
    if (critical.includes(rec.error_name) && rec.count > 0) {
      const where = formatErrorLocation(rec) || "unknown sensor";
      problems.push({
        key: errorProblemKey(rec),
        label: `${rec.error_name} (${where})`,
        detail: `${rec.count} occurrence${rec.count !== 1 ? "s" : ""}`,
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

// The pipeline produces one report per day, so listing every monitoring
// timestamp as a button gets unusable within a couple of months. Only the most
// recent RECENT_DAYS calendar days stay on screen; the rest move to a dropdown.
export const RECENT_DAYS = 7;

// Start of the earliest day still counted as "recent" — today plus the
// RECENT_DAYS-1 days before it. Anchoring to midnight rather than to
// `now - 7*24h` means a whole calendar day is either in the window or out of
// it, regardless of what time of day that day's report happened to run.
export function recentCutoff(now = new Date(), days = RECENT_DAYS) {
  const cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  cutoff.setDate(cutoff.getDate() - (days - 1));
  return cutoff.getTime();
}

// Split timestamps into { recent, older }, both newest-first.
export function partitionTimestamps(timestamps = [], now = new Date()) {
  const cutoff = recentCutoff(now);
  const recent = [];
  const older = [];
  for (const ts of [...timestamps].sort((a, b) => Date.parse(b) - Date.parse(a))) {
    (Date.parse(ts) >= cutoff ? recent : older).push(ts);
  }
  return { recent, older };
}

// Status colors come in pairs. `fill` is the bright hue, used for solid marks —
// gauge bar fills, dots, accent rails — where a block of color reads fine on a
// white page. `ink` is the darker companion in the same hue, used for text,
// which needs ~4.5:1 contrast that the bright hue cannot reach on white.
//
// Always pick by role, never reuse a fill as text or vice versa.
export const STATUS = {
  good: { fill: "#4ade80", ink: "#15803d" },
  warn: { fill: "#facc15", ink: "#a16207" },
  bad: { fill: "#ef4444", ink: "#dc2626" },
};

// The metric getters return a level key into STATUS rather than a color, so the
// call site decides whether it needs the fill or the ink.
export function getBatteryLevel(val) {
  if (val >= 3.6) return "good";
  if (val >= 3.4) return "warn";
  return "bad";
}

export function getSystemLevel(val) {
  // Order matters: `bad` must be tested first, since every value at or above
  // the 0.364W limit is also above the 0.2W warning threshold.
  if (val >= 0.364) return "bad";
  if (val > 0.2) return "warn";
  return "good";
}

export function getHumidityLevel(val) {
  return val > 65 ? "warn" : "good";
}
