# Data Parser Module

Parse and process raw sensor data files from GEMS devices, converting JSON message formats into structured data.

## CLI Usage

### List Available Parsers

```bash
# List all available packet type parsers
rtgs data-parser list-parsers
```

### Parse Data Files

```bash
# Basic parsing - parse all packet types
rtgs data-parser parse --input-file raw_data.csv --output-file parsed_data.csv

# Parse specific packet types
rtgs data-parser parse --input-file raw_data.csv --output-file parsed_data.csv --packet-types "data,diagnostic"

# Parse with output format selection
rtgs data-parser parse --input-file raw_data.csv --output-file parsed_data --output-format parquet

# Parse with custom output directory
rtgs data-parser parse --input-file raw_data.csv --output-dir ./processed_data/
```

### Command Options

- `--input-file TEXT`: Input CSV file with raw sensor data (required)
- `--output-file TEXT`: Output filename (without extension)
- `--output-dir TEXT`: Output directory (default: ./data/parsed)
- `--output-format [csv|parquet]`: Output format (default: csv)
- `--packet-types TEXT`: Comma-separated packet types to parse (default: "all")
- `--skip-confirmation`: Skip interactive confirmation prompts

## Python API Usage

### Import and Basic Usage

```python
from rtgs_lab_tools.data_parser import parse_file, list_available_parsers

# List available parsers
parsers = list_available_parsers()
for parser_name, description in parsers.items():
    print(f"{parser_name}: {description}")

# Parse a data file
result = parse_file(
    input_file="raw_sensor_data.csv",
    output_file="parsed_data.csv",
    packet_types=["data", "diagnostic"]
)

print(f"Parsed {result['records_processed']} records")
print(f"Output: {result['output_file']}")
```

### Advanced Parsing with Specific Parsers

```python
from rtgs_lab_tools.data_parser.parsers import DataParser, DiagnosticParser
from rtgs_lab_tools.data_parser.core import MessageProcessor
import pandas as pd

# Load raw data
df = pd.read_csv("raw_data.csv")

# Initialize message processor
processor = MessageProcessor()

# Register specific parsers
processor.register_parser("data", DataParser())
processor.register_parser("diagnostic", DiagnosticParser())

# Process messages
parsed_data = []
for _, row in df.iterrows():
    try:
        parsed = processor.process_message(row['message'], row.get('packet_type'))
        parsed_data.append(parsed)
    except Exception as e:
        print(f"Failed to parse message: {e}")

# Convert to DataFrame
parsed_df = pd.DataFrame(parsed_data)
```

### Custom Parser Development

```python
from rtgs_lab_tools.data_parser.parsers.base import BaseParser
import json

class CustomSensorParser(BaseParser):
    """Custom parser for specific sensor type."""
    
    def get_packet_type(self) -> str:
        return "custom_sensor"
    
    def parse_message(self, message: str) -> dict:
        """Parse custom sensor message format."""
        try:
            data = json.loads(message)
            return {
                'timestamp': data.get('ts'),
                'node_id': data.get('node'),
                'temperature': data.get('temp'),
                'humidity': data.get('hum'),
                'battery_voltage': data.get('batt')
            }
        except Exception as e:
            raise ValueError(f"Failed to parse custom sensor message: {e}")

# Register and use custom parser
from rtgs_lab_tools.data_parser.core import MessageProcessor

processor = MessageProcessor()
processor.register_parser("custom_sensor", CustomSensorParser())

# Process with custom parser
result = processor.process_message(message_string, "custom_sensor")
```

### Batch Processing

```python
from rtgs_lab_tools.data_parser import parse_file
import os

# Process multiple files
input_dir = "./raw_data/"
output_dir = "./processed_data/"

for filename in os.listdir(input_dir):
    if filename.endswith('.csv'):
        input_path = os.path.join(input_dir, filename)
        output_name = filename.replace('.csv', '_parsed')
        
        result = parse_file(
            input_file=input_path,
            output_file=output_name,
            output_dir=output_dir,
            packet_types=["data"]
        )
        
        print(f"Processed {filename}: {result['records_processed']} records")
```

## Available Parsers

### Data Parser
- **Packet Type**: `data`
- **Description**: Parses main sensor measurement messages
- **Output Fields**: Timestamp, node_id, measurements, environmental data

### Diagnostic Parser
- **Packet Type**: `diagnostic`
- **Description**: Parses device diagnostic and status messages
- **Output Fields**: System status, error codes, battery levels, signal strength

### Error Parser
- **Packet Type**: `error`
- **Description**: Parses error and fault condition messages
- **Output Fields**: Error codes, error descriptions, timestamps, affected components

### Metadata Parser
- **Packet Type**: `metadata`
- **Description**: Parses device configuration and metadata messages
- **Output Fields**: Device settings, firmware versions, configuration parameters

### JSON Parser
- **Packet Type**: `json`
- **Description**: Generic JSON message parser for structured data
- **Output Fields**: Flattened JSON structure with dot notation keys

### CSV Parser
- **Packet Type**: `csv`
- **Description**: Handles CSV-formatted message payloads
- **Output Fields**: Column-based data extraction

