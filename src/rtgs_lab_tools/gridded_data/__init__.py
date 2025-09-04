"""Gridded climate data access tools for RTGS Lab Tools."""

# Only import lightweight utilities immediately
from .utils import sources, load_roi_json

# Heavy dependencies are imported lazily when needed
# This prevents long load times for simple commands like 'rtgs --help'

def __getattr__(name):
    """Lazy loading of heavy dependencies"""
    if name == "init_ee":
        from .gee import init_ee
        return init_ee
    elif name == "list_GEE_vars":
        from .gee import list_GEE_vars
        return list_GEE_vars
    elif name == "load_roi":
        from .gee import load_roi
        return load_roi
    elif name == "search_images":
        from .gee import search_images
        return search_images
    elif name == "download_GEE_point":
        from .gee import download_GEE_point
        return download_GEE_point
    elif name == "download_GEE_raster":
        from .gee import download_GEE_raster
        return download_GEE_raster
    elif name == "quick_search":
        from .planet import quick_search
        return quick_search
    elif name == "download_scenes":
        from .planet import download_scenes
        return download_scenes
    elif name == "download_clipped_scenes":
        from .planet import download_clipped_scenes
        return download_clipped_scenes
    elif name == "extract_time_series":
        from .processors import extract_time_series
        return extract_time_series
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

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
