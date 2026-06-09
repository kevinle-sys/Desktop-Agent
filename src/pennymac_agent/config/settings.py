"""Central application configuration.

All runtime configuration is loaded from environment variables (and a local
``.env`` file) via pydantic-settings. This is the single source of truth for the
data-source connections and the Excel/VBA/knowledge paths used by the MCP tools.

The reasoning layer (Cursor subagents) runs on the user's Cursor account, so no
LLM provider keys are configured here.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

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
        # Treat blank env values (e.g. SQL_SERVER_PORT=) as unset so optional
        # int/bool fields fall back to their defaults instead of failing.
        env_ignore_empty=True,
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

    # --- SQL Server (legacy, transitioning to Snowflake) ---
    sqlserver_host: Optional[str] = Field(default=None, alias="SQL_SERVER_HOST")
    sqlserver_port: Optional[int] = Field(default=None, alias="SQL_SERVER_PORT")
    sqlserver_database: Optional[str] = Field(
        default=None, alias="SQL_SERVER_DATABASE"
    )
    sqlserver_user: Optional[str] = Field(default=None, alias="SQL_SERVER_USER")
    sqlserver_password: Optional[str] = Field(
        default=None, alias="SQL_SERVER_PASSWORD"
    )
    sqlserver_driver: str = Field(
        default="ODBC Driver 17 for SQL Server", alias="SQL_SERVER_DRIVER"
    )
    sqlserver_trusted_connection: bool = Field(
        default=False, alias="SQL_SERVER_TRUSTED_CONNECTION"
    )
    sqlserver_encrypt: bool = Field(default=True, alias="SQL_SERVER_ENCRYPT")
    sqlserver_trust_server_certificate: bool = Field(
        default=False, alias="SQL_SERVER_TRUST_SERVER_CERTIFICATE"
    )

    # --- Excel / VBA ---
    excel_models_dir: Path = Field(
        default=PROJECT_ROOT / "models" / "workbooks", alias="EXCEL_MODELS_DIR"
    )
    excel_visible: bool = Field(default=False, alias="EXCEL_VISIBLE")
    vba_scripts_dir: Path = Field(default=PROJECT_ROOT / "vba", alias="VBA_SCRIPTS_DIR")
    model_registry_path: Path = Field(
        default=PROJECT_ROOT / "models" / "registry.yaml",
        alias="MODEL_REGISTRY_PATH",
    )

    # --- SQL template libraries (organized by engine) ---
    sql_dir: Path = Field(default=PROJECT_ROOT / "sql" / "snowflake", alias="SQL_DIR")
    sql_server_dir: Path = Field(
        default=PROJECT_ROOT / "sql" / "sqlserver", alias="SQL_SERVER_DIR"
    )

    # --- Paths ---
    artifacts_dir: Path = Field(
        default=PROJECT_ROOT / "artifacts", alias="ARTIFACTS_DIR"
    )
    knowledge_dir: Path = Field(
        default=PROJECT_ROOT / "knowledge", alias="KNOWLEDGE_DIR"
    )

    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Convenience ---
    @property
    def snowflake_configured(self) -> bool:
        """True when minimum Snowflake connection fields are present."""
        return bool(self.snowflake_account and self.snowflake_user)

    @property
    def sqlserver_configured(self) -> bool:
        """True when minimum SQL Server connection fields are present.

        A host and database are always required. Auth is satisfied by either a
        trusted (Windows) connection or a user/password pair.
        """
        if not (self.sqlserver_host and self.sqlserver_database):
            return False
        if self.sqlserver_trusted_connection:
            return True
        return bool(self.sqlserver_user and self.sqlserver_password)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance loaded from the environment."""
    return Settings()
