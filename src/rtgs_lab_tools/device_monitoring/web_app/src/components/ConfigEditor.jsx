import { useState } from "react";
import { DEFAULT_CONFIG, STATUS } from "../utils";
import { SectionCard } from "./Layout";
import { color, font, size } from "../theme";

// `short` is the per-product table's column header — the full labels no longer
// fit across the table at the larger type size.
const NUMERIC_FIELDS = [
  { key: "battery_voltage_min", label: "Battery min voltage", short: "Battery min", unit: "V", step: "0.01" },
  { key: "system_power_max", label: "System power max", short: "Power max", unit: "W", step: "0.001" },
  { key: "inbox_humidity_max", label: "Inbox humidity max", short: "Humidity max", unit: "%", step: "0.1" },
];
const ALL_KEYS = [...NUMERIC_FIELDS.map(f => f.key), "critical_errors"];

const mono = font.mono;
const sans = font.sans;

// Green/red here report whether a save succeeded rather than device state, but
// they reuse the status inks so there is only one readable green and red.
const OK_GREEN = STATUS.good.ink;
const ERR_RED = STATUS.bad.ink;

// Shared control styling for the numeric inputs and the critical-errors textarea.
const inputStyle = {
  background: color.surface,
  border: `1px solid ${color.borderStrong}`,
  borderRadius: 5,
  color: color.text,
  fontFamily: mono,
  fontSize: size.base,
  padding: "7px 10px",
};

