"""Test isolation: unit tests never depend on downloaded models.

* default: the semantic models are switched off, so results are deterministic everywhere.
* @pytest.mark.requires_nli: loads the real NLI/embedding models; skipped when they are unavailable
  (no sentence-transformers, or no network for the one-time model download).
"""
import pytest

from app.core.model_registry import registry


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_nli: needs the real NLI model (meaning-based verification)")


@pytest.fixture(autouse=True)
def _model_isolation(request):
    if request.node.get_closest_marker("requires_nli"):
        registry.reset()
        if registry.nli is None:
            pytest.skip("NLI model not available in this environment")
        yield
    else:
        registry.override(None, None)
        yield
    registry.override(None, None)
