"""Tests for configuration validation."""

import pytest
from swatplus_auto.config import ConfigValidator


def test_hongxin_config_loads():
    cfg = ConfigValidator("configs/hongxin.yaml")
    assert cfg.get("project.name") == "hongxin_swat"
    assert cfg.get("basin.outlet_coords") == [122.371902, 45.849787]


def test_config_missing_basin_key():
    import yaml
    from pathlib import Path

    bad_config = {"project": {"name": "test"}, "basin": {"dem_path": "./fake.tif"}}
    Path("/tmp/bad_config.yaml").write_text(yaml.dump(bad_config))

    with pytest.raises(ValueError):
        ConfigValidator("/tmp/bad_config.yaml")
