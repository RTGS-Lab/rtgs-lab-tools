import { color, font, size } from "../theme";
import { partitionTimestamps, formatTimestampShort, RECENT_DAYS } from "../utils";

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
  const { recent, older } = partitionTimestamps(timestamps);
  // An older report stays selectable, but it lives in the dropdown rather than
  // the button row — so the dropdown, not a button, shows the active state.
  const selectedIsOlder = older.includes(selectedTs);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {recent.length > 0 ? (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {recent.map(ts => {
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
                {formatTimestampShort(ts)}
              </button>
            );
          })}
        </div>
      ) : (
        <span style={{ fontFamily: font.mono, fontSize: size.sm, color: color.textFaint }}>
          No reports in the last {RECENT_DAYS} days
        </span>
      )}

      {older.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <label
            htmlFor="older-report"
            style={{
              fontFamily: font.mono,
              fontSize: size.sm,
              fontWeight: 600,
              color: color.textMuted,
              letterSpacing: "0.11em",
              textTransform: "uppercase",
            }}
          >
            Older Reports
          </label>
          <select
            id="older-report"
            value={selectedIsOlder ? selectedTs : ""}
            onChange={e => { if (e.target.value) onChange(e.target.value); }}
            style={{
              padding: "6px 12px",
              borderRadius: 5,
              border: `1px solid ${selectedIsOlder ? color.violet : color.border}`,
              background: selectedIsOlder ? color.violetTint : color.surface,
              color: selectedIsOlder ? color.violet : color.textMuted,
              fontFamily: font.mono,
              fontSize: size.md,
              fontWeight: selectedIsOlder ? 600 : 400,
              cursor: "pointer",
              maxWidth: "100%",
            }}
          >
            <option value="">Select a report ({older.length})</option>
            {older.map(ts => (
              <option key={ts} value={ts}>{formatTimestampShort(ts)}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
