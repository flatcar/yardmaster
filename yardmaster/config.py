from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class RepositoryConfig(BaseModel):
    scripts: str


class PathsConfig(BaseModel):
    build_scripts: str = "./flatcar-build-scripts"
    scripts: str = "./scripts"
    workspace: str = "~/.yardmaster/workspace"


class JenkinsConfig(BaseModel):
    url: str
    username: str | None = None
    token: str | None = None
    jobs: dict[str, str] = Field(default_factory=dict)
    pipeline_branch: str = "flatcar-master"


class ChannelConfig(BaseModel):
    release_url: str
    description: str = ""


class GPGConfig(BaseModel):
    enabled: bool = True
    key_id: str | None = None
    keyring_path: str = "os/keyring"
    keyserver: str = "https://keys.openpgp.org"


class SDKConfig(BaseModel):
    auto_detect: bool = True
    fallback_strategy: str = "major_version"
    seed_sdk_offset: int = 1000


class ValidationConfig(BaseModel):
    check_version_progression: bool = True
    require_unique_channels: bool = True
    warn_on_downgrade: bool = True
    check_sdk_compatibility: bool = True


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str | None = "~/.yardmaster/yardmaster.log"
    console_format: str = "pretty"


class BehaviorConfig(BaseModel):
    default_dry_run: bool = False
    auto_confirm: bool = False
    parallel_builds: bool = False
    retry_failed_commands: int = 3
    command_timeout: int = 300


class NetworkConfig(BaseModel):
    timeout: int = 30
    retries: int = 3
    verify_ssl: bool = True


class Config(BaseModel):
    repositories: RepositoryConfig
    paths: PathsConfig = Field(default_factory=PathsConfig)
    jenkins: JenkinsConfig
    channels: dict[str, ChannelConfig]
    gpg: GPGConfig = Field(default_factory=GPGConfig)
    sdk: SDKConfig = Field(default_factory=SDKConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        if config_path is None:
            config_path = Path.cwd() / ".yardmaster.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with config_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        raw = cls._expand_env_vars(raw)
        cfg = cls(**raw)
        cfg._validate()
        return cfg

    def _validate(self) -> None:
        if self.paths.scripts.startswith(("http://", "https://", "git@")):
            raise ValueError(
                "Config error: paths.scripts must be a local path to the scripts repo."
            )
        scripts_path = Path(self.paths.scripts).expanduser()
        if not scripts_path.exists():
            raise ValueError(f"Config error: paths.scripts path does not exist: {scripts_path}")

    @staticmethod
    def _expand_env_vars(data: Any) -> Any:
        if isinstance(data, dict):
            return {k: Config._expand_env_vars(v) for k, v in data.items()}
        if isinstance(data, list):
            return [Config._expand_env_vars(i) for i in data]
        if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            return os.getenv(data[2:-1], data)
        return data

    def save(self, config_path: Path) -> None:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.model_dump(), f, sort_keys=False)


def load_config(config_path: Path | None = None) -> Config:
    return Config.load(config_path)
