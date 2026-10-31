import pytest

from auditor.config import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # A developer's real keys or model settings must not leak into these tests.
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
