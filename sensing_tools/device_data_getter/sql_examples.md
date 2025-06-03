# SQL Examples

Below are examples of correct and functioning sql queries for the GEMS Sensing database.


```
SELECT
node_id,
  to_timestamp((message::json->'Diagnostic'->>'Time')::int) as "Time",
  (elems1->'LiCor ET'->>'PUMP_V')::float AS "Pump V",
  (elems1->'LiCor ET'->>'PA_CELL')::float as "PA Cell",
  (elems1->'LiCor ET'->>'RH_CELL')::float as "RH Cell",
  (elems1->'LiCor ET'->>'TA_CELL')::float AS "TA Cell",
  (elems1->'LiCor ET'->>'RH_ENCL')::float AS "RH Encl",
  (elems1->'LiCor ET'->>'FLOW')::float AS "Flow",
  (elems1->'LiCor ET'->>'INPUT_V')::float AS "Input V",
  (elems1->'LiCor ET'->>'DATA_QC')::float AS "Data QC",
  (elems1->'LiCor ET'->>'TILT')::float AS "Tilt"
FROM $project_key.raw,
jsonb_array_elements((message::jsonb)->'Diagnostic'->'Devices') elems1
WHERE
  $__timeFilter(publish_time) 
  AND node_id IN ($node)
  AND event = 'diagnostic/v2' 
  AND elems1 ? 'LiCor ET'
  -- AND is_valid_json(message) 
  AND is_valid_time(message)
ORDER BY "Time"
```

