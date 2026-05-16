#!/usr/bin/env python3
"""
SWAT+ Automated Setup Tool
===========================
A command-line tool to automate watershed delineation, HRU generation,
and TxtInOut creation for SWAT+ models.

Usage:
    python swatplus_setup.py --config config.yaml

The configuration file (YAML) specifies all input data paths, parameters,
and output locations.
"""
import argparse
import logging
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.delineation import run_delineation
from core.hru_generator import run_hru_generation
from core.txtinout import run_txtinout_generation
from core.state import save_delineation_result, load_delineation_result


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    
    required_sections = ["project", "inputs", "delineation", "hru", "swatplus"]
    for sec in required_sections:
        if sec not in config:
            raise ValueError(f"Missing required section '{sec}' in config file")
    
    os.makedirs(config["project"]["output_dir"], exist_ok=True)
    
    return config


def main():
    parser = argparse.ArgumentParser(description="SWAT+ Automated Setup Tool")
    parser.add_argument("--config", "-c", required=True, help="Path to YAML configuration file")
    parser.add_argument("--step", "-s", choices=["delineation", "hru", "txtinout", "all"],
                        default="all", help="Which step to run (default: all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger("swatplus_setup")
    
    logger.info("=" * 60)
    logger.info("SWAT+ Automated Setup Tool")
    logger.info("=" * 60)
    
    logger.info(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    logger.info(f"Project: {config['project']['name']}")
    logger.info(f"Output directory: {config['project']['output_dir']}")
    
    state_path = os.path.join(config["project"]["output_dir"], "delineation", "state.json")
    delineation_result = None
    hrus = None
    
    # Step 1: Delineation
    if args.step in ("delineation", "all"):
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: Watershed Delineation")
        logger.info("=" * 60)
        delineation_result = run_delineation(config)
        logger.info(f"  Channels: {delineation_result.channel_count}")
        logger.info(f"  Subbasins: {delineation_result.subbasin_count}")
        logger.info(f"  Watershed raster: {delineation_result.watershed_raster}")
        
        # Save state for subsequent steps
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        save_delineation_result(delineation_result, state_path)
        logger.info(f"  State saved to {state_path}")
    
    # Step 2: HRU Generation
    if args.step in ("hru", "all"):
        if delineation_result is None:
            logger.info("Loading delineation result from previous run...")
            delineation_result = load_delineation_result(state_path)
        
        if delineation_result is None:
            logger.error("Delineation result required for HRU generation. Run step 1 first.")
            sys.exit(1)
        
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: HRU Generation")
        logger.info("=" * 60)
        hrus = run_hru_generation(config, delineation_result)
        logger.info(f"  Generated {len(hrus)} HRUs")
    
    # Step 3: TxtInOut Generation
    if args.step in ("txtinout", "all"):
        if delineation_result is None:
            logger.info("Loading delineation result from previous run...")
            delineation_result = load_delineation_result(state_path)
        
        if delineation_result is None:
            logger.error("Delineation result required for TxtInOut generation.")
            sys.exit(1)
        
        # If running txtinout-only, we need to regenerate HRUs since they are not saved
        if hrus is None:
            logger.info("Regenerating HRUs...")
            hrus = run_hru_generation(config, delineation_result)
        
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: TxtInOut Generation")
        logger.info("=" * 60)
        txtinout_dir = run_txtinout_generation(config, delineation_result, hrus)
        logger.info(f"  TxtInOut directory: {txtinout_dir}")
    
    logger.info("\n" + "=" * 60)
    logger.info("All steps completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
