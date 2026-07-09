from __future__ import annotations


class MockBackendDisabled(RuntimeError):
    """The production workflow is LLM-required; mock backend is not used for final outputs."""


