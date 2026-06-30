import { formatTimestamp, getBatteryColor, isFlagged } from "../utils";
import StatusPill from "./StatusPill";

export default function FieldSelector({ productName, fields, onSelect, onBack }) {
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #060d14; }
      `}</style>

      <div style={{
        minHeight: "100vh",
        background: "#060d14",
        color: "#c8ddef",
        padding: "32px 24px",
        maxWidth: 900,
        margin: "0 auto",
      }}>

        {/* Header */}
        <div style={{ marginBottom: 36 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 6 }}>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, letterSpacing: "0.3em", color: "#1e4060", textTransform: "uppercase" }}>
              ◈ SYSTEM
            </span>
            <div style={{ flex: 1, height: 1, background: "#0f1c28" }} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {onBack && (
              <button onClick={onBack} style={{
                background: "none",
                border: "1px solid #1e2d40",
                borderRadius: 4,
                color: "#6dc5ff",
                fontFamily: "'Space Mono', monospace",
                fontSize: 12,
                letterSpacing: "0.08em",
                padding: "5px 12px",
                cursor: "pointer",
              }}>
                ← BACK
              </button>
            )}
            <h1 style={{ fontFamily: "'Space Mono', monospace", fontSize: 22, fontWeight: 200, color: "#e8f4ff", letterSpacing: "0.08em", textTransform: "uppercase" }}>
              {productName}
            </h1>
          </div>
          <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 13, color: "#6dc5ff", marginTop: 6 }}>
            Select a field to view detailed monitoring data
          </p>
        </div>

        {/* Column headers */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 20,
          padding: "0 20px 8px 28px",
          borderBottom: "1px solid #0f1c28",
          marginBottom: 8,
        }}>
          <div style={{ flex: 1, fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#71c6ff", letterSpacing: "0.15em", textTransform: "uppercase" }}>Field Name</div>
          <div style={{ minWidth: 110, textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#71c6ff", letterSpacing: "0.15em", textTransform: "uppercase" }}>Status</div>
          <div style={{ minWidth: 80, textAlign: "center", fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#71c6ff", letterSpacing: "0.15em", textTransform: "uppercase" }}>Battery</div>
          <div style={{ minWidth: 160, textAlign: "right", fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#71c6ff", letterSpacing: "0.15em", textTransform: "uppercase" }}>Last Heard</div>
          <div style={{ width: 20 }} />
        </div>

        {/* Field rows — active nodes in two groups, inactive at the bottom */}
        {[
          { label: "Needs Attention", color: "#ff0000",  dim: false, subset: fields.filter(f =>  f.active && f.effectiveFlagged) },
          { label: "OK",              color: "#4ade80",  dim: false, subset: fields.filter(f =>  f.active && !f.effectiveFlagged) },
          { label: "Inactive",        color: "#2a4a60",  dim: true,  subset: fields.filter(f => !f.active) },
        ].map(({ label, color, dim, subset }) => subset.length === 0 ? null : (
          <div key={label} style={{ marginBottom: 28 }}>
            {/* Group heading */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, display: "inline-block", flexShrink: 0 }} />
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color, letterSpacing: "0.18em", textTransform: "uppercase" }}>
                {label} — {subset.length}
              </span>
              <div style={{ flex: 1, height: 1, background: `${color}22` }} />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {subset.map(field => {
                const batteryColor = field.battery != null ? getBatteryColor(field.battery) : "#4a6880";
                return (
                  <button
                    key={field.node_id}
                    onClick={() => onSelect(field.node_id)}
                    style={{
                      background: "#0b1622",
                      border: `1px solid ${field.effectiveFlagged ? "#f8717133" : "#131f2e"}`,
                      borderRadius: 8,
                      padding: "14px 20px",
                      textAlign: "left",
                      cursor: "pointer",
                      position: "relative",
                      overflow: "hidden",
                      transition: "background 0.15s",
                      display: "flex",
                      alignItems: "center",
                      gap: 20,
                      opacity: dim ? 0.45 : 1,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = "#0d1e30"; }}
                    onMouseLeave={e => { e.currentTarget.style.background = "#0b1622"; }}
                  >
                    {/* accent bar */}
                    <div style={{
                      position: "absolute", top: 0, left: 0,
                      width: 3, height: "100%",
                      background: dim ? "#2a4a60" : (field.effectiveFlagged ? "#ff0000" : "#4ade80"),
                      borderRadius: "8px 0 0 8px",
                    }} />

                    {/* Field name */}
                    <div style={{ flex: 1, paddingLeft: 4 }}>
                      <div style={{
                        fontFamily: "'Space Mono', monospace",
                        fontSize: 13,
                        fontWeight: 700,
                        color: "#c8ddef",
                        letterSpacing: "0.03em",
                      }}>
                        {field.field_name}
                      </div>
                    </div>

                    {/* Flagged status */}
                    <div style={{ minWidth: 110, textAlign: "center" }}>
                      <StatusPill
                        value={field.effectiveFlagged}
                        trueLabel="NEEDS ATTN"
                        falseLabel="ALL GOOD"
                        trueColor="#ff0000"
                        falseColor="#4ade80"
                      />
                    </div>

                    {/* Battery */}
                    <div style={{ minWidth: 80, textAlign: "center" }}>
                      <span style={{
                        fontFamily: "'Space Mono', monospace",
                        fontSize: 13,
                        fontWeight: 700,
                        color: batteryColor,
                      }}>
                        {field.battery != null ? `${field.battery.toFixed(2)}V` : "—"}
                      </span>
                    </div>

                    {/* Time last heard */}
                    <div style={{ minWidth: 160, textAlign: "right" }}>
                      <span style={{
                        fontFamily: "'Space Mono', monospace",
                        fontSize: 13,
                        color: "#6dc5ff",
                      }}>
                        {formatTimestamp(field.device_timestamp)}
                      </span>
                    </div>

                    {/* Arrow */}
                    <div style={{ width: 20, fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#2a4a60" }}>→</div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}

      </div>
    </>
  );
}
