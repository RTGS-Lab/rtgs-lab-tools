export default function StatusPill({ value, trueLabel = "YES", falseLabel = "NO", trueColor = "#f87171", falseColor = "#4ade80" }) {
  const isTrue = value === "true" || value === true;
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: 99,
      fontSize: 11,
      fontFamily: "'Space Mono', monospace",
      fontWeight: 700,
      letterSpacing: "0.1em",
      background: isTrue ? `${trueColor}22` : `${falseColor}22`,
      color: isTrue ? trueColor : falseColor,
      border: `1px solid ${isTrue ? trueColor : falseColor}44`,
    }}>
      {isTrue ? trueLabel : falseLabel}
    </span>
  );
}
