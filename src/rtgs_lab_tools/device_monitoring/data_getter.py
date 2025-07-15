'''
Overview:
    - This file is responsible for fetching raw data from the database.
    - It uses the `get_raw_data` function from the `sensing_data` module to retrieve data based on specified parameters.
Inputs:
    - start_date: Start date for the data retrieval in 'YYYY-MM-DD' format.
    - end_date: End date for the data retrieval in 'YYYY-MM-DD' format.
    - project: Project name to filter the data.
    - node_ids: Optional list of node IDs to filter the data.
Outputs:
    - pandas DataFrame containing the raw data.
'''

from ..core.config import Config
from ..core.database import DatabaseManager
from ..sensing_data.data_extractor import get_raw_data


def get_data(start_date, end_date, project, node_ids=None):
    # get the raw data using get_sensning_data methods
    # return the dataframe

    # Initialize database connection
    config = Config()
    db_manager = DatabaseManager(config)

    # extract data
    raw_data_df = get_raw_data(
        db_manager, project, start_date, end_date, node_ids
    )  # df = dataframe

    if raw_data_df.empty:
        print("No data found for the given timeframe.")
        return None

    return raw_data_df
