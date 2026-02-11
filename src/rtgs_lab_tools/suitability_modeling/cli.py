"""CLI commands for suitability modeling.

Provides interactive and config-driven suitability analysis pipelines.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional

import click

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def suitability_cli(ctx):
    """AI-powered suitability analysis pipeline.

    Design and execute spatial suitability models using natural language
    requirements and Claude AI with structured outputs.
    """
    pass


# ---------------------------------------------------------------------------
# rtgs suitability run  (interactive)
# ---------------------------------------------------------------------------


@suitability_cli.command(name="run")
@click.option(
    "--api-key",
    default=None,
    help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
)
@click.option(
    "--output-dir",
    "-o",
    default="./results",
    help="Output directory for results (default: ./results)",
)
@click.option(
    "--output-format",
    "-f",
    default="geoparquet",
    type=click.Choice(["geoparquet", "shapefile", "geojson", "csv"]),
    help="Output file format (default: geoparquet)",
)
@click.pass_context
def run_command(ctx, api_key: Optional[str], output_dir: str, output_format: str):
    """Run the full suitability analysis pipeline interactively.

    Walks through each step: study area, analysis units, datasets,
    requirements, AI model design, review, and execution.

    Example:
        rtgs suitability run
        rtgs suitability run --output-dir ./my_results --output-format shapefile
    """
    try:
        _run_interactive_pipeline(api_key, output_dir, output_format)
    except KeyboardInterrupt:
        click.echo("\nAborted.")
        ctx.exit(1)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        logger.exception("Pipeline failed")
        ctx.exit(1)


def _run_interactive_pipeline(
    api_key: Optional[str], output_dir: str, output_format: str
) -> None:
    """Run the interactive suitability analysis pipeline."""
    import geopandas as gpd

    from ..spatial_data.core.extractor import extract_from_path
    from ..spatial_data.core.grid import generate_grid
    from ..spatial_data.core.schema import get_dataset_schema, format_schemas_for_llm
    from ..spatial_data.sources.fgdb import extract_all_fgdb_layers
    from ..spatial_data.sources.local_file import extract_all_from_directory
    from .core.model_designer import design_model, print_model_summary
    from .core.execution_engine import execute_model

    # === Step 1: Study Area ===
    click.echo()
    click.echo("=== Step 1: Study Area ===")
    study_area_path = click.prompt("Path to study area boundary file")
    study_area_boundary = extract_from_path(study_area_path)
    click.echo(
        f"  Loaded {len(study_area_boundary)} features, "
        f"CRS: {study_area_boundary.crs}"
    )

    # === Step 2: Analysis Units ===
    click.echo()
    click.echo("=== Step 2: Analysis Units ===")
    use_grid = click.confirm("Generate a regular grid?", default=True)

    analysis_units = None
    if use_grid:
        cell_size = click.prompt("Grid cell size in meters", default=100, type=float)
        max_cells = click.prompt("Maximum number of cells", default=50000, type=int)
        click.echo("  Generating grid...")
        analysis_units = generate_grid(
            study_area_boundary, cell_size=cell_size, max_cells=max_cells
        )
        click.echo(f"  Generated grid: {len(analysis_units):,} cells")
    else:
        units_path = click.prompt("Path to analysis units file")
        analysis_units = extract_from_path(units_path)
        click.echo(f"  Loaded {len(analysis_units):,} analysis units")

    # === Step 3: Variable Datasets ===
    click.echo()
    click.echo("=== Step 3: Variable Datasets ===")
    datasets_path = click.prompt("Path to datasets (directory, .gdb, or file)")
    datasets = _load_datasets(datasets_path)

    click.echo(f"  Loaded {len(datasets)} datasets:")
    for name, gdf in datasets.items():
        click.echo(f"    - {name}: {len(gdf):,} features")

    if not datasets:
        click.echo("  No datasets loaded. Cannot continue.", err=True)
        raise SystemExit(1)

    # Build schemas for LLM
    schemas = [get_dataset_schema(name, gdf) for name, gdf in datasets.items()]

    # === Step 4: Requirements ===
    click.echo()
    click.echo("=== Step 4: Requirements ===")
    click.echo("Type your objective OR enter a path to a .txt file:")
    requirements_input = click.prompt("Requirements")

    # Check if it's a file path
    req_path = Path(requirements_input)
    if req_path.exists() and req_path.is_file():
        with open(req_path, "r") as f:
            requirements_text = f.read()
        click.echo(f"  Read requirements from: {req_path}")
    else:
        requirements_text = requirements_input

    # === Step 5: AI Model Design ===
    click.echo()
    click.echo("=== Step 5: AI Model Design ===")
    click.echo("Calling Claude AI...")
    start = time.time()

    model_spec = design_model(
        requirements=requirements_text,
        dataset_schemas=schemas,
        output_file=None,
        api_key=api_key,
    )

    elapsed = time.time() - start
    click.echo(f"  Model designed in {elapsed:.1f} seconds")
    click.echo()

    # Display summary
    summary = print_model_summary(model_spec)
    click.echo(summary)

    # === Step 6: Review ===
    click.echo()
    click.echo("=== Step 6: Review ===")

    # Offer to save YAML for editing
    accept = click.confirm("Accept this model?", default=True)
    if not accept:
        yaml_path = Path(output_dir) / f"{model_spec.model_id}.yaml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        model_spec.to_yaml(str(yaml_path))
        click.echo(f"  Model saved to: {yaml_path}")
        click.echo("  Edit the YAML file and re-run with:")
        click.echo(f"    rtgs suitability run-config --config {yaml_path}")
        return

    # === Step 7: Executing ===
    click.echo()
    click.echo("=== Step 7: Executing ===")
    start = time.time()

    results = execute_model(
        model_spec=model_spec,
        datasets=datasets,
        study_area_boundary=study_area_boundary,
        analysis_units=analysis_units,
        output_dir=output_dir,
        output_format=output_format,
    )

    elapsed = time.time() - start
    click.echo(f"  Done in {elapsed:.1f} seconds")

    # === Results ===
    click.echo()
    click.echo("=== Results ===")
    click.echo(f"Output: {results['output_file']}")
    click.echo(f"Model:  {results['model_yaml']}")
    click.echo(f"Features analyzed: {results['num_features']:,}")
    click.echo()


def _load_datasets(path_str: str) -> Dict[str, "gpd.GeoDataFrame"]:
    """Load datasets from a path (directory, .gdb, or single file).

    Args:
        path_str: Path to directory, FGDB, or single spatial file

    Returns:
        Dict mapping dataset names to GeoDataFrames
    """
    from ..spatial_data.core.extractor import extract_from_path
    from ..spatial_data.sources.fgdb import extract_all_fgdb_layers
    from ..spatial_data.sources.local_file import extract_all_from_directory

    path = Path(path_str)

    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path_str}")

    # FGDB directory
    if path.suffix.lower() == ".gdb" or (path.is_dir() and path.name.endswith(".gdb")):
        click.echo(f"  Loading FGDB: {path}")
        return extract_all_fgdb_layers(str(path))

    # Regular directory
    if path.is_dir():
        click.echo(f"  Loading directory: {path}")
        return extract_all_from_directory(path)

    # Single file
    click.echo(f"  Loading file: {path}")
    name = path.stem
    gdf = extract_from_path(str(path))
    return {name: gdf}


# ---------------------------------------------------------------------------
# rtgs suitability run-config  (non-interactive)
# ---------------------------------------------------------------------------


@suitability_cli.command(name="run-config")
@click.option(
    "--config",
    "-c",
    "config_file",
    required=True,
    type=click.Path(exists=True),
    help="YAML configuration file with all paths and parameters",
)
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="Override output directory from config",
)
@click.option(
    "--output-format",
    "-f",
    default=None,
    type=click.Choice(["geoparquet", "shapefile", "geojson", "csv"]),
    help="Override output format from config",
)
@click.pass_context
def run_config_command(
    ctx,
    config_file: str,
    output_dir: Optional[str],
    output_format: Optional[str],
):
    """Run suitability analysis from a YAML configuration file.

    The config file should contain:
      study_area_path: path/to/boundary.shp
      datasets_path: path/to/datasets_dir
      model_spec_path: path/to/model.yaml  (or inline model_spec)
      output_dir: ./results
      output_format: geoparquet
      grid:
        cell_size: 100
        max_cells: 50000

    Example:
        rtgs suitability run-config --config pipeline_config.yaml
    """
    import yaml

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        _run_config_pipeline(config, output_dir, output_format)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("Config pipeline failed")
        ctx.exit(1)


def _run_config_pipeline(
    config: dict,
    output_dir_override: Optional[str],
    output_format_override: Optional[str],
) -> None:
    """Run the suitability pipeline from a config dict."""
    from ..spatial_data.core.extractor import extract_from_path
    from ..spatial_data.core.grid import generate_grid
    from .core.model_specification import ModelSpecification
    from .core.execution_engine import execute_model

    # Load study area
    study_area_path = config["study_area_path"]
    click.echo(f"Loading study area: {study_area_path}")
    study_area_boundary = extract_from_path(study_area_path)
    click.echo(f"  {len(study_area_boundary)} features, CRS: {study_area_boundary.crs}")

    # Load datasets
    datasets_path = config["datasets_path"]
    click.echo(f"Loading datasets: {datasets_path}")
    datasets = _load_datasets(datasets_path)
    click.echo(f"  Loaded {len(datasets)} datasets")

    # Analysis units
    analysis_units = None
    grid_config = config.get("grid", {})
    if grid_config:
        cell_size = grid_config.get("cell_size", 100)
        max_cells = grid_config.get("max_cells", 50000)
        click.echo(f"Generating grid: {cell_size}m cells, max {max_cells}")
        analysis_units = generate_grid(
            study_area_boundary, cell_size=cell_size, max_cells=max_cells
        )
        click.echo(f"  Generated {len(analysis_units):,} cells")
    elif "analysis_units_path" in config:
        units_path = config["analysis_units_path"]
        click.echo(f"Loading analysis units: {units_path}")
        analysis_units = extract_from_path(units_path)
        click.echo(f"  Loaded {len(analysis_units):,} units")

    # Load model specification
    model_spec_path = config.get("model_spec_path")
    if not model_spec_path:
        raise ValueError("Config must include 'model_spec_path' pointing to a model YAML")

    click.echo(f"Loading model: {model_spec_path}")
    model_spec = ModelSpecification.from_yaml(model_spec_path)
    model_spec.validate()
    click.echo(f"  Model: {model_spec.model_id} ({len(model_spec.criteria)} criteria)")

    # Execute
    final_output_dir = output_dir_override or config.get("output_dir", "./results")
    final_output_format = output_format_override or config.get("output_format", "geoparquet")

    click.echo("Executing model...")
    results = execute_model(
        model_spec=model_spec,
        datasets=datasets,
        study_area_boundary=study_area_boundary,
        analysis_units=analysis_units,
        output_dir=final_output_dir,
        output_format=final_output_format,
    )

    click.echo()
    click.echo("Done!")
    click.echo(f"  Output: {results['output_file']}")
    click.echo(f"  Model:  {results['model_yaml']}")
    click.echo(f"  Features: {results['num_features']:,}")
    click.echo(f"  Duration: {results['duration_seconds']:.1f}s")
    click.echo()


# ---------------------------------------------------------------------------
# rtgs suitability validate
# ---------------------------------------------------------------------------


@suitability_cli.command(name="validate")
@click.argument("model_file", type=click.Path(exists=True))
def validate_command(model_file: str):
    """Validate a model specification YAML file.

    Checks that:
    - YAML is valid and parseable
    - Pydantic validation passes (types, weights sum to 100, etc.)
    - Scoring functions are properly configured

    Example:
        rtgs suitability validate model.yaml
    """
    from .core.model_specification import ModelSpecification

    try:
        click.echo(f"Validating: {model_file}")
        click.echo()

        spec = ModelSpecification.from_yaml(model_file)
        spec.validate()

        click.echo("Model specification is valid!")
        click.echo()
        click.echo(f"  Model ID: {spec.model_id}")
        click.echo(f"  Objective: {spec.objective}")
        click.echo(f"  Criteria: {len(spec.criteria)}")
        click.echo(f"  Total weight: {sum(c.weight for c in spec.criteria)}%")

        for i, c in enumerate(spec.criteria, 1):
            click.echo(f"    {i}. {c.criterion_name} ({c.weight}%) - {c.dataset_name}")

        click.echo()

    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        raise SystemExit(1)
