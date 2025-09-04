"""Device configuration management tools for RTGS Lab Tools."""

# Heavy dependencies are imported lazily when needed
# This prevents long load times for simple commands like 'rtgs --help'

def __getattr__(name):
    """Lazy loading of heavy dependencies"""
    if name == "device_configuration_cli":
        from .cli import device_configuration_cli
        return device_configuration_cli
    elif name == "ParticleClient":
        from .particle_client import ParticleClient
        return ParticleClient
    elif name == "ParticleConfigUpdater":
        from .update_configuration import ParticleConfigUpdater
        return ParticleConfigUpdater
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["device_configuration_cli", "ParticleConfigUpdater", "ParticleClient"]
