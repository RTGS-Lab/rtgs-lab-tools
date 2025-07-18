# Audit Module

Track and analyze tool usage, generate reports, and create reproduction scripts for RTGS Lab Tools.

## CLI Usage

### View Recent Activity

```bash
# Show recent tool executions
rtgs audit recent

# Show last 20 operations
rtgs audit recent --limit 20

# Show activity from last hour
rtgs audit recent --minutes 60

# Filter by specific tool
rtgs audit recent --tool-name sensing-data
```

### Generate Audit Reports

```bash
# Generate reports for date range
rtgs audit report --start-date 2023-06-01 --end-date 2023-06-30

# Generate reports for specific tool
rtgs audit report --start-date 2023-06-01 --end-date 2023-06-30 --tool-name visualization

# Custom output directory
rtgs audit report --start-date 2023-06-01 --end-date 2023-06-30 --output-dir ./audit_reports
```

### Create Reproduction Scripts

```bash
# Create script from curated log files
rtgs audit reproduce --logs-dir ./logs --output-file reproduce_analysis.sh

# Quick script from recent activity
rtgs audit reproduce --recent --minutes 30 --output-file recent_work.sh
```

### Postgres Logging Control

```bash
# Check current logging status
rtgs audit postgres-logging-status

# Enable postgres logging globally
rtgs audit enable-postgres-logging

# Disable postgres logging globally
rtgs audit disable-postgres-logging
```

### Command Options

**recent:**
- `--limit INTEGER`: Maximum number of recent logs to return (default: 10)
- `--tool-name TEXT`: Filter by specific tool name
- `--minutes INTEGER`: Only show logs from the last N minutes

**report:**
- `--start-date TEXT`: Start date in YYYY-MM-DD format (required)
- `--end-date TEXT`: End date in YYYY-MM-DD format (required)
- `--tool-name TEXT`: Filter by specific tool name
- `--output-dir TEXT`: Directory to save log files (default: logs)

**reproduce:**
- `--logs-dir TEXT`: Directory containing log files to process (default: logs)
- `--output-file TEXT`: Name for the generated script file (default: reproduce_commands.sh)

## Python API Usage

### Import and Basic Usage

```python
from rtgs_lab_tools.audit import recent_logs, generate_report, create_reproduction_script

# Get recent activity
logs = recent_logs(limit=20, tool_name="sensing-data")
for log in logs:
    print(f"{log['timestamp']}: {log['operation']} - {log['status']}")

# Generate audit report
report_files = generate_report(
    start_date="2023-06-01",
    end_date="2023-06-30",
    output_dir="./audit_reports"
)
print(f"Generated {len(report_files)} report files")

# Create reproduction script
script_info = create_reproduction_script(
    logs_dir="./audit_reports",
    output_file="reproduce_june_analysis.sh"
)
print(f"Created reproduction script: {script_info['script_path']}")
```

### Advanced Audit Analysis

```python
from rtgs_lab_tools.audit.audit_service import AuditService
import pandas as pd

# Initialize audit service
audit = AuditService()

# Get detailed audit data
audit_data = audit.get_audit_logs(
    start_date="2023-06-01",
    end_date="2023-06-30",
    include_details=True
)

# Convert to DataFrame for analysis
df = pd.DataFrame(audit_data)

# Analyze tool usage patterns
tool_usage = df.groupby('tool_name').agg({
    'operation_id': 'count',
    'duration_seconds': ['mean', 'sum'],
    'success': 'mean'
}).round(2)

print("Tool Usage Statistics:")
print(tool_usage)

# Find most active days
daily_activity = df.groupby(df['timestamp'].dt.date).size()
print(f"\nMost active day: {daily_activity.idxmax()} ({daily_activity.max()} operations)")
```

### Custom Report Generation

```python
from rtgs_lab_tools.audit.report_service import ReportService
from datetime import datetime, timedelta

# Initialize report service
reporter = ReportService()

# Generate weekly reports
end_date = datetime.now()
start_date = end_date - timedelta(weeks=4)

weekly_reports = reporter.generate_weekly_reports(
    start_date=start_date,
    end_date=end_date,
    output_dir="./weekly_reports"
)

for week, report_path in weekly_reports.items():
    print(f"Week {week}: {report_path}")
```

### Reproduction Script Customization

