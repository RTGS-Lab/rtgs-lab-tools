# Visualization Module

Create time-series plots and multi-parameter visualizations from sensor data. Visualization tool can take raw data files or pre-parsed CSV files, and automatically handles parsing if needed. Raw data files come from the sensing data module, and can be downloaded from the GEMS database. Parsed CSV files can be created using the data parser module.

## CLI Usage

### List Available Parameters

```bash
# List all parameters in a data file
rtgs visualization list-parameters data.csv

# Or use the create command with --list-params
rtgs visualization create --file data.csv --list-params
```

### Single Parameter Plots

```bash
# Basic time series plot
rtgs visualization create --file data.csv --parameter "Kestrel.PORT_V[0]" --node-id "e00fce68c148e3450a925509"

# Array parameter with index
rtgs visualization create --file data.csv --parameter "Kestrel.PORT_V[0]" --node-id "e00fce68c148e3450a925509"

# Custom output settings
rtgs visualization create --file data.csv --parameter "Kestrel.PORT_V[0]" --node-id "e00fce68c148e3450a925509" \
  --output-dir ./plots --output-file temp_analysis --format png --title "Battery Analysis"
```

### Multi-Parameter Plots

```bash
# Compare same parameter across nodes
rtgs visualization create --file data.csv \
  --multi-param "e00fce68c148e3450a925509,Kestrel.PORT_V[0]" \
  --multi-param "e00fce685bf38074f81ea5f1,Kestrel.PORT_V[0]"

# Compare different parameters from same node
rtgs visualization create --file data.csv \
  --multi-param "e00fce68c148e3450a925509,PORT_V[0]" \
  --multi-param "e00fce68c148e3450a925509,PORT_I[1]"

# Mixed comparison
rtgs visualization create --file data.csv \
  --multi-param "e00fce68c148e3450a925509,PORT_V[0]" \
  --multi-param "e00fce685bf38074f81ea5f1,PORT_I[1]" \
```

### Command Options

- `--file TEXT`: CSV file with sensor data (required)
- `--parameter TEXT`: Parameter path to plot (e.g., "Temperature", "PORT_V[0]")
- `--node-id TEXT`: Specific node ID to plot (required for single parameter plots)
- `--multi-param TEXT`: Multiple parameters as "node_id,parameter_path" (can be used multiple times)
- `--output-dir TEXT`: Output directory for plots (default: current directory)
- `--output-file TEXT`: Output filename without extension (auto-generated if not specified)
- `--format [png|pdf|svg]`: Output format (default: png)
- `--list-params`: List available parameters and exit
- `--title TEXT`: Custom plot title
- `--no-markers`: Disable data point markers for cleaner lines

## Python API Usage

### Import and Basic Usage

```python
from rtgs_lab_tools.visualization import create_time_series_plot, create_multi_parameter_plot
import pandas as pd

# Load your data
df = pd.read_csv("sensor_data.csv")

# Single parameter time series
output_path = create_time_series_plot(
    df=df,
    measurement_name="Temperature",
    node_ids=["node001"],
    title="Temperature Over Time",
    format="png"
)

print(f"Plot saved to: {output_path}")
```

### Multi-Parameter Visualization

```python
from rtgs_lab_tools.visualization import create_multi_parameter_plot

# Compare multiple measurements
measurements = [
    ("Temperature", "node001"),
    ("Temperature", "node002"),
    ("Humidity", "node001")
]

output_path = create_multi_parameter_plot(
    df=df,
    measurements=measurements,
    title="Multi-Parameter Comparison",
    output_dir="./plots",
    format="pdf"
)
```

### Advanced Data Handling

```python
from rtgs_lab_tools.visualization.data_utils import load_and_prepare_data, get_available_measurements

# Load and automatically parse raw data
df, data_type, parsing_results = load_and_prepare_data(
    file_path="raw_sensor_data.csv",
    packet_types="all",
    auto_parse=True
)

# Get available measurements by node
measurements_by_node = get_available_measurements(df)
for node, measurements in measurements_by_node.items():
    print(f"{node}: {measurements}")
```

