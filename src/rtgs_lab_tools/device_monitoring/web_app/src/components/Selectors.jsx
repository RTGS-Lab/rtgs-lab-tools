import { color, font, size } from "../theme";

export function NodeSelector({ nodeIds, selectedNode, onChange, nodeIdToFieldName = {} }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {nodeIds.map(id => {
        const on = selectedNode === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            style={{
              padding: "7px 15px",
              borderRadius: 5,
              border: `1px solid ${on ? color.accent : color.border}`,
              background: on ? color.accentTint : color.surface,
              color: on ? color.accent : color.textMuted,
              fontFamily: font.mono,
              fontSize: size.md,
              fontWeight: on ? 600 : 400,
              cursor: "pointer",
              transition: "all 0.2s",
              letterSpacing: "0.04em",
            }}
          >
            {nodeIdToFieldName[id] ?? id}
          </button>
        );
      })}
    </div>
  );
}

export function TimestampSelector({ timestamps = [], selectedTs, onChange }) {
  const sorted = [...timestamps].sort((a, b) => Date.parse(b) - Date.parse(a));

  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      {sorted.map(ts => {
        const on = selectedTs === ts;
        return (
          <button
            key={ts}
            onClick={() => onChange(ts)}
            style={{
              padding: "6px 13px",
              borderRadius: 5,
              border: `1px solid ${on ? color.violet : color.border}`,
              background: on ? color.violetTint : color.surface,
              color: on ? color.violet : color.textMuted,
              fontFamily: font.mono,
              fontSize: size.md,
              fontWeight: on ? 600 : 400,
              cursor: "pointer",
              transition: "all 0.2s",
              letterSpacing: "0.02em",
              whiteSpace: "nowrap",
            }}
          >
            {ts.slice(0, 19)}
          </button>
        );
      })}
    </div>
  );
}
