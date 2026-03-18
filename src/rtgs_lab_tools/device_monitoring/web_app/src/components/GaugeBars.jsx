function GaugeBar({ label, displayValue, pct, color }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#8899aa", letterSpacing: "0.08em", textTransform: "uppercase" }}>{label}</span>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 15, color, fontWeight: 500 }}>{displayValue}</span>
      </div>
      <div style={{ height: 6, background: "#1a2233", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 3, transition: "width 0.5s cubic-bezier(0.4,0,0.2,1)" }} />
      </div>
    </div>
  );
}

export function GaugeBarHumidity({ value, max = 100, color, label }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return <GaugeBar label={label} displayValue={`${value.toFixed(1)}%`} pct={pct} color={color} />;
}

export function GaugeBarBattery({ value, min = 3.0, max = 4.2, color, label }) {
  const pct = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  return <GaugeBar label={label} displayValue={`${value.toFixed(2)}V`} pct={pct} color={color} />;
}

export function GaugeBarSystem({ value, max = 2.0, color, label }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return <GaugeBar label={label} displayValue={`${value.toFixed(3)}W`} pct={pct} color={color} />;
}
