"""Core data parsing functions for GEMS sensing data."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from ..core.postgres_logger import PostgresLogger

logger = logging.getLogger(__name__)


def parse_gems_data(
    raw_df: pd.DataFrame,
    packet_types: str = 'all',
    output_file: Optional[str] = None,
    output_format: str = 'csv',
    save_to_parsed_dir: bool = False,
    original_file_path: Optional[str] = None,
    logger_func: Optional[callable] = None,
    note: Optional[str] = None,
    auto_commit_postgres_log: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """Parse GEMS sensing data using the appropriate parsers.
    
    Args:
        raw_df: Raw DataFrame to parse
        packet_types: Packet types to parse ('all' or comma-separated list)
        output_file: Optional output file path
        output_format: Output format ('csv' or 'parquet')
        save_to_parsed_dir: Whether to save to data/parsed directory
        original_file_path: Path to original file (for naming saved files)
        logger_func: Optional logging function to call with messages
        note: Optional note for git logging
        auto_commit_postgres_log: Whether to automatically create and commit postgres log
        
    Returns:
        Tuple of (parsed_dataframe, results_dict)
        
    Raises:
        ValueError: If no records were successfully parsed
    """
    from .parsers.factory import ParserFactory
    from .parsers.data_parser import DataV2Parser
    from .parsers.diagnostic_parser import DiagnosticV2Parser
    from .parsers.metadata_parser import MetadataV2Parser
    from .parsers.error_parser import ErrorV2Parser
    from .output.csv_writer import CSVWriter
    from .output.parquet_writer import ParquetWriter

    # Initialize postgres logger
    postgres_logger = PostgresLogger("data-parser") if auto_commit_postgres_log else None
    start_time = datetime.now()

    def log(message: str):
        """Internal logging helper."""
        if logger_func:
            logger_func(message)
        else:
            logger.info(message)

    log(f"Parsing raw data with packet types: {packet_types}")
    
    try:
        # Set up parser factory
        factory = ParserFactory()
        factory.register_parser("data/v2", DataV2Parser)
        factory.register_parser("diagnostic/v2", DiagnosticV2Parser)
        factory.register_parser("metadata/v2", MetadataV2Parser)
        factory.register_parser("error/v2", ErrorV2Parser)

        # Parse packet types filter
        if packet_types.lower() == 'all':
            selected_types = None  # Parse all types
        else:
            selected_types = [t.strip().lower() for t in packet_types.split(',')]
            log(f"Filtering for packet types: {selected_types}")

        # Parse the data
        log("Parsing data records...")
        
        parsed_records = []
        parsed_count = 0
        skipped_count = 0

        for idx, row in raw_df.iterrows():
            event_type = row.get('event', '').lower()
            
            # Skip if filtering by packet types and this type is not selected
            if selected_types and event_type not in selected_types:
                skipped_count += 1
                continue
            
            parser = factory.create_parser(event_type)
            if parser:
                try:
                    parsed_data = parser.parse(row)
                    parsed_records.extend(parsed_data)
                    parsed_count += 1
                except Exception as e:
                    log(f"Failed to parse record {idx} (event: {event_type}): {e}")
                    continue
            else:
                logger.debug(f"No parser available for event type: {event_type}")
                skipped_count += 1

        if not parsed_records:
            raise ValueError("No records were successfully parsed.")

        # Create DataFrame from parsed records
        parsed_df = pd.DataFrame(parsed_records)
        
        log(f"Successfully parsed {parsed_count} records into {len(parsed_df)} measurements")
        if skipped_count > 0:
            log(f"Skipped {skipped_count} records (no parser or filtered out)")

        # Save data if requested
        saved_file_path = None
        if output_file or save_to_parsed_dir:
            if save_to_parsed_dir:
                # Save to data/parsed directory with auto-generated name
                saved_file_path = _save_to_parsed_dir(
                    parsed_df, original_file_path or "unknown", output_format
                )
            else:
                # Save to specified path
                saved_file_path = Path(output_file)
                saved_file_path.parent.mkdir(parents=True, exist_ok=True)
                
            # Write the file
            if output_format == 'csv':
                writer = CSVWriter()
                writer.write(parsed_df, str(saved_file_path))
            elif output_format == 'parquet':
                writer = ParquetWriter()
                writer.write(parsed_df, str(saved_file_path))
            
            log(f"Parsed data saved to: {saved_file_path}")

        # Prepare results
        end_time = datetime.now()
        results = {
            'success': True,
            'input_records': len(raw_df),
            'parsed_records': parsed_count,
            'output_measurements': len(parsed_df),
            'skipped_records': skipped_count,
            'packet_types': packet_types,
            'output_file': str(saved_file_path) if saved_file_path else None,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': (end_time - start_time).total_seconds()
        }
        
        # Add note to results if provided
        if note:
            results['note'] = note
        
        # Log execution to postgres if enabled
        if postgres_logger:
            try:
                operation = f"Parse GEMS data ({packet_types} packets)"
                parameters = {
                    'input_records': len(raw_df),
                    'packet_types': packet_types,
                    'output_format': output_format,
                    'save_to_parsed_dir': save_to_parsed_dir,
                    'original_file_path': original_file_path or 'N/A'
                }
                postgres_logger.log_execution(
                    operation=operation,
                    parameters=parameters,
                    results=results,
                    script_path=__file__,
                    auto_save=True
                )
            except Exception as e:
                logger.warning(f"Failed to create postgres log: {e}")
        
        return parsed_df, results
        
    except Exception as e:
        # Prepare error results
        end_time = datetime.now()
        error_results = {
            'success': False,
            'error': str(e),
            'input_records': len(raw_df),
            'packet_types': packet_types,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': (end_time - start_time).total_seconds()
        }
        
        # Add note to results if provided
        if note:
            error_results['note'] = note
        
        # Log execution to postgres if enabled (even for failures)
        if postgres_logger:
            try:
                operation = f"Parse GEMS data ({packet_types} packets) - FAILED"
                parameters = {
                    'input_records': len(raw_df),
                    'packet_types': packet_types,
                    'output_format': output_format,
                    'save_to_parsed_dir': save_to_parsed_dir,
                    'original_file_path': original_file_path or 'N/A'
                }
                postgres_logger.log_execution(
                    operation=operation,
                    parameters=parameters,
                    results=error_results,
                    script_path=__file__,
                    auto_save=True
                )
            except Exception as log_e:
                logger.warning(f"Failed to create postgres log for error: {log_e}")
        
        # Re-raise the original exception
        raise


def _save_to_parsed_dir(
    parsed_df: pd.DataFrame, 
    original_file_path: str, 
    output_format: str = 'csv'
) -> Path:
    """Save parsed data to data/parsed directory with standard naming."""
    from .output.csv_writer import CSVWriter
    from .output.parquet_writer import ParquetWriter
    
    # Generate output file path
    repo_root = Path(__file__).parents[3]  # Go up from src/rtgs_lab_tools/data_parser/core.py to project root
    parsed_dir = repo_root / "data" / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_stem = Path(original_file_path).stem
    output_filename = f"{input_stem}_parsed_{timestamp}.{output_format}"
    output_path = parsed_dir / output_filename
    
    # Save using appropriate writer
    if output_format == 'csv':
        writer = CSVWriter()
        writer.write(parsed_df, str(output_path))
    elif output_format == 'parquet':
        writer = ParquetWriter()
        writer.write(parsed_df, str(output_path))
    
    return output_path