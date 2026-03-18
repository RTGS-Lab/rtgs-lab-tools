import { useState, useEffect } from "react";
import './App.css';
import { fetchLoggerInfo } from "./api";
import ProductSelector from "./components/ProductSelector";
import NodeMonitorDashboard from "./components/NodeMonitorDashboard";

function App() {
  const [loggerInfo, setLoggerInfo] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);

  useEffect(() => {
    fetchLoggerInfo().then(setLoggerInfo);
  }, []);

  // Unique product names
  const productNames = [...new Set(loggerInfo.map(l => l.product_name))].sort();

  // Node IDs belonging to the selected product
  const allowedNodeIds = selectedProduct
    ? loggerInfo.filter(l => l.product_name === selectedProduct).map(l => l.node_id)
    : null;

  // Map from node_id -> field_name for the selected product
  const nodeIdToFieldName = selectedProduct
    ? Object.fromEntries(
        loggerInfo
          .filter(l => l.product_name === selectedProduct)
          .map(l => [l.node_id, l.field_name])
      )
    : {};

  if (selectedProduct) {
    return (
      <NodeMonitorDashboard
        allowedNodeIds={allowedNodeIds}
        nodeIdToFieldName={nodeIdToFieldName}
        productName={selectedProduct}
        onBack={() => setSelectedProduct(null)}
      />
    );
  }

  return (
    <ProductSelector
      productNames={productNames}
      onSelect={setSelectedProduct}
    />
  );
}

export default App;