# Sensing Data Module

Extract and manage environmental sensor data from the GEMS PostgreSQL database.

## CLI Usage

### List Available Projects

```bash
rtgs sensing-data list-projects
```

List all available projects in the GEMS database with node counts.

### Extract Data

```bash
# Basic extraction
rtgs sensing-data extract --project "Winter Turf - v3" --start-date 2023-01-01 --end-date 2023-01-31

# Filter by specific nodes
rtgs sensing-data extract --project "My Project" --node-ids "e00fce68f374e425e2d6b891,f00fce68f374e425e2d6b892"

# Create compressed archive
rtgs sensing-data extract --project "My Project" --create-zip

# Export as Parquet format
rtgs sensing-data extract --project "My Project" --output-format parquet

# Custom output directory
rtgs sensing-data extract --project "My Project" --output-dir ./my-data/
```

### Command Options

- `--project TEXT`: Project name to extract data from (required)
- `--start-date TEXT`: Start date in YYYY-MM-DD format (default: 30 days ago)
- `--end-date TEXT`: End date in YYYY-MM-DD format (default: today)
- `--node-ids TEXT`: Comma-separated list of node IDs to filter
- `--output-dir PATH`: Output directory (default: ./data)
- `--output-format [csv|parquet]`: Output format (default: csv)
- `--create-zip`: Create a compressed ZIP archive
- `--retry-count INTEGER`: Maximum retry attempts for database operations (default: 3)

## Python API Usage

### Import and Basic Usage

```python
from rtgs_lab_tools.sensing_data import extract_data, list_available_projects

# List all projects
projects = list_available_projects()
for project_name, node_count in projects:
    print(f"{project_name}: {node_count} nodes")

# Extract data
results = extract_data(
    project="Winter Turf - v3",
    start_date="2023-01-01",
    end_date="2023-01-31",
    output_format="csv"
)

print(f"Extracted {results['records_extracted']} records")
print(f"Output file: {results['output_file']}")
```

### Advanced Usage

```python
from rtgs_lab_tools.sensing_data.data_extractor import DataExtractor
from rtgs_lab_tools.core import DatabaseManager

# Direct database access
db_manager = DatabaseManager()
extractor = DataExtractor(db_manager)

# Extract with custom parameters
data = extractor.extract_project_data(
    project="My Project",
    start_date="2023-01-01",
    end_date="2023-01-31",
    node_ids=["e00fce68f374e425e2d6b891", "f00fce68f374e425e2d6b892"]
)

# Process the data
print(f"Retrieved {len(data)} records")
```

### Low-level Database Operations

```python
from rtgs_lab_tools.sensing_data.data_extractor import list_projects
from rtgs_lab_tools.core import DatabaseManager

# Direct project listing
db_manager = DatabaseManager()
projects = list_projects(db_manager, max_retries=5)

for project_name, node_count in projects:
    print(f"{project_name}: {node_count} nodes")
```

## Output Formats

### CSV Format
- Human-readable, Excel-compatible
- Default format for easy data analysis
- Includes full metadata headers

### Parquet Format
- Efficient binary format for large datasets
- Better compression and faster I/O
- Preserves data types accurately

### File Naming Convention
```
Project_Name_YYYY-MM-DD_to_YYYY-MM-DD_YYYYMMDDHHMMSS.{csv|parquet}
```

Example: `Winter_Turf_v3_2023-01-01_to_2023-01-31_20240315143022.csv`

## Configuration

### Database Connection
Requires connection to the GEMS PostgreSQL database via UMN VPN.

Environment variables (in `.env` file):
```env
DB_HOST=sensing-0.msi.umn.edu
DB_PORT=5433
DB_NAME=gems
DB_USER=your_username
DB_PASSWORD=your_password
```

### Network Requirements
- **UMN VPN**: Required for database access
- **Database Credentials**: Contact Bryan Runck (runck014@umn.edu)

## Data Integrity

All extractions include:
- SHA-256 hash verification
- Detailed metadata files
- Query parameters and statistics
- Automatic git logging for audit trails

## Error Handling

The module includes robust error handling with:
- Automatic retry logic for database connections
- Comprehensive logging of all operations
- Graceful handling of network interruptions
- Detailed error messages with context

## Examples

### Extract Recent Data
```bash
# Extract last 7 days of data
rtgs sensing-data extract --project "My Project" --start-date $(date -d '7 days ago' +%Y-%m-%d)
```

### Batch Processing
```python
from rtgs_lab_tools.sensing_data import extract_data, list_available_projects

# Extract data from all projects
projects = list_available_projects()
for project_name, _ in projects:
    print(f"Processing {project_name}...")
    results = extract_data(
        project=project_name,
        start_date="2023-01-01",
        end_date="2023-01-31",
        create_zip=True
    )
    print(f"Completed: {results['output_file']}")
```

## Troubleshooting

### Database Connection Issues
1. Ensure UMN VPN is connected
2. Verify credentials in `.env` file
3. Check firewall settings
4. Test connection with `rtgs sensing-data list-projects`

### Common Errors
- **No data found**: Check project name spelling and date range
- **Connection timeout**: Verify VPN connection and retry
- **Permission denied**: Ensure database credentials are correct