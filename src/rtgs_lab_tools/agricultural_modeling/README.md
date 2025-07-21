# Agricultural Modeling Module

Crop calculations, unit conversions, and agricultural modeling tools.

## CLI Usage

### Crop Parameters and Calculations

```bash
# List all available crops and their parameters
rtgs agricultural-modeling crops list-crops

# Get parameters for a specific crop
rtgs agricultural-modeling crops get-params --crop corn

# Calculate Growing Degree Days (GDD)
rtgs agricultural-modeling crops calculate-gdd \
  --t-min 15.5 --t-max 28.2 --crop corn

# Calculate with different method
rtgs agricultural-modeling crops calculate-gdd \
  --t-min 15.5 --t-max 28.2 --crop corn --method original

# Calculate Corn Heat Units (CHU)
rtgs agricultural-modeling crops calculate-chu \
  --t-min 15.5 --t-max 28.2

# Calculate with custom base temperature
rtgs agricultural-modeling crops calculate-chu \
  --t-min 15.5 --t-max 28.2 --t-base 8.0
```

### Evapotranspiration Calculations

```bash
# Show required columns for ET calculation
rtgs agricultural-modeling evapotranspiration requirements

# Calculate ET from weather data CSV
rtgs agricultural-modeling evapotranspiration calculate \
  --input-file weather_data.csv \
  --output et_results.csv

# Validate input data without calculation
rtgs agricultural-modeling evapotranspiration calculate \
  --input-file weather_data.csv --validate-only
```

### Unit Conversions

```bash
# Temperature conversions
rtgs agricultural-modeling temperature celsius-to-fahrenheit 25.0
rtgs agricultural-modeling temperature fahrenheit-to-celsius 77.0
rtgs agricultural-modeling temperature celsius-to-kelvin 25.0

# Distance conversions
rtgs agricultural-modeling distance meters-to-feet 100.0
rtgs agricultural-modeling distance feet-to-meters 328.0
rtgs agricultural-modeling distance km-to-miles 10.0

# Speed conversions
rtgs agricultural-modeling speed mps-to-mph 10.0
rtgs agricultural-modeling speed mph-to-mps 22.4
rtgs agricultural-modeling speed kmh-to-mph 100.0
```

## Python API Usage

### Import and Basic Usage

```python
from rtgs_lab_tools.agricultural_modeling import crop_parameters, growing_degree_days, evapotranspiration

# Get crop parameters
corn_params = crop_parameters.get_crop_parameters("corn")
print(f"Corn base temp: {corn_params['base_temp']}°C")
print(f"Corn upper temp: {corn_params['upper_temp']}°C")

# Calculate GDD
gdd = growing_degree_days.calculate_gdd(
    t_min=15.5,
    t_max=28.2,
    base_temp=corn_params['base_temp'],
    upper_temp=corn_params['upper_temp']
)
print(f"GDD: {gdd}")

# Calculate CHU
chu = growing_degree_days.calculate_chu(t_min=15.5, t_max=28.2)
print(f"CHU: {chu}")
```

### Advanced Crop Modeling

```python
from rtgs_lab_tools.agricultural_modeling.growing_degree_days import GDDCalculator
import pandas as pd

# Load weather data
weather_df = pd.read_csv("weather_data.csv")

# Initialize GDD calculator
calculator = GDDCalculator()

# Calculate accumulated GDD for growing season
weather_df['gdd'] = weather_df.apply(
    lambda row: calculator.calculate_gdd(
        t_min=row['temp_min'],
        t_max=row['temp_max'],
        crop="corn"
    ), axis=1
)

# Calculate cumulative GDD
weather_df['cumulative_gdd'] = weather_df['gdd'].cumsum()

# Determine crop development stages
def get_growth_stage(cumulative_gdd):
    if cumulative_gdd < 280:
        return "emergence"
    elif cumulative_gdd < 680:
        return "vegetative"
    elif cumulative_gdd < 1400:
        return "reproductive"
    else:
        return "maturity"

weather_df['growth_stage'] = weather_df['cumulative_gdd'].apply(get_growth_stage)
```

