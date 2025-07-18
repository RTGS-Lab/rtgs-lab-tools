# Gridded Data Module

Download and process climate data from Google Earth Engine (GEE) and other gridded data sources.

## CLI Usage

### List Available Datasets

```bash
# List all available GEE datasets
rtgs gridded-data list-gee-datasets

# List variables for a specific dataset
rtgs gridded-data list-gee-variables --source MOD
```

### Download Point Data

Download satellite data as point-like pixel values to local CSV files:

```bash
# Basic point data download
rtgs gridded-data get-gee-point \
  --source MOD \
  --variables "sur_refl_b01,sur_refl_b02" \
  --start-date 2023-06-25 \
  --end-date 2023-07-01 \
  --roi ./data/point_roi.json \
  --out-dir ./data

# With cloud filtering
rtgs gridded-data get-gee-point \
  --source MOD \
  --variables "sur_refl_b01,sur_refl_b02" \
  --start-date 2023-06-25 \
  --end-date 2023-07-01 \
  --roi ./data/point_roi.json \
  --clouds 30 \
  --out-dir ./data
```

### Download Raster Data

Download satellite imagery as raster files to Google Drive or Google Cloud Storage:

```bash
# Download to Google Drive
rtgs gridded-data get-gee-raster \
  --source MOD \
  --variables "sur_refl_b01,sur_refl_b02" \
  --start-date 2023-06-25 \
  --end-date 2023-07-01 \
  --roi ./data/bbox_roi.json \
  --clouds 50 \
  --out-dest drive \
  --folder my_satellite_data

# Download to Google Cloud Storage bucket
rtgs gridded-data get-gee-raster \
  --source MOD \
  --variables "sur_refl_b01,sur_refl_b02" \
  --start-date 2023-06-25 \
  --end-date 2023-07-01 \
  --roi ./data/bbox_roi.json \
  --out-dest bucket \
  --folder gs://my-bucket/satellite-data
```

### Search GEE Data

```bash
# Search for available data between dates
rtgs gridded-data gee-search \
  --source MOD \
  --start-date 2023-06-01 \
  --end-date 2023-06-30 \
  --roi ./data/search_roi.json
```

### PlanetLabs Imagery

```bash
# Search for available images between dates for given sensors and ROI
# Saves a CSV file with all available images
rtgs gridded-data quick-search \
  --source PSScene,SkySatScene \
  --start-date 2020-06-01 \
  --end-date 2022-06-01 \
  --roi ./data/test_bbox_roi.json \
  --clouds 50 \
  --out-dir ./data

# Download raw scenes from file or between dates for a given ROI
rtgs gridded-data download-scenes \
  --source PSScene,SkySatScene \
  --meta-file ./data/search_results_PlanetLabs_2015-06-01_2022-06-01 \
  --out-dir ./data

# Download clipped imagery for selected sensor and region of interest
# Saves image raster file, XML and JSON with metadata
rtgs gridded-data download-clipped-scenes \
  --source PSScene \
  --meta-file ./data/search_results_PlanetLabs_2015-06-01_2022-06-01 \
  --out-dir ./data \
  --roi ./data/test_bbox_roi.json
```

### Command Options

**Common Options:**
- `--source TEXT`: Dataset short name (e.g., "MOD" for MODIS) (required)
- `--variables TEXT`: Comma-separated variable names (required)
- `--start-date TEXT`: Start date in YYYY-MM-DD format (required)
- `--end-date TEXT`: End date in YYYY-MM-DD format (required)
- `--roi TEXT`: Region of interest JSON file path (required)
- `--clouds TEXT`: Cloud percentage threshold for filtering

**Point Data Options:**
- `--out-dir TEXT`: Local output directory (required)

**Raster Data Options:**
- `--out-dest TEXT`: "drive" for Google Drive or "bucket" for Cloud Storage (required)
- `--folder TEXT`: Output folder name or bucket path

**PlanetLabs Options:**
- `--source TEXT`: Sensor types (e.g., "PSScene,SkySatScene") (required)
- `--meta-file TEXT`: Path to search results file for download operations
- `--out-dir TEXT`: Local output directory (required)
- `--roi TEXT`: Region of interest JSON file path (required for clipped scenes)
- `--clouds INTEGER`: Cloud percentage threshold for filtering

## Python API Usage

### Import and Basic Usage

```python
from rtgs_lab_tools.gridded_data import gee

# List available datasets
datasets = gee.list_available_datasets()
for dataset in datasets:
    print(f"{dataset['short_name']}: {dataset['description']}")

# List variables for a dataset
variables = gee.list_dataset_variables("MOD")
for var in variables:
    print(f"{var['name']}: {var['description']}")
```

