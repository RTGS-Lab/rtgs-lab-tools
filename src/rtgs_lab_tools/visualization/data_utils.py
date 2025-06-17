"""Data utilities for visualization tools."""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


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
    """Get available measurements from parsed data.
    
    Args:
        df: Parsed DataFrame
        
    Returns:
        Dict mapping node_ids to sets of available measurements
    """
    if 'node_id' not in df.columns or 'measurement_name' not in df.columns:
        raise ValueError("DataFrame must have 'node_id' and 'measurement_name' columns")
    
    measurements_by_node = {}
    
    for node_id in df['node_id'].unique():
        node_data = df[df['node_id'] == node_id]
        measurements = set(node_data['measurement_name'].dropna().unique())
        measurements_by_node[node_id] = measurements
    
    return measurements_by_node


def filter_parsed_data(
    df: pd.DataFrame,
    measurement_name: str,
    node_ids: Optional[list] = None
) -> pd.DataFrame:
    """Filter parsed data for specific measurement and nodes.
    
    Args:
        df: Parsed DataFrame
        measurement_name: Name of measurement to filter for
        node_ids: Optional list of node IDs to include
        
    Returns:
        Filtered DataFrame
    """
    # Filter by measurement name
    filtered_df = df[df['measurement_name'] == measurement_name].copy()
    
    # Filter by node IDs if specified
    if node_ids:
        filtered_df = filtered_df[filtered_df['node_id'].isin(node_ids)]
    
    return filtered_df


