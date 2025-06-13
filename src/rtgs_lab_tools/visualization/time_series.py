"""Time series plotting functions for parsed GEMS sensor data."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from ..core.exceptions import RTGSLabToolsError, ValidationError
from .data_utils import filter_parsed_data

logger = logging.getLogger(__name__)

# Set non-interactive backend by default
matplotlib.use("Agg")


def create_time_series_plot(
    df: pd.DataFrame,
    measurement_name: str,
    node_ids: Optional[List[str]] = None,
    title: Optional[str] = None,
    output_file: Optional[str] = None,
    output_dir: str = "figures",
    show_markers: bool = True,
    format: str = "png",
    figsize: Tuple[int, int] = (12, 8),
) -> str:
    """Create time series plot for a specific measurement from parsed data.

    Args:
        df: Parsed DataFrame with measurements
        measurement_name: Name of measurement to plot (e.g., "Temperature")
        node_ids: Optional list of node IDs to include
        title: Optional plot title
        output_file: Optional output filename
        output_dir: Output directory for saved plots
        show_markers: Whether to show data point markers
        format: Output format (png, pdf, svg)
        figsize: Figure size as (width, height)

    Returns:
        Path to saved plot file

    Raises:
        ValidationError: If measurement not found or data invalid
        RTGSLabToolsError: If plotting fails
    """
    # Filter data for the specified measurement
    filtered_df = filter_parsed_data(df, measurement_name, node_ids)
    
    if filtered_df.empty:
        available_measurements = df['measurement_name'].unique()
        raise ValidationError(
            f"No data found for measurement '{measurement_name}'. "
            f"Available measurements: {', '.join(available_measurements)}"
        )

    # Convert timestamp to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(filtered_df['timestamp']):
        filtered_df = filtered_df.copy()
        filtered_df['timestamp'] = pd.to_datetime(filtered_df['timestamp'])

    # Group by node_id for plotting multiple nodes
    plt.figure(figsize=figsize)
    
    for node_id in filtered_df['node_id'].unique():
        node_data = filtered_df[filtered_df['node_id'] == node_id].copy()
        node_data = node_data.sort_values('timestamp')
        
        # Plot the data
        if show_markers:
            plt.plot(node_data['timestamp'], node_data['value'], 
                    marker='o', markersize=3, label=f"Node {node_id}", alpha=0.7)
        else:
            plt.plot(node_data['timestamp'], node_data['value'], 
                    label=f"Node {node_id}", alpha=0.7)

    # Customize the plot
    if title:
        plt.title(title)
    else:
        unit_info = ""
        if not filtered_df['unit'].isna().all():
            units = filtered_df['unit'].dropna().unique()
            if len(units) == 1 and units[0]:
                unit_info = f" ({units[0]})"
        
        if node_ids and len(node_ids) == 1:
            plt.title(f"{measurement_name} - Node {node_ids[0]}{unit_info}")
        else:
            plt.title(f"{measurement_name}{unit_info}")

    plt.xlabel("Time")
    plt.ylabel(measurement_name)
    
    # Add legend if multiple nodes
    if len(filtered_df['node_id'].unique()) > 1:
        plt.legend()

    # Format x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=6))
    plt.xticks(rotation=45)

    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save the plot
    output_path = _save_plot(output_file, output_dir, measurement_name, format, node_ids)
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"Time series plot saved to: {output_path}")
    return str(output_path)


def create_multi_parameter_plot(
    df: pd.DataFrame,
    measurements: List[Tuple[str, Optional[str]]],  # (measurement_name, node_id)
    title: Optional[str] = None,
    output_file: Optional[str] = None,
    output_dir: str = "figures",
    show_markers: bool = True,
    format: str = "png",
    figsize: Tuple[int, int] = (12, 8),
) -> str:
    """Create multi-parameter plot from parsed data.

    Args:
        df: Parsed DataFrame with measurements
        measurements: List of (measurement_name, node_id) tuples to plot
        title: Optional plot title
        output_file: Optional output filename
        output_dir: Output directory for saved plots
        show_markers: Whether to show data point markers
        format: Output format (png, pdf, svg)
        figsize: Figure size as (width, height)

    Returns:
        Path to saved plot file

    Raises:
        ValidationError: If measurements not found or data invalid
        RTGSLabToolsError: If plotting fails
    """
    plt.figure(figsize=figsize)
    
    plot_data = []
    
    for measurement_name, node_id in measurements:
        # Filter data for this measurement and node
        node_ids = [node_id] if node_id else None
        filtered_df = filter_parsed_data(df, measurement_name, node_ids)
        
        if filtered_df.empty:
            logger.warning(f"No data found for measurement '{measurement_name}' on node '{node_id}'")
            continue
        
        # Convert timestamp to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(filtered_df['timestamp']):
            filtered_df = filtered_df.copy()
            filtered_df['timestamp'] = pd.to_datetime(filtered_df['timestamp'])
        
        # Sort by timestamp
        filtered_df = filtered_df.sort_values('timestamp')
        
        # Create label
        if node_id:
            label = f"{measurement_name} (Node {node_id})"
        else:
            label = measurement_name
        
        # Plot the data
        if show_markers:
            plt.plot(filtered_df['timestamp'], filtered_df['value'], 
                    marker='o', markersize=3, label=label, alpha=0.7)
        else:
            plt.plot(filtered_df['timestamp'], filtered_df['value'], 
                    label=label, alpha=0.7)
        
        plot_data.append((measurement_name, node_id, len(filtered_df)))

    if not plot_data:
        raise ValidationError("No valid data found for any of the specified measurements")

    # Customize the plot
    if title:
        plt.title(title)
    else:
        plt.title("Multi-Parameter Time Series")

    plt.xlabel("Time")
    plt.ylabel("Values")
    plt.legend()

    # Format x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=6))
    plt.xticks(rotation=45)

    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save the plot
    measurement_names = [m[0] for m in measurements]
    output_path = _save_plot(output_file, output_dir, "_".join(measurement_names[:3]), format)
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    logger.info(f"Multi-parameter plot saved to: {output_path}")
    return str(output_path)


# Legacy function for backwards compatibility
def plot_sensor_data(*args, **kwargs):
    """Legacy function - use create_time_series_plot instead."""
    logger.warning("plot_sensor_data is deprecated, use create_time_series_plot instead")
    return create_time_series_plot(*args, **kwargs)


def _save_plot(
    output_file: Optional[str],
    output_dir: str,
    base_name: str,
    format: str,
    node_ids: Optional[List[str]] = None
) -> Path:
    """Generate output file path for plots."""
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if output_file:
        # Use provided filename
        file_path = Path(output_file)
        if not file_path.is_absolute():
            file_path = output_path / file_path
    else:
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in base_name if c.isalnum() or c in "._-")
        
        if node_ids and len(node_ids) == 1:
            filename = f"{safe_name}_node_{node_ids[0]}_{timestamp}.{format}"
        else:
            filename = f"{safe_name}_{timestamp}.{format}"
        
        file_path = output_path / filename

    return file_path