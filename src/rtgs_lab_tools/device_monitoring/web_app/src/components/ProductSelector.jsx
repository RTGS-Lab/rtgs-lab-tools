export default function ProductSelector({ productNames, onSelect, flaggedCounts = {} }) {
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
        <div style={{ marginBottom: 48 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 6 }}>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, letterSpacing: "0.3em", color: "#1e4060", textTransform: "uppercase" }}>
              ◈ SYSTEM
            </span>
            <div style={{ flex: 1, height: 1, background: "#0f1c28" }} />
          </div>
          <h1 style={{ fontFamily: "'Space Mono', monospace", fontSize: 22, fontWeight: 700, color: "#e8f4ff", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Node Monitor
          </h1>
          <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 13, color: "#6dc5ff", marginTop: 6 }}>
            Select a product to view its nodes
          </p>
        </div>

        {/* Product Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 16 }}>
          {productNames.map(name => {
            const counts = flaggedCounts[name] || { flagged: 0, ok: 0 };
            return (
            <button
              key={name}
              onClick={() => onSelect(name)}
              style={{
                background: "#0b1622",
                border: "1px solid #131f2e",
                borderRadius: 8,
                padding: "28px 24px",
                textAlign: "left",
                cursor: "pointer",
                position: "relative",
                overflow: "hidden",
                transition: "border-color 0.2s, background 0.2s",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = "#60a5fa44";
                e.currentTarget.style.background = "#0d1e30";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = "#131f2e";
                e.currentTarget.style.background = "#0b1622";
              }}
            >
              {/* accent bar */}
              <div style={{
                position: "absolute", top: 0, left: 0,
                width: 3, height: "100%",
                background: "#6dc5ff",
                borderRadius: "8px 0 0 8px",
              }} />
              <div style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 16,
                fontWeight: 300,
                color: "#c8ddef",
                letterSpacing: "0.05em",
                paddingLeft: 4,
              }}>
                {name}
              </div>
              <div style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: 12,
                color: "#6dc5ff",
                marginTop: 10,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                paddingLeft: 4,
              }}>
                View nodes →
              </div>

              {/* Flagged / OK indicator */}
              <div style={{
                marginTop: 16,
                paddingTop: 12,
                paddingLeft: 4,
                borderTop: "1px solid #0f1c28",
                display: "flex",
                gap: 16,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#f87171", display: "inline-block", flexShrink: 0 }} />
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 14, color: "#f87171", letterSpacing: "0.08em" }}>
                    {counts.flagged} FLAGGED
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#4ade80", display: "inline-block", flexShrink: 0 }} />
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 14, color: "#4ade80", letterSpacing: "0.08em" }}>
                    {counts.ok} OK
                  </span>
                </div>
              </div>
            </button>
            );
          })}
        </div>

      </div>
    </>
  );
}
