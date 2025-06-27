"""Data utilities for visualization tools."""

import logging
import tempfile
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import pandas as pd

logger = logging.getLogger(__name__)


def parse_measurement_spec(measurement_spec: str) -> Tuple[str, Optional[int]]:
    """Parse measurement specification to extract measurement name and array index.
    
    Args:
        measurement_spec: Measurement specification (e.g., "Temperature", "PORT_V[0]")
        
    Returns:
        Tuple of (measurement_name, array_index) where array_index is None if not specified
        
    Examples:
        "Temperature" -> ("Temperature", None)
        "PORT_V[0]" -> ("PORT_V", 0)
        "PORT_I[3]" -> ("PORT_I", 3)
    """
    # Pattern to match measurement name with optional array index
    pattern = r'^([^[\]]+)(?:\[(\d+)\])?$'
    match = re.match(pattern, measurement_spec.strip())
    
    if not match:
        raise ValueError(f"Invalid measurement specification: '{measurement_spec}'. "
                        f"Expected format: 'measurement_name' or 'measurement_name[index]'")
    
    measurement_name = match.group(1).strip()
    array_index = int(match.group(2)) if match.group(2) is not None else None
    
    return measurement_name, array_index


def extract_array_value(value: Union[str, list, float, int], index: int) -> Union[float, int, None]:
    """Extract a specific index from an array value.
    
    Args:
        value: The value to extract from (could be array, string representation, or scalar)
        index: Array index to extract
        
    Returns:
        The value at the specified index, or None if extraction fails
    """
    # Handle None values
    if value is None or pd.isna(value):
        return None
    
    # If it's already a list
    if isinstance(value, list):
        if 0 <= index < len(value):
            return value[index]
        return None
    
    # If it's a string representation of an array (from CSV)
    if isinstance(value, str):
        try:
            # Handle string representations like "[3.251406, 3.251344, 3.251437, 3.251437]"
            if value.startswith('[') and value.endswith(']'):
                # Remove brackets and split by comma
                values_str = value[1:-1].strip()
                if not values_str:  # Empty array
                    return None
                
                values = []
                for item in values_str.split(','):
                    item = item.strip()
                    if item:
                        try:
                            # Try to convert to float first, then int
                            if '.' in item:
                                values.append(float(item))
                            else:
                                values.append(int(item))
                        except ValueError:
                            # Keep as string if conversion fails
                            values.append(item)
                
                if 0 <= index < len(values):
                    return values[index]
                return None
        except (ValueError, IndexError):
            pass
    
    # If it's a scalar value and index is 0, return the value
    if index == 0:
        return value
    
    return None


def detect_data_type(df: pd.DataFrame) -> str:
    """Detect if DataFrame contains raw or parsed GEMS data.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        str: 'raw', 'parsed', or 'unknown'
    """
    # Check for parsed data structure
    parsed_columns = {
        'device_type', 'measurement_name', 'measurement_path', 
        'value', 'unit', 'timestamp', 'node_id', 'event_type'
    }
    
    # Check for raw data structure  
    raw_columns = {'event', 'message', 'publish_time', 'node_id'}
    
    df_columns = set(df.columns.str.lower())
    
    # Check if it has parsed data structure
    if len(parsed_columns.intersection(df_columns)) >= 6:
        return 'parsed'
    
    # Check if it has raw data structure
    if len(raw_columns.intersection(df_columns)) >= 3:
        return 'raw'
    
    return 'unknown'




def load_and_prepare_data(
    file_path: str,
    packet_types: str = 'all',
    cli_ctx=None,
    auto_parse: bool = False
) -> Tuple[pd.DataFrame, str, Optional[Dict]]:
    """Load data file and prepare it for visualization.
    
    Args:
        file_path: Path to data file (raw or parsed)
        packet_types: Packet types to parse if raw data
        cli_ctx: CLI context for logging
        auto_parse: If True, skip user confirmation for parsing
        
    Returns:
        Tuple of (dataframe, data_type, parsing_results)
        parsing_results is None if no parsing was needed
    """
    # Load the data
    if file_path.endswith('.parquet'):
        df = pd.read_parquet(file_path)
    else:
        df = pd.read_csv(file_path)
    
    # Detect data type
    data_type = detect_data_type(df)
    
    if cli_ctx:
        cli_ctx.logger.info(f"Detected data type: {data_type}")
    
    if data_type == 'raw':
        # Prompt user for confirmation unless auto_parse is True
        if not auto_parse:
            import click
            click.echo(f"\n🔍 Detected raw GEMS data in: {file_path}")
            click.echo("This data needs to be parsed before visualization.")
            click.echo("\nOptions:")
            click.echo("1. Parse the data now (recommended)")
            click.echo("2. Cancel and provide a pre-parsed file")
            
            if not click.confirm("\nWould you like to parse the data now?", default=True):
                click.echo("\n💡 To use pre-parsed data:")
                click.echo("   - First run: rtgs-lab-tools data-parser parse your_raw_file.csv")
                click.echo("   - Then use the generated parsed file for visualization")
                raise click.Abort()
        else:
            # Auto-parse mode: notify user that parsing is happening automatically
            import click
            click.echo(f"🔍 Detected raw GEMS data in: {file_path}")
            click.echo("📊 Automatically parsing data for visualization...")
        
        # Parse the raw data using shared function
        from ..data_parser.core import parse_gems_data
        
        logger_func = cli_ctx.logger.info if cli_ctx else None
        parsed_df, parsing_results = parse_gems_data(
            raw_df=df,
            packet_types=packet_types,
            save_to_parsed_dir=True,
            original_file_path=file_path,
            logger_func=logger_func
        )
        
        parsed_file_path = Path(parsing_results['output_file'])
        
        # Inform user about saved file
        import click
        if not auto_parse:
            click.echo(f"✅ Data parsed successfully!")
            click.echo(f"📁 Parsed data saved to: {parsed_file_path}")
            click.echo("💡 You can reuse this parsed file for future visualizations.")
        else:
            click.echo(f"✅ Data parsed successfully! Saved to: {parsed_file_path.name}")
            if cli_ctx:
                cli_ctx.logger.info(f"Parsed data saved to: {parsed_file_path}")
        
        # Log the parsing operation to git
        if cli_ctx:
            operation = f"Parse raw data for visualization from {Path(file_path).name}"
            
            parameters = {
                "input_file": file_path,
                "packet_types": packet_types,
                "purpose": "visualization preprocessing",
                "saved_parsed_file": str(parsed_file_path)
            }
            
            results = {
                **parsing_results,
                "start_time": cli_ctx.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
            }
            
            additional_sections = {
                "Parsing Summary": f"- **Input Records**: {parsing_results['input_records']}\n- **Parsed Records**: {parsing_results['parsed_records']}\n- **Output Measurements**: {parsing_results['output_measurements']}\n- **Skipped Records**: {parsing_results['skipped_records']}\n- **Saved File**: {parsed_file_path.name}"
            }
            
            if parsing_results['packet_types'] != 'all':
                additional_sections["Packet Types"] = f"- **Filtered Types**: {parsing_results['packet_types']}"
            
            cli_ctx.log_success(
                operation=operation,
                parameters=parameters,
                results=results,
                script_path=__file__,
                additional_sections=additional_sections,
            )
        
        return parsed_df, 'parsed', parsing_results
        
    elif data_type == 'parsed':
        if cli_ctx:
            cli_ctx.logger.info("Data is already parsed, proceeding with visualization")
        return df, 'parsed', None
        
    else:
        raise ValueError(f"Unknown data format in file: {file_path}")


