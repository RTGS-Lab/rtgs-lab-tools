import { formatTimestampShort, getBatteryLevel, STATUS } from "../utils";
import StatusPill from "./StatusPill";
import { color, font, size, cardShadow } from "../theme";

const columnHeader = {
  fontFamily: font.mono,
  fontSize: size.sm,
  fontWeight: 600,
  color: color.accent,
  letterSpacing: "0.13em",
  textTransform: "uppercase",
};

export default function FieldSelector({ productName, fields, onSelect, onBack }) {
  return (
    <div style={{
      minHeight: "100vh",
      background: color.pageBg,
      color: color.text,
      padding: "36px 24px",
      maxWidth: 900,
      margin: "0 auto",
    }}>

      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 8 }}>
          <span style={{ fontFamily: font.mono, fontSize: size.tiny, letterSpacing: "0.3em", color: color.decor, textTransform: "uppercase" }}>
            ◈ SYSTEM
          </span>
          <div style={{ flex: 1, height: 1, background: color.divider }} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {onBack && (
            <button onClick={onBack} style={{
              background: color.surface,
              border: `1px solid ${color.borderStrong}`,
              borderRadius: 5,
              color: color.accent,
              fontFamily: font.mono,
              fontSize: size.sm,
              fontWeight: 600,
              letterSpacing: "0.07em",
              padding: "7px 14px",
              cursor: "pointer",
            }}>
              ← BACK
            </button>
          )}
          <h1 style={{ fontFamily: font.mono, fontSize: size.h1, fontWeight: 700, color: color.text, letterSpacing: "0.04em", textTransform: "uppercase" }}>
            {productName}
          </h1>
        </div>
        <p style={{ fontFamily: font.sans, fontSize: size.base, color: color.textMuted, marginTop: 8 }}>
          Select a field to view detailed monitoring data
        </p>
      </div>

      {/* Column headers */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 20,
        padding: "0 20px 9px 28px",
        borderBottom: `1px solid ${color.border}`,
        marginBottom: 10,
      }}>
        <div style={{ ...columnHeader, flex: 1 }}>Field Name</div>
        <div style={{ ...columnHeader, minWidth: 120, textAlign: "center" }}>Status</div>
        <div style={{ ...columnHeader, minWidth: 85, textAlign: "center" }}>Battery</div>
        <div style={{ ...columnHeader, minWidth: 175, textAlign: "right" }}>Last Heard</div>
        <div style={{ width: 20 }} />
      </div>

      {/* Field rows — active nodes in two groups, inactive at the bottom */}
      {[
        { label: "Needs Attention", fill: STATUS.bad.fill,  ink: STATUS.bad.ink,   dim: false, subset: fields.filter(f =>  f.active && f.effectiveFlagged) },
        { label: "OK",              fill: STATUS.good.fill, ink: STATUS.good.ink,  dim: false, subset: fields.filter(f =>  f.active && !f.effectiveFlagged) },
        { label: "Inactive",        fill: color.decor,      ink: color.textFaint,  dim: true,  subset: fields.filter(f => !f.active) },
      ].map(({ label, fill, ink, dim, subset }) => subset.length === 0 ? null : (
        <div key={label} style={{ marginBottom: 28 }}>
          {/* Group heading */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: fill, display: "inline-block", flexShrink: 0 }} />
            <span style={{ fontFamily: font.mono, fontSize: size.sm, fontWeight: 600, color: ink, letterSpacing: "0.16em", textTransform: "uppercase" }}>
              {label} — {subset.length}
            </span>
            <div style={{ flex: 1, height: 1, background: `${fill}44` }} />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {subset.map(field => {
              const batteryInk = field.battery != null
                ? STATUS[getBatteryLevel(field.battery)].ink
                : color.textFaint;
              return (
                <button
                  key={field.node_id}
                  onClick={() => onSelect(field.node_id)}
                  style={{
                    background: color.surface,
                    border: `1px solid ${field.effectiveFlagged ? `${STATUS.bad.fill}66` : color.border}`,
                    borderRadius: 8,
                    boxShadow: cardShadow,
                    padding: "15px 20px",
                    textAlign: "left",
                    cursor: "pointer",
                    position: "relative",
                    overflow: "hidden",
                    transition: "background 0.15s",
                    display: "flex",
                    alignItems: "center",
                    gap: 20,
                    opacity: dim ? 0.65 : 1,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = color.surfaceHover; }}
                  onMouseLeave={e => { e.currentTarget.style.background = color.surface; }}
                >
                  {/* accent bar */}
                  <div style={{
                    position: "absolute", top: 0, left: 0,
                    width: 3, height: "100%",
                    background: dim ? color.decor : (field.effectiveFlagged ? STATUS.bad.fill : STATUS.good.fill),
                    borderRadius: "8px 0 0 8px",
                  }} />

                  {/* Field name */}
                  <div style={{ flex: 1, paddingLeft: 4 }}>
                    <div style={{
                      fontFamily: font.mono,
                      fontSize: size.base,
                      fontWeight: 700,
                      color: color.text,
                      letterSpacing: "0.01em",
                    }}>
                      {field.field_name}
                    </div>
                  </div>

                  {/* Flagged status */}
                  <div style={{ minWidth: 120, textAlign: "center" }}>
                    <StatusPill
                      value={field.effectiveFlagged}
                      trueLabel="NEEDS ATTN"
                      falseLabel="ALL GOOD"
                    />
                  </div>

                  {/* Battery */}
                  <div style={{ minWidth: 85, textAlign: "center" }}>
                    <span style={{
                      fontFamily: font.mono,
                      fontSize: size.base,
                      fontWeight: 700,
                      color: batteryInk,
                    }}>
                      {field.battery != null ? `${field.battery.toFixed(2)}V` : "—"}
                    </span>
                  </div>

                  {/* Time last heard */}
                  <div style={{ minWidth: 175, textAlign: "right" }}>
                    <span style={{
                      fontFamily: font.mono,
                      fontSize: size.base,
                      color: color.accent,
                    }}>
                      {formatTimestampShort(field.device_timestamp)}
                    </span>
                  </div>

                  {/* Arrow */}
                  <div style={{ width: 20, fontFamily: font.mono, fontSize: size.sm, color: color.decor }}>→</div>
                </button>
              );
            })}
          </div>
        </div>
      ))}

    </div>
  );
}