```python
from rtgs_lab_tools.audit.report_service import create_custom_reproduction_script

# Create script with specific filters
script_config = {
    "include_tools": ["sensing-data", "visualization"],
    "exclude_operations": ["list-projects"],
    "add_timing": True,
    "add_error_handling": True
}

script_path = create_custom_reproduction_script(
    logs_dir="./filtered_logs",
    output_file="custom_reproduction.sh",
    config=script_config
)

print(f"Custom script created: {script_path}")
```

## Audit Log Structure

### Log Entry Format

Each audit log entry contains:

```json
{
    "timestamp": "2023-06-15T14:30:22.123Z",
    "operation_id": "uuid4-string",
    "tool_name": "sensing-data",
    "operation": "extract",
    "user": "username",
    "git_branch": "feature/analysis",
    "git_commit": "abc123...",
    "parameters": {
        "project": "Winter Turf - v3",
        "start_date": "2023-01-01",
        "end_date": "2023-01-31"
    },
    "results": {
        "success": true,
        "records_extracted": 15420,
        "output_file": "./data/Winter_Turf_v3_2023-01-01_to_2023-01-31.csv"
    },
    "duration_seconds": 45.7,
    "note": "Monthly analysis for winter conditions"
}
```

### Database Schema

The audit system uses PostgreSQL for storage with the following tables:

**audit_logs:**
- `id`: Primary key
- `timestamp`: Operation timestamp
- `operation_id`: Unique operation identifier
- `tool_name`: Name of the tool used
- `operation`: Specific operation performed
- `user_name`: User who executed the operation
- `git_branch`: Git branch at execution time
- `git_commit_hash`: Git commit hash
- `parameters`: JSON parameters passed to operation
- `results`: JSON results from operation
- `duration_seconds`: Execution duration
- `success`: Boolean success indicator
- `error_message`: Error details if failed
- `note`: User-provided note

## Report Types

### Daily Reports
Generated markdown files showing all operations for a specific day:

```markdown
# Audit Report - 2023-06-15

## Summary
- Total Operations: 12
- Successful: 11 (91.7%)
- Failed: 1 (8.3%)
- Tools Used: sensing-data, visualization, gridded-data

## Operations

### 14:30:22 - sensing-data extract ✅
- **Project**: Winter Turf - v3
- **Date Range**: 2023-01-01 to 2023-01-31
- **Records**: 15,420
- **Duration**: 45.7s
- **Output**: ./data/Winter_Turf_v3_2023-01-01_to_2023-01-31.csv
```

### Weekly Summaries
Aggregated statistics and trends over a week period.

### Tool-Specific Reports
Detailed analysis of individual tool usage patterns.

## Reproduction Scripts

### Generated Script Structure

```bash
#!/bin/bash
# Reproduction script generated on 2023-06-15T16:45:30
# Original execution timespan: 2023-06-01 to 2023-06-30

set -e  # Exit on error

echo "Starting reproduction of RTGS Lab Tools operations..."

# Ensure correct git state
git checkout abc123...

# Operation 1: Extract sensing data
echo "Executing: sensing-data extract (2023-06-01 14:30:22)"
rtgs sensing-data extract \
  --project "Winter Turf - v3" \
  --start-date "2023-01-01" \
  --end-date "2023-01-31" \
  --note "Reproduction: Monthly analysis for winter conditions"

# Operation 2: Create visualization
echo "Executing: visualization create (2023-06-01 14:32:15)"
rtgs visualization create \
  --file "./data/Winter_Turf_v3_2023-01-01_to_2023-01-31.csv" \
  --parameter "Temperature" \
  --node-id "LCCMR_01" \
  --note "Reproduction: Temperature analysis visualization"

echo "Reproduction script completed successfully"
```

### Script Features

- **Git state management**: Checks out correct commits for each operation
- **Error handling**: Stops execution on failures
- **Progress tracking**: Shows which operation is being executed
- **Parameter preservation**: Exact parameters from original execution
- **Note annotation**: Marks operations as reproductions

## Usage Patterns

### Research Workflow Tracking

```python
from rtgs_lab_tools.audit import recent_logs
import pandas as pd

# Track a research session
session_logs = recent_logs(minutes=120)  # Last 2 hours

# Analyze the workflow
workflow_df = pd.DataFrame(session_logs)
workflow_df['step'] = range(1, len(workflow_df) + 1)

print("Research Session Workflow:")
for _, step in workflow_df.iterrows():
    print(f"  {step['step']}. {step['tool_name']} {step['operation']}")
    print(f"     Duration: {step['duration_seconds']:.1f}s")
    if step['note']:
        print(f"     Note: {step['note']}")
    print()
```

