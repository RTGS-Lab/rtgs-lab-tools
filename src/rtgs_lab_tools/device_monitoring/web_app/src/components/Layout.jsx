import { color, font, size, cardShadow } from "../theme";

export function SectionCard({ title, accent = color.accent, children }) {
  return (
    <div style={{
      background: color.surface,
      border: `1px solid ${color.border}`,
      borderRadius: 8,
      boxShadow: cardShadow,
      padding: "22px 26px",
      position: "relative",
      overflow: "hidden",
    }}>
      <div style={{
        position: "absolute",
        top: 0, left: 0,
        width: 3, height: "100%",
        background: accent,
        borderRadius: "8px 0 0 8px",
      }} />
      <div style={{
        fontFamily: font.mono,
        fontSize: size.lg,
        fontWeight: 600,
        color: accent,
        letterSpacing: "0.16em",
        textTransform: "uppercase",
        marginBottom: 16,
        paddingLeft: 4,
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

export function DataRow({ label, value, mono = true }) {
  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "flex-start",
      padding: "11px 0",
      borderBottom: `1px solid ${color.divider}`,
    }}>
      <span style={{
        fontFamily: font.mono,
        fontSize: size.sm,
        fontWeight: 500,
        color: color.textMuted,
        textTransform: "uppercase",
        letterSpacing: "0.09em",
        minWidth: 150,
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: mono ? font.mono : font.sans,
        fontSize: mono ? size.md : size.base,
        color: color.text,
        textAlign: "right",
        wordBreak: "break-all",
        maxWidth: "60%",
      }}>
        {value || "—"}
      </span>
    </div>
  );
}
