import { useState } from "react";
import { DEFAULT_CONFIG } from "../utils";
import { SectionCard } from "./Layout";

const NUMERIC_FIELDS = [
  { key: "battery_voltage_min", label: "Battery min voltage", unit: "V", step: "0.01" },
  { key: "system_power_max", label: "System power max", unit: "W", step: "0.001" },
  { key: "inbox_humidity_max", label: "Inbox humidity max", unit: "%", step: "0.1" },
];
const ALL_KEYS = [...NUMERIC_FIELDS.map(f => f.key), "critical_errors"];

const mono = "'Space Mono', monospace";

// mode: "keep" (don't touch) | "set" (write value) | "default" (revert to default)
function ModeToggle({ mode, onChange }) {
  const opts = [
    { m: "keep", label: "Keep", color: "#4a6880" },
    { m: "set", label: "Set", color: "#6dc5ff" },
    { m: "default", label: "Default", color: "#a78bfa" },
  ];
  return (
    <div style={{ display: "inline-flex", gap: 4 }}>
      {opts.map(({ m, label, color }) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          style={{
            background: mode === m ? `${color}22` : "none",
            border: `1px solid ${mode === m ? color : "#1e2d40"}`,
            borderRadius: 4,
            color: mode === m ? color : "#4a6880",
            fontFamily: mono,
            fontSize: 10,
            letterSpacing: "0.06em",
            padding: "3px 8px",
            cursor: "pointer",
            textTransform: "uppercase",
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export default function ConfigEditor({ productNames = [], defaults = {}, productConfig = {}, onSave, onBack }) {
  const [selected, setSelected] = useState([]);
  const [modes, setModes] = useState(() => Object.fromEntries(ALL_KEYS.map(k => [k, "keep"])));
  const [values, setValues] = useState({
    battery_voltage_min: "",
    system_power_max: "",
    inbox_humidity_max: "",
    critical_errors: "", // one code per line
  });
  const [status, setStatus] = useState(null);
  const [saving, setSaving] = useState(false);

  const eff = { ...DEFAULT_CONFIG, ...defaults }; // global effective defaults

  function effectiveFor(product, key) {
    const override = productConfig[product]?.[key];
    return override !== undefined ? override : eff[key];
  }

  function isOverridden(product, key) {
    return productConfig[product]?.[key] !== undefined;
  }

  function toggleProduct(name) {
    setSelected(prev => (prev.includes(name) ? prev.filter(p => p !== name) : [...prev, name]));
  }

  function setMode(key, mode) {
    setModes(prev => ({ ...prev, [key]: mode }));
    // When switching a field to "set", prefill from the first selected product's
    // effective value (or the global default) as a convenience.
    if (mode === "set") {
      const source = selected.length === 1 ? effectiveFor(selected[0], key) : eff[key];
      setValues(prev => ({
        ...prev,
        [key]: key === "critical_errors" ? (source || []).join("\n") : String(source ?? ""),
      }));
    }
  }

  function buildOverrides() {
    const overrides = {};
    for (const f of NUMERIC_FIELDS) {
      if (modes[f.key] === "default") overrides[f.key] = null;
      else if (modes[f.key] === "set") {
        const num = parseFloat(values[f.key]);
        if (Number.isNaN(num)) throw new Error(`${f.label} must be a number`);
        overrides[f.key] = num;
      }
    }
    if (modes.critical_errors === "default") overrides.critical_errors = null;
    else if (modes.critical_errors === "set") {
      overrides.critical_errors = values.critical_errors
        .split("\n")
        .map(s => s.trim())
        .filter(Boolean);
    }
    return overrides;
  }

  async function handleSave() {
    setStatus(null);
    if (selected.length === 0) {
      setStatus({ ok: false, msg: "Select at least one product." });
      return;
    }
    let overrides;
    try {
      overrides = buildOverrides();
    } catch (e) {
      setStatus({ ok: false, msg: e.message });
      return;
    }
    if (Object.keys(overrides).length === 0) {
      setStatus({ ok: false, msg: "Set or reset at least one field (all are on 'Keep')." });
      return;
    }
    setSaving(true);
    try {
      await onSave(selected, overrides);
      setStatus({ ok: true, msg: `Applied to ${selected.length} product${selected.length !== 1 ? "s" : ""}.` });
      setModes(Object.fromEntries(ALL_KEYS.map(k => [k, "keep"])));
    } catch {
      setStatus({ ok: false, msg: "Failed to save. Please try again." });
    } finally {
      setSaving(false);
    }
  }

  async function resetProduct(product) {
    setSaving(true);
    setStatus(null);
    try {
      await onSave([product], Object.fromEntries(ALL_KEYS.map(k => [k, null])));
      setStatus({ ok: true, msg: `${product} reset to standard defaults.` });
    } catch {
      setStatus({ ok: false, msg: "Failed to reset." });
    } finally {
      setSaving(false);
    }
  }

  const allSelected = selected.length === productNames.length && productNames.length > 0;

  const labelStyle = { fontFamily: mono, fontSize: 12, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 8 };
  const valueStyle = { fontFamily: mono, fontSize: 14, color: "#c8ddef" };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #060d14; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #060d14; }
        ::-webkit-scrollbar-thumb { background: #1e2d40; border-radius: 3px; }
      `}</style>

      <div style={{ minHeight: "100vh", background: "#060d14", color: "#c8ddef", padding: "32px 24px", maxWidth: 900, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 6 }}>
            <span style={{ fontFamily: mono, fontSize: 10, letterSpacing: "0.3em", color: "#1e4060", textTransform: "uppercase" }}>◈ SYSTEM</span>
            <div style={{ flex: 1, height: 1, background: "#0f1c28" }} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {onBack && (
              <button onClick={onBack} style={{ background: "none", border: "1px solid #1e2d40", borderRadius: 4, color: "#6dc5ff", fontFamily: mono, fontSize: 12, letterSpacing: "0.08em", padding: "5px 12px", cursor: "pointer" }}>← BACK</button>
            )}
            <h1 style={{ fontFamily: mono, fontSize: 22, fontWeight: 200, color: "#e8f4ff", letterSpacing: "0.08em", textTransform: "uppercase" }}>Configuration</h1>
          </div>
          <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 13, color: "#2a4a60", marginTop: 6 }}>
            Standard values apply unless overridden per product. Overrides affect the dashboard only.
          </p>
        </div>

        {/* Standard defaults reference */}
        <SectionCard title="Standard Defaults" accent="#38bdf8">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 16 }}>
            {NUMERIC_FIELDS.map(f => (
              <div key={f.key}>
                <div style={labelStyle}>{f.label}</div>
                <div style={valueStyle}>{eff[f.key]}{f.unit}</div>
              </div>
            ))}
            <div style={{ gridColumn: "1 / -1" }}>
              <div style={labelStyle}>Critical Errors ({(eff.critical_errors || []).length})</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {(eff.critical_errors || []).map(e => (
                  <span key={e} style={{ fontFamily: mono, fontSize: 11, color: "#f87171", background: "#f8717118", border: "1px solid #f8717133", padding: "2px 8px", borderRadius: 4 }}>{e}</span>
                ))}
              </div>
            </div>
          </div>
        </SectionCard>

        <div style={{ height: 16 }} />

        {/* Editor */}
        <SectionCard title="Apply Changes" accent="#a78bfa">
          {/* Product multi-select */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <div style={labelStyle}>Products ({selected.length} selected)</div>
              <button
                onClick={() => setSelected(allSelected ? [] : [...productNames])}
                style={{ background: "none", border: "1px solid #1e2d40", borderRadius: 4, color: "#6dc5ff", fontFamily: mono, fontSize: 10, letterSpacing: "0.06em", padding: "3px 9px", cursor: "pointer", textTransform: "uppercase" }}
              >
                {allSelected ? "Clear all" : "Select all"}
              </button>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {productNames.map(name => {
                const on = selected.includes(name);
                return (
                  <button
                    key={name}
                    onClick={() => toggleProduct(name)}
                    style={{
                      background: on ? "#6dc5ff22" : "#0b1622",
                      border: `1px solid ${on ? "#6dc5ff" : "#1e2d40"}`,
                      borderRadius: 4,
                      color: on ? "#c8ddef" : "#4a6880",
                      fontFamily: mono,
                      fontSize: 11,
                      padding: "5px 11px",
                      cursor: "pointer",
                    }}
                  >
                    {on ? "✓ " : ""}{name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Numeric field editors */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {NUMERIC_FIELDS.map(f => (
              <div key={f.key} style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div style={{ minWidth: 170, fontFamily: mono, fontSize: 12, color: "#c8ddef" }}>{f.label}</div>
                <ModeToggle mode={modes[f.key]} onChange={m => setMode(f.key, m)} />
                {modes[f.key] === "set" && (
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                    <input
                      type="number"
                      step={f.step}
                      value={values[f.key]}
                      onChange={e => setValues(prev => ({ ...prev, [f.key]: e.target.value }))}
                      style={{ width: 100, background: "#060d14", border: "1px solid #1e2d40", borderRadius: 4, color: "#c8ddef", fontFamily: mono, fontSize: 13, padding: "5px 8px" }}
                    />
                    <span style={{ fontFamily: mono, fontSize: 12, color: "#4a6880" }}>{f.unit}</span>
                  </span>
                )}
              </div>
            ))}

            {/* Critical errors editor */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ minWidth: 170, fontFamily: mono, fontSize: 12, color: "#c8ddef" }}>Critical errors</div>
                <ModeToggle mode={modes.critical_errors} onChange={m => setMode("critical_errors", m)} />
              </div>
              {modes.critical_errors === "set" && (
                <>
                  <textarea
                    value={values.critical_errors}
                    onChange={e => setValues(prev => ({ ...prev, critical_errors: e.target.value }))}
                    rows={6}
                    placeholder="One error code per line, e.g.&#10;SD_ACCESS_FAIL&#10;FRAM_OVERRUN"
                    style={{ width: "100%", background: "#060d14", border: "1px solid #1e2d40", borderRadius: 4, color: "#c8ddef", fontFamily: mono, fontSize: 12, padding: "8px 10px", resize: "vertical" }}
                  />
                  <span style={{ fontFamily: mono, fontSize: 10, color: "#4a6880" }}>One error code per line. These will be highlighted and will flag a device for the selected product(s).</span>
                </>
              )}
            </div>
          </div>

          {/* Save */}
          <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 14 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{ background: "#a78bfa22", border: "1px solid #a78bfa", borderRadius: 4, color: "#a78bfa", fontFamily: mono, fontSize: 12, letterSpacing: "0.08em", padding: "7px 18px", cursor: saving ? "default" : "pointer", textTransform: "uppercase", opacity: saving ? 0.5 : 1 }}
            >
              {saving ? "Saving…" : "Apply to selected"}
            </button>
            {status && (
              <span style={{ fontFamily: mono, fontSize: 12, color: status.ok ? "#4ade80" : "#f87171" }}>{status.msg}</span>
            )}
          </div>
        </SectionCard>

        <div style={{ height: 16 }} />

        {/* Per-product overview */}
        <SectionCard title="Per-Product Configuration" accent="#8bbbf7">
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 560 }}>
              <thead>
                <tr>
                  {["Product", ...NUMERIC_FIELDS.map(f => f.label), "Critical", ""].map((h, i) => (
                    <th key={i} style={{ textAlign: i === 0 ? "left" : "center", fontFamily: mono, fontSize: 10, color: "#71c6ff", letterSpacing: "0.1em", textTransform: "uppercase", padding: "6px 10px", borderBottom: "1px solid #0f1c28", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {productNames.map(product => {
                  const anyOverride = ALL_KEYS.some(k => isOverridden(product, k));
                  return (
                    <tr key={product}>
                      <td style={{ fontFamily: mono, fontSize: 12, color: "#c8ddef", padding: "8px 10px", borderBottom: "1px solid #0b1622", whiteSpace: "nowrap" }}>{product}</td>
                      {NUMERIC_FIELDS.map(f => (
                        <td key={f.key} style={{ textAlign: "center", padding: "8px 10px", borderBottom: "1px solid #0b1622" }}>
                          <span style={{ fontFamily: mono, fontSize: 12, color: isOverridden(product, f.key) ? "#a78bfa" : "#8899aa" }}>
                            {effectiveFor(product, f.key)}{f.unit}{isOverridden(product, f.key) ? " *" : ""}
                          </span>
                        </td>
                      ))}
                      <td style={{ textAlign: "center", padding: "8px 10px", borderBottom: "1px solid #0b1622" }}>
                        <span
                          title={(effectiveFor(product, "critical_errors") || []).join(", ")}
                          style={{ fontFamily: mono, fontSize: 12, color: isOverridden(product, "critical_errors") ? "#a78bfa" : "#8899aa", cursor: "help" }}
                        >
                          {(effectiveFor(product, "critical_errors") || []).length}{isOverridden(product, "critical_errors") ? " *" : ""}
                        </span>
                      </td>
                      <td style={{ textAlign: "center", padding: "8px 10px", borderBottom: "1px solid #0b1622" }}>
                        {anyOverride && (
                          <button
                            onClick={() => resetProduct(product)}
                            disabled={saving}
                            style={{ background: "none", border: "1px solid #1e2d40", borderRadius: 4, color: "#4a6880", fontFamily: mono, fontSize: 10, letterSpacing: "0.05em", padding: "3px 8px", cursor: "pointer", textTransform: "uppercase", whiteSpace: "nowrap" }}
                          >
                            Reset
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div style={{ fontFamily: mono, fontSize: 10, color: "#4a6880", marginTop: 10 }}>
            <span style={{ color: "#a78bfa" }}>*</span> overridden for this product (differs from standard default)
          </div>
        </SectionCard>

      </div>
    </>
  );
}