def get_available_measurements(df: pd.DataFrame) -> Dict[str, set]:
    """Get available measurements from parsed data with array index support.
    
    Args:
        df: Parsed DataFrame
        
    Returns:
        Dict mapping node_ids to sets of available measurements including array indices
    """
    if 'node_id' not in df.columns or 'measurement_name' not in df.columns:
        raise ValueError("DataFrame must have 'node_id' and 'measurement_name' columns")
    
    measurements_by_node = {}
    
    for node_id in df['node_id'].unique():
        node_data = df[df['node_id'] == node_id]
        measurements = set()
        
        for measurement_name in node_data['measurement_name'].dropna().unique():
            # Add the base measurement name
            measurements.add(measurement_name)
            
            # Check if this measurement has array values and add indexed versions
            measurement_rows = node_data[node_data['measurement_name'] == measurement_name]
            
            # Sample a few values to detect arrays
            sample_values = measurement_rows['value'].dropna().head(5)
            
            for value in sample_values:
                array_length = _detect_array_length(value)
                if array_length > 1:
                    # Add indexed versions for this array measurement
                    for i in range(array_length):
                        measurements.add(f"{measurement_name}[{i}]")
                    break  # Only need to detect once per measurement
        
        measurements_by_node[node_id] = measurements
    
    return measurements_by_node


def _detect_array_length(value: Union[str, list, float, int]) -> int:
    """Detect if a value is an array and return its length.
    
    Args:
        value: The value to check
        
    Returns:
        Length of array, or 1 if not an array
    """
    # Handle None values
    if value is None or pd.isna(value):
        return 0
    
    # If it's already a list
    if isinstance(value, list):
        return len(value)
    
    # If it's a string representation of an array
    if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
        try:
            # Remove brackets and split by comma
            values_str = value[1:-1].strip()
            if not values_str:  # Empty array
                return 0
            
            # Count comma-separated items
            items = [item.strip() for item in values_str.split(',') if item.strip()]
            return len(items)
        except:
            pass
    
    # Single value
    return 1


def filter_parsed_data(
    df: pd.DataFrame,
    measurement_spec: str,
    node_ids: Optional[list] = None
) -> pd.DataFrame:
    """Filter parsed data for specific measurement and nodes with array index support.
    
    Args:
        df: Parsed DataFrame
        measurement_spec: Measurement specification (e.g., "Temperature", "PORT_V[0]")
        node_ids: Optional list of node IDs to include
        
    Returns:
        Filtered DataFrame with array values extracted if index specified
    """
    # Parse measurement specification to get measurement name and array index
    measurement_name, array_index = parse_measurement_spec(measurement_spec)
    
    # Filter by measurement name
    filtered_df = df[df['measurement_name'] == measurement_name].copy()
    
    # Filter by node IDs if specified
    if node_ids:
        filtered_df = filtered_df[filtered_df['node_id'].isin(node_ids)]
    
    # If array index is specified, extract the specific array element
    if array_index is not None and not filtered_df.empty:
        # Apply array extraction to the value column
        filtered_df['value'] = filtered_df['value'].apply(
            lambda x: extract_array_value(x, array_index)
        )
        
        # Remove rows where array extraction failed (None values)
        filtered_df = filtered_df.dropna(subset=['value'])
        
        # Update measurement_path to indicate the array index
        if 'measurement_path' in filtered_df.columns:
            filtered_df['measurement_path'] = filtered_df['measurement_path'].apply(
                lambda x: f"{x}[{array_index}]" if pd.notna(x) else f"{measurement_name}[{array_index}]"
            )
    
    return filtered_df


