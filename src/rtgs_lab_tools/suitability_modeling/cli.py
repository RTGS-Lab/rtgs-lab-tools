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
    """
    pass


@suitability_cli.command(name="design")
@click.option(
    '--input',
    '-i',
    'input_file',
    required=True,
    type=click.Path(exists=True),
    help='Input text file with requirements'
)
@click.option(
    '--output',
    '-o',
    'output_file',
    default=None,
    help='Output YAML file for model specification (default: {model_id}.yaml)'
)
@click.option(
    '--api-key',
    default=None,
    help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
)
@click.option(
    '--db-url',
    default=None,
    help='PostGIS database URL (or set SUITABILITY_DB_URL env var)'
)
def design_command(input_file: str, output_file: Optional[str], api_key: Optional[str], db_url: Optional[str]):
    """Design a suitability model from natural language requirements.

    This command uses Claude AI to interpret your requirements and design
    a weighted overlay suitability model using available spatial datasets.

    Example:
        rtgs suitability design --input requirements.txt --output model.yaml

    The generated YAML file contains the complete model specification that
    you can review, edit, and execute.
    """
    from .core.model_designer import design_model

    try:
        click.echo("🤖 Designing suitability model with Claude AI...")
        click.echo()

        model_spec = design_model(
            requirements_file=input_file,
            output_file=output_file,
            api_key=api_key,
            db_url=db_url
        )

        click.echo()
        click.echo("✓ Model design complete!")
        click.echo()
        click.echo(f"Next steps:")
        click.echo(f"  1. Review the model specification: {model_spec.model_id}.yaml")
        click.echo(f"  2. Edit if needed (it's human-readable YAML)")
        click.echo(f"  3. Execute: rtgs suitability execute --model {model_spec.model_id}.yaml")
        click.echo()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        logger.exception("Model design failed")
        ctx.exit(1)


@suitability_cli.command(name="execute")
@click.option(
    '--model',
    '-m',
    'model_file',
    required=True,
    type=click.Path(exists=True),
    help='Model specification YAML file'
)
@click.option(
    '--output-dir',
    '-o',
    default='./results',
    help='Output directory for results (default: ./results)'
)
@click.option(
    '--output-format',
    '-f',
    default='geoparquet',
    type=click.Choice(['geoparquet', 'shapefile', 'geojson', 'csv']),
    help='Output file format (default: geoparquet)'
)
@click.option(
    '--db-url',
    default=None,
    help='PostGIS database URL (or set SUITABILITY_DB_URL env var)'
)
@click.pass_context
def execute_command(
    ctx,
    model_file: str,
    output_dir: str,
    output_format: str,
    db_url: Optional[str]
):
    """Execute a suitability model and generate results.

    This command loads a model specification YAML file, executes the
    weighted overlay analysis, and exports results in your chosen format.

    Example:
        rtgs suitability execute --model wildlife_corridor.yaml --format geoparquet

    The results include:
    - Suitability scores for each grid cell
    - Individual criterion scores (for transparency)
    - Results exported in GeoParquet/Shapefile/GeoJSON/CSV format
    """
    from .core.execution_engine import execute_model

    try:
        click.echo(f"🚀 Executing suitability model: {model_file}")
        click.echo()

        results = execute_model(
            model_spec=model_file,
            output_dir=output_dir,
            output_format=output_format,
            db_url=db_url
        )

        click.echo()
        click.echo("✓ Model execution complete!")
        click.echo()
        click.echo(f"Results:")
        click.echo(f"  Output file: {results['output_file']}")
        click.echo(f"  Features analyzed: {results['num_features']:,}")
        click.echo(f"  Execution time: {results['duration_seconds']:.1f} seconds")
        click.echo()
        click.echo("You can now load the results in QGIS, ArcGIS, or Python/R for further analysis.")
        click.echo()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        logger.exception("Model execution failed")
        ctx.exit(1)


@suitability_cli.command(name="validate")
@click.argument('model_file', type=click.Path(exists=True))
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

    try:
        click.echo(f"Validating model specification: {model_file}")
        click.echo()

        spec = ModelSpecification.from_yaml(model_file)
        spec.validate()

        click.echo("✓ Model specification is valid!")
        click.echo()
        click.echo(f"Model ID: {spec.model_id}")
        click.echo(f"Criteria: {len(spec.criteria)}")
        click.echo(f"Total weight: {sum(c.weight for c in spec.criteria)}%")
        click.echo()

    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        raise SystemExit(1)
