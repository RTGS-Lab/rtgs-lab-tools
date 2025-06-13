import pandas as pd

from gems_sensing_parser.parsers.factory import ParserFactory
from gems_sensing_parser.parsers.data_parser import DataV2Parser
from gems_sensing_parser.parsers.diagnostic_parser import DiagnosticV2Parser
from gems_sensing_parser.parsers.error_parser import ErrorV2Parser
from gems_sensing_parser.parsers.metadata_parser import MetadataV2Parser


# Initialize the parser factory
factory = ParserFactory()
# Register parsers
factory.register_parser("data/v2", DataV2Parser)
factory.register_parser("diagnostic/v2", DiagnosticV2Parser)
factory.register_parser("error/v2", ErrorV2Parser)
factory.register_parser("metadata/v2", MetadataV2Parser)

# Load raw data
raw_data = pd.read_csv("/home/zach/Code/gems_sensing_parser/LCCMR_Irrigation_2024-06-01_to_2024-08-31_20250610_103156.csv")

# Iterate through the raw data and parse each record and append to df
parsed_data = []
for _, row in raw_data.iterrows():
    #check event type of row
    event_type = row.get("event", "")
    try:
        parsed_record = factory.create_parser(event_type).parse(row)
    except Exception as e:
        print(f"Error parsing record {row.get('id')}: {e}")
        parsed_record = None
    if parsed_record:
        parsed_data.extend(parsed_record)
# Convert parsed data to DataFrame
df_data = pd.DataFrame(parsed_data)
# Save parsed data to CSV
df_data.to_csv('gems_sensing_parser/parsed_combined_example.csv', index=False)
# Print parsed data
print("Parsed Data (data/v2):")
print(df_data.head())