### Evapotranspiration Analysis

```python
from rtgs_lab_tools.agricultural_modeling.evapotranspiration import calculate_reference_et
import pandas as pd

# Load weather data with required columns
weather_data = pd.read_csv("daily_weather.csv")

# Calculate reference ET
et_results = calculate_reference_et(
    temperature_max=weather_data['temp_max'],
    temperature_min=weather_data['temp_min'],
    humidity_max=weather_data['rh_max'],
    humidity_min=weather_data['rh_min'],
    wind_speed=weather_data['wind_speed'],
    solar_radiation=weather_data['solar_rad'],
    latitude=44.9778,  # Minneapolis
    elevation=260      # meters
)

# Add ET to weather data
weather_data['et0'] = et_results['et0_mm_day']
weather_data['et0_inches'] = et_results['et0_mm_day'] * 0.0393701

# Calculate crop ET with crop coefficient
weather_data['etc_corn'] = weather_data['et0'] * 1.2  # Corn Kc = 1.2 mid-season
```

### Unit Conversion Utilities

```python
from rtgs_lab_tools.agricultural_modeling import temperature, distance_speed

# Temperature conversions
temp_f = temperature.celsius_to_fahrenheit(25.0)
temp_c = temperature.fahrenheit_to_celsius(77.0)
temp_k = temperature.celsius_to_kelvin(25.0)

# Distance conversions
feet = distance_speed.meters_to_feet(100.0)
meters = distance_speed.feet_to_meters(328.0)
miles = distance_speed.km_to_miles(10.0)

# Speed conversions
mph = distance_speed.mps_to_mph(10.0)
mps = distance_speed.mph_to_mps(22.4)

# Batch conversions
temperatures_c = [20, 25, 30, 35]
temperatures_f = [temperature.celsius_to_fahrenheit(t) for t in temperatures_c]
```

## Available Crops

### Supported Crop Types

The module includes parameters for common agricultural crops:

**Field Crops:**
- `corn` - Corn/Maize (Zea mays)
- `soybean` - Soybean (Glycine max)
- `wheat` - Wheat (Triticum aestivum)
- `barley` - Barley (Hordeum vulgare)
- `oats` - Oats (Avena sativa)

**Vegetable Crops:**
- `tomato` - Tomato (Solanum lycopersicum)
- `potato` - Potato (Solanum tuberosum)
- `carrot` - Carrot (Daucus carota)
- `lettuce` - Lettuce (Lactuca sativa)

**Tree Fruits:**
- `apple` - Apple (Malus domestica)
- `grape` - Grape (Vitis vinifera)

### Crop Parameters

Each crop includes the following parameters:

```python
{
    "name": "corn",
    "scientific_name": "Zea mays",
    "base_temp": 10.0,      # Base temperature (°C)
    "upper_temp": 30.0,     # Upper temperature limit (°C)
    "gdd_to_maturity": 2700, # Total GDD needed for maturity
    "development_stages": {
        "emergence": 120,
        "vegetative": 680,
        "reproductive": 1400,
        "maturity": 2700
    }
}
```

## Growing Degree Days (GDD)

### Calculation Methods

**Modified Method (Default):**
```
GDD = ((T_max + T_min) / 2) - T_base
where T_max and T_min are capped at T_upper
```

**Original Method:**
```
GDD = ((T_max + T_min) / 2) - T_base
No upper temperature limit applied
```

### Usage Examples

```python
from rtgs_lab_tools.agricultural_modeling.growing_degree_days import calculate_gdd_for_crop

# Calculate GDD for specific crop
gdd = calculate_gdd_for_crop(
    t_min=15.0,
    t_max=28.0,
    crop="corn",
    method="modified"
)

# Calculate GDD with custom parameters
gdd_custom = calculate_gdd_for_crop(
    t_min=15.0,
    t_max=28.0,
    base_temp=8.0,
    upper_temp=32.0,
    method="original"
)
```

