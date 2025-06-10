"""Time series plotting functions for sensor data."""

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
from .data_parser import extract_time_series_data, parse_sensor_messages

logger = logging.getLogger(__name__)

# Set non-interactive backend by default
matplotlib.use("Agg")


def create_time_series_plot(
    df: pd.DataFrame,
    parameter_path: str,
    node_ids: Optional[List[str]] = None,
    title: Optional[str] = None,
    output_file: Optional[str] = None,
    output_dir: str = "figures",
    show_markers: bool = True,
    format: str = "png",
    figsize: Tuple[int, int] = (12, 8),
) -> str:
    """Create time series plot for a specific parameter.

    Args:
        df: DataFrame with sensor data
        parameter_path: Parameter path to plot (e.g., "Data.Devices.0.Temperature")
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
        ValidationError: If data is invalid
        RTGSLabToolsError: If plotting fails
    """
    try:
        # Parse sensor messages if not already done
        if "parsed_message" not in df.columns:
            df = parse_sensor_messages(df)

        # Extract time series data
        time_series_data = extract_time_series_data(df, parameter_path, node_ids)

        if not time_series_data:
            raise ValidationError(f"No data found for parameter: {parameter_path}")

        # Create plot
        fig, ax = plt.subplots(figsize=figsize)

        colors = plt.cm.tab10(range(len(time_series_data)))

        for i, (node_id, node_df) in enumerate(time_series_data.items()):
            marker_style = "o" if show_markers else None

            ax.plot(
                node_df["timestamp"],
                node_df["value"],
                label=node_id,
                marker=marker_style,
                markersize=4,
                color=colors[i % len(colors)],
            )

        # Format plot
        if title is None:
            param_name = parameter_path.split(".")[-1]
            title = f"{param_name} Time Series"

        ax.set_title(title)
        ax.set_xlabel("Time")
        ax.set_ylabel("Value")
        ax.grid(True, alpha=0.3)

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())

        # Add legend if multiple nodes
        if len(time_series_data) > 1:
            ax.legend()

        # Rotate date labels
        fig.autofmt_xdate()
        plt.tight_layout()

        # Save plot
        output_path = _save_plot(
            fig,
            output_file or f"{parameter_path.replace('.', '_')}_timeseries",
            output_dir,
            format,
        )

        plt.close(fig)
        return output_path

    except Exception as e:
        logger.error(f"Failed to create time series plot: {e}")
        raise RTGSLabToolsError(f"Time series plotting failed: {e}")


def create_multi_parameter_plot(
    df: pd.DataFrame,
    parameters: List[Tuple[str, Optional[str]]],  # [(parameter_path, node_id), ...]
    title: Optional[str] = None,
    output_file: Optional[str] = None,
    output_dir: str = "figures",
    show_markers: bool = True,
    format: str = "png",
    figsize: Tuple[int, int] = (12, 8),
) -> str:
    """Create plot with multiple parameters from different nodes.

    Args:
        df: DataFrame with sensor data
        parameters: List of (parameter_path, node_id) tuples
        title: Optional plot title
        output_file: Optional output filename
        output_dir: Output directory for saved plots
        show_markers: Whether to show data point markers
        format: Output format (png, pdf, svg)
        figsize: Figure size as (width, height)

    Returns:
        Path to saved plot file
    """
    try:
        # Parse sensor messages if not already done
        if "parsed_message" not in df.columns:
            df = parse_sensor_messages(df)

        fig, ax = plt.subplots(figsize=figsize)

        colors = plt.cm.tab10(range(len(parameters)))
        plot_count = 0

        for i, (parameter_path, node_id) in enumerate(parameters):
            # Extract data for specific parameter and node
            node_ids = [node_id] if node_id else None
            time_series_data = extract_time_series_data(df, parameter_path, node_ids)

            if not time_series_data:
                logger.warning(f"No data found for {parameter_path} on node {node_id}")
                continue

            # Plot each node's data
            for node, node_df in time_series_data.items():
                if node_id and node != node_id:
                    continue

                marker_style = "o" if show_markers else None
                param_name = parameter_path.split(".")[-1]
                label = f"{node} - {param_name}"

                ax.plot(
                    node_df["timestamp"],
                    node_df["value"],
                    label=label,
                    marker=marker_style,
                    markersize=4,
                    color=colors[i % len(colors)],
                )
                plot_count += 1

        if plot_count == 0:
            raise ValidationError("No data found for any of the specified parameters")

        # Format plot
        ax.set_title(title or "Multi-Parameter Time Series")
        ax.set_xlabel("Time")
        ax.set_ylabel("Value")
        ax.grid(True, alpha=0.3)

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())

        # Add legend
        ax.legend()

        # Rotate date labels
        fig.autofmt_xdate()
        plt.tight_layout()

        # Save plot
        output_path = _save_plot(
            fig,
            output_file
            or f"multi_parameter_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            output_dir,
            format,
        )

        plt.close(fig)
        return output_path

    except Exception as e:
        logger.error(f"Failed to create multi-parameter plot: {e}")
        raise RTGSLabToolsError(f"Multi-parameter plotting failed: {e}")


def plot_sensor_data(
    df: pd.DataFrame,
    parameter_path: str,
    node_id: Optional[str] = None,
    output_dir: str = "figures",
    **kwargs,
) -> str:
    """Simplified function to plot sensor data for a single parameter.

    Args:
        df: DataFrame with sensor data
        parameter_path: Parameter path to plot
        node_id: Optional specific node ID
        output_dir: Output directory
        **kwargs: Additional arguments passed to create_time_series_plot

    Returns:
        Path to saved plot file
    """
    node_ids = [node_id] if node_id else None

    return create_time_series_plot(
        df=df,
        parameter_path=parameter_path,
        node_ids=node_ids,
        output_dir=output_dir,
        **kwargs,
    )


def _save_plot(fig: plt.Figure, filename: str, output_dir: str, format: str) -> str:
    """Save matplotlib figure to file.

    Args:
        fig: Matplotlib figure
        filename: Base filename (without extension)
        output_dir: Output directory
        format: File format

    Returns:
        Path to saved file
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Add extension if not present
    if not filename.lower().endswith(f".{format}"):
        filename = f"{filename}.{format}"

    # Save figure
    file_path = output_path / filename
    fig.savefig(str(file_path), format=format, dpi=300, bbox_inches="tight")

    logger.info(f"Plot saved to {file_path}")
    return str(file_path)
