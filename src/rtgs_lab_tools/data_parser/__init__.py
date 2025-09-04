"""Universal JSON packet parser for historical packets based on device JSON schema tool for RTGS Lab Tools."""

# Heavy dependencies are imported lazily when needed
# This prevents long load times for simple commands like 'rtgs --help'

def __getattr__(name):
    """Lazy loading of heavy dependencies"""
    if name == "parse_gems_data":
        from .core import parse_gems_data
        return parse_gems_data
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["parse_gems_data"]
