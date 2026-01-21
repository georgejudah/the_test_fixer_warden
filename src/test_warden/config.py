"""Configuration management for Test Warden."""

from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file at import time
load_dotenv()


class GeminiConfig(BaseModel):
    """Gemini AI configuration."""
    
    model: str = "gemini-2.0-flash"
    vision_enabled: bool = True
    max_retries: int = 3


class LangfuseConfig(BaseModel):
    """Langfuse observability configuration."""
    
    enabled: bool = True
    public_key: str | None = None
    secret_key: str | None = None


class HealingConfig(BaseModel):
    """Healing behavior configuration."""
    
    mode: Literal["suggest", "auto-heal"] = "suggest"
    confidence_threshold: float = 0.85
    max_retries: int = 3


class DiscoveryConfig(BaseModel):
    """Test discovery configuration."""
    
    paths: list[str] = Field(default_factory=lambda: ["tests"])
    patterns: list[str] = Field(default_factory=lambda: ["test_*.py", "*.spec.js"])


class IntegrationsConfig(BaseModel):
    """Third-party integrations configuration."""
    
    github_create_pr: bool = True
    github_labels: list[str] = Field(default_factory=lambda: ["test-warden", "auto-heal"])
    slack_channel: str | None = None


class Config(BaseSettings):
    """Main configuration for Test Warden."""
    
    model_config = SettingsConfigDict(
        env_prefix="TEST_WARDEN_",
        env_nested_delimiter="__",
    )
    
    # Core settings
    test_command: str = "pytest"
    baseline_storage: Path = Path(".test_warden/baselines")
    
    # Sub-configurations
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    healing: HealingConfig = Field(default_factory=HealingConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from YAML file and environment variables."""
    config_data: dict = {}
    
    # Try to find config file
    if config_path is None:
        for name in ["test_warden.yaml", "test_warden.yml", ".test_warden.yaml"]:
            if Path(name).exists():
                config_path = Path(name)
                break
    
    # Load from YAML if exists
    if config_path and config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f)
            if raw and "test_warden" in raw:
                config_data = raw["test_warden"]
            elif raw:
                config_data = raw
    
    # Environment variables override YAML
    return Config(**config_data)
