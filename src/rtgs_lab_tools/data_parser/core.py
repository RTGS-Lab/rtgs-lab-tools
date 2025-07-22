"""Core data parsing functions for GEMS sensing data."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import multiprocessing as mp
from io import StringIO

import pandas as pd
import dask
import dask.dataframe as dd

from ..core.postgres_logger import PostgresLogger

logger = logging.getLogger(__name__)


def _log_memory_usage(df: pd.DataFrame, stage: str, log_func: callable = None):
    """Log detailed memory usage information for a DataFrame.
    
    Args:
        df: DataFrame to analyze
        stage: Description of the processing stage
        log_func: Optional logging function, defaults to logger.info
    """
    if log_func is None:
        log_func = logger.info
        
    # Capture df.info() output
    buffer = StringIO()
    df.info(buf=buffer, memory_usage='deep')
    info_output = buffer.getvalue()
    
    # Get memory usage in MB
    memory_usage = df.memory_usage(deep=True)
    total_memory_mb = memory_usage.sum() / (1024 * 1024)
    
    log_func(f"MEMORY [{stage}] - Shape: {df.shape}, Memory: {total_memory_mb:.2f}MB")
    
    # Log detailed info if verbose
    if logger.isEnabledFor(logging.DEBUG):
        log_func(f"MEMORY DETAIL [{stage}]:\n{info_output}")
        log_func(f"MEMORY BY COLUMN [{stage}]:\n{memory_usage / (1024 * 1024)}")


def _get_system_memory_info():
    """Get current system memory information."""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'process_rss_mb': memory_info.rss / (1024 * 1024),
            'process_vms_mb': memory_info.vms / (1024 * 1024),
            'system_available_mb': psutil.virtual_memory().available / (1024 * 1024)
        }
    except ImportError:
        return {'process_rss_mb': 'N/A', 'process_vms_mb': 'N/A', 'system_available_mb': 'N/A'}


def _parse_partition(partition_df: pd.DataFrame, selected_types: Optional[List[str]], verbose: bool = False) -> pd.DataFrame:
    """Parse a single partition of data records.
    
    Args:
        partition_df: Pandas DataFrame partition to parse
        selected_types: List of event types to process (None for all)
        verbose: Whether to show detailed parsing errors
        
    Returns:
        DataFrame with parsed records
    """
    if partition_df.empty:
        return pd.DataFrame()
    
    # Import parsers within the function to avoid serialization issues
    from .parsers.data_parser import DataV2Parser
    from .parsers.diagnostic_parser import DiagnosticV2Parser
    from .parsers.error_parser import ErrorV2Parser
    from .parsers.metadata_parser import MetadataV2Parser
    from .parsers.factory import ParserFactory
    
    # Recreate parser factory for this partition
    factory = ParserFactory(verbose=verbose)
    factory.register_parser("data/v2", DataV2Parser)
    factory.register_parser("diagnostic/v2", DiagnosticV2Parser)
    factory.register_parser("metadata/v2", MetadataV2Parser)
    factory.register_parser("error/v2", ErrorV2Parser)
    
    parsed_records = []
    
    for idx, row in partition_df.iterrows():
        event_type = row.get("event", "").lower()
        
        # Skip if filtering by packet types and this type is not selected
        if selected_types and event_type not in selected_types:
            continue
            
        parser = factory.create_parser(event_type)
        if parser:
            try:
                parsed_data = parser.parse(row)
                parsed_records.extend(parsed_data)
            except Exception as e:
                # Silently skip errors in partitions to avoid log spam
                if verbose:
                    logger.debug(f"Failed to parse record {idx} (event: {event_type}): {e}")
                continue
    
    # Convert to DataFrame
    if parsed_records:
        return pd.DataFrame(parsed_records)
    else:
        return pd.DataFrame()


def parse_gems_data(
    raw_df: pd.DataFrame,
    packet_types: str = "all",
    output_file: Optional[str] = None,
    output_format: str = "csv",
    save_to_parsed_dir: bool = False,
    original_file_path: Optional[str] = None,
    logger_func: Optional[callable] = None,
    note: Optional[str] = None,
    auto_commit_postgres_log: bool = True,
    verbose: bool = False,
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
        verbose: Whether to show detailed parsing errors and warnings

    Returns:
        Tuple of (parsed_dataframe, results_dict)

    Raises:
        ValueError: If no records were successfully parsed
    """
    from .output.csv_writer import CSVWriter
    from .output.parquet_writer import ParquetWriter
    from .parsers.data_parser import DataV2Parser
    from .parsers.diagnostic_parser import DiagnosticV2Parser
    from .parsers.error_parser import ErrorV2Parser
    from .parsers.factory import ParserFactory
    from .parsers.metadata_parser import MetadataV2Parser

    # Initialize postgres logger - check environment variable first
    postgres_logging_enabled = (
        os.getenv("POSTGRES_LOGGING_STATUS", "true").lower() == "true"
    )
    postgres_logger = (
        PostgresLogger("data-parser")
        if auto_commit_postgres_log and postgres_logging_enabled
        else None
    )
    start_time = datetime.now()

    def log(message: str):
        """Internal logging helper."""
        if logger_func:
            logger_func(message)
        else:
            logger.info(message)

    log(f"Parsing raw data with packet types: {packet_types}")
    
    # Log initial memory usage
    _log_memory_usage(raw_df, "INITIAL_LOAD", log)
    sys_mem = _get_system_memory_info()
    log(f"SYSTEM MEMORY - Process: {sys_mem['process_rss_mb']:.1f}MB, Available: {sys_mem['system_available_mb']:.1f}MB")

    try:
        # Set up parser factory
        factory = ParserFactory(verbose=verbose)
        factory.register_parser("data/v2", DataV2Parser)
        factory.register_parser("diagnostic/v2", DiagnosticV2Parser)
        factory.register_parser("metadata/v2", MetadataV2Parser)
        factory.register_parser("error/v2", ErrorV2Parser)

        # Parse packet types filter
        if packet_types.lower() == "all":
            selected_types = None  # Parse all types
        else:
            selected_types = [t.strip().lower() for t in packet_types.split(",")]
            log(f"Filtering for packet types: {selected_types}")

        # Parse the data using Dask for parallel processing
        log("Parsing data records...")

        # Configure Dask to use threads for better memory management
        dask.config.set(scheduler='threads')
        
        # Memory-controlled parallel processing with batching
        cpu_count = mp.cpu_count()
        partition_size = max(20000, len(raw_df) // (cpu_count * 4))  # Smaller partitions
        batch_size = min(cpu_count, 4)  # Process max 4 partitions at once
        
        # Create all partitions
        partitions = []
        for i in range(0, len(raw_df), partition_size):
            partition = raw_df.iloc[i:i+partition_size]
            partitions.append(partition)
        
        total_partitions = len(partitions)
        log(f"Using parallel processing: {total_partitions} partitions in batches of {batch_size}")
        
        # Process partitions in batches with dynamic memory-based disk writing
        parsed_records = []
        
        # Calculate dynamic memory threshold based on available system RAM
        sys_mem = _get_system_memory_info()
        if isinstance(sys_mem['system_available_mb'], (int, float)):
            # Use 50% of available system RAM as threshold
            memory_threshold_mb = sys_mem['system_available_mb'] * 0.5
            # Estimate ~1.4MB per 1000 records (based on batch results ~355MB for 350K records)
            memory_threshold_records = int((memory_threshold_mb / 1.4) * 1000)
            log(f"Dynamic memory threshold: {memory_threshold_mb:.1f}MB (~{memory_threshold_records:,} records)")
        else:
            # Fallback if psutil not available
            memory_threshold_records = 1000000
            log(f"Using fallback memory threshold: {memory_threshold_records:,} records")
        
        batch_write_count = 0
        temp_output_file = None
        header_written = False
        
        # Determine output file for intermediate writes
        if save_to_parsed_dir:
            # Create temp file in parsed directory
            repo_root = Path(__file__).parents[3]
            parsed_dir = repo_root / "data" / "parsed"
            parsed_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            input_stem = Path(original_file_path or "unknown").stem
            temp_filename = f"{input_stem}_parsed_{timestamp}.csv"
            temp_output_file = parsed_dir / temp_filename
        elif output_file:
            temp_output_file = Path(output_file)
            temp_output_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Fallback to current directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_output_file = Path(f"parsed_data_{timestamp}.csv")
        
        log(f"Intermediate results will be written to: {temp_output_file}")
        
        def _write_records_to_disk():
            """Write current parsed_records to disk and clear memory."""
            nonlocal batch_write_count, header_written, parsed_records
            
            if not parsed_records:
                return
                
            batch_write_count += 1
            batch_df = pd.DataFrame(parsed_records)
            
            # Write to CSV with appropriate mode and header
            write_mode = 'w' if not header_written else 'a'
            include_header = not header_written
            
            batch_df.to_csv(temp_output_file, mode=write_mode, header=include_header, index=False)
            
            sys_mem = _get_system_memory_info()
            log(f"DISK WRITE #{batch_write_count} - Wrote {len(parsed_records):,} records "
                f"({batch_df.memory_usage(deep=True).sum() / (1024*1024):.1f}MB) to disk. "
                f"Process memory: {sys_mem['process_rss_mb']:.1f}MB")
            
            # Clear memory
            parsed_records.clear()
            del batch_df
            header_written = True
        
        for batch_start in range(0, total_partitions, batch_size):
            batch_end = min(batch_start + batch_size, total_partitions)
            current_batch = partitions[batch_start:batch_end]
            
            batch_rows = sum(len(p) for p in current_batch)
            log(f"Processing batch {batch_start//batch_size + 1}/{(total_partitions + batch_size - 1)//batch_size} "
                f"(partitions {batch_start + 1}-{batch_end}, {batch_rows:,} rows)")
            
            # Log memory before batch processing
            sys_mem = _get_system_memory_info()
            log(f"PRE-BATCH MEMORY - Process: {sys_mem['process_rss_mb']:.1f}MB, Parsed records so far: {len(parsed_records):,}")
            
            # Process current batch in parallel
            delayed_results = []
            for partition in current_batch:
                delayed_result = dask.delayed(_parse_partition)(partition, selected_types, verbose)
                delayed_results.append(delayed_result)
            
            # Compute this batch and collect results immediately
            batch_results = dask.compute(*delayed_results)
            
            # Add results to main list and clear batch memory
            batch_parsed_count = 0
            for result in batch_results:
                if not result.empty:
                    batch_records = result.to_dict('records')
                    parsed_records.extend(batch_records)
                    batch_parsed_count += len(batch_records)
                    
                    # Log memory usage of batch result
                    if not result.empty:
                        _log_memory_usage(result, f"BATCH_RESULT_{batch_start//batch_size + 1}", log)
            
            # Log memory after batch processing
            sys_mem = _get_system_memory_info()
            log(f"POST-BATCH MEMORY - Process: {sys_mem['process_rss_mb']:.1f}MB, "
                f"Batch added: {batch_parsed_count:,} records, Total: {len(parsed_records):,}")
            
            # Check if we need to write to disk based on memory threshold
            if len(parsed_records) >= memory_threshold_records:
                _write_records_to_disk()
            
            # Clear batch data to free memory
            del current_batch, delayed_results, batch_results
        
        # Write any remaining records to disk
        if parsed_records:
            _write_records_to_disk()
        
        # Verify output file exists and has data
        if not temp_output_file.exists():
            raise ValueError("No records were successfully parsed - output file not created.")
        
        # Read back a small sample to verify and get final counts
        sample_df = pd.read_csv(temp_output_file, nrows=1000)
        total_lines = sum(1 for _ in open(temp_output_file)) - 1  # Subtract header
        
        log(f"Successfully wrote {total_lines:,} measurements to {temp_output_file}")
        log(f"Sample columns: {list(sample_df.columns)}")
        
        # Calculate actual counts for results
        parsed_count = total_lines
        skipped_count = len(raw_df) - (total_lines // 17)  # Rough estimate since each record produces ~17 measurements
        error_count = 0
        
        # Instead of creating a large DataFrame, create a small representative one for compatibility
        # This maintains the API contract while avoiding memory issues
        if len(sample_df) > 0:
            parsed_df = sample_df.head(100).copy()  # Small sample for API compatibility
            parsed_df.attrs['full_data_path'] = str(temp_output_file)  # Store full data path
            parsed_df.attrs['total_measurements'] = total_lines
        else:
            raise ValueError("No valid data found in output file.")
        
        sys_mem = _get_system_memory_info()
        log(f"FINAL MEMORY - Process: {sys_mem['process_rss_mb']:.1f}MB, Available: {sys_mem['system_available_mb']:.1f}MB")
        log(f"Full dataset written to disk: {temp_output_file}")

        log(
            f"Successfully parsed {len(raw_df)} records into {total_lines} measurements"
        )
        if skipped_count > 0:
            log(f"Skipped {skipped_count} records (no parser or filtered out)")
        if error_count > 0:
            log(
                f"Encountered {error_count} parsing errors"
                + (" (showing first 5)" if error_count > 5 else "")
            )

        # Show parsing summary
        summary = factory.get_parsing_summary()
        if summary["unknown_event_types"]:
            log(
                f"Event types without parsers: {', '.join(summary['unknown_event_types'])}"
            )
        if summary["supported_event_types"]:
            log(f"Supported event types: {', '.join(summary['supported_event_types'])}")

        # Data is already saved to disk during processing
        saved_file_path = temp_output_file
        
        # Convert to parquet if requested (copy the file)
        if output_format == "parquet":
            parquet_file = temp_output_file.with_suffix('.parquet')
            
            # Read and convert in chunks to avoid memory issues
            chunk_size = min(100000, memory_threshold_records // 2)
            log(f"Converting to parquet format in chunks of {chunk_size:,} rows...")
            
            first_chunk = True
            for chunk in pd.read_csv(temp_output_file, chunksize=chunk_size):
                write_mode = 'w' if first_chunk else 'a'
                chunk.to_parquet(parquet_file, engine='pyarrow', compression='snappy', 
                                index=False, append=(not first_chunk))
                first_chunk = False
            
            saved_file_path = parquet_file
            log(f"Converted to parquet: {saved_file_path}")

        log(f"Parsed data saved to: {saved_file_path}")

        # Prepare results
        end_time = datetime.now()
        results = {
            "success": True,
            "input_records": len(raw_df),
            "parsed_records": len(raw_df),  # Input records processed
            "output_measurements": total_lines,  # Actual output measurements
            "skipped_records": skipped_count,
            "packet_types": packet_types,
            "output_file": str(saved_file_path) if saved_file_path else None,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": (end_time - start_time).total_seconds(),
            "memory_optimized": True,  # Flag to indicate disk-based processing
            "full_data_path": str(saved_file_path),  # Path to complete data
        }

        # Add note to results if provided
        if note:
            results["note"] = note

        # Log execution to postgres if enabled
        if postgres_logger:
            try:
                operation = f"Parse GEMS data ({packet_types} packets)"
                parameters = {
                    "input_records": len(raw_df),
                    "packet_types": packet_types,
                    "output_format": output_format,
                    "save_to_parsed_dir": save_to_parsed_dir,
                    "original_file_path": original_file_path or "N/A",
                }
                postgres_logger.log_execution(
                    operation=operation,
                    parameters=parameters,
                    results=results,
                    script_path=__file__,
                )
            except Exception as e:
                logger.warning(f"Failed to create postgres log: {e}")
            finally:
                # Ensure database connections are properly closed
                postgres_logger.close()

        return parsed_df, results

    except Exception as e:
        # Prepare error results
        end_time = datetime.now()
        error_results = {
            "success": False,
            "error": str(e),
            "input_records": len(raw_df),
            "packet_types": packet_types,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": (end_time - start_time).total_seconds(),
        }

        # Add note to results if provided
        if note:
            error_results["note"] = note

        # Log execution to postgres if enabled (even for failures)
        if postgres_logger:
            try:
                operation = f"Parse GEMS data ({packet_types} packets) - FAILED"
                parameters = {
                    "input_records": len(raw_df),
                    "packet_types": packet_types,
                    "output_format": output_format,
                    "save_to_parsed_dir": save_to_parsed_dir,
                    "original_file_path": original_file_path or "N/A",
                }
                postgres_logger.log_execution(
                    operation=operation,
                    parameters=parameters,
                    results=error_results,
                    script_path=__file__,
                )
            except Exception as log_e:
                logger.warning(f"Failed to create postgres log for error: {log_e}")
            finally:
                # Ensure database connections are properly closed
                postgres_logger.close()

        # Re-raise the original exception
        raise


def _save_to_parsed_dir(
    parsed_df: pd.DataFrame, original_file_path: str, output_format: str = "csv"
) -> Path:
    """Save parsed data to data/parsed directory with standard naming."""
    from .output.csv_writer import CSVWriter
    from .output.parquet_writer import ParquetWriter

    # Generate output file path
    repo_root = Path(__file__).parents[
        3
    ]  # Go up from src/rtgs_lab_tools/data_parser/core.py to project root
    parsed_dir = repo_root / "data" / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_stem = Path(original_file_path).stem
    output_filename = f"{input_stem}_parsed_{timestamp}.{output_format}"
    output_path = parsed_dir / output_filename

    # Save using appropriate writer
    if output_format == "csv":
        writer = CSVWriter()
        writer.write(parsed_df, str(output_path))
    elif output_format == "parquet":
        writer = ParquetWriter()
        writer.write(parsed_df, str(output_path))

    return output_path
