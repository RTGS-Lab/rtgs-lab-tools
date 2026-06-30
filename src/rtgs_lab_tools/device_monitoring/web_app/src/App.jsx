import { useState, useEffect } from "react";
import './App.css';
import { fetchLoggerInfo, fetchAllEntries } from "./api";
import { isFlagged } from "./utils";
import ProductSelector from "./components/ProductSelector";
import FieldSelector from "./components/FieldSelector";
import NodeMonitorDashboard from "./components/NodeMonitorDashboard";

function App() {
  const [loggerInfo, setLoggerInfo] = useState([]);
  const [allEntries, setAllEntries] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [overrides, setOverridesState] = useState(() => {
    try {
      const stored = localStorage.getItem('device-flag-overrides');
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  useEffect(() => {
    fetchLoggerInfo().then(setLoggerInfo);
    fetchAllEntries().then(setAllEntries);
  }, []);

  function setOverride(nodeId, value) {
    setOverridesState(prev => {
      const next = { ...prev };
      if (value === null) {
        delete next[nodeId];
      } else {
        next[nodeId] = value;
      }
      try {
        localStorage.setItem('device-flag-overrides', JSON.stringify(next));
      } catch {}
      return next;
    });
  }

  function getEffectiveFlagged(nodeId, rawFlagged) {
    if (nodeId in overrides) return overrides[nodeId];
    return isFlagged(rawFlagged);
  }

  const productNames = [...new Set(loggerInfo.map(l => l.product_name))].sort();

  // Latest monitoring entry per node_id
  const latestEntryPerNode = {};
  for (const entry of allEntries) {
    const existing = latestEntryPerNode[entry.node_id];
    if (!existing || entry.monitoring_timestamp > existing.monitoring_timestamp) {
      latestEntryPerNode[entry.node_id] = entry;
    }
  }

  // Flagged/ok counts per product (based on latest entry per node)
  const flaggedCountsPerProduct = {};
  for (const product of productNames) {
    const nodeIds = loggerInfo.filter(l => l.product_name === product).map(l => l.node_id);
    let flagged = 0, ok = 0;
    for (const nodeId of nodeIds) {
      const loggerEntry = loggerInfo.find(l => l.node_id === nodeId);
      if (!loggerEntry?.active) continue;
      const entry = latestEntryPerNode[nodeId];
      if (entry) {
        if (getEffectiveFlagged(nodeId, entry.flagged)) flagged++;
        else ok++;
      }
    }
    flaggedCountsPerProduct[product] = { flagged, ok };
  }

  // Fields for the selected product (with latest monitoring data)
  const productFields = selectedProduct
    ? loggerInfo
        .filter(l => l.product_name === selectedProduct)
        .map(l => {
          const entry = latestEntryPerNode[l.node_id] || {};
          return {
            node_id: l.node_id,
            field_name: l.field_name,
            flagged: entry.flagged,
            effectiveFlagged: getEffectiveFlagged(l.node_id, entry.flagged),
            hasOverride: l.node_id in overrides,
            battery: entry.battery != null ? entry.battery : null,
            device_timestamp: entry.time_of_last_device_connection || null,
            active: l.active,
          };
        })
        .sort((a, b) => a.field_name.localeCompare(b.field_name))
    : [];

  const allowedNodeIds = selectedProduct
    ? loggerInfo.filter(l => l.product_name === selectedProduct).map(l => l.node_id)
    : null;

  const nodeIdToFieldName = selectedProduct
    ? Object.fromEntries(
        loggerInfo
          .filter(l => l.product_name === selectedProduct)
          .map(l => [l.node_id, l.field_name])
      )
    : {};

  const nodeIdToParticleUrl = Object.fromEntries(
    loggerInfo.map(l => [l.node_id, l.particle_url])
  );

  if (selectedNodeId) {
    return (
      <NodeMonitorDashboard
        allowedNodeIds={allowedNodeIds}
        nodeIdToFieldName={nodeIdToFieldName}
        nodeIdToParticleUrl={nodeIdToParticleUrl}
        productName={selectedProduct}
        defaultNodeId={selectedNodeId}
        allEntriesProp={allEntries}
        onBack={() => setSelectedNodeId(null)}
        overrides={overrides}
        onOverride={setOverride}
      />
    );
  }

  if (selectedProduct) {
    return (
      <FieldSelector
        productName={selectedProduct}
        fields={productFields}
        onSelect={setSelectedNodeId}
        onBack={() => setSelectedProduct(null)}
      />
    );
  }

  return (
    <ProductSelector
      productNames={productNames}
      flaggedCounts={flaggedCountsPerProduct}
      onSelect={setSelectedProduct}
    />
  );
}

export default App;
