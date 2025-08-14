-- Device Monitoring Dashboard Queries for Read-Only Database
-- Since the database is read-only, these are the direct queries to use in Grafana panels
-- Copy and paste these into your Grafana dashboard panels instead of creating views
-- Updated to match the actual database schema with Diagnostic/Kestrel structure

-- =============================================================================
-- QUERY 1: DEVICE STATUS OVERVIEW (for pie chart and summary stats)
-- Use this for: Overview pie chart and Alert Summary stat panel
-- =============================================================================

WITH device_metrics AS (
    WITH parsed_data AS (
        SELECT 
            r.node_id,
            n.project,
            r.publish_time,
            r.message,
            -- Extract battery voltage (PORT_V[0])
            (elems1->'Kestrel'->'PORT_V'->>0)::float as battery_voltage,
            -- Extract system power (AVG_P[1])  
            (elems1->'Kestrel'->'AVG_P'->>1)::float as system_power,
            -- Extract error information (adjust based on your error message format)
            CASE 
                WHEN r.event = 'error/v2' OR r.message::text LIKE '%"Error"%'
                THEN r.message::jsonb->>'Error'
                ELSE NULL
            END as error_message,
            -- Rank by publish_time to get latest per node
            ROW_NUMBER() OVER (PARTITION BY r.node_id ORDER BY r.publish_time DESC) as rn
        FROM raw r
        JOIN node n ON r.node_id = n.node_id,
        jsonb_array_elements((r.message::jsonb)->'Diagnostic'->'Devices') elems1
        WHERE r.publish_time > NOW() - INTERVAL '7 days'
          AND r.event = 'diagnostic/v2'
          AND elems1 ? 'Kestrel'
          AND is_valid_json(r.message) 
          AND is_valid_time(r.message)
    )
    SELECT 
        node_id,
        project,
        publish_time as last_seen,
        battery_voltage,
        system_power,
        error_message,
        -- Alert conditions
        CASE WHEN battery_voltage < 3.6 THEN TRUE ELSE FALSE END as battery_alert,
        CASE WHEN system_power > 0.364 THEN TRUE ELSE FALSE END as power_alert,  
        CASE WHEN error_message IS NOT NULL THEN TRUE ELSE FALSE END as error_alert,
        -- Minutes since last seen
        EXTRACT(EPOCH FROM (NOW() - publish_time))/60 as minutes_since_seen,
        CASE WHEN publish_time < NOW() - INTERVAL '2 hours' THEN TRUE ELSE FALSE END as offline_alert,
        -- Overall alert status
        CASE 
            WHEN battery_voltage < 3.6 OR 
                 system_power > 0.364 OR 
                 error_message IS NOT NULL OR
                 publish_time < NOW() - INTERVAL '2 hours'
            THEN 'alerting'
            ELSE 'ok' 
        END as alert_state,
        -- Alert priority (higher number = more urgent)
        CASE 
            WHEN battery_voltage < 3.6 THEN 3
            WHEN system_power > 0.364 THEN 2  
            WHEN error_message IS NOT NULL THEN 4
            WHEN publish_time < NOW() - INTERVAL '2 hours' THEN 1
            ELSE 0
        END as alert_priority
    FROM parsed_data 
    WHERE rn = 1
)
-- PIE CHART QUERY: Device Status Overview
SELECT 
  'Flagged Devices' as metric,
  COUNT(CASE WHEN alert_state = 'alerting' THEN 1 END) as value
FROM device_metrics
WHERE ('${project}' = 'ALL' OR project = '${project}')
UNION ALL
SELECT 
  'Normal Devices' as metric,
  COUNT(CASE WHEN alert_state = 'ok' THEN 1 END) as value
FROM device_metrics
WHERE ('${project}' = 'ALL' OR project = '${project}');

-- =============================================================================
-- QUERY 2: ALERT SUMMARY STATS
-- Use this for: Alert Summary stat panel (modify the SELECT for different metrics)
-- =============================================================================

