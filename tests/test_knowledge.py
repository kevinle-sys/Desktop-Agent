"""Knowledge loader tests (offline; no embedding calls).

We verify the enable/disable gates and the embedder dict shape without building
real knowledge sources (which would require an embedding backend at run time).
"""

from pennymac_agent.config.settings import Settings
from pennymac_agent.knowledge import build_embedder, shared_sources


def test_embedder_none_when_disabled():
    s = Settings(ENABLE_KNOWLEDGE=False, OPENAI_API_KEY="sk-test")
    assert build_embedder(s) is None
    assert shared_sources(s) == []


def test_embedder_none_without_key():
    s = Settings(ENABLE_KNOWLEDGE=True, OPENAI_API_KEY=None, EMBEDDING_API_KEY=None)
    assert build_embedder(s) is None


def test_embedder_shape_when_configured():
    # knowledge_dir defaults to the repo's knowledge/ folder, which exists.
    s = Settings(
        ENABLE_KNOWLEDGE=True,
        OPENAI_API_KEY="sk-test",
        EMBEDDING_MODEL="text-embedding-3-small",
    )
    embedder = build_embedder(s)
    assert embedder is not None
    assert embedder["provider"] == "openai"
    assert embedder["config"]["model_name"] == "text-embedding-3-small"
    assert embedder["config"]["api_key"] == "sk-test"
