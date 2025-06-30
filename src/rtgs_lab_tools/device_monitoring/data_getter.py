# should uitlize get_raw_data from sensing_data module
# should return a df
# To run: python -m rtgs_lab_tools.device_monitoring.data_getter

# gets data from a database
# inputs: timeframe, database, project, credentials, node_ids
# outputs: csv file
# utilizes functions from get_sensing_data

# list_available_projects() FUNCITON

import sys
import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # temporary fix to import modules from parent directory

# from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import pprint
# from error_code_parser import parse_json_file
# from error_code_parser import load_error_database
from datetime import datetime, timedelta

# from get_sensing_data import create_engine_from_credentials, load_credentials_from_env, get_raw_data, ensure_data_directory, save_data
from ..core.config import Config
from ..core.database import DatabaseManager
from ..sensing_data.data_extractor import get_raw_data

# load_dotenv()  # Load environment variables from .env

# use this connection for direct queries
# def get_connection():
#     return psycopg2.connect(
#         host=os.getenv("DB_HOST"),
#         port=os.getenv("DB_PORT"),
#         database=os.getenv("DB_NAME"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         cursor_factory=RealDictCursor  # Makes query results dict-like instead of tuples
#     )

# def load_credentials():
#     return {
#         'host': os.getenv('DB_HOST'),
#         'port': os.getenv('DB_PORT'),
#         'db': os.getenv('DB_NAME'),
#         'user': os.getenv('DB_USER'),
#         'pass': os.getenv('DB_PASSWORD')
#     }

# Example usage of the get_connection function
# old method for getting data directly from the database
# def fetch_latest_raw_entries(limit=5):
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute(f"""
#                 SELECT * 
#                 FROM public.raw 
#                 ORDER BY ingest_time DESC 
#                 LIMIT {limit};
#                 """) # DESC is descending order
    
#     rows = cur.fetchall() # The data type is a list of dict-like objects due to RealDictCursor
#     cur.close()
#     conn.close()
#     return rows


# Get the most recent diagnostic/v2 row for a given node_id where the message contains 
# a Kestrel object inside Diagnostic -> Devices, and then
# extract the first value in PORT_V as the battery level.
# old method for getting data directly from the database
# def fetch_latest_battery(node_id):
#     conn = get_connection()
#     cur = conn.cursor()
    
#     query = """
#     SELECT
#       node_id,
#       publish_time,
#       (kestrel_data->'PORT_V'->>0)::float AS battery_voltage
#     FROM public.raw,
#       jsonb_array_elements((message::jsonb)->'Diagnostic'->'Devices') device_data,
#       LATERAL (
#         SELECT device_data->'Kestrel' AS kestrel_data
#         WHERE device_data ? 'Kestrel'
#       ) sub
#     WHERE
#       event = 'diagnostic/v2'
#       AND node_id = %s
#     ORDER BY publish_time DESC
#     LIMIT 1;
#     """
    
#     cur.execute(query, (node_id,))
#     row = cur.fetchone()
#     cur.close()
#     conn.close()

#     return row # battery['node_id'], battery['battery_voltage'], battery['publish_time']



def get_data(start_date, end_date, project, node_ids=None):
    #create engine using get_sensing_data methods
    #get the raw data using get_sensning_data methods
    #return the dataframe

    # Initialize database connection
    config = Config()
    db_manager = DatabaseManager(config)

    # extract data
    raw_data_df = get_raw_data(db_manager, project, start_date, end_date, node_ids) # df = dataframe

    if raw_data_df.empty:
        print("No data found for the given timeframe.")
        return None
    
    return raw_data_df
   

if __name__ == "__main__":
    data = get_data(
        start_date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        end_date=datetime.now().strftime('%Y-%m-%d'),
        project="ALL",
        node_ids=None  # Example node ID
    )

    # pprint.pprint(data)