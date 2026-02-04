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
    elif name == "get_dataset_config":
        from .registry.dataset_registry import get_dataset_config

        return get_dataset_config
    elif name == "get_dataset_source":
        from .registry.dataset_registry import get_dataset_source

        return get_dataset_source
    elif name == "format_dataset_list_for_llm":
        from .registry.dataset_registry import format_dataset_list_for_llm

        return format_dataset_list_for_llm
    elif name == "is_fgdb_available":
        from .sources.fgdb import is_fgdb_available

        return is_fgdb_available
    elif name == "get_fgdb_path":
        from .sources.fgdb import get_fgdb_path

        return get_fgdb_path
    elif name == "get_config":
        from .config import get_config

        return get_config
    elif name == "load_config":
        from .config import load_config

        return load_config
    elif name == "set_config":
        from .config import set_config

        return set_config
    elif name == "SpatialDataConfig":
        from .config import SpatialDataConfig

        return SpatialDataConfig
    elif name == "list_datasets_by_mode":
        from .registry.dataset_registry import list_datasets_by_mode

        return list_datasets_by_mode
    elif name == "get_dataset_config_by_mode":
        from .registry.dataset_registry import get_dataset_config_by_mode

        return get_dataset_config_by_mode
    elif name == "format_dataset_list_by_mode":
        from .registry.dataset_registry import format_dataset_list_by_mode

        return format_dataset_list_by_mode
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "extract_spatial_data",
    "list_available_datasets",
    "get_dataset_config",
    "get_dataset_source",
    "format_dataset_list_for_llm",
    "is_fgdb_available",
    "get_fgdb_path",
    "get_config",
    "load_config",
    "set_config",
    "SpatialDataConfig",
    "list_datasets_by_mode",
    "get_dataset_config_by_mode",
    "format_dataset_list_by_mode",
]
