# Device Monitoring Grafana Dashboard

This directory contains a Grafana dashboard implementation that replaces the Python-based device monitoring system with a real-time dashboard showing flagged devices prominently and normal devices in collapsible sections.

## 🎯 Dashboard Features

### **Flagged-First Design**
- **🚨 Flagged Devices**: Always visible at the top with red highlighting
- **✅ Normal Devices**: Collapsed by default, expandable with click
- **📊 Overview**: Summary statistics and charts
- **📈 Historical Trends**: Time-series charts in expandable section

### **Smart Alerts**
- Battery voltage < 3.6V (red background)
- System power > 0.364W (red background) 
- Error messages present (flagged)
- Devices offline > 2 hours (flagged)
- Priority sorting by alert severity

## 📋 Installation Steps

### Step 1: Setup Database Views

1. **Connect to your GEMS database**:
   ```bash
   psql -h your-db-host -p 5432 -U your-username -d gems
   ```

2. **Run the view creation script**:
   ```bash
   \i /path/to/rtgs-lab-tools/src/rtgs_lab_tools/device_monitoring/grafana/setup_views.sql
   ```

3. **Verify views were created**:
   ```sql
   -- Check if views exist
   SELECT schemaname, viewname FROM pg_views WHERE viewname LIKE '%device%';
   
   -- Test data retrieval
   SELECT * FROM device_alert_status LIMIT 5;
   SELECT * FROM device_monitoring_summary;
   ```

### Step 2: Configure Grafana Data Source

