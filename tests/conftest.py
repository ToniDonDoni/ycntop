from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _disable_real_openai_key_for_tests(monkeypatch):
    """Prevent accidental real OpenAI calls in tests by default."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
