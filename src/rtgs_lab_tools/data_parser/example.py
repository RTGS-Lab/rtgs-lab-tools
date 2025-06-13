import pandas as pd



#parse data packet example
from gems_sensing_parser.parsers.data_parser import DataV2Parser
parser = DataV2Parser()
print("Parser can handle 'data/v2':", parser.can_parse("data/v2"))
raw_data = pd.read_csv("/home/zach/Code/gems_sensing_parser/LCCMR_Irrigation_2024-06-01_to_2024-08-31_20250610_103156.csv")
# Parse the first data record
parsed_data = parser.parse(raw_data.iloc[1])
print("Parsed data type:", type(parsed_data))
print("Parsed data list type:", type(parsed_data[0]))
df = pd.DataFrame(parsed_data)
df.to_csv('gems_sensing_parser/parsed_datav2_example.csv', index=False)
print(df)


#parse diagnostic packet example
from gems_sensing_parser.parsers.diagnostic_parser import DiagnosticV2Parser
parser = DiagnosticV2Parser()
print("Parser can handle 'diagnostic':", parser.can_parse("diagnostic"))
raw_data = pd.read_csv("/home/zach/Code/gems_sensing_parser/LCCMR_Irrigation_2024-06-01_to_2024-08-31_20250610_103156.csv")
# Parse the first diagnostic record
parsed_diagnostic = parser.parse(raw_data.iloc[3])
print("Parsed diagnostic type:", type(parsed_diagnostic))
print("Parsed diagnostic list type:", type(parsed_diagnostic[0]))
df_diag = pd.DataFrame(parsed_diagnostic)
df_diag.to_csv('gems_sensing_parser/parsed_diagnostic_example.csv', index=False)
print(df_diag)