WITH device_metrics AS (
    -- [Same CTE as above - copy the full CTE from Query 1]
    WITH parsed_data AS (
        SELECT 
            r.node_id,
            n.project,
            r.publish_time,
            r.message,
            -- Extract battery voltage (PORT_V[0])
            (elems1->'Kestrel'->'PORT_V'->>0)::float as battery_voltage,
            -- Extract system power (AVG_P[1])  
            (elems1->'Kestrel'->'AVG_P'->>1)::float as system_power,
            -- Extract error information
            CASE 
                WHEN r.event = 'error/v2' OR r.message::text LIKE '%"Error"%'
                THEN r.message::jsonb->>'Error'
                ELSE NULL
            END as error_message,
            ROW_NUMBER() OVER (PARTITION BY r.node_id ORDER BY r.publish_time DESC) as rn
        FROM $project_key.raw r
        JOIN node n ON r.node_id = n.node_id,
        jsonb_array_elements((r.message::jsonb)->'Diagnostic'->'Devices') elems1
        WHERE r.publish_time > NOW() - INTERVAL '7 days'
          AND r.event = 'diagnostic/v2'
          AND elems1 ? 'Kestrel'
          AND is_valid_json(r.message) 
          AND is_valid_time(r.message)
    )
    SELECT 
        node_id,
        project,
        publish_time as last_seen,
        battery_voltage,
        system_power,
        error_message,
        CASE WHEN battery_voltage < 3.6 THEN TRUE ELSE FALSE END as battery_alert,
        CASE WHEN system_power > 0.364 THEN TRUE ELSE FALSE END as power_alert,  
        CASE WHEN error_message IS NOT NULL THEN TRUE ELSE FALSE END as error_alert,
        EXTRACT(EPOCH FROM (NOW() - publish_time))/60 as minutes_since_seen,
        CASE WHEN publish_time < NOW() - INTERVAL '2 hours' THEN TRUE ELSE FALSE END as offline_alert,
        CASE 
            WHEN battery_voltage < 3.6 OR 
                 system_power > 0.364 OR 
                 error_message IS NOT NULL OR
                 publish_time < NOW() - INTERVAL '2 hours'
            THEN 'alerting'
            ELSE 'ok' 
        END as alert_state,
        CASE 
            WHEN battery_voltage < 3.6 THEN 3
            WHEN system_power > 0.364 THEN 2  
            WHEN error_message IS NOT NULL THEN 4
            WHEN publish_time < NOW() - INTERVAL '2 hours' THEN 1
            ELSE 0
        END as alert_priority
    FROM parsed_data 
    WHERE rn = 1
)
-- STAT PANEL QUERY: Multiple metrics for stat panel
SELECT 
  'Total Devices' as metric,
  COUNT(*) as value
FROM device_metrics
WHERE ('${project}' = 'ALL' OR project = '${project}')
UNION ALL
SELECT 
  'Flagged' as metric,
  COUNT(CASE WHEN alert_state = 'alerting' THEN 1 END) as value
FROM device_metrics
WHERE ('${project}' = 'ALL' OR project = '${project}')
UNION ALL
SELECT 
  'Battery Alerts' as metric,
  COUNT(CASE WHEN battery_alert THEN 1 END) as value
FROM device_metrics
WHERE ('${project}' = 'ALL' OR project = '${project}')
UNION ALL
SELECT 
  'Power Alerts' as metric,
  COUNT(CASE WHEN power_alert THEN 1 END) as value
FROM device_metrics
WHERE ('${project}' = 'ALL' OR project = '${project}')
UNION ALL
SELECT 
  'Error Alerts' as metric,
  COUNT(CASE WHEN error_alert THEN 1 END) as value
FROM device_metrics
WHERE ('${project}' = 'ALL' OR project = '${project}')
UNION ALL
SELECT 
  'Offline Devices' as metric,
  COUNT(CASE WHEN offline_alert THEN 1 END) as value
FROM device_metrics
WHERE ('${project}' = 'ALL' OR project = '${project}');

