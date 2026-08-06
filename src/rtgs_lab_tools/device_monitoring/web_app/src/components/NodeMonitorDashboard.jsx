import { useState, useEffect, useCallback } from "react";
import { fetchAllEntries } from "../api";
import { formatTimestamp, parseUtcTimestamp, getBatteryLevel, getSystemLevel, getHumidityLevel, STATUS, computeEffectiveFlagged, deriveProblems, parseErrors, formatErrorLocation, DEFAULT_CONFIG } from "../utils";
import { GaugeBarBattery, GaugeBarSystem, GaugeBarHumidity } from "./GaugeBars";
import StatusPill from "./StatusPill";
import { SectionCard, DataRow } from "./Layout";
import { NodeSelector, TimestampSelector } from "./Selectors";
import { color, font, size, cardShadow } from "../theme";

// Sub-label above each block inside the Status card ("Flagged", "Problems", …).
const subLabel = {
  fontFamily: font.mono,
  fontSize: size.sm,
  fontWeight: 600,
  color: color.textMuted,
  letterSpacing: "0.11em",
  textTransform: "uppercase",
  marginBottom: 8,
};

// "NONE" chip — bright green tints it, dark green ink carries the label.
const noneChip = {
  fontFamily: font.mono,
  fontSize: size.xs,
  fontWeight: 600,
  color: STATUS.good.ink,
  background: `${STATUS.good.fill}26`,
  border: `1px solid ${STATUS.good.fill}66`,
  padding: "4px 11px",
  borderRadius: 4,
};