1. **Open Grafana** (typically http://localhost:3000 or your Grafana URL)

2. **Add PostgreSQL Data Source**:
   - Go to **Configuration → Data Sources → Add data source**
   - Select **PostgreSQL**
   - Configure connection:
     ```
     Host: your-gems-db-host:5432
     Database: gems
     User: your-db-username
     Password: your-db-password
     SSL Mode: require (if needed)
     ```

3. **Test Connection** and **Save & Test**

### Step 3: Import Dashboard

1. **Import Dashboard**:
   - Go to **Dashboards → Import**
   - Click **Upload JSON file**
   - Select: `/path/to/rtgs-lab-tools/src/rtgs_lab_tools/device_monitoring/grafana/device_monitoring_dashboard.json`
   - Or copy/paste the JSON content

2. **Configure Data Source**:
   - Select your PostgreSQL data source from the dropdown
   - Click **Import**

3. **Set Dashboard Variables**:
   - **Data Source**: Select your PostgreSQL connection
   - **Project**: Choose project or "ALL" for all projects

### Step 4: Test the Dashboard

1. **Check Overview Section**:
   - Verify pie chart shows device status distribution
   - Confirm alert summary shows correct counts

2. **Verify Flagged Devices**:
   - Should show devices with battery < 3.6V, power > 0.364W, errors, or offline
   - Table should be sorted by alert priority

3. **Test Collapsible Sections**:
   - "Normal Devices" row should be collapsed by default
   - Click to expand and verify normal devices appear
   - "Historical Trends" should show time-series charts

## 🎛️ Dashboard Usage

### **Main Interface**
- **📊 Overview**: Quick stats and device status pie chart
- **🚨 Flagged Devices**: Critical issues requiring immediate attention
- **✅ Normal Devices**: Click to expand healthy devices
- **📈 Historical Trends**: Click to expand battery/power time-series

### **Filtering**
- **Project Dropdown**: Filter by specific project or view "ALL"
- **Time Range**: Upper right - adjust time window for historical data
- **Auto-Refresh**: Set to 5 minutes by default (configurable)

### **Alert Priority System**
1. **Priority 4** (Highest): Error messages present
2. **Priority 3**: Battery voltage < 3.6V  
3. **Priority 2**: System power > 0.364W
4. **Priority 1**: Device offline > 2 hours

### **Color Coding**
- 🔴 **Red Background**: Alert conditions (battery/power thresholds)
- 🟢 **Green**: Normal operating values
- 🟡 **Yellow**: Warning thresholds
- ⚪ **Gray**: Normal devices (collapsed section)

## 🔧 Customization Options

### **Modify Alert Thresholds**

Edit `setup_views.sql` and update:
```sql
-- Battery threshold
CASE WHEN ldm.battery_voltage < 3.6 THEN TRUE ELSE FALSE END as battery_alert,

-- Power threshold  
CASE WHEN ldm.system_power > 0.364 THEN TRUE ELSE FALSE END as power_alert,

-- Offline threshold
CASE WHEN ldm.last_seen < NOW() - INTERVAL '2 hours' THEN TRUE ELSE FALSE END as offline_alert,
```

### **Add Device Names**

If you have a device lookup table:
```sql
-- In device_alert_status view, replace:
COALESCE(ldm.node_id, 'Unknown Device') as device_name,

-- With:
COALESCE(lookup.device_name, ldm.node_id) as device_name,

-- And add JOIN:
LEFT JOIN device_lookup lookup ON ldm.node_id = lookup.node_id
```

### **Extend Data Retention**

Modify the time window in `latest_device_metrics`:
```sql
WHERE r.publish_time > NOW() - INTERVAL '30 days'  -- Extend from 7 to 30 days
```

### **Add More Projects**

The dashboard automatically discovers projects from your `node` table. New projects will appear in the dropdown after refresh.

## 🚨 Setting Up Alerting

### **Configure Grafana Alerts**

1. **Create Alert Rules**:
   ```
   Alert Rule: "Critical Battery Alert"
   Query: SELECT COUNT(*) FROM device_alert_status WHERE battery_alert = true
   Condition: IS ABOVE 0
   ```

2. **Notification Channels**:
   - Email: Send to your team
   - Slack: Post to monitoring channel
   - Webhook: Integrate with existing systems

3. **Alert Templates**:
   ```
   Subject: 🔋 {{ .CommonLabels.alertname }}
   Body: {{ .CommonAnnotations.summary }}
   Devices affected: {{ .CommonAnnotations.devices }}
   ```

## 📊 Sample Queries for Testing

Test these queries in Grafana's Explore tab:

### **Device Status Count**
```sql
SELECT 
  alert_state,
  COUNT(*) as count
FROM device_alert_status 
GROUP BY alert_state;
```

### **Recent Flagged Devices**
```sql
SELECT 
  node_id,
  battery_voltage,
  system_power,
  minutes_since_seen,
  alert_state
FROM device_alert_status 
WHERE alert_state = 'alerting'
ORDER BY alert_priority DESC;
```

### **Project Summary**
```sql
SELECT * FROM device_monitoring_summary ORDER BY project;
```

## 🔍 Troubleshooting

### **No Data Showing**
- Check database connection in Data Sources
- Verify views were created: `\dv` in psql
- Confirm data exists: `SELECT COUNT(*) FROM raw;`

### **Views Not Working**
- Check PostgreSQL version supports JSON operators (`::jsonb`, `->`, `->>`)
- Verify message format matches expected JSON structure
- Test individual JSON extractions

### **Performance Issues**
- Add indexes: Already included in `setup_views.sql`
- Reduce time window in views if needed
- Consider materialized views for large datasets

### **Dashboard Variables Not Loading**
- Refresh browser cache
- Check PostgreSQL data source connection
- Verify view permissions for Grafana user

## 📈 Performance Optimization

### **For Large Datasets**

1. **Create Materialized Views**:
   ```sql
   CREATE MATERIALIZED VIEW latest_device_metrics_mv AS 
   SELECT * FROM latest_device_metrics;
   
   -- Refresh periodically via cron
   REFRESH MATERIALIZED VIEW latest_device_metrics_mv;
   ```

2. **Add More Indexes**:
   ```sql
   CREATE INDEX idx_raw_jsonb_data ON raw USING GIN ((message::jsonb));
   CREATE INDEX idx_raw_publish_time_node ON raw(publish_time, node_id);
   ```

3. **Partition Raw Table** (if very large):
   ```sql
   -- Partition by month for better performance
   CREATE TABLE raw_2024_01 PARTITION OF raw 
   FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
   ```

This dashboard provides a modern, real-time replacement for the Python-based monitoring system with better visualization, alerting, and user experience!