-- =============================================================================
-- QUERY 3: FLAGGED DEVICES TABLE
-- Use this for: The main flagged devices table that's always visible
-- =============================================================================

WITH device_metrics AS (
    -- [Same CTE as above]
    WITH parsed_data AS (
        SELECT 
            r.node_id,
            n.project,
            r.publish_time,
            r.message,
            -- Extract battery voltage (PORT_V[0])
            (elems1->'Kestrel'->'PORT_V'->>0)::float as battery_voltage,
            -- Extract system power (AVG_P[1])  
            (elems1->'Kestrel'->'AVG_P'->>1)::float as system_power,
            -- Extract error information
            CASE 
                WHEN r.event = 'error/v2' OR r.message::text LIKE '%"Error"%'
                THEN r.message::jsonb->>'Error'
                ELSE NULL
            END as error_message,
            ROW_NUMBER() OVER (PARTITION BY r.node_id ORDER BY r.publish_time DESC) as rn
        FROM $project_key.raw r
        JOIN node n ON r.node_id = n.node_id,
        jsonb_array_elements((r.message::jsonb)->'Diagnostic'->'Devices') elems1
        WHERE r.publish_time > NOW() - INTERVAL '7 days'
          AND r.event = 'diagnostic/v2'
          AND elems1 ? 'Kestrel'
          AND is_valid_json(r.message) 
          AND is_valid_time(r.message)
    )
    SELECT 
        node_id,
        project,
        publish_time as last_seen,
        battery_voltage,
        system_power,
        error_message,
        CASE WHEN battery_voltage < 3.6 THEN TRUE ELSE FALSE END as battery_alert,
        CASE WHEN system_power > 0.364 THEN TRUE ELSE FALSE END as power_alert,  
        CASE WHEN error_message IS NOT NULL THEN TRUE ELSE FALSE END as error_alert,
        EXTRACT(EPOCH FROM (NOW() - publish_time))/60 as minutes_since_seen,
        CASE WHEN publish_time < NOW() - INTERVAL '2 hours' THEN TRUE ELSE FALSE END as offline_alert,
        CASE 
            WHEN battery_voltage < 3.6 OR 
                 system_power > 0.364 OR 
                 error_message IS NOT NULL OR
                 publish_time < NOW() - INTERVAL '2 hours'
            THEN 'alerting'
            ELSE 'ok' 
        END as alert_state,
        CASE 
            WHEN battery_voltage < 3.6 THEN 3
            WHEN system_power > 0.364 THEN 2  
            WHEN error_message IS NOT NULL THEN 4
            WHEN publish_time < NOW() - INTERVAL '2 hours' THEN 1
            ELSE 0
        END as alert_priority
    FROM parsed_data 
    WHERE rn = 1
)
-- FLAGGED DEVICES TABLE
SELECT 
  node_id as "Device ID",
  COALESCE(node_id, 'Unknown Device') as "Device Name",
  alert_state as "Status",
  battery_voltage as "Battery (V)",
  system_power as "Power (W)", 
  error_message as "Error",
  ROUND(minutes_since_seen::numeric, 1) as "Minutes Since Seen",
  last_seen as "Last Seen",
  alert_priority
FROM device_metrics
WHERE alert_state = 'alerting'
  AND ('${project}' = 'ALL' OR project = '${project}')
ORDER BY alert_priority DESC, last_seen DESC;

-- =============================================================================
-- QUERY 4: NORMAL DEVICES TABLE (for collapsible section)
-- Use this for: The normal devices table in the collapsible row
-- =============================================================================