## Message Formats

### Standard GEMS Message Structure

```json
{
    "timestamp": "2023-06-15T14:30:00Z",
    "node_id": "LCCMR_01",
    "packet_type": "data",
    "message": {
        "Data": {
            "Devices": [
                {
                    "Temperature": 23.5,
                    "Humidity": 65.2,
                    "PORT_V": [3.3, 5.0, 12.0]
                }
            ]
        }
    }
}
```

### Diagnostic Message Format

```json
{
    "timestamp": "2023-06-15T14:30:00Z",
    "node_id": "LCCMR_01", 
    "packet_type": "diagnostic",
    "message": {
        "Diagnostic": {
            "BatteryVoltage": 3.7,
            "SignalStrength": -65,
            "ErrorCodes": ["0x00000000"],
            "SystemStatus": "normal"
        }
    }
}
```

## Output Formats

### CSV Output
- **Structure**: Tabular data with flattened JSON paths
- **Columns**: timestamp, node_id, measurement_name, value, units
- **Benefits**: Excel-compatible, human-readable

### Parquet Output  
- **Structure**: Columnar binary format
- **Benefits**: Efficient storage, faster I/O, preserves data types
- **Use Case**: Large datasets, data analysis workflows

## Data Processing Features

### Automatic Type Detection
- Numeric values converted to appropriate types
- Timestamps parsed to datetime objects
- Arrays handled as separate columns or JSON arrays

### Error Handling
- Malformed JSON messages logged but don't stop processing
- Partial parsing continues when possible
- Detailed error reporting with line numbers and context

### Memory Optimization
- Streaming processing for large files
- Configurable batch sizes
- Efficient memory usage for massive datasets

### Data Validation
- Schema validation for known message types
- Range checking for sensor values
- Duplicate detection and handling

## Configuration

### Parser Configuration
```python
from rtgs_lab_tools.data_parser.core import MessageProcessor

# Configure processor options
processor = MessageProcessor(
    batch_size=1000,           # Process in batches for memory efficiency
    validate_json=True,        # Validate JSON schema
    strict_mode=False,         # Continue on errors vs. strict validation
    include_raw_message=False  # Include original message in output
)
```

### Output Configuration
```python
# CSV output options
csv_options = {
    'index': False,
    'encoding': 'utf-8',
    'float_format': '%.6f'
}

# Parquet output options
parquet_options = {
    'compression': 'snappy',
    'engine': 'pyarrow'
}
```

## Examples

### Complete Workflow Example

```python
from rtgs_lab_tools import sensing_data, data_parser, visualization

# 1. Extract raw data
raw_results = sensing_data.extract_data(
    project="Sensor Network Study",
    start_date="2023-06-01",
    end_date="2023-06-30"
)

# 2. Parse the raw sensor messages
parsed_results = data_parser.parse_file(
    input_file=raw_results['output_file'],
    packet_types=["data", "diagnostic"],
    output_format="parquet"
)

# 3. Create visualizations from parsed data
plot_path = visualization.create_time_series_plot(
    df=parsed_results['data'],
    measurement_name="Temperature",
    title="Sensor Network Temperature Analysis"
)

print(f"Analysis complete: {plot_path}")
```

### Quality Control Processing

```python
from rtgs_lab_tools.data_parser import parse_file
import pandas as pd

# Parse with quality control
result = parse_file(
    input_file="field_data.csv",
    packet_types=["data", "diagnostic"]
)

# Load parsed data for analysis
df = pd.read_csv(result['output_file'])

# Quality control checks
print(f"Total records: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Unique nodes: {df['node_id'].nunique()}")
print(f"Missing values: {df.isnull().sum().sum()}")

# Identify potential data quality issues
temp_data = df[df['measurement_name'] == 'Temperature']
outliers = temp_data[(temp_data['value'] < -40) | (temp_data['value'] > 60)]
print(f"Temperature outliers: {len(outliers)}")
```

## Integration

### With Sensing Data Module
```python
from rtgs_lab_tools import sensing_data, data_parser

# Extract and parse in one workflow
raw_data = sensing_data.extract_data(project="My Project")
parsed_data = data_parser.parse_file(raw_data['output_file'])
```

### With Visualization Module
```python
from rtgs_lab_tools import data_parser, visualization

# Parse and visualize
parsed_data = data_parser.parse_file("raw_data.csv")
plot = visualization.create_time_series_plot(
    df=parsed_data['data'],
    measurement_name="Temperature"
)
```

## Error Handling

### Common Issues
- **Malformed JSON**: Invalid JSON in message field
- **Unknown packet types**: Unregistered packet type encountered  
- **Schema mismatches**: Message doesn't match expected format
- **Large file processing**: Memory issues with very large files

### Debugging
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Parse with error details
result = data_parser.parse_file(
    input_file="problematic_data.csv",
    packet_types=["data"]
)

# Check parsing statistics
print(f"Success rate: {result['success_rate']:.2%}")
print(f"Errors: {result['error_count']}")
print(f"Error details: {result['error_summary']}")
```