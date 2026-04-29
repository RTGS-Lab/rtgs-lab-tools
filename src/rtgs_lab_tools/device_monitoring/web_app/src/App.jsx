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

  useEffect(() => {
    fetchLoggerInfo().then(setLoggerInfo);
    fetchAllEntries().then(setAllEntries);
  }, []);

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
        if (isFlagged(entry.flagged)) flagged++;
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
