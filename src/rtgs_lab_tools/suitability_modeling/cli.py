"""CLI commands for suitability modeling."""

import logging
from typing import Optional

import click

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def suitability_cli(ctx):
    """AI-powered suitability analysis model builder.

    Design and execute spatial suitability models using natural language
    requirements and Claude AI.

    Data sources:
    - FGDB: Hennepin County datasets (set RTGS_FGDB_PATH env var)
    - MN Geospatial Commons: Public Minnesota datasets
    """
    pass


@suitability_cli.command(name="list-datasets")
def list_datasets_command():
    """List all available spatial datasets.

    Shows datasets from both sources:
    - FGDB (Hennepin County) - requires RTGS_FGDB_PATH env var
    - MN Geospatial Commons (public)

    Example:
        rtgs suitability list-datasets
    """
    from .core.dataset_registry import get_all_available_datasets, is_fgdb_available

    try:
        click.echo("Available Spatial Datasets")
        click.echo("=" * 60)
        click.echo()

        # Check FGDB status
        if is_fgdb_available():
            click.echo("FGDB Status: Configured and available")
        else:
            click.echo("FGDB Status: Not configured")
            click.echo("  Set RTGS_FGDB_PATH environment variable to enable")
        click.echo()

        datasets = get_all_available_datasets()

        # Group by source
        fgdb_datasets = {k: v for k, v in datasets.items() if v.get("source") == "fgdb"}
        mn_datasets = {
            k: v for k, v in datasets.items() if v.get("source") == "mn_geospatial"
        }

        if fgdb_datasets:
            click.echo("Hennepin County Datasets (FGDB)")
            click.echo("-" * 40)
            for name, info in sorted(fgdb_datasets.items()):
                desc = info.get("description", "No description")
                features = info.get("expected_features", "?")
                click.echo(f"  {name}")
                click.echo(f"    {desc}")
                click.echo(f"    Features: {features}")
            click.echo()

        if mn_datasets:
            click.echo("MN Geospatial Commons (Public)")
            click.echo("-" * 40)
            for name, info in sorted(mn_datasets.items()):
                desc = info.get("description", "No description")
                click.echo(f"  {name}")
                click.echo(f"    {desc}")
            click.echo()

        click.echo(f"Total: {len(datasets)} datasets")
        click.echo(f"  - FGDB: {len(fgdb_datasets)}")
        click.echo(f"  - MN Geospatial: {len(mn_datasets)}")

    except Exception as e:
        click.echo(f"Error listing datasets: {e}", err=True)
        raise SystemExit(1)


@suitability_cli.command(name="design")
@click.option(
    "--input",
    "-i",
    "input_file",
    required=True,
    type=click.Path(exists=True),
    help="Input text file with requirements",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    default=None,
    help="Output YAML file for model specification (default: {model_id}.yaml)",
)
@click.option(
    "--api-key",
    default=None,
    help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
)
@click.pass_context
def design_command(
    ctx, input_file: str, output_file: Optional[str], api_key: Optional[str]
):
    """Design a suitability model from natural language requirements.

    This command uses Claude AI to interpret your requirements and design
    a weighted overlay suitability model using available spatial datasets.

    Data sources are determined automatically:
    - FGDB datasets (if RTGS_FGDB_PATH is set)
    - MN Geospatial Commons datasets (always available)

    Example:
        rtgs suitability design --input requirements.txt --output model.yaml

    The generated YAML file contains the complete model specification that
    you can review, edit, and execute.
    """
    from .core.model_designer import design_model

    try:
        click.echo("Designing suitability model with Claude AI...")
        click.echo()

        model_spec = design_model(
            requirements_file=input_file, output_file=output_file, api_key=api_key
        )

        click.echo()
        click.echo("Model design complete!")
        click.echo()
        click.echo("Next steps:")
        click.echo(f"  1. Review the model specification: {model_spec.model_id}.yaml")
        click.echo("  2. Edit if needed (it's human-readable YAML)")
        click.echo(
            f"  3. Execute: rtgs suitability execute --model {model_spec.model_id}.yaml"
        )
        click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("Model design failed")
        ctx.exit(1)


@suitability_cli.command(name="execute")
@click.option(
    "--model",
    "-m",
    "model_file",
    required=True,
    type=click.Path(exists=True),
    help="Model specification YAML file",
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
def execute_command(
    ctx,
    model_file: str,
    output_dir: str,
    output_format: str,
):
    """Execute a suitability model and generate results.

    This command loads a model specification YAML file, executes the
    weighted overlay analysis, and exports results in your chosen format.

    Datasets are loaded from:
    - FGDB (if RTGS_FGDB_PATH is set)
    - MN Geospatial Commons

    Example:
        rtgs suitability execute --model wildlife_corridor.yaml --format geoparquet

    The results include:
    - Suitability scores for each grid cell
    - Individual criterion scores (for transparency)
    - Results exported in GeoParquet/Shapefile/GeoJSON/CSV format
    """
    from .core.execution_engine import execute_model

    try:
        click.echo(f"Executing suitability model: {model_file}")
        click.echo()

        results = execute_model(
            model_spec=model_file,
            output_dir=output_dir,
            output_format=output_format,
        )

        click.echo()
        click.echo("Model execution complete!")
        click.echo()
        click.echo("Results:")
        click.echo(f"  Output file: {results['output_file']}")
        click.echo(f"  Features analyzed: {results['num_features']:,}")
        click.echo(f"  Execution time: {results['duration_seconds']:.1f} seconds")
        click.echo()
        click.echo(
            "You can now load the results in QGIS, ArcGIS, or Python/R for further analysis."
        )
        click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.exception("Model execution failed")
        ctx.exit(1)


@suitability_cli.command(name="validate")
@click.argument("model_file", type=click.Path(exists=True))
def validate_command(model_file: str):
    """Validate a model specification file.

    Checks that:
    - YAML file is valid
    - All required datasets are available
    - Weights sum to 100%
    - Scoring functions are properly configured

    Example:
        rtgs suitability validate model.yaml
    """
    from .core.model_specification import ModelSpecification
    from .core.dataset_registry import get_dataset_source

    try:
        click.echo(f"Validating model specification: {model_file}")
        click.echo()

        spec = ModelSpecification.from_yaml(model_file)
        spec.validate()

        # Check dataset availability
        click.echo("Checking dataset availability...")
        all_available = True
        for criterion in spec.criteria:
            source = get_dataset_source(criterion.dataset_name)
            if source == "unknown":
                click.echo(f"  {criterion.dataset_name}: NOT FOUND", err=True)
                all_available = False
            else:
                click.echo(f"  {criterion.dataset_name}: {source}")

        click.echo()

        if not all_available:
            click.echo("Some datasets are not available!", err=True)
            click.echo("Make sure RTGS_FGDB_PATH is set for FGDB datasets.")
            raise SystemExit(1)

        click.echo("Model specification is valid!")
        click.echo()
        click.echo(f"Model ID: {spec.model_id}")
        click.echo(f"Criteria: {len(spec.criteria)}")
        click.echo(f"Total weight: {sum(c.weight for c in spec.criteria)}%")
        click.echo()

    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        raise SystemExit(1)
