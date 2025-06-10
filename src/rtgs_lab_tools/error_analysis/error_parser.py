"""Error code parsing and analysis for GEMS devices."""

import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Error code mappings
ERROR_CLASSES = {
    "0": "Unknown",
    "1": "I2C",
    "2": "Power",
    "3": "IO",
    "4": "Memory",
    "5": "Timing",
    "6": "Coms",
    "7": "Disagree",
    "8": "Internal",
    "9": "Math/Logical",
    "A": "Sensor",
    "E": "System",
    "F": "Warning",
}

HARDWARE_DEVICES = {
    "0": "System Wide",
    "1": "Port 1 Talon",
    "2": "Port 2 Talon",
    "3": "Port 3 Talon",
    "4": "Port 4 Talon",
    "E": "Gonk",
    "F": "Kestrel",
}

HARDWARE_SUB_DEVICES = {
    "0": "General",
    "1": "Power",
    "2": "I2C",
    "3": "UART",
    "4": "SPI",
    "5": "GPIO",
    "6": "ADC",
    "7": "DAC",
    "8": "PWM",
    "9": "Timer",
}


class ErrorCodeParser:
    """Parser for GEMS device error codes."""

    def __init__(self):
        """Initialize error code parser."""
        self.error_classes = ERROR_CLASSES
        self.hardware_devices = HARDWARE_DEVICES
        self.hardware_sub_devices = HARDWARE_SUB_DEVICES

    def parse_error_code(self, error_code: Union[str, int]) -> Dict[str, str]:
        """Parse a single error code into components.

        Args:
            error_code: Error code as string or integer

        Returns:
            Dictionary with parsed error components

        Raises:
            ValidationError: If error code format is invalid
        """
        try:
            # Convert to string and normalize
            code_str = str(error_code).upper().strip()

            # Remove 0x prefix if present
            if code_str.startswith("0X"):
                code_str = code_str[2:]

            # Validate length (should be 4-8 hex digits for GEMS error codes)
            if len(code_str) < 4 or len(code_str) > 8:
                raise ValidationError(
                    f"Error code must be 4-8 hex digits, got: {code_str}"
                )

            # Parse components based on code length
            if len(code_str) == 8:
                # 8-digit format: 0xCCCDDDSS where C=class, D=device, S=subdevice
                error_class = code_str[0]
                hardware_device = code_str[6] if len(code_str) >= 7 else "0"
                hardware_sub_device = code_str[7] if len(code_str) >= 8 else "0"
                specific_error = code_str[1:6]  # Middle part
            else:
                # 4-digit format: CCDX where C=class, D=device, X=sub
                error_class = code_str[0]
                hardware_device = code_str[1]
                hardware_sub_device = code_str[2]
                specific_error = code_str[3]

            # Look up descriptions
            parsed = {
                "raw_code": error_code,
                "normalized_code": code_str,
                "error_class": error_class,
                "error_class_name": self.error_classes.get(
                    error_class, f"Unknown Class ({error_class})"
                ),
                "hardware_device": hardware_device,
                "hardware_device_name": self.hardware_devices.get(
                    hardware_device, f"Unknown Device ({hardware_device})"
                ),
                "hardware_sub_device": hardware_sub_device,
                "hardware_sub_device_name": self.hardware_sub_devices.get(
                    hardware_sub_device, f"Unknown Sub-device ({hardware_sub_device})"
                ),
                "specific_error": specific_error,
                "full_description": self._generate_description(
                    error_class, hardware_device, hardware_sub_device, specific_error
                ),
            }

            return parsed

        except Exception as e:
            raise ValidationError(f"Failed to parse error code '{error_code}': {e}")

    def _generate_description(
        self, error_class: str, device: str, sub_device: str, specific: str
    ) -> str:
        """Generate human-readable error description."""
        class_name = self.error_classes.get(error_class, f"Unknown ({error_class})")
        device_name = self.hardware_devices.get(device, f"Unknown Device ({device})")
        sub_device_name = self.hardware_sub_devices.get(
            sub_device, f"Unknown Sub-device ({sub_device})"
        )

        return f"{class_name} error on {device_name} - {sub_device_name} (Code: {specific})"

    def parse_error_codes_from_data(
        self, df: pd.DataFrame, error_column: str = "message"
    ) -> pd.DataFrame:
        """Parse error codes from a DataFrame with JSON messages.

        Args:
            df: DataFrame containing error data
            error_column: Column name containing JSON error data

        Returns:
            DataFrame with parsed error information
        """
        parsed_errors = []

        for _, row in df.iterrows():
            try:
                # Parse JSON message
                if error_column in row:
                    message = row[error_column]

                    if isinstance(message, str):
                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError:
                            continue
                    else:
                        data = message

                    # Extract error codes from various possible locations
                    error_codes = self._extract_error_codes_from_json(data)

                    for error_code in error_codes:
                        parsed_error = self.parse_error_code(error_code)

                        # Add metadata from original row
                        error_entry = {
                            "timestamp": row.get("publish_time", row.get("timestamp")),
                            "node_id": row.get("node_id"),
                            "original_message": message,
                            **parsed_error,
                        }
                        parsed_errors.append(error_entry)

            except Exception as e:
                logger.warning(f"Failed to parse error from row: {e}")
                continue

        if not parsed_errors:
            return pd.DataFrame()

        return pd.DataFrame(parsed_errors)

    def _extract_error_codes_from_json(self, data: Dict[str, Any]) -> List[str]:
        """Extract error codes from JSON data structure using GEMS format."""
        error_codes = []

        # Check if this is an error record in GEMS format (this is the primary source)
        if "Error" in data and "Devices" in data["Error"]:
            devices = data["Error"]["Devices"]

            # Process each device in the error record
            for device_entry in devices:
                for device_name, device_info in device_entry.items():
                    # Process each error code for this device
                    if "CODES" in device_info and isinstance(
                        device_info["CODES"], list
                    ):
                        for code in device_info["CODES"]:
                            error_codes.append(str(code).lower())

        return list(set(error_codes))  # Remove duplicates

    def _find_hex_patterns(self, text: str) -> List[str]:
        """Find hex patterns that could be error codes."""
        # Pattern for hex codes, optionally prefixed with 0x (4-8 digits)
        pattern = r"\b(?:0[xX])?([0-9A-Fa-f]{4,8})\b"
        matches = re.findall(pattern, text)
        return [match.lower() for match in matches]


