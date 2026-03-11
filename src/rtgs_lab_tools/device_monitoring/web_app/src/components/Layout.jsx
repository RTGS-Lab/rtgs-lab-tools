export function SectionCard({ title, accent = "#60a5fa", children }) {
  return (
    <div style={{
      background: "#0b1622",
      border: "1px solid #131f2e",
      borderRadius: 8,
      padding: "20px 24px",
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
        fontFamily: "'Space Mono', monospace",
        fontSize: 10,
        color: accent,
        letterSpacing: "0.2em",
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
      padding: "10px 0",
      borderBottom: "1px solid #0f1c28",
    }}>
      <span style={{
        fontFamily: "'Space Mono', monospace",
        fontSize: 11,
        color: "#4a6880",
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        minWidth: 140,
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: mono ? "'Space Mono', monospace" : "'DM Sans', sans-serif",
        fontSize: mono ? 12 : 13,
        color: "#c8ddef",
        textAlign: "right",
        wordBreak: "break-all",
        maxWidth: "60%",
      }}>
        {value || "—"}
      </span>
    </div>
  );
}