## Corn Heat Units (CHU)

CHU is a specialized index used primarily for corn in Canada:

```python
from rtgs_lab_tools.agricultural_modeling.growing_degree_days import calculate_chu

# Standard CHU calculation (base temp = 10°C)
chu = calculate_chu(t_min=12.5, t_max=25.5)

# CHU with custom base temperature
chu_custom = calculate_chu(t_min=12.5, t_max=25.5, t_base=8.0)
```

## Evapotranspiration (ET)

### Reference ET Calculation

The module implements the FAO-56 Penman-Monteith equation for reference evapotranspiration:

```python
from rtgs_lab_tools.agricultural_modeling.evapotranspiration import calculate_et0_daily

et0 = calculate_et0_daily(
    temp_max=28.5,      # Maximum temperature (°C)
    temp_min=15.2,      # Minimum temperature (°C)
    rh_max=85,          # Maximum relative humidity (%)
    rh_min=42,          # Minimum relative humidity (%)
    wind_speed=2.1,     # Wind speed at 2m height (m/s)
    solar_radiation=25.2, # Solar radiation (MJ/m²/day)
    latitude=44.9778,   # Latitude (decimal degrees)
    elevation=260,      # Elevation (m)
    day_of_year=150     # Day of year (1-365)
)
```

### Required Data Format for CSV Input

When using the CLI or `calculate_reference_et` function with CSV files, the following columns are required:

```csv
date,temp_max,temp_min,rh_max,rh_min,wind_speed,solar_radiation
2023-06-01,28.5,15.2,85,42,2.1,25.2
2023-06-02,30.1,16.8,78,38,1.8,26.8
```

**Column Descriptions:**
- `date`: Date in YYYY-MM-DD format
- `temp_max`: Maximum daily temperature (°C)
- `temp_min`: Minimum daily temperature (°C)
- `rh_max`: Maximum relative humidity (%)
- `rh_min`: Minimum relative humidity (%)
- `wind_speed`: Wind speed at 2m height (m/s)
- `solar_radiation`: Solar radiation (MJ/m²/day)

## Examples

### Seasonal GDD Analysis

```python
from rtgs_lab_tools.agricultural_modeling import growing_degree_days
import pandas as pd
import matplotlib.pyplot as plt

# Load daily weather data for growing season
weather = pd.read_csv("growing_season_2023.csv")
weather['date'] = pd.to_datetime(weather['date'])

# Calculate daily GDD for multiple crops
crops = ['corn', 'soybean', 'wheat']
for crop in crops:
    weather[f'gdd_{crop}'] = weather.apply(
        lambda row: growing_degree_days.calculate_gdd_for_crop(
            t_min=row['temp_min'],
            t_max=row['temp_max'],
            crop=crop
        ), axis=1
    )
    weather[f'cumulative_gdd_{crop}'] = weather[f'gdd_{crop}'].cumsum()

# Plot cumulative GDD
plt.figure(figsize=(12, 8))
for crop in crops:
    plt.plot(weather['date'], weather[f'cumulative_gdd_{crop}'], 
             label=f'{crop.title()} GDD', linewidth=2)

plt.xlabel('Date')
plt.ylabel('Cumulative Growing Degree Days (°C·day)')
plt.title('Cumulative GDD Comparison - Growing Season 2023')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

### Crop Development Tracking

```python
from rtgs_lab_tools.agricultural_modeling.crop_parameters import get_crop_parameters
from rtgs_lab_tools.agricultural_modeling.growing_degree_days import calculate_gdd_for_crop

# Get corn development stages
corn_params = get_crop_parameters("corn")
stages = corn_params['development_stages']