WITH device_metrics AS (
    -- [Same CTE as above - abbreviated for space]
    WITH parsed_data AS (
        SELECT 
            r.node_id,
            n.project,
            r.publish_time,
            -- Extract battery voltage (PORT_V[0])
            (elems1->'Kestrel'->'PORT_V'->>0)::float as battery_voltage,
            -- Extract system power (AVG_P[1])  
            (elems1->'Kestrel'->'AVG_P'->>1)::float as system_power,
            -- Extract error information
            CASE 
                WHEN r.event = 'error/v2' OR r.message::text LIKE '%"Error"%'
                THEN r.message::jsonb->>'Error'
                ELSE NULL
            END as error_message,
            ROW_NUMBER() OVER (PARTITION BY r.node_id ORDER BY r.publish_time DESC) as rn
        FROM $project_key.raw r
        JOIN node n ON r.node_id = n.node_id,
        jsonb_array_elements((r.message::jsonb)->'Diagnostic'->'Devices') elems1
        WHERE r.publish_time > NOW() - INTERVAL '7 days'
          AND r.event = 'diagnostic/v2'
          AND elems1 ? 'Kestrel'
          AND is_valid_json(r.message) 
          AND is_valid_time(r.message)
    )
    SELECT 
        node_id,
        project,
        publish_time as last_seen,
        battery_voltage,
        system_power,
        error_message,
        EXTRACT(EPOCH FROM (NOW() - publish_time))/60 as minutes_since_seen,
        CASE 
            WHEN battery_voltage < 3.6 OR 
                 system_power > 0.364 OR 
                 error_message IS NOT NULL OR
                 publish_time < NOW() - INTERVAL '2 hours'
            THEN 'alerting'
            ELSE 'ok' 
        END as alert_state
    FROM parsed_data 
    WHERE rn = 1
)
-- NORMAL DEVICES TABLE  
SELECT 
  node_id as "Device ID",
  COALESCE(node_id, 'Unknown Device') as "Device Name",
  alert_state as "Status",
  battery_voltage as "Battery (V)",
  system_power as "Power (W)",
  ROUND(minutes_since_seen::numeric, 1) as "Minutes Since Seen",
  last_seen as "Last Seen"
FROM device_metrics
WHERE alert_state = 'ok'
  AND ('${project}' = 'ALL' OR project = '${project}')
ORDER BY node_id;

-- =============================================================================
-- QUERY 5: BATTERY VOLTAGE TIME SERIES (for historical trends)
-- Use this for: Battery voltage time series chart in collapsible section
-- =============================================================================

SELECT 
  $__timeGroup(r.publish_time,'1h') as time,
  r.node_id as metric,
  AVG((elems1->'Kestrel'->'PORT_V'->>0)::float) as value
FROM $project_key.raw r
JOIN node n ON r.node_id = n.node_id,
jsonb_array_elements((r.message::jsonb)->'Diagnostic'->'Devices') elems1
WHERE $__timeFilter(r.publish_time)
  AND ('${project}' = 'ALL' OR n.project = '${project}')
  AND r.event = 'diagnostic/v2'
  AND elems1 ? 'Kestrel'
  AND is_valid_json(r.message) 
  AND is_valid_time(r.message)
GROUP BY time, r.node_id
ORDER BY time;

-- =============================================================================
-- QUERY 6: SYSTEM POWER TIME SERIES (for historical trends)
-- Use this for: System power time series chart in collapsible section
-- =============================================================================

SELECT 
  $__timeGroup(r.publish_time,'1h') as time,
  r.node_id as metric,
  AVG((elems1->'Kestrel'->'AVG_P'->>1)::float) as value
FROM $project_key.raw r
JOIN node n ON r.node_id = n.node_id,
jsonb_array_elements((r.message::jsonb)->'Diagnostic'->'Devices') elems1
WHERE $__timeFilter(r.publish_time)
  AND ('${project}' = 'ALL' OR n.project = '${project}')
  AND r.event = 'diagnostic/v2'
  AND elems1 ? 'Kestrel'
  AND is_valid_json(r.message) 
  AND is_valid_time(r.message)
GROUP BY time, r.node_id
ORDER BY time;

-- =============================================================================
-- QUERY 7: PROJECT DROPDOWN VALUES (for dashboard variable)
-- Use this for: Dashboard template variable query
-- =============================================================================

SELECT DISTINCT project 
FROM node 
WHERE project IS NOT NULL 
ORDER BY CASE WHEN project = 'ALL' THEN 0 ELSE 1 END, project;