"""RTGS Lab Tools - Environmental sensing and climate data toolkit."""

__version__ = "0.1.0"
__author__ = "RTGS Lab"
__email__ = "rtgs@umn.edu"

# Public names resolve on first use (PEP 562), not at import. Importing any subpackage imports
# this file first, so eager imports here made every tool -- including the MSI device-monitoring
# cron -- load matplotlib, the Particle client and the parsers whether it used them or not.
_LAZY = {
    "Config": ".core",
    "DatabaseManager": ".core",
    "APIError": ".core.exceptions",
    "DatabaseError": ".core.exceptions",
    "ValidationError": ".core.exceptions",
    "PostgresLogger": ".core.postgres_logger",
    "DataV2Parser": ".data_parser.parsers.data_parser",
    "ParserFactory": ".data_parser.parsers.factory",
    "ParticleClient": ".device_configuration",
    "ParticleConfigUpdater": ".device_configuration",
    "extract_data": ".sensing_data",
    "get_raw_data": ".sensing_data",
    "list_available_projects": ".sensing_data",
    "create_multi_parameter_plot": ".visualization",
    "create_time_series_plot": ".visualization",
    "detect_data_type": ".visualization",
    "load_and_prepare_data": ".visualization",
    # Climate data: download_GEE_raster stays out (slow import), as before.
}


def __getattr__(name):
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    value = getattr(importlib.import_module(module, __name__), name)
    globals()[name] = value  # cache: later lookups skip __getattr__
    return value


def __dir__():
    return sorted(set(globals()) | set(_LAZY))


__all__ = [
    # Core
    "DatabaseManager",
    "Config",
    "PostgresLogger",
    "ValidationError",
    "DatabaseError",
    "APIError",
    # Data extraction
    "extract_data",
    "list_available_projects",
    "get_raw_data",
    # Data parsing
    "ParserFactory",
    "DataV2Parser",
    # Visualization
    "create_time_series_plot",
    "create_multi_parameter_plot",
    "detect_data_type",
    "load_and_prepare_data",
    # Device management
    "ParticleConfigUpdater",
    "ParticleClient",
    "ErrorCodeParser",
    # Climate data
    # "download_GEE_raster",  # Commented out to avoid slow imports
]
