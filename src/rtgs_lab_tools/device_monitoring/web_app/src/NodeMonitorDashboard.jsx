import { useState, useEffect, useCallback } from "react";


// --- API helpers (swap MOCK_DATA with real fetch in production) ---
async function fetchAllEntries() {
  const res = await fetch("http://localhost:5000/api/entries");
  return res.json();
}

// --- Utility ---
function formatTimestamp(ts) {
  if (!ts) return "—";
  return ts.replace("T", " ").slice(0, 23);
}

function getBatteryColor(val) {
  if (val >= 3.6) return "#4ade80";
  if (val >= 3.4) return "#facc15";
  return "#f87171";
}

function getSystemColor(val) {
  if (val >= 85) return "#f87171";
  if (val >= 60) return "#facc15";
  return "#4ade80";
}

function getHumidityColor(val) {
  if (val > 70 || val < 20) return "#facc15";
  return "#60a5fa";
}

// --- Sub-components ---

function GaugeBar({ value, max = 100, color, label }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#8899aa", letterSpacing: "0.08em", textTransform: "uppercase" }}>{label}</span>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, color, fontWeight: 700 }}>{value.toFixed(1)}%</span>
      </div>
      <div style={{ height: 6, background: "#1a2233", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 3, transition: "width 0.5s cubic-bezier(0.4,0,0.2,1)" }} />
      </div>
    </div>
  );
}

function StatusPill({ value, trueLabel = "YES", falseLabel = "NO", trueColor = "#f87171", falseColor = "#4ade80" }) {
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

function NodeSelector({ nodeIds, selectedNode, onChange }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {nodeIds.map(id => (
        <button
          key={id}
          onClick={() => onChange(id)}
          style={{
            padding: "6px 14px",
            borderRadius: 4,
            border: selectedNode === id ? "1px solid #60a5fa" : "1px solid #1e2d40",
            background: selectedNode === id ? "#60a5fa18" : "#0d1520",
            color: selectedNode === id ? "#60a5fa" : "#4a6080",
            fontFamily: "'Space Mono', monospace",
            fontSize: 12,
            cursor: "pointer",
            transition: "all 0.2s",
            letterSpacing: "0.05em",
          }}
        >
          {id}
        </button>
      ))}
    </div>
  );
}

function TimestampSelector({ timestamps, selectedTs, onChange }) {
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      {timestamps.map(ts => (
        <button
          key={ts}
          onClick={() => onChange(ts)}
          style={{
            padding: "5px 12px",
            borderRadius: 4,
            border: selectedTs === ts ? "1px solid #a78bfa" : "1px solid #1e2d40",
            background: selectedTs === ts ? "#a78bfa18" : "#0a1018",
            color: selectedTs === ts ? "#a78bfa" : "#3a5060",
            fontFamily: "'Space Mono', monospace",
            fontSize: 11,
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

function DataRow({ label, value, mono = true }) {
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

function SectionCard({ title, accent = "#60a5fa", children }) {
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

// --- Main Dashboard ---
export default function NodeMonitorDashboard() {
  const [allEntries, setAllEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedTs, setSelectedTs] = useState(null);

  useEffect(() => {
    fetchAllEntries().then(data => {
      setAllEntries(data);
      setLoading(false);
      if (data.length > 0) {
        setSelectedNode(data[0].node_id);
        setSelectedTs(data[0].monitoring_timestamp);
      }
    });
  }, []);

  const nodeIds = [...new Set(allEntries.map(e => e.node_id))].sort();

  const timestampsForNode = allEntries
    .filter(e => e.node_id === selectedNode)
    .map(e => e.monitoring_timestamp)
    .sort();

  const entry = allEntries.find(
    e => e.node_id === selectedNode && e.monitoring_timestamp === selectedTs
  );

  const handleNodeChange = useCallback((id) => {
    setSelectedNode(id);
    const ts = allEntries.find(e => e.node_id === id)?.monitoring_timestamp || null;
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
            <span style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 10,
              letterSpacing: "0.3em",
              color: "#1e4060",
              textTransform: "uppercase",
            }}>
              ◈ SYSTEM
            </span>
            <div style={{ flex: 1, height: 1, background: "#0f1c28" }} />
          </div>
          <h1 style={{
            fontFamily: "'Space Mono', monospace",
            fontSize: 22,
            fontWeight: 700,
            color: "#e8f4ff",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}>
            Node Monitor
          </h1>
          <p style={{ fontFamily: "'DM Sans', sans-serif", fontSize: 13, color: "#2a4a60", marginTop: 6 }}>
            {allEntries.length} entries across {nodeIds.length} node{nodeIds.length !== 1 ? "s" : ""}
          </p>
        </div>

        {/* Node Selector */}
        <SectionCard title="Node ID" accent="#60a5fa">
          <NodeSelector nodeIds={nodeIds} selectedNode={selectedNode} onChange={handleNodeChange} />
        </SectionCard>

        <div style={{ height: 16 }} />

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
            <SectionCard title="Metrics" accent="#4ade80">
              <GaugeBar value={entry.battery} color={getBatteryColor(entry.battery)} label="Battery" />
              <GaugeBar value={entry.system} color={getSystemColor(entry.system)} label="System Load" />
              <GaugeBar value={entry.humidity} color={getHumidityColor(entry.humidity)} label="Humidity" />
            </SectionCard>

            {/* Status */}
            <SectionCard title="Status" accent="#f97316">
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Flagged</div>
                  <StatusPill value={entry.flagged} trueLabel="FLAGGED" falseLabel="CLEAR" trueColor="#f87171" falseColor="#4ade80" />
                </div>
                <div>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Missing</div>
                  <StatusPill value={entry.is_missing} trueLabel="MISSING" falseLabel="PRESENT" trueColor="#f87171" falseColor="#4ade80" />
                </div>
                <div>
                  <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#4a6880", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Errors</div>
                  {entry.errors
                    ? <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#f87171", background: "#f8717118", border: "1px solid #f8717133", padding: "3px 10px", borderRadius: 4 }}>{entry.errors}</span>
                    : <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#4ade80", background: "#4ade8018", border: "1px solid #4ade8033", padding: "3px 10px", borderRadius: 4 }}>NONE</span>
                  }
                </div>
              </div>
            </SectionCard>

            {/* Timestamps */}
            <div style={{ gridColumn: "1 / -1" }}>
              <SectionCard title="Timestamps" accent="#38bdf8">
                <DataRow label="Monitoring TS" value={formatTimestamp(entry.monitoring_timestamp)} />
                <DataRow label="Device TS" value={formatTimestamp(entry.device_timestamp)} />
                <DataRow label="Last Heard" value={formatTimestamp(entry.last_heard)} />
              </SectionCard>
            </div>

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
            SELECT A NODE AND TIMESTAMP TO VIEW DATA
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