def parse_error_codes(df: pd.DataFrame, error_column: str = "message") -> pd.DataFrame:
    """Convenience function to parse error codes from data.

    Args:
        df: DataFrame with error data
        error_column: Column containing error information

    Returns:
        DataFrame with parsed errors
    """
    parser = ErrorCodeParser()
    return parser.parse_error_codes_from_data(df, error_column)


def analyze_error_patterns(
    parsed_errors_df: pd.DataFrame,
    group_by: str = "error_class_name",
    time_window: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze error patterns and generate statistics.

    Args:
        parsed_errors_df: DataFrame with parsed error data
        group_by: Column to group errors by
        time_window: Optional time window for grouping ('D', 'H', etc.)

    Returns:
        Dictionary with error analysis results
    """
    if parsed_errors_df.empty:
        return {"total_errors": 0, "patterns": {}}

    analysis = {
        "total_errors": len(parsed_errors_df),
        "unique_error_codes": parsed_errors_df["normalized_code"].nunique(),
        "date_range": {
            "start": parsed_errors_df["timestamp"].min(),
            "end": parsed_errors_df["timestamp"].max(),
        },
    }

    # Error frequency by category
    if group_by in parsed_errors_df.columns:
        error_counts = parsed_errors_df[group_by].value_counts()
        analysis["error_frequency"] = error_counts.to_dict()

    # Top error codes
    top_codes = (
        parsed_errors_df.groupby(["normalized_code", "full_description"])
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    analysis["top_error_codes"] = [
        {"code": code, "description": desc, "count": count}
        for (code, desc), count in top_codes.items()
    ]

    # Errors by device
    if "hardware_device_name" in parsed_errors_df.columns:
        device_errors = parsed_errors_df["hardware_device_name"].value_counts()
        analysis["errors_by_device"] = device_errors.to_dict()

    # Errors by node
    if "node_id" in parsed_errors_df.columns:
        node_errors = parsed_errors_df["node_id"].value_counts()
        analysis["errors_by_node"] = node_errors.to_dict()

    # Temporal patterns
    if time_window and "timestamp" in parsed_errors_df.columns:
        df_copy = parsed_errors_df.copy()
        df_copy["timestamp"] = pd.to_datetime(df_copy["timestamp"])
        temporal_counts = df_copy.set_index("timestamp").resample(time_window).size()
        analysis["temporal_pattern"] = temporal_counts.to_dict()

    logger.info(
        f"Analyzed {analysis['total_errors']} errors with {analysis['unique_error_codes']} unique codes"
    )

    return analysis


# CLI Helper Functions for Error Analysis
def load_data_file(file_path: str) -> pd.DataFrame:
    """
    Load data from CSV or JSON file.

    Args:
        file_path: Path to the data file

    Returns:
        DataFrame with loaded data

    Raises:
        ValueError: If file format is not supported
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    if file_path.suffix.lower() == ".csv":
        return pd.read_csv(file_path)
    elif file_path.suffix.lower() == ".json":
        return pd.read_json(file_path)
    else:
        raise ValueError(
            f"Unsupported file format: {file_path.suffix}. Supported formats: .csv, .json"
        )


def filter_by_nodes(df: pd.DataFrame, node_filter: list) -> pd.DataFrame:
    """
    Filter DataFrame by node IDs.

    Args:
        df: Input DataFrame
        node_filter: List of node IDs to filter by

    Returns:
        Filtered DataFrame
    """
    if "node_id" not in df.columns:
        # Try alternative column names
        node_columns = [col for col in df.columns if "node" in col.lower()]
        if not node_columns:
            raise ValueError(
                "No node ID column found in data. Expected 'node_id' or similar."
            )
        node_col = node_columns[0]
    else:
        node_col = "node_id"

    return df[df[node_col].isin(node_filter)]


def setup_output_directory(output_dir: str) -> Path:
    """
    Set up output directory for plots and analysis results.

    Args:
        output_dir: Path to output directory

    Returns:
        Path object for the created directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def create_error_frequency_plot(
    errors_df: pd.DataFrame, output_dir: Path, node_id: str, top_n: int = 10
) -> Optional[str]:
    """
    Create error frequency plot.

    Args:
        errors_df: DataFrame with parsed error data
        output_dir: Output directory for the plot
        node_id: Node ID for the plot (used in filename)
        top_n: Number of top errors to include in plot

    Returns:
        Path to the generated plot file, or None if no data
    """
    if errors_df.empty:
        return None

    try:
        # Import matplotlib here to avoid import issues if not available
        import matplotlib.pyplot as plt
        import seaborn as sns

        # Count error frequencies
        if "normalized_code" in errors_df.columns:
            error_counts = errors_df["normalized_code"].value_counts().head(top_n)
        elif "error_code" in errors_df.columns:
            error_counts = errors_df["error_code"].value_counts().head(top_n)
        else:
            # Fallback to any column that might contain error info
            error_cols = [
                col
                for col in errors_df.columns
                if "error" in col.lower() or "code" in col.lower()
            ]
            if not error_cols:
                return None
            error_counts = errors_df[error_cols[0]].value_counts().head(top_n)

        if error_counts.empty:
            return None

        # Create the plot
        plt.figure(figsize=(12, 8))
        sns.barplot(x=error_counts.values, y=error_counts.index)

        plt.title(f"Top {len(error_counts)} Error Codes - {node_id}")
        plt.xlabel("Frequency")
        plt.ylabel("Error Code")
        plt.tight_layout()

        # Generate filename
        if node_id == "all":
            filename = f"error_frequency_all_nodes.png"
        else:
            filename = f"error_frequency_{node_id}.png"

        plot_path = output_dir / filename
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        return str(plot_path)

    except ImportError:
        logger.warning("Matplotlib/seaborn not available. Skipping plot generation.")
        return None
    except Exception as e:
        logger.warning(f"Could not create error frequency plot: {e}")
        return None


def display_enhanced_error_analysis(
    parsed_errors_df: pd.DataFrame,
    analysis: Dict[str, Any],
    node_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Display enhanced error analysis with detailed breakdowns like the original script."""

    if parsed_errors_df.empty:
        print("No errors found in the file.")
        return {"enhanced_analysis": {}, "node_analysis": {}, "overall_analysis": {}}

    # Initialize enhanced analysis structure
    enhanced_analysis = {
        "enhanced_analysis": {},
        "node_analysis": {},
        "overall_analysis": {},
    }

    # Load error code database for enhanced translations
    print("Loading error code database...")
    error_db = load_errorcodes_database()

    # Show per-node analysis if filtering by specific nodes or "all"
    if node_filter:
        if "all" in node_filter:
            # Show analysis for all unique nodes in the data
            unique_nodes = parsed_errors_df["node_id"].unique()
            for node_id in unique_nodes:
                node_errors = parsed_errors_df[parsed_errors_df["node_id"] == node_id]
                if not node_errors.empty:
                    print(f"\n=== ERROR SUMMARY FOR NODE {node_id} ===")
                    print(
                        f"Found {len(node_errors)} errors of {node_errors['normalized_code'].nunique()} distinct types:"
                    )

                    # Get error counts for this node
                    error_counts = node_errors["normalized_code"].value_counts()

                    # Build node analysis data
                    node_analysis_data = {
                        "total_errors": len(node_errors),
                        "unique_error_codes": node_errors["normalized_code"].nunique(),
                        "error_details": [],
                    }

                    # Print each error with enhanced details and capture data
                    for code, count in error_counts.items():
                        error_info = node_errors[
                            node_errors["normalized_code"] == code
                        ].iloc[0]
                        enhanced_details = get_enhanced_error_details(
                            code, count, error_info, error_db
                        )
                        node_analysis_data["error_details"].append(enhanced_details)
                        print_enhanced_error_details_from_data(enhanced_details)

                    enhanced_analysis["node_analysis"][node_id] = node_analysis_data
        else:
            # Show analysis for specific nodes only
            for node_id in node_filter:
                node_errors = parsed_errors_df[parsed_errors_df["node_id"] == node_id]
                if not node_errors.empty:
                    print(f"\n=== ERROR SUMMARY FOR NODE {node_id} ===")
                    print(
                        f"Found {len(node_errors)} errors of {node_errors['normalized_code'].nunique()} distinct types:"
                    )

                    # Get error counts for this node
                    error_counts = node_errors["normalized_code"].value_counts()

                    # Build node analysis data
                    node_analysis_data = {
                        "total_errors": len(node_errors),
                        "unique_error_codes": node_errors["normalized_code"].nunique(),
                        "error_details": [],
                    }

                    # Print each error with enhanced details and capture data
                    for code, count in error_counts.items():
                        error_info = node_errors[
                            node_errors["normalized_code"] == code
                        ].iloc[0]
                        enhanced_details = get_enhanced_error_details(
                            code, count, error_info, error_db
                        )
                        node_analysis_data["error_details"].append(enhanced_details)
                        print_enhanced_error_details_from_data(enhanced_details)

                    enhanced_analysis["node_analysis"][node_id] = node_analysis_data
                else:
                    print(f"\nNode {node_id}: No errors found")
                    enhanced_analysis["node_analysis"][node_id] = {
                        "total_errors": 0,
                        "unique_error_codes": 0,
                        "error_details": [],
                    }

    # Check if there's only one unique node and we already showed its analysis
    unique_nodes = parsed_errors_df["node_id"].nunique()
    show_overall_summary = True

    if unique_nodes == 1 and node_filter and "all" not in node_filter:
        # Single node was specifically requested, skip overall summary
        show_overall_summary = False
    elif unique_nodes == 1 and node_filter and "all" in node_filter:
        # Single node with "all" filter, skip overall summary since it's identical
        show_overall_summary = False

    # Build overall analysis data (always needed for return value)
    error_counts = parsed_errors_df["normalized_code"].value_counts()
    overall_analysis_data = {
        "total_errors": analysis["total_errors"],
        "unique_error_codes": analysis["unique_error_codes"],
        "basic_analysis": analysis,
        "error_details": [],
    }

    for code, count in error_counts.items():
        error_info = parsed_errors_df[parsed_errors_df["normalized_code"] == code].iloc[
            0
        ]
        enhanced_details = get_enhanced_error_details(code, count, error_info, error_db)
        overall_analysis_data["error_details"].append(enhanced_details)

    # Only print overall summary if it's not a duplicate of single node analysis
    if show_overall_summary:
        print("\n=== OVERALL ERROR SUMMARY ===")
        print(
            f"Found {analysis['total_errors']} errors of {analysis['unique_error_codes']} distinct types:"
        )

        for enhanced_details in overall_analysis_data["error_details"]:
            print_enhanced_error_details_from_data(enhanced_details)

    enhanced_analysis["overall_analysis"] = overall_analysis_data
    enhanced_analysis["enhanced_analysis"] = {
        "timestamp": datetime.now().isoformat(),
        "database_loaded": len(error_db) > 0 if error_db else False,
        "database_error_count": len(error_db) if error_db else 0,
    }

    return enhanced_analysis


def get_enhanced_error_details(
    code: str,
    count: int,
    error_info: pd.Series,
    error_db: Dict[str, Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Get enhanced error details as a data structure."""

    # Try to get enhanced description from error database first
    db_info = find_error_in_db(code, error_db) if error_db else None

    enhanced_details = {
        "code": code,
        "count": count,
        "database_match": db_info is not None,
    }

    if db_info:
        # Use database information for enhanced output
        enhanced_details.update(
            {
                "specific_name": db_info.get("specific_name", "Unknown Error"),
                "description": db_info.get("description", "No description available"),
                "hardware_device": db_info.get("hardware_device", "Unknown"),
                "hardware_subdevice": db_info.get("hardware_subdevice", "Unknown"),
                "error_class": db_info.get("class", "Unknown"),
                "code_location": db_info.get("code_location", ""),
                "base_error_code_hex": db_info.get("base_error_code_hex", ""),
                "base_error_code_value": db_info.get("base_error_code_value", ""),
                "error_code_structure": db_info.get("error_code_structure", ""),
                "subtype": db_info.get("subtype", ""),
                "code_name": db_info.get("code_name", ""),
            }
        )
    else:
        # Fall back to parsed error info
        description = error_info.get("full_description", "Unknown error")
        error_class = error_info.get("error_class_name", "Unknown")
        hw_device = error_info.get("hardware_device_name", "Unknown")
        hw_subdevice = error_info.get("hardware_sub_device_name", "Unknown")

        # Create a comprehensive error description like the original script
        if hw_device != "Unknown" and hw_subdevice != "Unknown":
            enhanced_description = f"{error_class} Error - {hw_device} {hw_subdevice}"
        elif hw_device != "Unknown":
            enhanced_description = f"{error_class} Error - {hw_device}"
        else:
            enhanced_description = f"{error_class} Error"

        enhanced_details.update(
            {
                "specific_name": enhanced_description,
                "description": description,
                "hardware_device": hw_device,
                "hardware_subdevice": hw_subdevice,
                "error_class": error_class,
                "code_location": "",
                "base_error_code_hex": code,
                "base_error_code_value": "",
                "error_code_structure": "",
                "subtype": "",
                "code_name": "",
            }
        )

    return enhanced_details


def print_enhanced_error_details_from_data(enhanced_details: Dict[str, Any]):
    """Print enhanced error details from data structure."""
    code = enhanced_details["code"]
    count = enhanced_details["count"]

    if enhanced_details["database_match"]:
        # Use database information for enhanced output
        specific_name = enhanced_details["specific_name"]
        description = enhanced_details["description"]
        hardware_device = enhanced_details["hardware_device"]
        hardware_subdevice = enhanced_details["hardware_subdevice"]
        error_class = enhanced_details["error_class"]
        code_location = enhanced_details["code_location"]

        print(f"{code} ({count}): {specific_name}")
        print(f"  Description: {description}")
        print(f"  Hardware: {hardware_device} / {hardware_subdevice}")
        print(f"  Class: {error_class}")
        if code_location:
            print(f"  Code Location: {code_location}")
    else:
        # Use parsed error info
        specific_name = enhanced_details["specific_name"]
        description = enhanced_details["description"]
        print(f"{code} ({count}): {specific_name} - {description}")

    print()  # Add spacing between error entries


def print_enhanced_error_details(
    code: str,
    count: int,
    error_info: pd.Series,
    error_db: Dict[str, Dict[str, str]] = None,
):
    """Print enhanced error details with database lookups if available."""

    # Try to get enhanced description from error database first
    db_info = find_error_in_db(code, error_db) if error_db else None

    if db_info:
        # Use database information for enhanced output
        specific_name = db_info.get("specific_name", "Unknown Error")
        description = db_info.get("description", "No description available")
        hardware_device = db_info.get("hardware_device", "Unknown")
        hardware_subdevice = db_info.get("hardware_subdevice", "Unknown")
        error_class = db_info.get("class", "Unknown")
        code_location = db_info.get("code_location", "")

        print(f"{code} ({count}): {specific_name}")
        print(f"  Description: {description}")
        print(f"  Hardware: {hardware_device} / {hardware_subdevice}")
        print(f"  Class: {error_class}")
        if code_location:
            print(f"  Code Location: {code_location}")
    else:
        # Fall back to parsed error info
        description = error_info.get("full_description", "Unknown error")
        error_class = error_info.get("error_class_name", "Unknown")
        hw_device = error_info.get("hardware_device_name", "Unknown")
        hw_subdevice = error_info.get("hardware_sub_device_name", "Unknown")

        # Create a comprehensive error description like the original script
        if hw_device != "Unknown" and hw_subdevice != "Unknown":
            enhanced_description = f"{error_class} Error - {hw_device} {hw_subdevice}"
        elif hw_device != "Unknown":
            enhanced_description = f"{error_class} Error - {hw_device}"
        else:
            enhanced_description = f"{error_class} Error"

        print(f"{code} ({count}): {enhanced_description} - {description}")

    print()  # Add spacing between error entries


def load_errorcodes_database(
    md_file: Optional[str] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Load error code database from ERRORCODES.md file or fetch from GitHub.
    This matches the functionality from the original script.
    """
    import os
    import re

    markdown_content = ""

    # If md_file is provided and exists, load it
    if md_file and os.path.exists(md_file):
        with open(md_file, "r", encoding="utf-8") as f:
            markdown_content = f.read()
    else:
        # Try to use local ERRORCODES.md file if it exists
        if os.path.exists("ERRORCODES.md"):
            with open("ERRORCODES.md", "r", encoding="utf-8") as f:
                markdown_content = f.read()
        else:
            try:
                print("Fetching error codes from GitHub...")
                import requests

                url = "https://raw.githubusercontent.com/gemsiot/Firmware_-_FlightControl-Demo/refs/heads/master/ERRORCODES.md"
                response = requests.get(url, allow_redirects=False, timeout=10)
                if response.status_code == 200:
                    markdown_content = response.text
                    print("Got ERRORCODES.md from Github.")
                    # Save for future use
                    with open("ERRORCODES.md", "w", encoding="utf-8") as f:
                        f.write(markdown_content)
                else:
                    print(f"Failed to fetch error codes: HTTP {response.status_code}")
                    return {}
            except Exception as e:
                print(f"Error fetching error codes: {e}")
                return {}

    # Parse the markdown table to extract error codes
    error_db = {}

    # Find the table section
    table_match = re.search(
        r"\| \*\*Base Error Code Hex\*\* \|.*?\n\|[-:|\s]+\|(.*?)(?:\n\n|$)",
        markdown_content,
        re.DOTALL,
    )

    if not table_match:
        print("Could not find error code table in the markdown file.")
        return {}

    table_content = table_match.group(1)

    # Process each row of the table
    for line in table_content.strip().split("\n"):
        if not line.startswith("|"):
            continue

        # Split the line into columns and remove leading/trailing whitespace
        columns = [col.strip() for col in line.split("|")[1:-1]]

        if len(columns) < 12:
            continue  # Skip malformed rows

        # Extract relevant information
        error_info = {
            "base_error_code_hex": columns[0].lower(),
            "specific_name": columns[1],
            "description": columns[2],
            "base_error_code_value": columns[3],
            "error_code_structure": columns[4],
            "class": columns[5],
            "code": columns[6],
            "subtype": columns[7],
            "hardware_device": columns[8],
            "hardware_subdevice": columns[9],
            "code_name": columns[10],
            "code_location": columns[11],
        }

        # Use the hex code as the key
        error_db[error_info["base_error_code_hex"]] = error_info

    print(f"Loaded {len(error_db)} error codes from database")
    return error_db


def find_error_in_db(
    hex_code: str, error_db: Dict[str, Dict[str, str]]
) -> Dict[str, str]:
    """Find error in database using the original script's matching logic."""
    hex_code = hex_code.lower()

    # Add 0x prefix if not present for database lookup
    if not hex_code.startswith("0x"):
        prefixed_code = "0x" + hex_code
    else:
        prefixed_code = hex_code

    # Try exact match first with 0x prefix
    if prefixed_code in error_db:
        return error_db[prefixed_code]

    # Try matching first 6 characters (0xCccc) like original script
    if len(prefixed_code) >= 6:
        base_code = prefixed_code[:6]  # e.g., "0x8007" from "0x80070000"
        for code, info in error_db.items():
            if code.startswith(base_code):
                return info

    # Try without 0x prefix
    clean_code = hex_code[2:] if hex_code.startswith("0x") else hex_code

    # Try first 4 characters without 0x for partial matching
    if len(clean_code) >= 4:
        base_code = clean_code[:4]
        search_pattern = "0x" + base_code
        for code, info in error_db.items():
            if code.startswith(search_pattern):
                return info

    return None
