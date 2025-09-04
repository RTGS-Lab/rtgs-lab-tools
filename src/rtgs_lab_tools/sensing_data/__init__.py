"""Sensing data tools for RTGS Lab Tools."""

# Heavy dependencies are imported lazily when needed
# This prevents long load times for simple commands like 'rtgs --help'


def __getattr__(name):
    """Lazy loading of heavy dependencies"""
    if name == "extract_data":
        from .data_extractor import extract_data

        return extract_data
    elif name == "get_nodes_for_project":
        from .data_extractor import get_nodes_for_project

        return get_nodes_for_project
    elif name == "get_raw_data":
        from .data_extractor import get_raw_data

        return get_raw_data
    elif name == "list_available_projects":
        from .data_extractor import list_available_projects

        return list_available_projects
    elif name == "list_projects":
        from .data_extractor import list_projects

        return list_projects
    elif name == "create_zip_archive":
        from .file_operations import create_zip_archive

        return create_zip_archive
    elif name == "save_data":
        from .file_operations import save_data

        return save_data
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "extract_data",
    "list_available_projects",
    "get_raw_data",
    "list_projects",
    "get_nodes_for_project",
    "save_data",
    "create_zip_archive",
]
