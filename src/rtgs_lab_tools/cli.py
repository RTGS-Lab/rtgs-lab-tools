"""Main CLI router for RTGS Lab Tools."""

import importlib
import click


class LazyGroup(click.Group):
    """A click Group that imports commands lazily."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Map command names to their module paths
        self._lazy_commands = {
            "sensing-data": ("rtgs_lab_tools.sensing_data.cli", "sensing_data_cli"),
            "data-parser": ("rtgs_lab_tools.data_parser.cli", "data_parser_cli"),
            "visualization": ("rtgs_lab_tools.visualization.cli", "visualization_cli"),
            "gridded-data": ("rtgs_lab_tools.gridded_data.cli", "gridded_data_cli"),
            "device-configuration": ("rtgs_lab_tools.device_configuration.cli", "device_configuration_cli"),
            "agricultural-modeling": ("rtgs_lab_tools.agricultural_modeling.cli", "agricultural_modeling_cli"),
            "audit": ("rtgs_lab_tools.audit.cli", "audit_cli"),
            "device-monitoring": ("rtgs_lab_tools.device_monitoring.cli", "device_monitoring_cli"),
            "auth": ("rtgs_lab_tools.auth.cli", "auth_cli"),
            "core": ("rtgs_lab_tools.core.cli", "core_cli"),
        }
    
    def get_command(self, ctx, cmd_name):
        # First check if command is already loaded
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        
        # Try to lazy load the command
        if cmd_name in self._lazy_commands:
            module_name, attr_name = self._lazy_commands[cmd_name]
            try:
                module = importlib.import_module(module_name)
                command = getattr(module, attr_name)
                self.add_command(command, name=cmd_name)
                return command
            except (ImportError, AttributeError):
                pass
        
        return None
    
    def list_commands(self, ctx):
        # Return both loaded and available lazy commands
        loaded = super().list_commands(ctx)
        lazy = list(self._lazy_commands.keys())
        return sorted(set(loaded + lazy))


@click.group(cls=LazyGroup)
def cli():
    """RTGS Lab Tools - Environmental sensing and climate data toolkit."""
    pass


if __name__ == "__main__":
    cli()
