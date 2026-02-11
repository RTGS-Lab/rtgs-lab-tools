"""Suitability Modeling Module - AI-Powered Spatial Analysis.

This module provides tools for designing and executing suitability analysis models
using natural language requirements and LLM-powered model generation.

Example:
    >>> from rtgs_lab_tools.suitability_modeling import design_model, execute_model
    >>> from rtgs_lab_tools.suitability_modeling import ModelSpecification
    >>>
    >>> # Design a model from requirements + dataset schemas
    >>> model_spec = design_model(requirements, dataset_schemas)
    >>>
    >>> # Execute the model with pre-loaded data
    >>> results = execute_model(model_spec, datasets, boundary)
"""

__version__ = "0.2.0"
__all__ = [
    "design_model",
    "execute_model",
    "print_model_summary",
    "ModelSpecification",
    "ScoringFunction",
    "ModelCriterion",
    "StudyAreaConfig",
    "AnalysisUnitsConfig",
]


# Lazy imports for better performance
def design_model(*args, **kwargs):
    """Design a suitability model from requirements text and dataset schemas."""
    from .core.model_designer import design_model as _design_model

    return _design_model(*args, **kwargs)


def execute_model(*args, **kwargs):
    """Execute a suitability model with pre-loaded data."""
    from .core.execution_engine import execute_model as _execute_model

    return _execute_model(*args, **kwargs)


def print_model_summary(*args, **kwargs):
    """Generate a human-readable summary of a model specification."""
    from .core.model_designer import print_model_summary as _print_model_summary

    return _print_model_summary(*args, **kwargs)


def __getattr__(name):
    """Lazy loading of model specification classes."""
    if name == "ModelSpecification":
        from .core.model_specification import ModelSpecification

        return ModelSpecification
    elif name == "ScoringFunction":
        from .core.model_specification import ScoringFunction

        return ScoringFunction
    elif name == "ModelCriterion":
        from .core.model_specification import ModelCriterion

        return ModelCriterion
    elif name == "StudyAreaConfig":
        from .core.model_specification import StudyAreaConfig

        return StudyAreaConfig
    elif name == "AnalysisUnitsConfig":
        from .core.model_specification import AnalysisUnitsConfig

        return AnalysisUnitsConfig
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
