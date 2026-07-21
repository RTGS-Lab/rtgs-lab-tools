import { useState, useEffect } from "react";
import './App.css';
import {
  fetchLoggerInfo,
  fetchAllEntries,
  fetchIgnoredProblems,
  fetchConfig,
  fetchProductConfig,
  saveProductConfig,
  ignoreProblem,
  unignoreProblem,
} from "./api";
import { computeEffectiveFlagged, deriveProblems, resolveConfig } from "./utils";
import ProductSelector from "./components/ProductSelector";
import FieldSelector from "./components/FieldSelector";
import NodeMonitorDashboard from "./components/NodeMonitorDashboard";
import ConfigEditor from "./components/ConfigEditor";

function App() {
  const [loggerInfo, setLoggerInfo] = useState([]);
  const [allEntries, setAllEntries] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [view, setView] = useState("monitor"); // "monitor" | "config"
  const [config, setConfig] = useState({}); // global defaults from /api/config
  const [productConfig, setProductConfig] = useState({}); // { product_name: { key: value } }
  // Map of node_id -> array of ignored problem keys, loaded from the server.
  const [ignores, setIgnores] = useState({});

  useEffect(() => {
    fetchLoggerInfo().then(setLoggerInfo);
    fetchAllEntries().then(setAllEntries);
    fetchConfig().then(setConfig);
    fetchProductConfig().then(setProductConfig);
    fetchIgnoredProblems().then(loadIgnores);
  }, []);

  function loadIgnores(rows) {
    const map = {};
    for (const row of rows) {
      (map[row.node_id] ||= []).push(row.problem_key);
    }
    setIgnores(map);
  }

  async function addIgnore(nodeId, problemKey) {
    setIgnores(prev => {
      const keys = prev[nodeId] || [];
      if (keys.includes(problemKey)) return prev;
      return { ...prev, [nodeId]: [...keys, problemKey] };
    });
    try {
      await ignoreProblem(nodeId, problemKey);
    } catch {
      fetchIgnoredProblems().then(loadIgnores); // resync on failure
    }
  }

  async function removeIgnore(nodeId, problemKey) {
    setIgnores(prev => ({
      ...prev,
      [nodeId]: (prev[nodeId] || []).filter(k => k !== problemKey),
    }));
    try {
      await unignoreProblem(nodeId, problemKey);
    } catch {
      fetchIgnoredProblems().then(loadIgnores); // resync on failure
    }
  }

  async function handleSaveProductConfig(productNames, overrides) {
    const updated = await saveProductConfig(productNames, overrides);
    setProductConfig(updated);
  }

  // Effective config for a product = global defaults + that product's overrides.
  const nodeIdToProduct = Object.fromEntries(
    loggerInfo.map(l => [l.node_id, l.product_name])
  );

  function effectiveConfigForProduct(productName) {
    return resolveConfig(config, productConfig[productName] || {});
  }

  function getEffectiveFlagged(nodeId, entry) {
    const cfg = effectiveConfigForProduct(nodeIdToProduct[nodeId]);
    return computeEffectiveFlagged(deriveProblems(entry, cfg), ignores[nodeId] || []);
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
        if (getEffectiveFlagged(nodeId, entry)) flagged++;
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
          const nodeIgnores = ignores[l.node_id] || [];
          return {
            node_id: l.node_id,
            field_name: l.field_name,
            flagged: entry.flagged,
            effectiveFlagged: getEffectiveFlagged(l.node_id, entry),
            hasIgnores: nodeIgnores.length > 0,
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

  if (view === "config") {
    return (
      <ConfigEditor
        productNames={productNames}
        defaults={config}
        productConfig={productConfig}
        onSave={handleSaveProductConfig}
        onBack={() => setView("monitor")}
      />
    );
  }

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
        config={effectiveConfigForProduct(selectedProduct)}
        ignores={ignores}
        onIgnore={addIgnore}
        onUnignore={removeIgnore}
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
      onOpenConfig={() => setView("config")}
    />
  );
}

export default App;