```
def get_winterturf_data(engine, start_date=None, end_date=None, chunksize=50000, max_retries=3):
    """
    Get data from the winterturf view using chunked queries to handle large datasets.
    
    Args:
        engine: SQLAlchemy engine
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        chunksize: Number of rows to fetch in each chunk
        max_retries: Maximum number of retry attempts for failed queries
        
    Returns:
        DataFrame or generator of DataFrames depending on data size
    """
    if start_date is None:
        start_date = "2018-01-01"
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    # Using the winterturf view as specified in the documentation
    query = """
    SELECT * FROM winterturf.data
    WHERE time BETWEEN :start_date AND :end_date
    ORDER BY time
    """
    
    print(f"Fetching winterturf data from {start_date} to {end_date}...")
    
    try:
        # First check the total row count to decide whether to use chunking
        count_query = """
        SELECT COUNT(*) FROM winterturf.data
        WHERE time BETWEEN :start_date AND :end_date
        """
        
        with engine.connect() as conn:
            for attempt in range(max_retries):
                try:
                    result = conn.execute(
                        text(count_query),
                        {"start_date": start_date, "end_date": end_date}
                    )
                    row_count = result.scalar()
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"Error getting row count (attempt {attempt+1}/{max_retries}): {e}")
                        print(f"Retrying in {2**attempt} seconds...")
                        time.sleep(2**attempt)  # Exponential backoff
                    else:
                        raise
        
        print(f"Found {row_count} data points in date range")
        
        # If data is small enough, fetch it all at once
        if row_count <= chunksize:
            with engine.connect() as conn:
                for attempt in range(max_retries):
                    try:
                        result = conn.execute(
                            text(query),
                            {"start_date": start_date, "end_date": end_date}
                        )
                        data_df = pd.DataFrame(result.fetchall(), columns=result.keys())
                        print(f"Fetched {len(data_df)} data points")
                        return data_df
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"Query error (attempt {attempt+1}/{max_retries}): {e}")
                            print(f"Retrying in {2**attempt} seconds...")
                            time.sleep(2**attempt)
                        else:
                            raise
        
        # For large datasets, use chunking based on time ranges
        else:
            print(f"Large dataset detected ({row_count} rows). Using chunked retrieval...")
            
            # Get min and max timestamps
            range_query = """
            SELECT MIN(time), MAX(time) FROM winterturf.data
            WHERE time BETWEEN :start_date AND :end_date
            """
            
            with engine.connect() as conn:
                result = conn.execute(
                    text(range_query),
                    {"start_date": start_date, "end_date": end_date}
                )
                min_time, max_time = result.fetchone()
            
            # Convert to datetime objects for chunking
            min_dt = pd.to_datetime(min_time)
            max_dt = pd.to_datetime(max_time)
            
            # Calculate number of chunks needed
            total_days = (max_dt - min_dt).days + 1
            days_per_chunk = max(1, total_days // (row_count // chunksize + 1))
            
            print(f"Data spans {total_days} days. Processing in chunks of approximately {days_per_chunk} days each")
            
            # Process data in chunks
            current_start = min_dt
            all_data = []
            
            while current_start <= max_dt:
                current_end = min(current_start + pd.Timedelta(days=days_per_chunk), max_dt)
                
                chunk_query = """
                SELECT * FROM winterturf.data
                WHERE time BETWEEN :chunk_start AND :chunk_end
                ORDER BY time
                """
                
                print(f"Fetching chunk: {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}")
                
                with engine.connect() as conn:
                    for attempt in range(max_retries):
                        try:
                            result = conn.execute(
                                text(chunk_query),
                                {"chunk_start": current_start, "chunk_end": current_end}
                            )
                            chunk_df = pd.DataFrame(result.fetchall(), columns=result.keys())
                            print(f"  Fetched {len(chunk_df)} rows in this chunk")
                            all_data.append(chunk_df)
                            break
                        except Exception as e:
                            if attempt < max_retries - 1:
                                print(f"Chunk query error (attempt {attempt+1}/{max_retries}): {e}")
                                print(f"Retrying in {2**attempt} seconds...")
                                time.sleep(2**attempt)
                            else:
                                raise
                
                current_start = current_end + pd.Timedelta(seconds=1)
            
            # Combine all chunks
            final_df = pd.concat(all_data, ignore_index=True)
            print(f"Combined {len(all_data)} chunks into dataset with {len(final_df)} rows")
            return final_df
            
    except Exception as e:
        print(f"Error executing winterturf view query: {e}")
        print("Attempting fallback query method...")
        return get_data_fallback(engine, start_date, end_date, chunksize, max_retries)

def get_data_fallback(engine, start_date, end_date, chunksize=50000, max_retries=3):
    """
    Fallback query method when the view is not available.
    Uses chunking for large datasets and includes retry logic.
    """
    # Get all winterturf project nodes
    nodes_query = """
    SELECT * FROM node
    WHERE project LIKE '%winter%' OR project LIKE '%turf%'
    """
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                result = conn.execute(text(nodes_query))
                nodes_df = pd.DataFrame(result.fetchall(), columns=result.keys())
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Node query error (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {2**attempt} seconds...")
                time.sleep(2**attempt)
            else:
                raise
    
    if len(nodes_df) == 0:
        print("No winterturf nodes found")
        return pd.DataFrame()
    
    print(f"Found {len(nodes_df)} winterturf nodes")
    
    # Get node measures for these nodes
    node_ids = tuple(nodes_df['node_id'].unique())
    if len(node_ids) == 1:
        node_ids_condition = f"= '{node_ids[0]}'"
    else:
        node_ids_condition = f"IN {node_ids}"
    
    measures_query = f"""
    SELECT * FROM node_measure
    WHERE node_id {node_ids_condition}
    """
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                result = conn.execute(text(measures_query))
                measures_df = pd.DataFrame(result.fetchall(), columns=result.keys())
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Measures query error (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {2**attempt} seconds...")
                time.sleep(2**attempt)
            else:
                raise
    
    if len(measures_df) == 0:
        print("No measures found for the winterturf nodes")
        return pd.DataFrame()
    
    print(f"Found {len(measures_df)} node-measure combinations")
    
    # Get data for these node-measures
    nm_ids = tuple(measures_df['id'].unique())
    
    # First get the count to determine if chunking is needed
    count_query = """
    SELECT COUNT(*) 
    FROM data d
    WHERE d.node_measure_id IN :nm_ids
    AND d.time BETWEEN :start_date AND :end_date
    """
    
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text(count_query),
                    {"nm_ids": nm_ids, "start_date": start_date, "end_date": end_date}
                )
                row_count = result.scalar()
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Count query error (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {2**attempt} seconds...")
                time.sleep(2**attempt)
            else:
                raise
    
    print(f"Found {row_count} data points in date range")
    
    # If dataset is small enough, fetch it all at once
    if row_count <= chunksize:
        data_query = """
        SELECT d.*, nm.node_id, nm.measure
        FROM data d
        JOIN node_measure nm ON d.node_measure_id = nm.id
        WHERE d.node_measure_id IN :nm_ids
        AND d.time BETWEEN :start_date AND :end_date
        ORDER BY d.time
        """
        
        for attempt in range(max_retries):
            try:
                with engine.connect() as conn:
                    result = conn.execute(
                        text(data_query),
                        {"nm_ids": nm_ids, "start_date": start_date, "end_date": end_date}
                    )
                    data_df = pd.DataFrame(result.fetchall(), columns=result.keys())
                
                print(f"Fetched {len(data_df)} data points using fallback query")
                return data_df
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Data query error (attempt {attempt+1}/{max_retries}): {e}")
                    print(f"Retrying in {2**attempt} seconds...")
                    time.sleep(2**attempt)
                else:
                    raise
    
    # For large datasets, use chunking by time
    else:
        print(f"Large dataset detected ({row_count} rows). Using chunked retrieval...")
        
        # Get min and max timestamps
        range_query = """
        SELECT MIN(d.time), MAX(d.time)
        FROM data d
        WHERE d.node_measure_id IN :nm_ids
        AND d.time BETWEEN :start_date AND :end_date
        """
        
        with engine.connect() as conn:
            result = conn.execute(
                text(range_query),
                {"nm_ids": nm_ids, "start_date": start_date, "end_date": end_date}
            )
            min_time, max_time = result.fetchone()
        
        # Convert to datetime objects for chunking
        min_dt = pd.to_datetime(min_time)
        max_dt = pd.to_datetime(max_time)
        
        # Calculate number of chunks needed
        total_days = (max_dt - min_dt).days + 1
        days_per_chunk = max(1, total_days // (row_count // chunksize + 1))
        
        print(f"Data spans {total_days} days. Processing in chunks of approximately {days_per_chunk} days each")
        
        # Process data in chunks
        current_start = min_dt
        all_data = []
        
        while current_start <= max_dt:
            current_end = min(current_start + pd.Timedelta(days=days_per_chunk), max_dt)
            
            chunk_query = """
            SELECT d.*, nm.node_id, nm.measure
            FROM data d
            JOIN node_measure nm ON d.node_measure_id = nm.id
            WHERE d.node_measure_id IN :nm_ids
            AND d.time BETWEEN :chunk_start AND :chunk_end
            ORDER BY d.time
            """
            
            print(f"Fetching chunk: {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}")
            
            with engine.connect() as conn:
                for attempt in range(max_retries):
                    try:
                        result = conn.execute(
                            text(chunk_query),
                            {"nm_ids": nm_ids, "chunk_start": current_start, "chunk_end": current_end}
                        )
                        chunk_df = pd.DataFrame(result.fetchall(), columns=result.keys())
                        print(f"  Fetched {len(chunk_df)} rows in this chunk")
                        all_data.append(chunk_df)
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"Chunk query error (attempt {attempt+1}/{max_retries}): {e}")
                            print(f"Retrying in {2**attempt} seconds...")
                            time.sleep(2**attempt)
                        else:
                            raise
            
            current_start = current_end + pd.Timedelta(seconds=1)
        
        # Combine all chunks
        final_df = pd.concat(all_data, ignore_index=True)
        print(f"Combined {len(all_data)} chunks into dataset with {len(final_df)} rows")
        return final_df
```