export default function NodeMonitorDashboard({ allowedNodeIds, nodeIdToFieldName = {}, nodeIdToParticleUrl = {}, productName, defaultNodeId, allEntriesProp, onBack, config = {}, ignores = {}, onIgnore, onUnignore }) {
  const [allEntries, setAllEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedTs, setSelectedTs] = useState(null);

  useEffect(() => {
    const load = allEntriesProp != null
      ? Promise.resolve(allEntriesProp)
      : fetchAllEntries();

    load.then(data => {
      const filtered = allowedNodeIds
        ? data.filter(e => allowedNodeIds.includes(e.node_id))
        : data;
      setAllEntries(filtered);
      setLoading(false);
      const startNode = defaultNodeId || (filtered.length > 0 ? filtered[0].node_id : null);
      if (startNode) {
        setSelectedNode(startNode);
        const ts = filtered
          .filter(e => e.node_id === startNode)
          .map(e => e.monitoring_timestamp)
          .sort((a, b) => (parseUtcTimestamp(b)?.getTime() ?? 0) - (parseUtcTimestamp(a)?.getTime() ?? 0))[0] || null;
        setSelectedTs(ts);
      }
    });
  }, [allowedNodeIds, defaultNodeId, allEntriesProp]);

  const nodeIds = [...new Set(allEntries.map(e => e.node_id))].sort((a, b) => {
    const nameA = nodeIdToFieldName[a] ?? a;
    const nameB = nodeIdToFieldName[b] ?? b;
    return nameA.localeCompare(nameB);
  });

  const timestampsForNode = allEntries
    .filter(e => e.node_id === selectedNode)
    .map(e => e.monitoring_timestamp)
    .sort((a, b) => (parseUtcTimestamp(b)?.getTime() ?? 0) - (parseUtcTimestamp(a)?.getTime() ?? 0));

  const entry = allEntries.find(
    e => e.node_id === selectedNode && e.monitoring_timestamp === selectedTs
  );

  const handleNodeChange = useCallback((id) => {
    setSelectedNode(id);
    const ts = allEntries
      .filter(e => e.node_id === id)
      .map(e => e.monitoring_timestamp)
      .sort((a, b) => (parseUtcTimestamp(b)?.getTime() ?? 0) - (parseUtcTimestamp(a)?.getTime() ?? 0))[0] || null;
    setSelectedTs(ts);
  }, [allEntries]);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: color.pageBg, color: color.accent, fontFamily: font.mono, fontSize: size.base, letterSpacing: "0.1em" }}>
        LOADING...
      </div>
    );
  }

  // Problem / ignore state for the selected node + entry. Problems are derived
  // from the raw metrics using this product's effective (possibly overridden)
  // config, so per-product threshold changes are reflected immediately.
  const problems = deriveProblems(entry, config);
  const criticalErrors = config.critical_errors || DEFAULT_CONFIG.critical_errors;
  const ignoredKeys = ignores[selectedNode] || [];
  const effectiveFlagged = computeEffectiveFlagged(problems, ignoredKeys);

  // Parse the raw errors JSON into per-sensor records for display
  const errorRecords = parseErrors(entry?.errors);

  // Group errors under a subheader per sensor (device_type [position]).
  // Sensors are listed alphabetically, and each sensor's errors alphabetically.
  const errorsBySensor = (() => {
    const groups = new Map();
    for (const rec of errorRecords) {
      const sensor = formatErrorLocation(rec) || "—";
      if (!groups.has(sensor)) groups.set(sensor, []);
      groups.get(sensor).push(rec);
    }
    return [...groups.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([sensor, recs]) => [
        sensor,
        recs.slice().sort((x, y) => x.error_name.localeCompare(y.error_name)),
      ]);
  })();

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
          <div>
            <h1 style={{ fontFamily: font.mono, fontSize: size.h1, fontWeight: 700, color: color.text, letterSpacing: "0.04em", textTransform: "uppercase" }}>
              {defaultNodeId ? (nodeIdToFieldName[defaultNodeId] || defaultNodeId) : (productName || "Node Monitor")}
            </h1>
            {defaultNodeId && productName && (
              <div style={{ fontFamily: font.mono, fontSize: size.xs, fontWeight: 500, color: color.textFaint, letterSpacing: "0.12em", textTransform: "uppercase", marginTop: 5 }}>
                {productName}
              </div>
            )}
          </div>
        </div>
        {!defaultNodeId && (
          <p style={{ fontFamily: font.sans, fontSize: size.base, color: color.textMuted, marginTop: 8 }}>
            {allEntries.length} entries across {nodeIds.length} field{nodeIds.length !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      {/* Node Selector — only shown when not navigating from a specific field */}
      {!defaultNodeId && (
        <>
          <SectionCard title="Field Name" accent={color.accent}>
            <NodeSelector nodeIds={nodeIds} selectedNode={selectedNode} onChange={handleNodeChange} nodeIdToFieldName={nodeIdToFieldName} />
          </SectionCard>
          <div style={{ height: 16 }} />
        </>
      )}

      {/* Timestamp Selector */}
      <SectionCard title="Monitoring Timestamp" accent={color.violet}>
        {timestampsForNode.length > 0
          ? <TimestampSelector timestamps={timestampsForNode} selectedTs={selectedTs} onChange={setSelectedTs} />
          : <span style={{ fontFamily: font.mono, fontSize: size.sm, color: color.textFaint }}>No entries</span>
        }
      </SectionCard>

      <div style={{ height: 24 }} />

      {/* Entry Detail */}
      {entry ? (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

            {/* Metrics */}
            <SectionCard title="Metrics" accent={color.teal}>
              <GaugeBarBattery value={entry.battery} level={getBatteryLevel(entry.battery)} label="Battery" />
              <GaugeBarSystem value={entry.system} level={getSystemLevel(entry.system)} label="System Load" />
              <GaugeBarHumidity value={entry.humidity} level={getHumidityLevel(entry.humidity)} label="Humidity" />
              <DataRow label="Last Connected" value={formatTimestamp(entry.time_of_last_device_connection)} />
            </SectionCard>

            {/* Status */}
            <SectionCard title="Status" accent={color.teal}>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <div style={subLabel}>Flagged</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <StatusPill value={effectiveFlagged} trueLabel="NEEDS ATTENTION" falseLabel="ALL GOOD" />
                    {problems.length > 0 && !effectiveFlagged && (
                      <span style={{
                        fontFamily: font.mono,
                        fontSize: size.xs,
                        fontWeight: 600,
                        color: color.violet,
                        background: color.violetTint,
                        border: `1px solid ${color.violet}44`,
                        padding: "3px 9px",
                        borderRadius: 3,
                        letterSpacing: "0.07em",
                      }}>ALL IGNORED</span>
                    )}
                  </div>
                </div>

                {/* Per-problem ignore controls */}
                <div>
                  <div style={subLabel}>Problems</div>
                  {problems.length === 0 ? (
                    <span style={noneChip}>NONE</span>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {problems.map(p => {
                        const isIgnored = ignoredKeys.includes(p.key);
                        // Severity is carried by the dot, the border and the
                        // CRITICAL badge, while the label itself takes the
                        // readable body color.
                        const severity = STATUS[p.is_critical ? "bad" : "warn"];
                        return (
                          <div key={p.key} style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 10,
                            padding: "9px 11px",
                            borderRadius: 6,
                            background: color.surfaceSunken,
                            border: `1px solid ${isIgnored ? color.border : severity.fill + "77"}`,
                            opacity: isIgnored ? 0.6 : 1,
                          }}>
                            <span style={{ width: 7, height: 7, borderRadius: "50%", background: severity.fill, flexShrink: 0 }} />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                                <span style={{
                                  fontFamily: font.mono,
                                  fontSize: size.sm,
                                  fontWeight: 500,
                                  color: color.text,
                                  textDecoration: isIgnored ? "line-through" : "none",
                                }}>
                                  {p.label}
                                </span>
                                {p.is_critical && (
                                  <span style={{
                                    fontFamily: font.mono,
                                    fontSize: size.micro,
                                    fontWeight: 700,
                                    color: STATUS.bad.ink,
                                    background: `${STATUS.bad.fill}26`,
                                    border: `1px solid ${STATUS.bad.fill}77`,
                                    padding: "1px 6px",
                                    borderRadius: 3,
                                    letterSpacing: "0.09em",
                                  }}>CRITICAL</span>
                                )}
                              </div>
                              {p.detail && (
                                <div style={{ fontFamily: font.mono, fontSize: size.xs, color: color.textMuted, marginTop: 3 }}>
                                  {p.detail}
                                </div>
                              )}
                            </div>
                            <button
                              onClick={() => (isIgnored ? onUnignore : onIgnore)(selectedNode, p.key)}
                              style={{
                                background: color.surface,
                                border: `1px solid ${isIgnored ? `${STATUS.good.fill}88` : color.borderStrong}`,
                                borderRadius: 4,
                                color: isIgnored ? STATUS.good.ink : color.accent,
                                fontFamily: font.mono,
                                fontSize: size.xs,
                                fontWeight: 600,
                                letterSpacing: "0.06em",
                                padding: "5px 10px",
                                cursor: "pointer",
                                textTransform: "uppercase",
                                flexShrink: 0,
                              }}
                            >
                              {isIgnored ? "Un-ignore" : "Ignore"}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div>
                  <div style={subLabel}>Missing</div>
                  <StatusPill value={entry.is_missing} trueLabel="MISSING" falseLabel="CONNECTED" />
                </div>

                {/* All errors (critical ones highlighted, matching the email) */}
                <div>
                  <div style={subLabel}>Errors</div>
                  {errorRecords.length === 0 ? (
                    <span style={noneChip}>NONE</span>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      {errorsBySensor.map(([sensor, recs]) => (
                        <div key={sensor}>
                          <div style={{
                            fontFamily: font.mono,
                            fontSize: size.sm,
                            fontWeight: 600,
                            color: color.accent,
                            letterSpacing: "0.06em",
                            marginBottom: 7,
                            paddingBottom: 4,
                            borderBottom: `1px solid ${color.border}`,
                          }}>
                            {sensor}
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                            {recs.map((rec, i) => {
                              const critical = criticalErrors.includes(rec.error_name);
                              // Critical errors get the red tint with red ink;
                              // ordinary ones stay neutral so the red stands out.
                              const tint = critical ? STATUS.bad.fill : color.textMuted;
                              const chipInk = critical ? STATUS.bad.ink : color.textMuted;
                              return (
                                <span key={`${rec.error_name}:${i}`} title={critical ? "Critical error" : "Error"} style={{
                                  fontFamily: font.mono,
                                  fontSize: size.xs,
                                  color: chipInk,
                                  background: `${tint}1a`,
                                  border: `1px solid ${tint}55`,
                                  padding: "4px 11px",
                                  borderRadius: 4,
                                  fontWeight: critical ? 700 : 500,
                                }}>
                                  {critical && "⚠ "}{rec.error_name} ({rec.count})
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </SectionCard>

          </div>

          {/* Particle URL */}
          {nodeIdToParticleUrl[selectedNode] && (
            <>
              <div style={{ height: 16 }} />
              <SectionCard title="Particle Console" accent={color.violet}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontFamily: font.mono, fontSize: size.sm, fontWeight: 600, color: color.textMuted, letterSpacing: "0.11em", textTransform: "uppercase", minWidth: 90 }}>
                    Device URL
                  </span>
                  <a
                    href={nodeIdToParticleUrl[selectedNode]}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontFamily: font.mono,
                      fontSize: size.base,
                      color: color.violet,
                      textDecoration: "none",
                      wordBreak: "break-all",
                      borderBottom: `1px solid ${color.violet}66`,
                      paddingBottom: 1,
                    }}
                  >
                    {nodeIdToParticleUrl[selectedNode]}
                  </a>
                </div>
              </SectionCard>
            </>
          )}
        </>
      ) : (
        <div style={{
          background: color.surface,
          border: `1px solid ${color.border}`,
          borderRadius: 8,
          boxShadow: cardShadow,
          padding: 40,
          textAlign: "center",
          fontFamily: font.mono,
          fontSize: size.sm,
          color: color.textFaint,
          letterSpacing: "0.1em",
        }}>
          SELECT A TIMESTAMP TO VIEW DATA
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: 40, paddingTop: 20, borderTop: `1px solid ${color.divider}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: font.mono, fontSize: size.tiny, color: color.textFaint, letterSpacing: "0.14em" }}>
          NODE MONITOR v1.0
        </span>
        <span style={{ fontFamily: font.mono, fontSize: size.tiny, color: color.textFaint, letterSpacing: "0.09em" }}>
          {formatTimestamp(new Date().toISOString())}
        </span>
      </div>

    </div>
  );
}