### Download Point Data

```python
from rtgs_lab_tools.gridded_data.gee import download_point_data

# Define region of interest
roi = {
    "type": "Point",
    "coordinates": [-93.2650, 44.9778]  # Minneapolis coordinates
}

# Download point data
result = download_point_data(
    source="MOD",
    variables=["sur_refl_b01", "sur_refl_b02"],
    start_date="2023-06-25",
    end_date="2023-07-01",
    roi=roi,
    cloud_threshold=30,
    output_dir="./data"
)

print(f"Downloaded to: {result['output_file']}")
```

### Download Raster Data

```python
from rtgs_lab_tools.gridded_data.gee import download_raster_data

# Define bounding box
roi = {
    "type": "Polygon",
    "coordinates": [[
        [-94.0, 45.0],  # Northwest corner
        [-93.0, 45.0],  # Northeast corner
        [-93.0, 44.0],  # Southeast corner
        [-94.0, 44.0],  # Southwest corner
        [-94.0, 45.0]   # Close polygon
    ]]
}

# Download raster data to Google Drive
result = download_raster_data(
    source="MOD",
    variables=["sur_refl_b01", "sur_refl_b02"],
    start_date="2023-06-25",
    end_date="2023-07-01",
    roi=roi,
    destination="drive",
    folder="satellite_analysis"
)

print(f"Export task created: {result['task_id']}")
```

### Advanced Usage with Custom Processing

```python
from rtgs_lab_tools.gridded_data.gee import get_image_collection
import ee

# Initialize Earth Engine (requires authentication)
ee.Initialize()

# Get image collection with custom filters
collection = get_image_collection(
    source="MOD",
    start_date="2023-06-01",
    end_date="2023-06-30",
    roi=roi,
    cloud_threshold=20
)

# Apply custom processing
def ndvi_calculation(image):
    nir = image.select('sur_refl_b02')
    red = image.select('sur_refl_b01')
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    return image.addBands(ndvi)

# Process collection
processed = collection.map(ndvi_calculation)

# Export results
task = ee.batch.Export.image.toDrive(
    image=processed.median(),
    description='NDVI_analysis',
    folder='satellite_analysis',
    scale=500
)
task.start()
```

## Region of Interest (ROI) Formats

### Point ROI
For point-based data extraction:

```json
{
    "type": "Point",
    "coordinates": [-93.2650, 44.9778]
}
```

### Polygon ROI
For area-based data extraction:

```json
{
    "type": "Polygon",
    "coordinates": [[
        [-94.0, 45.0],
        [-93.0, 45.0],
        [-93.0, 44.0],
        [-94.0, 44.0],
        [-94.0, 45.0]
    ]]
}
```

### Multi-Point ROI
For multiple point locations:

```json
{
    "type": "MultiPoint",
    "coordinates": [
        [-93.2650, 44.9778],
        [-93.2000, 44.9500],
        [-93.3000, 45.0000]
    ]
}
```

## Available Datasets

### MODIS (MOD)
- **Description**: Moderate Resolution Imaging Spectroradiometer
- **Temporal Coverage**: 2000-present
- **Spatial Resolution**: 250m-1km
- **Key Variables**: Surface reflectance, NDVI, LST, snow cover

**Common Variables:**
- `sur_refl_b01`: Red surface reflectance
- `sur_refl_b02`: NIR surface reflectance
- `sur_refl_b03`: Blue surface reflectance
- `sur_refl_b04`: Green surface reflectance

### Landsat (LS)
- **Description**: Landsat 8/9 Collection 2
- **Temporal Coverage**: 2013-present
- **Spatial Resolution**: 30m
- **Key Variables**: Surface reflectance, thermal, panchromatic

### Sentinel-2 (S2)
- **Description**: Sentinel-2 MSI
- **Temporal Coverage**: 2015-present
- **Spatial Resolution**: 10-60m
- **Key Variables**: Surface reflectance, vegetation indices

### PlanetLabs
- **Description**: High-resolution commercial satellite imagery
- **Temporal Coverage**: 2009-present (varies by sensor)
- **Spatial Resolution**: 0.8m-5m depending on sensor
- **Key Sensors**: PSScene (PlanetScope), SkySatScene (SkySat)

**Available Sensors:**
- `PSScene`: PlanetScope constellation (3-5m resolution, daily coverage)
- `SkySatScene`: SkySat constellation (0.8-1m resolution, targeted coverage)

