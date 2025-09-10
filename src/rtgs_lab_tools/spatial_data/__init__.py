"""Spatial data extraction tools for RTGS Lab Tools."""

# Heavy dependencies are imported lazily when needed
# This prevents long load times for simple commands like 'rtgs --help'


def __getattr__(name):
    """Lazy loading of heavy dependencies"""
    if name == "extract_spatial_data":
        from .core.extractor import extract_spatial_data
        return extract_spatial_data
    elif name == "list_available_datasets":
        from .registry.dataset_registry import list_available_datasets
        return list_available_datasets
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "extract_spatial_data",
    "list_available_datasets",
]