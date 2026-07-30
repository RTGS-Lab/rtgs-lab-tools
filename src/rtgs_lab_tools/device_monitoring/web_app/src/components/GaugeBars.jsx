import { color as c, font, size } from "../theme";
import { STATUS } from "../utils";

function GaugeBar({ label, displayValue, pct, level }) {
  const { fill, ink } = STATUS[level];
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 5 }}>
        <span style={{ fontFamily: font.mono, fontSize: size.sm, fontWeight: 500, color: c.textMuted, letterSpacing: "0.08em", textTransform: "uppercase" }}>{label}</span>
        <span style={{ fontFamily: font.mono, fontSize: size.lg, color: ink, fontWeight: 600 }}>{displayValue}</span>
      </div>
      <div style={{ height: 7, background: c.divider, borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: fill, borderRadius: 4, transition: "width 0.5s cubic-bezier(0.4,0,0.2,1)" }} />
      </div>
    </div>
  );
}

export function GaugeBarHumidity({ value, max = 100, level, label }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return <GaugeBar label={label} displayValue={`${value.toFixed(1)}%`} pct={pct} level={level} />;
}

export function GaugeBarBattery({ value, min = 3.0, max = 4.2, level, label }) {
  const pct = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  return <GaugeBar label={label} displayValue={`${value.toFixed(2)}V`} pct={pct} level={level} />;
}

export function GaugeBarSystem({ value, max = 2.0, level, label }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return <GaugeBar label={label} displayValue={`${value.toFixed(3)}W`} pct={pct} level={level} />;
}