## Configuration

### Google Earth Engine Setup

1. **Create Google Cloud Project**
   ```bash
   # Install gcloud CLI and authenticate
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Enable Earth Engine API**
   - Go to Google Cloud Console
   - Enable Earth Engine API for your project
   - Create service account credentials

3. **Authenticate Earth Engine**
   ```python
   import ee
   ee.Authenticate()  # Follow prompts for authentication
   ee.Initialize(project='your-project-id')
   ```

4. **Environment Variables**
   Add to your `.env` file:
   ```env
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

### Google Drive Setup
For raster downloads to Google Drive:
1. Ensure your Google account has sufficient storage
2. Authenticate with the same account used for Earth Engine
3. Files will appear in the specified folder in your Drive

### PlanetLabs Setup
For PlanetLabs imagery access:
1. **Create PlanetLabs Account**
   - Sign up at [Planet.com](https://www.planet.com/)
   - Obtain API access credentials

2. **Environment Variables**
   Add to your `.env` file:
   ```env
   PL_API_KEY=your_planet_labs_api_key
   ```

3. **Authentication**
   The API key is automatically used for all PlanetLabs operations

## Output Formats

### Point Data Output
- **Format**: CSV files
- **Structure**: Date, location, variable values
- **Naming**: `{source}_{variables}_{start_date}_to_{end_date}_point.csv`

### Raster Data Output
- **Format**: GeoTIFF files
- **Structure**: Multi-band raster images
- **Naming**: `{source}_{variables}_{date}.tif`
- **Location**: Google Drive or Cloud Storage

## Examples

### Vegetation Monitoring Workflow

```python
from rtgs_lab_tools.gridded_data import gee
import json

# Define study area (Minnesota agricultural region)
roi = {
    "type": "Polygon", 
    "coordinates": [[
        [-96.0, 47.0], [-90.0, 47.0],
        [-90.0, 43.0], [-96.0, 43.0],
        [-96.0, 47.0]
    ]]
}

# Save ROI to file
with open("mn_agriculture.json", "w") as f:
    json.dump(roi, f)

# Download MODIS vegetation data for growing season
result = gee.download_point_data(
    source="MOD",
    variables=["sur_refl_b01", "sur_refl_b02", "NDVI"],
    start_date="2023-04-01",
    end_date="2023-10-31",
    roi=roi,
    cloud_threshold=20,
    output_dir="./vegetation_data"
)

print(f"Vegetation data saved to: {result['output_file']}")
```

### Multi-Sensor Comparison

```python
# Compare MODIS and Landsat data for the same region
sensors = ["MOD", "LS"]
variables = ["sur_refl_b01", "sur_refl_b02"]

for sensor in sensors:
    result = gee.download_point_data(
        source=sensor,
        variables=variables,
        start_date="2023-06-01",
        end_date="2023-08-31",
        roi=roi,
        output_dir=f"./comparison/{sensor}"
    )
    print(f"{sensor} data: {result['output_file']}")
```

## Error Handling

### Common Issues
- **Authentication errors**: Ensure Google Earth Engine is properly authenticated
- **Quota exceeded**: Check Google Earth Engine usage limits
- **Invalid ROI**: Verify JSON format and coordinate system (WGS84)
- **No data available**: Check date ranges and cloud thresholds

### Troubleshooting
1. **Authentication**: Run `ee.Authenticate()` in Python to re-authenticate
2. **Project setup**: Verify Google Cloud project has Earth Engine enabled
3. **ROI validation**: Use GeoJSON validators to check ROI format
4. **Data availability**: Use `gee-search` command to check data availability

## Integration

### With Sensing Data Module
```python
from rtgs_lab_tools import sensing_data, gridded_data

# Get field sensor locations
sensor_data = sensing_data.extract_data(project="Field Study")
locations = sensor_data.get_unique_locations()

# Download satellite data for sensor locations
for location in locations:
    roi = {"type": "Point", "coordinates": [location.lon, location.lat]}
    satellite_data = gridded_data.download_point_data(
        source="MOD",
        variables=["NDVI", "LST"],
        roi=roi,
        start_date="2023-01-01",
        end_date="2023-12-31"
    )
```

### With Visualization Module
```python
from rtgs_lab_tools import gridded_data, visualization

# Download and visualize satellite time series
result = gridded_data.download_point_data(...)
plot_path = visualization.create_time_series_plot(
    df=result["data"],
    measurement_name="NDVI",
    title="NDVI Time Series"
)
```