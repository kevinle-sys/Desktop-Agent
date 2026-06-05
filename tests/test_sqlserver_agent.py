"""Tests for the SQL Server agent that don't require a live database.

The read-only guardrail and the not-configured check both run before any
pyodbc/SQLAlchemy import, so these execute with no drivers installed.
"""

from pennymac_agent.agents.sqlserver_agent import SQLServerAgent
from pennymac_agent.config.settings import Settings


def _unconfigured_settings() -> Settings:
    # Explicitly empty so a developer's real .env cannot affect the test.
    return Settings(
        SQL_SERVER_HOST=None,
        SQL_SERVER_DATABASE=None,
        SQL_SERVER_USER=None,
        SQL_SERVER_PASSWORD=None,
        SQL_SERVER_TRUSTED_CONNECTION=False,
    )


def test_read_only_guardrail_blocks_writes():
    agent = SQLServerAgent(_unconfigured_settings())
    result = agent.run(sql="DELETE FROM dbo.locks WHERE 1=1")
    assert result.ok is False
    assert "read-only" in result.summary.lower()


def test_requires_a_query():
    agent = SQLServerAgent(_unconfigured_settings())
    result = agent.run()
    assert result.ok is False
    assert "no query" in result.summary.lower()


def test_reports_when_not_configured():
    agent = SQLServerAgent(_unconfigured_settings())
    result = agent.run(sql="SELECT 1 AS one")
    assert result.ok is False
    assert "not configured" in result.summary.lower()


def test_configured_detection_with_trusted_connection():
    settings = Settings(
        SQL_SERVER_HOST="db-server",
        SQL_SERVER_DATABASE="SecondaryMarket",
        SQL_SERVER_TRUSTED_CONNECTION=True,
    )
    assert settings.sqlserver_configured is True
