export function NodeSelector({ nodeIds, selectedNode, onChange, nodeIdToFieldName = {} }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {nodeIds.map(id => (
        <button
          key={id}
          onClick={() => onChange(id)}
          style={{
            padding: "6px 14px",
            borderRadius: 4,
            border: selectedNode === id ? "1px solid #8bbbf7" : "1px solid #a3a3a3",
            background: selectedNode === id ? "#60a5fa18" : "#0d1520",
            color: selectedNode === id ? "#8bbbf7" : "#a3a3a3",
            fontFamily: "'Space Mono', monospace",
            fontSize: 14,
            cursor: "pointer",
            transition: "all 0.2s",
            letterSpacing: "0.05em",
          }}
        >
          {nodeIdToFieldName[id] ?? id}
        </button>
      ))}
    </div>
  );
}

export function TimestampSelector({ timestamps = [], selectedTs, onChange }) {
  const sorted = [...timestamps].sort((a, b) => Date.parse(b) - Date.parse(a));

  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      {sorted.map(ts => (
        <button
          key={ts}
          onClick={() => onChange(ts)}
          style={{
            padding: "5px 12px",
            borderRadius: 4,
            border: selectedTs === ts ? "1px solid #a78bfa" : "1px solid #a3a3a3",
            background: selectedTs === ts ? "#a78bfa18" : "#0a1018",
            color: selectedTs === ts ? "#a78bfa" : "#a3a3a3",
            fontFamily: "'Space Mono', monospace",
            fontSize: 14,
            cursor: "pointer",
            transition: "all 0.2s",
            letterSpacing: "0.03em",
            whiteSpace: "nowrap",
          }}
        >
          {ts.slice(0, 19)}
        </button>
      ))}
    </div>
  );
}