### Quality Assurance

```python
from rtgs_lab_tools.audit import generate_report
from datetime import datetime, timedelta

# Generate QA report for recent work
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

qa_files = generate_report(
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d"),
    output_dir="./qa_review"
)

# Review failed operations
failed_ops = []
for file_path in qa_files:
    with open(file_path, 'r') as f:
        content = f.read()
        if '❌' in content:  # Failed operation marker
            failed_ops.append(file_path)

print(f"QA Review: {len(failed_ops)} files contain failed operations")
```

### Collaboration and Sharing

```python
from rtgs_lab_tools.audit import create_reproduction_script

# Create reproduction script for sharing analysis
script_info = create_reproduction_script(
    logs_dir="./shared_analysis_logs",
    output_file="shared_analysis_reproduction.sh"
)

print(f"Reproduction script created for collaboration:")
print(f"  Script: {script_info['script_path']}")
print(f"  Operations: {script_info['operation_count']}")
print(f"  Time span: {script_info['start_date']} to {script_info['end_date']}")
```

## Configuration

### Postgres Logging Setup

The audit system requires PostgreSQL for persistent logging:

```env
# In .env file
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rtgs_audit
POSTGRES_USER=audit_user
POSTGRES_PASSWORD=audit_password
```

### Global Logging Control

```python
from rtgs_lab_tools.audit.audit_service import set_global_logging

# Enable logging for all tools
set_global_logging(enabled=True)

# Disable logging (operations will still work but won't be logged)
set_global_logging(enabled=False)

# Check current status
from rtgs_lab_tools.audit.audit_service import get_logging_status
status = get_logging_status()
print(f"Postgres logging enabled: {status['enabled']}")
```

## Examples

### Weekly Report Generation

```python
from rtgs_lab_tools.audit import generate_report
from datetime import datetime, timedelta
import os

# Generate reports for each week of the month
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

current_date = start_date
week_reports = []

while current_date < end_date:
    week_end = min(current_date + timedelta(days=7), end_date)
    
    report_files = generate_report(
        start_date=current_date.strftime("%Y-%m-%d"),
        end_date=week_end.strftime("%Y-%m-%d"),
        output_dir=f"./reports/week_{current_date.strftime('%Y%m%d')}"
    )
    
    week_reports.append({
        'week': current_date.strftime('%Y-%m-%d'),
        'files': report_files
    })
    
    current_date = week_end

print(f"Generated reports for {len(week_reports)} weeks")
```

### Tool Performance Analysis

```python
from rtgs_lab_tools.audit.audit_service import AuditService
import pandas as pd
import matplotlib.pyplot as plt

# Get performance data
audit = AuditService()
logs = audit.get_audit_logs(
    start_date="2023-06-01",
    end_date="2023-06-30"
)

df = pd.DataFrame(logs)

# Analyze tool performance
performance = df.groupby('tool_name')['duration_seconds'].agg([
    'count', 'mean', 'std', 'min', 'max'
]).round(2)

print("Tool Performance Summary:")
print(performance)

# Plot tool usage over time
daily_usage = df.groupby([
    df['timestamp'].dt.date, 
    'tool_name'
]).size().unstack(fill_value=0)

daily_usage.plot(kind='bar', stacked=True, figsize=(12, 6))
plt.title('Daily Tool Usage - June 2023')
plt.xlabel('Date')
plt.ylabel('Number of Operations')
plt.legend(title='Tool')
plt.tight_layout()
plt.show()
```

## Integration

### With All Modules

The audit module automatically tracks operations from all other RTGS Lab Tools modules:

```python
from rtgs_lab_tools import sensing_data, visualization, audit

# Normal tool usage - automatically logged
data = sensing_data.extract_data(project="Research Project")
plot = visualization.create_time_series_plot(data, "Temperature")

# Review what was just done
recent = audit.recent_logs(limit=5)
for log in recent:
    print(f"{log['tool_name']}: {log['operation']} - {log['success']}")
```

### Custom Operation Logging

```python
from rtgs_lab_tools.audit.audit_service import log_custom_operation

# Log custom analysis steps
with log_custom_operation("custom_analysis", "statistical_summary") as logger:
    # Perform custom analysis
    results = perform_statistical_analysis(data)
    
    # Log results
    logger.add_result("mean_temperature", results.mean())
    logger.add_result("std_temperature", results.std())
    logger.add_note("Statistical summary of temperature data")
```