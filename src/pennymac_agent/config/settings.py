"""Central application configuration.

All runtime configuration is loaded from environment variables (and a local
``.env`` file) via pydantic-settings. This is the single source of truth for
LLM credentials, Snowflake connection details, and Excel/VBA paths.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root: .../src/pennymac_agent/config/settings.py -> up 3 levels.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM provider selection ---
    llm_provider: Literal["openai", "anthropic"] = Field(
        default="anthropic", alias="LLM_PROVIDER"
    )
    llm_max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-opus-4-20250514", alias="ANTHROPIC_MODEL"
    )

    # --- Snowflake ---
    snowflake_account: Optional[str] = Field(default=None, alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: Optional[str] = Field(default=None, alias="SNOWFLAKE_USER")
    snowflake_password: Optional[str] = Field(default=None, alias="SNOWFLAKE_PASSWORD")
    snowflake_private_key_path: Optional[str] = Field(
        default=None, alias="SNOWFLAKE_PRIVATE_KEY_PATH"
    )
    snowflake_private_key_passphrase: Optional[str] = Field(
        default=None, alias="SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"
    )
    snowflake_role: Optional[str] = Field(default=None, alias="SNOWFLAKE_ROLE")
    snowflake_warehouse: Optional[str] = Field(
        default=None, alias="SNOWFLAKE_WAREHOUSE"
    )
    snowflake_database: Optional[str] = Field(default=None, alias="SNOWFLAKE_DATABASE")
    snowflake_schema: Optional[str] = Field(default=None, alias="SNOWFLAKE_SCHEMA")
    snowflake_authenticator: Optional[str] = Field(
        default=None, alias="SNOWFLAKE_AUTHENTICATOR"
    )

    # --- Excel / VBA ---
    excel_models_dir: Path = Field(
        default=PROJECT_ROOT / "models" / "workbooks", alias="EXCEL_MODELS_DIR"
    )
    excel_visible: bool = Field(default=False, alias="EXCEL_VISIBLE")
    vba_scripts_dir: Path = Field(
        default=PROJECT_ROOT / "vba", alias="VBA_SCRIPTS_DIR"
    )
    model_registry_path: Path = Field(
        default=PROJECT_ROOT / "models" / "registry.yaml",
        alias="MODEL_REGISTRY_PATH",
    )
    sql_dir: Path = Field(default=PROJECT_ROOT / "sql", alias="SQL_DIR")

    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Convenience ---
    @property
    def active_model(self) -> str:
        """Return the model name for the currently selected provider."""
        return (
            self.openai_model
            if self.llm_provider == "openai"
            else self.anthropic_model
        )

    @property
    def active_api_key(self) -> Optional[str]:
        """Return the API key for the currently selected provider."""
        return (
            self.openai_api_key
            if self.llm_provider == "openai"
            else self.anthropic_api_key
        )

    @property
    def llm_configured(self) -> bool:
        """True when the selected provider has an API key available."""
        return bool(self.active_api_key)

    @property
    def snowflake_configured(self) -> bool:
        """True when minimum Snowflake connection fields are present."""
        return bool(self.snowflake_account and self.snowflake_user)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance loaded from the environment."""
    return Settings()
