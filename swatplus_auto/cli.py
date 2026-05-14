"""Command-line interface for SWAT+ Auto."""

import sys
from pathlib import Path

import click

from .config import ConfigValidator


@click.group()
@click.version_option(version="0.1.0", prog_name="swatplus-auto")
def cli():
    """SWAT+ Auto: Config-driven watershed modeling framework."""
    pass


@cli.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True), help="Path to YAML config file")
@click.option("--step", "-s", default="all", help="Step to run: delineation, hru, weather, txtinout, run, calibrate, or all")
@click.option("--workspace", "-w", type=click.Path(), help="Override workspace directory")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
def run(config, step, workspace, dry_run):
    """Run a modeling step or the full workflow."""
    click.echo(f"Loading config: {config}")

    try:
        cfg = ConfigValidator(config)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Project: {cfg.get('project.name')}")
    click.echo(f"Simulation period: {cfg.get('project.simulation_period')}")
    click.echo(f"Step: {step}")

    if dry_run:
        click.echo("[DRY RUN] No changes will be made.")
        return

    # Import workflow here to avoid heavy imports at CLI load time
    from . import Workflow

    workflow = Workflow.from_config(config)
    workflow.run(step=step)


@cli.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True), help="Path to YAML config file")
def validate(config):
    """Validate a configuration file."""
    click.echo(f"Validating: {config}")
    try:
        cfg = ConfigValidator(config)
        click.echo("Configuration is valid.")
        click.echo(f"  Project name: {cfg.get('project.name')}")
        click.echo(f"  DEM: {cfg.get('basin.dem_path')}")
        click.echo(f"  Landuse: {cfg.get('basin.landuse_path')}")
        click.echo(f"  Soil: {cfg.get('basin.soil_path')}")
        click.echo(f"  Outlet: {cfg.get('basin.outlet_coords')}")
        click.echo(f"  Simulation: {cfg.get('project.simulation_period')}")
    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", default="config.yaml", help="Output file path")
def init(output):
    """Create a template configuration file."""
    template = """project:
  name: my_swat_project
  workspace: ./workspace
  simulation_period: [2012, 2022]
  warmup_years: 2

basin:
  dem_path: ./data/dem.tif
  landuse_path: ./data/landuse.tif
  soil_path: ./data/soil.tif
  outlet_coords: [120.0, 46.0]  # [lon, lat]
  projection: EPSG:32651
  threshold_area_km2: 50

weather:
  cmfd_dir: ./data/cmfd
  variables: [lrad, prec, rhum, srad, wind]
  grid_spacing_deg: 0.1

model:
  swatplus_executable: ./swatplus
  output_variables: [flo_out]
"""
    Path(output).write_text(template, encoding="utf-8")
    click.echo(f"Template config written to: {output}")


def main():
    cli()


if __name__ == "__main__":
    main()
