from pathlib import Path

import pytest

from yardmaster.config import Config
from yardmaster.core.release import ReleaseManager


def test_parse_specs() -> None:
    specs = ReleaseManager.parse_specs(["alpha:3800.0.0", "beta:3795.1.0"])
    assert specs[0].channel.value == "alpha"
    assert str(specs[0].version) == "3800.0.0"
    assert specs[1].channel.value == "beta"


def test_validate_unique_channels(tmp_path: Path) -> None:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    cfg_text = tmp_path / ".yardmaster.yaml"
    cfg_text.write_text(
        f"""repositories:
  scripts: https://example.invalid/scripts.git
  coreos_overlay: https://example.invalid/coreos-overlay.git
  portage_stable: https://example.invalid/portage-stable.git
paths:
  scripts: {scripts_dir}
jenkins:
  url: http://example.invalid:8080
channels:
  alpha:
    release_url: https://alpha.example.invalid
"""
    )
    cfg = Config.load(cfg_text)
    mgr = ReleaseManager(cfg)
    specs = mgr.parse_specs(["alpha:3800.0.0", "alpha:3800.0.1"])
    with pytest.raises(RuntimeError):
        mgr.validate(specs)
