import { useState, useEffect, useCallback } from "react";
import { fetchAllEntries } from "../api";
import { formatTimestamp, getBatteryColor, getSystemColor, getHumidityColor, computeEffectiveFlagged, deriveProblems, parseErrors, formatErrorLocation, DEFAULT_CONFIG } from "../utils";
import { GaugeBarBattery, GaugeBarSystem, GaugeBarHumidity } from "./GaugeBars";
import StatusPill from "./StatusPill";
import { SectionCard, DataRow } from "./Layout";
import { NodeSelector, TimestampSelector } from "./Selectors";

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
          .sort((a, b) => Date.parse(b) - Date.parse(a))[0] || null;
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
    .sort((a, b) => Date.parse(b) - Date.parse(a));

  const entry = allEntries.find(
    e => e.node_id === selectedNode && e.monitoring_timestamp === selectedTs
  );

  const handleNodeChange = useCallback((id) => {
    setSelectedNode(id);
    const ts = allEntries
      .filter(e => e.node_id === id)
      .map(e => e.monitoring_timestamp)
      .sort((a, b) => Date.parse(b) - Date.parse(a))[0] || null;
    setSelectedTs(ts);
  }, [allEntries]);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "#060d14", color: "#60a5fa", fontFamily: "'Space Mono', monospace", fontSize: 13, letterSpacing: "0.1em" }}>
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

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #060d14; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #060d14; }
        ::-webkit-scrollbar-thumb { background: #1e2d40; border-radius: 3px; }
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
            <div>
              <h1 style={{ fontFamily: "'Space Mono', monospace", fontSize: 22, fontWeight: 200, color: "#e8f4ff", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                {defaultNodeId ? (nodeIdToFieldName[defaultNodeId] || defaultNodeId) : (productName || "Node Monitor")}
              </h1>
              {defaultNodeId && productName && (
                <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#2a4a60", letterSpacing: "0.12em", textTransform: "uppercase", marginTop: 4 }}>
                  {productName}
                </div>
              )}
            </div>
          </div>
          {!defaultNodeId && (
            <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 13, color: "#2a4a60", marginTop: 6 }}>
              {allEntries.length} entries across {nodeIds.length} field{nodeIds.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>

        {/* Node Selector — only shown when not navigating from a specific field */}
        {!defaultNodeId && (
          <>
            <SectionCard title="Field Name" accent="#8bbbf7">
              <NodeSelector nodeIds={nodeIds} selectedNode={selectedNode} onChange={handleNodeChange} nodeIdToFieldName={nodeIdToFieldName} />
            </SectionCard>
            <div style={{ height: 16 }} />
          </>
        )}

        {/* Timestamp Selector */}
        <SectionCard title="Monitoring Timestamp" accent="#a78bfa">
          {timestampsForNode.length > 0
            ? <TimestampSelector timestamps={timestampsForNode} selectedTs={selectedTs} onChange={setSelectedTs} />
            : <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#2a4060" }}>No entries</span>
          }
        </SectionCard>

        <div style={{ height: 24 }} />

        {/* Entry Detail */}
        {entry ? (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

              {/* Metrics */}
              <SectionCard title="Metrics" accent="#38bdf8">
                <GaugeBarBattery value={entry.battery} color={getBatteryColor(entry.battery)} label="Battery" />
                <GaugeBarSystem value={entry.system} color={getSystemColor(entry.system)} label="System Load" />
                <GaugeBarHumidity value={entry.humidity} color={getHumidityColor(entry.humidity)} label="Humidity" />
                <DataRow label="Last Connected" value={formatTimestamp(entry.time_of_last_device_connection)} />
              </SectionCard>

              {/* Status */}
              <SectionCard title="Status" accent="#38bdf8">
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div>
                    <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Flagged</div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <StatusPill value={effectiveFlagged} trueLabel="NEEDS ATTENTION" falseLabel="ALL GOOD" trueColor="#f87171" falseColor="#4ade80" />
                      {problems.length > 0 && !effectiveFlagged && (
                        <span style={{
                          fontFamily: "'Space Mono', monospace",
                          fontSize: 10,
                          color: "#a78bfa",
                          background: "#a78bfa18",
                          border: "1px solid #a78bfa33",
                          padding: "2px 7px",
                          borderRadius: 3,
                          letterSpacing: "0.08em",
                        }}>ALL IGNORED</span>
                      )}
                    </div>
                  </div>

                  {/* Per-problem ignore controls */}
                  <div>
                    <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Problems</div>
                    {problems.length === 0 ? (
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#4ade80", background: "#4ade8018", border: "1px solid #4ade8033", padding: "3px 10px", borderRadius: 4 }}>NONE</span>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {problems.map(p => {
                          const isIgnored = ignoredKeys.includes(p.key);
                          const accent = p.is_critical ? "#f87171" : "#facc15";
                          return (
                            <div key={p.key} style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 10,
                              padding: "8px 10px",
                              borderRadius: 6,
                              background: "#0b1622",
                              border: `1px solid ${isIgnored ? "#1e2d40" : accent + "33"}`,
                              opacity: isIgnored ? 0.5 : 1,
                            }}>
                              <span style={{ width: 6, height: 6, borderRadius: "50%", background: accent, flexShrink: 0 }} />
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                                  <span style={{
                                    fontFamily: "'Space Mono', monospace",
                                    fontSize: 12,
                                    color: p.is_critical ? "#f8a4a4" : "#d6c98a",
                                    textDecoration: isIgnored ? "line-through" : "none",
                                  }}>
                                    {p.label}
                                  </span>
                                  {p.is_critical && (
                                    <span style={{
                                      fontFamily: "'Space Mono', monospace",
                                      fontSize: 9,
                                      color: "#f87171",
                                      background: "#f8717118",
                                      border: "1px solid #f8717144",
                                      padding: "1px 5px",
                                      borderRadius: 3,
                                      letterSpacing: "0.1em",
                                    }}>CRITICAL</span>
                                  )}
                                </div>
                                {p.detail && (
                                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#4a6880", marginTop: 2 }}>
                                    {p.detail}
                                  </div>
                                )}
                              </div>
                              <button
                                onClick={() => (isIgnored ? onUnignore : onIgnore)(selectedNode, p.key)}
                                style={{
                                  background: "none",
                                  border: `1px solid ${isIgnored ? "#4ade8055" : "#1e2d40"}`,
                                  borderRadius: 4,
                                  color: isIgnored ? "#4ade80" : "#6dc5ff",
                                  fontFamily: "'Space Mono', monospace",
                                  fontSize: 10,
                                  letterSpacing: "0.08em",
                                  padding: "4px 9px",
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
                    <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Missing</div>
                    <StatusPill value={entry.is_missing} trueLabel="MISSING" falseLabel="CONNECTED" trueColor="#f87171" falseColor="#4ade80" />
                  </div>

                  {/* All errors (critical ones highlighted, matching the email) */}
                  <div>
                    <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Errors</div>
                    {errorRecords.length === 0 ? (
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#4ade80", background: "#4ade8018", border: "1px solid #4ade8033", padding: "3px 10px", borderRadius: 4 }}>NONE</span>
                    ) : (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {errorRecords.map((rec, i) => {
                          const critical = criticalErrors.includes(rec.error_name);
                          const color = critical ? "#f87171" : "#8899aa";
                          const where = formatErrorLocation(rec) || "—";
                          return (
                            <span key={`${rec.device_type}:${rec.device_position}:${rec.error_name}:${i}`} title={critical ? "Critical error" : "Error"} style={{
                              display: "inline-flex",
                              flexDirection: "column",
                              fontFamily: "'Space Mono', monospace",
                              fontSize: 11,
                              color,
                              background: `${color}18`,
                              border: `1px solid ${color}33`,
                              padding: "4px 10px",
                              borderRadius: 4,
                              fontWeight: critical ? 700 : 400,
                            }}>
                              <span>{critical && "⚠ "}{rec.error_name} ({rec.count})</span>
                              <span style={{ fontSize: 9, color: "#4a6880", fontWeight: 400, marginTop: 2 }}>{where}</span>
                            </span>
                          );
                        })}
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
                <SectionCard title="Particle Console" accent="#a78bfa">
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", minWidth: 80 }}>
                      Device URL
                    </span>
                    <a
                      href={nodeIdToParticleUrl[selectedNode]}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontFamily: "'Space Mono', monospace",
                        fontSize: 13,
                        color: "#a78bfa",
                        textDecoration: "none",
                        wordBreak: "break-all",
                        borderBottom: "1px solid #a78bfa44",
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
            background: "#0b1622",
            border: "1px solid #131f2e",
            borderRadius: 8,
            padding: 40,
            textAlign: "center",
            fontFamily: "'Space Mono', monospace",
            fontSize: 12,
            color: "#2a4060",
            letterSpacing: "0.1em",
          }}>
            SELECT A TIMESTAMP TO VIEW DATA
          </div>
        )}

        {/* Footer */}
        <div style={{ marginTop: 40, paddingTop: 20, borderTop: "1px solid #0f1c28", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#1a2c3a", letterSpacing: "0.15em" }}>
            NODE MONITOR v1.0
          </span>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#1a2c3a", letterSpacing: "0.1em" }}>
            {new Date().toISOString().slice(0, 19).replace("T", " ")} UTC
          </span>
        </div>

      </div>
    </>
  );
}