### Direct Function Usage

```python
from rtgs_lab_tools.visualization.time_series import plot_time_series
import matplotlib.pyplot as plt

# Create custom plots with direct function access
fig, ax = plt.subplots(figsize=(12, 6))

plot_time_series(
    df=df,
    measurement_name="Temperature",
    node_ids=["node001", "node002"],
    ax=ax,
    show_markers=True
)

plt.title("Custom Temperature Plot")
plt.savefig("custom_plot.png", dpi=300, bbox_inches='tight')
```

## Supported Data Formats

### Parsed Sensor Data
The module automatically handles both raw and parsed sensor data:
- **Raw CSV files**: Automatically parsed using the data parser module
- **Pre-parsed CSV files**: Directly loaded and visualized
- **JSON format**: Handles nested sensor message structures

### Parameter Naming
Parameters can be specified in several formats:
- **Simple names**: `Temperature`, `Humidity`
- **Nested paths**: `Data.Devices.0.Temperature`
- **Array indices**: `PORT_V[0]`, `Data.Measurements[2]`

## Output Formats

### PNG (Default)
- High-quality raster format
- Good for web display and presentations
- Smaller file sizes

### PDF
- Vector format for publications
- Scalable without quality loss
- Professional documentation

### SVG
- Web-friendly vector format
- Editable in graphics software
- Excellent for interactive applications

## Visualization Features

### Time Series Plots
- Automatic time axis formatting
- Multiple node support
- Customizable markers and colors
- Statistical overlays (mean, trends)

### Multi-Parameter Plots
- Automatic y-axis scaling
- Legend generation
- Color coordination
- Subplot organization for different units

### Customization Options
- Custom titles and labels
- Marker styles and sizes
- Color schemes
- Grid and axis formatting

## Examples

### Workflow Example

```python
from rtgs_lab_tools import sensing_data, visualization

# 1. Extract recent data
results = sensing_data.extract_data(
    project="Winter Turf - v3",
    start_date="2023-12-01",
    end_date="2023-12-31"
)

# 2. Create visualization
plot_path = visualization.create_time_series_plot(
    df=results["data"],
    measurement_name="Temperature",
    node_ids=["LCCMR_01", "LCCMR_02"],
    title="Winter Temperature Comparison",
    format="pdf"
)

print(f"Analysis complete: {plot_path}")
```

### Batch Visualization

```python
import pandas as pd
from rtgs_lab_tools.visualization import create_time_series_plot
from rtgs_lab_tools.visualization.data_utils import get_available_measurements

# Load data
df = pd.read_csv("sensor_data.csv")

# Get all available measurements
measurements_by_node = get_available_measurements(df)

# Create plots for all temperature measurements
for node, measurements in measurements_by_node.items():
    temp_measurements = [m for m in measurements if "Temperature" in m]
    
    for measurement in temp_measurements:
        output_path = create_time_series_plot(
            df=df,
            measurement_name=measurement,
            node_ids=[node],
            output_file=f"{node}_{measurement.replace('.', '_')}",
            format="png"
        )
        print(f"Created: {output_path}")
```

## Error Handling

### Common Issues
- **No data found**: Check parameter names and node IDs
- **Empty plots**: Verify date ranges and data availability
- **Format errors**: Ensure CSV files are properly formatted

### Data Validation
The module automatically:
- Validates parameter existence
- Checks for sufficient data points
- Handles missing values gracefully
- Provides informative error messages

## Integration

### With Sensing Data Module
```python
from rtgs_lab_tools import sensing_data, visualization

# Extract and visualize in one workflow
results = sensing_data.extract_data(project="My Project")
plot_path = visualization.create_time_series_plot(
    df=results["data"],
    measurement_name="Temperature"
)
```

### With Data Parser Module
```python
from rtgs_lab_tools import data_parser, visualization

# Parse raw data and visualize
parsed_data = data_parser.parse_file("raw_data.csv")
plot_path = visualization.create_time_series_plot(
    df=parsed_data,
    measurement_name="Temperature"
)
```