# Calculate development progress
daily_weather = pd.read_csv("field_weather.csv")
daily_weather['gdd'] = daily_weather.apply(
    lambda row: calculate_gdd_for_crop(
        t_min=row['temp_min'],
        t_max=row['temp_max'],
        crop="corn"
    ), axis=1
)

daily_weather['cumulative_gdd'] = daily_weather['gdd'].cumsum()

# Determine current growth stage
def get_corn_stage(cumulative_gdd):
    for stage, threshold in sorted(stages.items(), key=lambda x: x[1]):
        if cumulative_gdd < threshold:
            return stage
    return "mature"

daily_weather['growth_stage'] = daily_weather['cumulative_gdd'].apply(get_corn_stage)

# Find stage transition dates
stage_transitions = {}
for stage in stages.keys():
    transition_row = daily_weather[daily_weather['growth_stage'] == stage].iloc[0]
    stage_transitions[stage] = {
        'date': transition_row['date'],
        'gdd': transition_row['cumulative_gdd']
    }

print("Corn Development Stages:")
for stage, info in stage_transitions.items():
    print(f"  {stage.title()}: {info['date']} (GDD: {info['gdd']:.1f})")
```

### Water Requirement Analysis

```python
from rtgs_lab_tools.agricultural_modeling.evapotranspiration import calculate_reference_et
import pandas as pd

# Load weather data
weather = pd.read_csv("irrigation_weather.csv")

# Calculate reference ET
et_results = calculate_reference_et(weather, latitude=44.9778, elevation=260)
weather['et0_mm'] = et_results['et0_mm_day']

# Define crop coefficients for corn by growth stage
crop_coefficients = {
    'initial': 0.3,     # Emergence to 10% ground cover
    'development': 0.7,  # 10% cover to effective full cover
    'mid_season': 1.2,   # Full cover to start of maturity
    'late_season': 0.6   # Start of maturity to harvest
}

# Assign Kc based on day of year (example for northern climate)
def get_kc(day_of_year):
    if day_of_year < 140:  # Before May 20
        return crop_coefficients['initial']
    elif day_of_year < 200:  # May 20 - July 19
        return crop_coefficients['development']
    elif day_of_year < 260:  # July 19 - Sept 17
        return crop_coefficients['mid_season']
    else:
        return crop_coefficients['late_season']

weather['day_of_year'] = pd.to_datetime(weather['date']).dt.dayofyear
weather['kc'] = weather['day_of_year'].apply(get_kc)
weather['etc_mm'] = weather['et0_mm'] * weather['kc']
weather['etc_inches'] = weather['etc_mm'] * 0.0393701

# Calculate seasonal water requirement
total_et_mm = weather['etc_mm'].sum()
total_et_inches = weather['etc_inches'].sum()

print(f"Seasonal Water Requirement:")
print(f"  Total ET: {total_et_mm:.1f} mm ({total_et_inches:.1f} inches)")
print(f"  Daily Average: {weather['etc_mm'].mean():.1f} mm/day")
```

## Integration

### With Sensing Data Module
```python
from rtgs_lab_tools import sensing_data, agricultural_modeling

# Extract weather data from sensors
weather_data = sensing_data.extract_data(
    project="Weather Station Network",
    start_date="2023-04-01",
    end_date="2023-10-31"
)

# Calculate GDD from sensor data
gdd_values = []
for _, row in weather_data.iterrows():
    gdd = agricultural_modeling.calculate_gdd_for_crop(
        t_min=row['temp_min'],
        t_max=row['temp_max'],
        crop="corn"
    )
    gdd_values.append(gdd)

weather_data['gdd'] = gdd_values
```

### With Visualization Module
```python
from rtgs_lab_tools import agricultural_modeling, visualization

# Calculate seasonal GDD data
weather_df = calculate_seasonal_gdd(weather_file="weather_2023.csv")

# Create GDD visualization
plot_path = visualization.create_time_series_plot(
    df=weather_df,
    measurement_name="cumulative_gdd_corn",
    title="Corn Growing Degree Days - 2023 Season"
)
```