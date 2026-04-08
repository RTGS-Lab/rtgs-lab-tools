import { useState, useEffect, useCallback } from "react";
import { fetchAllEntries } from "../api";
import { formatTimestamp, getBatteryColor, getSystemColor, getHumidityColor } from "../utils";
import { GaugeBarBattery, GaugeBarSystem, GaugeBarHumidity } from "./GaugeBars";
import StatusPill from "./StatusPill";
import { SectionCard, DataRow } from "./Layout";
import { NodeSelector, TimestampSelector } from "./Selectors";

export default function NodeMonitorDashboard({ allowedNodeIds, nodeIdToFieldName = {}, productName, defaultNodeId, allEntriesProp, onBack }) {
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
                  <StatusPill value={entry.flagged} trueLabel="NEEDS ATTENTION" falseLabel="ALL GOOD" trueColor="#f87171" falseColor="#4ade80" />
                </div>
                <div>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Missing</div>
                  <StatusPill value={entry.is_missing} trueLabel="MISSING" falseLabel="CONNECTED" trueColor="#f87171" falseColor="#4ade80" />
                </div>
                <div>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Errors</div>
                  {entry.errors
                    ? <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#f87171", background: "#f8717118", border: "1px solid #f8717133", padding: "3px 10px", borderRadius: 4 }}>{entry.errors}</span>
                    : <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#4ade80", background: "#4ade8018", border: "1px solid #4ade8033", padding: "3px 10px", borderRadius: 4 }}>NONE</span>
                  }
                </div>
              </div>
            </SectionCard>

          </div>
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