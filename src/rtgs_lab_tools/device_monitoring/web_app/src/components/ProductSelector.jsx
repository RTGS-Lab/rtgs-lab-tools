import { color, font, size, cardShadow } from "../theme";
import { STATUS } from "../utils";

export default function ProductSelector({ productNames, onSelect, flaggedCounts = {}, onOpenConfig }) {
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
      <div style={{ marginBottom: 44 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 8 }}>
          <span style={{ fontFamily: font.mono, fontSize: size.tiny, letterSpacing: "0.3em", color: color.decor, textTransform: "uppercase" }}>
            ◈ SYSTEM
          </span>
          <div style={{ flex: 1, height: 1, background: color.divider }} />
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
          <h1 style={{ fontFamily: font.mono, fontSize: size.h1, fontWeight: 700, color: color.text, letterSpacing: "0.04em", textTransform: "uppercase" }}>
            Node Monitor
          </h1>
          {onOpenConfig && (
            <button onClick={onOpenConfig} style={{
              background: color.violetTint,
              border: `1px solid ${color.violet}55`,
              borderRadius: 5,
              color: color.violet,
              fontFamily: font.mono,
              fontSize: size.sm,
              fontWeight: 600,
              letterSpacing: "0.09em",
              padding: "8px 16px",
              cursor: "pointer",
              textTransform: "uppercase",
              whiteSpace: "nowrap",
            }}>
              ⚙ Configuration
            </button>
          )}
        </div>
        <p style={{ fontFamily: font.sans, fontSize: size.base, color: color.textMuted, marginTop: 8 }}>
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
              background: color.surface,
              border: `1px solid ${color.border}`,
              borderRadius: 8,
              boxShadow: cardShadow,
              padding: "26px 24px",
              textAlign: "left",
              cursor: "pointer",
              position: "relative",
              overflow: "hidden",
              transition: "border-color 0.2s, background 0.2s",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = color.accent;
              e.currentTarget.style.background = color.surfaceHover;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = color.border;
              e.currentTarget.style.background = color.surface;
            }}
          >
            {/* accent bar */}
            <div style={{
              position: "absolute", top: 0, left: 0,
              width: 3, height: "100%",
              background: color.accent,
              borderRadius: "8px 0 0 8px",
            }} />
            <div style={{
              fontFamily: font.mono,
              fontSize: size.xl,
              fontWeight: 600,
              color: color.text,
              letterSpacing: "0.02em",
              paddingLeft: 4,
            }}>
              {name}
            </div>
            <div style={{
              fontFamily: font.mono,
              fontSize: size.sm,
              fontWeight: 500,
              color: color.accent,
              marginTop: 10,
              letterSpacing: "0.09em",
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
              borderTop: `1px solid ${color.divider}`,
              display: "flex",
              gap: 16,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: STATUS.bad.fill, display: "inline-block", flexShrink: 0 }} />
                <span style={{ fontFamily: font.mono, fontSize: size.md, fontWeight: 600, color: STATUS.bad.ink, letterSpacing: "0.06em" }}>
                  {counts.flagged} FLAGGED
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: STATUS.good.fill, display: "inline-block", flexShrink: 0 }} />
                <span style={{ fontFamily: font.mono, fontSize: size.md, fontWeight: 600, color: STATUS.good.ink, letterSpacing: "0.06em" }}>
                  {counts.ok} OK
                </span>
              </div>
            </div>
          </button>
          );
        })}
      </div>

    </div>
  );
}
