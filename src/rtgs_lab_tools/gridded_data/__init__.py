"""Gridded climate data access tools for RTGS Lab Tools."""

# Import sources for immediate availability
from .utils import sources

# Empty __init__.py to avoid loading heavy dependencies at import time
# Functions are imported directly from submodules when needed

__all__ = [
    "download_GEE_raster",
    "download_GEE_point",
    "search_images",
    "load_roi",
    "list_GEE_vars",
    "extract_time_series",
    "init_ee",
    "sources",
    "quick_search",
    "download_scenes",
    "download_clipped_scenes",
]
