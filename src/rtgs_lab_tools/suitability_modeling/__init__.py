"""Suitability Modeling Module - AI-Powered Spatial Analysis.

This module provides tools for designing and executing suitability analysis models
using natural language requirements and LLM-powered model generation.

Example:
    >>> from rtgs_lab_tools.suitability_modeling import design_model, execute_model
    >>>
    >>> # Design a model from requirements
    >>> model_spec = design_model("requirements.txt")
    >>>
    >>> # Execute the model
    >>> results = execute_model(model_spec)
"""

__version__ = "0.1.0"
__all__ = ["design_model", "execute_model"]

# Lazy imports for better performance
def design_model(*args, **kwargs):
    """Design a suitability model from requirements text."""
    from .core.model_designer import design_model as _design_model
    return _design_model(*args, **kwargs)

def execute_model(*args, **kwargs):
    """Execute a suitability model."""
    from .core.execution_engine import execute_model as _execute_model
    return _execute_model(*args, **kwargs)