// mode: "keep" (don't touch) | "set" (write value) | "default" (revert to default)
function ModeToggle({ mode, onChange }) {
  const opts = [
    { m: "keep", label: "Keep", c: color.textMuted },
    { m: "set", label: "Set", c: color.accent },
    { m: "default", label: "Default", c: color.violet },
  ];
  return (
    <div style={{ display: "inline-flex", gap: 4 }}>
      {opts.map(({ m, label, c }) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          style={{
            background: mode === m ? `${c}1f` : color.surface,
            border: `1px solid ${mode === m ? c : color.border}`,
            borderRadius: 4,
            color: mode === m ? c : color.textMuted,
            fontFamily: mono,
            fontSize: size.xs,
            fontWeight: mode === m ? 600 : 400,
            letterSpacing: "0.05em",
            padding: "5px 11px",
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

  const labelStyle = { fontFamily: sans, fontSize: size.sm, fontWeight: 600, color: color.textMuted, letterSpacing: "0.09em", textTransform: "uppercase", marginBottom: 8 };
  const valueStyle = { fontFamily: mono, fontSize: size.lg, fontWeight: 600, color: color.text };
  const fieldLabelStyle = { minWidth: 190, fontFamily: sans, fontSize: size.base, fontWeight: 500, color: color.text };
  const helpStyle = { fontFamily: sans, fontSize: size.xs, color: color.textMuted };

  return (
    <div style={{ minHeight: "100vh", background: color.pageBg, color: color.text, padding: "36px 24px", maxWidth: 900, margin: "0 auto" }}>

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 8 }}>
          <span style={{ fontFamily: mono, fontSize: size.tiny, letterSpacing: "0.3em", color: color.decor, textTransform: "uppercase" }}>◈ SYSTEM</span>
          <div style={{ flex: 1, height: 1, background: color.divider }} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {onBack && (
            <button onClick={onBack} style={{ background: color.surface, border: `1px solid ${color.borderStrong}`, borderRadius: 5, color: color.accent, fontFamily: mono, fontSize: size.sm, fontWeight: 600, letterSpacing: "0.07em", padding: "7px 14px", cursor: "pointer" }}>← BACK</button>
          )}
          <h1 style={{ fontFamily: mono, fontSize: size.h1, fontWeight: 700, color: color.text, letterSpacing: "0.04em", textTransform: "uppercase" }}>Configuration</h1>
        </div>
        <p style={{ fontFamily: sans, fontSize: size.base, color: color.textMuted, marginTop: 8 }}>
          Standard values apply unless overridden per product. Overrides affect the dashboard only.
        </p>
      </div>

      {/* Standard defaults reference */}
      <SectionCard title="Standard Defaults" accent={color.teal}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 18 }}>
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
                <span key={e} style={{ fontFamily: mono, fontSize: size.xs, fontWeight: 600, color: STATUS.bad.ink, background: `${STATUS.bad.fill}26`, border: `1px solid ${STATUS.bad.fill}66`, padding: "3px 10px", borderRadius: 4 }}>{e}</span>
              ))}
            </div>
          </div>
        </div>
      </SectionCard>

      <div style={{ height: 16 }} />

      {/* Editor */}
      <SectionCard title="Apply Changes" accent={color.violet}>
        {/* Product multi-select */}
        <div style={{ marginBottom: 22 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <div style={labelStyle}>Products ({selected.length} selected)</div>
            <button
              onClick={() => setSelected(allSelected ? [] : [...productNames])}
              style={{ background: color.surface, border: `1px solid ${color.borderStrong}`, borderRadius: 4, color: color.accent, fontFamily: mono, fontSize: size.xs, fontWeight: 600, letterSpacing: "0.05em", padding: "5px 11px", cursor: "pointer", textTransform: "uppercase" }}
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
                    background: on ? color.accentTint : color.surface,
                    border: `1px solid ${on ? color.accent : color.border}`,
                    borderRadius: 4,
                    color: on ? color.accent : color.textMuted,
                    fontFamily: mono,
                    fontSize: size.sm,
                    fontWeight: on ? 600 : 400,
                    padding: "6px 12px",
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
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {NUMERIC_FIELDS.map(f => (
            <div key={f.key} style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <div style={fieldLabelStyle}>{f.label}</div>
              <ModeToggle mode={modes[f.key]} onChange={m => setMode(f.key, m)} />
              {modes[f.key] === "set" && (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <input
                    type="number"
                    step={f.step}
                    value={values[f.key]}
                    onChange={e => setValues(prev => ({ ...prev, [f.key]: e.target.value }))}
                    style={{ ...inputStyle, width: 110 }}
                  />
                  <span style={{ fontFamily: mono, fontSize: size.sm, color: color.textMuted }}>{f.unit}</span>
                </span>
              )}
            </div>
          ))}

          {/* Critical errors editor */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={fieldLabelStyle}>Critical errors</div>
              <ModeToggle mode={modes.critical_errors} onChange={m => setMode("critical_errors", m)} />
            </div>
            {modes.critical_errors === "set" && (
              <>
                <textarea
                  value={values.critical_errors}
                  onChange={e => setValues(prev => ({ ...prev, critical_errors: e.target.value }))}
                  rows={6}
                  placeholder="One error code per line, e.g.&#10;SD_ACCESS_FAIL&#10;FRAM_OVERRUN"
                  style={{ ...inputStyle, width: "100%", resize: "vertical" }}
                />
                <span style={helpStyle}>One error code per line. These will be highlighted and will flag a device for the selected product(s).</span>
              </>
            )}
          </div>
        </div>

        {/* Save */}
        <div style={{ marginTop: 22, display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{ background: color.violet, border: `1px solid ${color.violet}`, borderRadius: 5, color: "#ffffff", fontFamily: mono, fontSize: size.base, fontWeight: 600, letterSpacing: "0.07em", padding: "9px 20px", cursor: saving ? "default" : "pointer", textTransform: "uppercase", opacity: saving ? 0.55 : 1 }}
          >
            {saving ? "Saving…" : "Apply to selected"}
          </button>
          {status && (
            <span style={{ fontFamily: sans, fontSize: size.base, fontWeight: 500, color: status.ok ? OK_GREEN : ERR_RED }}>{status.msg}</span>
          )}
        </div>
      </SectionCard>

      <div style={{ height: 16 }} />

      {/* Per-product overview */}
      <SectionCard title="Per-Product Configuration" accent={color.accent}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 620 }}>
            <thead>
              <tr>
                {["Product", ...NUMERIC_FIELDS.map(f => f.short), "Critical", ""].map((h, i) => (
                  <th key={i} style={{ textAlign: i === 0 ? "left" : "center", fontFamily: mono, fontSize: size.xs, fontWeight: 600, color: color.accent, letterSpacing: "0.09em", textTransform: "uppercase", padding: "8px 10px", borderBottom: `1px solid ${color.border}`, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {productNames.map(product => {
                const anyOverride = ALL_KEYS.some(k => isOverridden(product, k));
                return (
                  <tr key={product}>
                    <td style={{ fontFamily: mono, fontSize: size.base, fontWeight: 600, color: color.text, padding: "10px", borderBottom: `1px solid ${color.divider}`, whiteSpace: "nowrap" }}>{product}</td>
                    {NUMERIC_FIELDS.map(f => (
                      <td key={f.key} style={{ textAlign: "center", padding: "10px", borderBottom: `1px solid ${color.divider}` }}>
                        <span style={{ fontFamily: mono, fontSize: size.base, color: isOverridden(product, f.key) ? color.violet : color.textMuted }}>
                          {effectiveFor(product, f.key)}{f.unit}{isOverridden(product, f.key) ? " *" : ""}
                        </span>
                      </td>
                    ))}
                    <td style={{ textAlign: "center", padding: "10px", borderBottom: `1px solid ${color.divider}` }}>
                      <span
                        title={(effectiveFor(product, "critical_errors") || []).join(", ")}
                        style={{ fontFamily: mono, fontSize: size.base, color: isOverridden(product, "critical_errors") ? color.violet : color.textMuted, cursor: "help" }}
                      >
                        {(effectiveFor(product, "critical_errors") || []).length}{isOverridden(product, "critical_errors") ? " *" : ""}
                      </span>
                    </td>
                    <td style={{ textAlign: "center", padding: "10px", borderBottom: `1px solid ${color.divider}` }}>
                      {anyOverride && (
                        <button
                          onClick={() => resetProduct(product)}
                          disabled={saving}
                          style={{ background: color.surface, border: `1px solid ${color.borderStrong}`, borderRadius: 4, color: color.textMuted, fontFamily: mono, fontSize: size.xs, fontWeight: 600, letterSpacing: "0.04em", padding: "5px 10px", cursor: "pointer", textTransform: "uppercase", whiteSpace: "nowrap" }}
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
        <div style={{ ...helpStyle, marginTop: 12 }}>
          <span style={{ color: color.violet, fontWeight: 700 }}>*</span> overridden for this product (differs from standard default)
        </div>
      </SectionCard>

    </div>
  );
}
