"""Visualization tools for RTGS Lab Tools."""

# Heavy dependencies are imported lazily when needed
# This prevents long load times for simple commands like 'rtgs --help'


def __getattr__(name):
    """Lazy loading of heavy dependencies"""
    if name == "create_time_series_plot":
        from .time_series import create_time_series_plot

        return create_time_series_plot
    elif name == "create_multi_parameter_plot":
        from .time_series import create_multi_parameter_plot

        return create_multi_parameter_plot
    elif name == "plot_sensor_data":
        from .time_series import plot_sensor_data

        return plot_sensor_data
    elif name == "detect_data_type":
        from .data_utils import detect_data_type

        return detect_data_type
    elif name == "get_available_measurements":
        from .data_utils import get_available_measurements

        return get_available_measurements
    elif name == "load_and_prepare_data":
        from .data_utils import load_and_prepare_data

        return load_and_prepare_data
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "create_time_series_plot",
    "create_multi_parameter_plot",
    "plot_sensor_data",
    "detect_data_type",
    "get_available_measurements",
    "load_and_prepare_data",
]
