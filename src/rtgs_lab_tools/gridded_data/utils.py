sources = {
    "Sentinel-2": "COPERNICUS/S2_SR_HARMONIZED",
    "Landsat-8": "LANDSAT/LC08/C02/T1_L2",
    "Landsat-9": "LANDSAT/LC09/C02/T1_L2",
    "MOD": "MODIS/061/MOD09GA",  # Terra
    "MYD": "MODIS/006/MYDOCGA",  # Aqua
    "VIIRS": "NASA/VIIRS/002/VNP09GA",
    "SMAP": "NASA/SMAP/SPL3SMP_E/005",
    "ERA5-Land": "ECMWF/ERA5_LAND/DAILY_AGGR",
    "OpenET": "OpenET/ENSEMBLE/CONUS/GRIDMET/MONTHLY/v2_0",
    "NLCD": "USGS/NLCD_RELEASES/2021_REL/NLCD",
    "ESA": "ESA/WorldCover/v200",
    # ... extend as needed
}

qa_bands = {
    "Sentinel-2": "QA60",
    "Landsat-8": "QA_PIXEL",
    "Landsat-9": "QA_PIXEL",
    "MOD": "state_1km",  # Terra
    "MYD": "state_1km",  # Aqua
    "VIIRS": "QF1",
}


def load_roi_json(path):
    """Load ROI as plain JSON for Planet Labs (no Earth Engine)"""
    import json
    with open(path) as f:
        roi_geom = json.load(f)
    
    # Convert to format Planet Labs functions expect
    return {
        "features": [{
            "geometry": roi_geom
        }]
    }
