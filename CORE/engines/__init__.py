"""AI explanation engine module."""


def __getattr__(name: str):
    """Lazy import to avoid pulling heavy LLM deps on every `from CORE.engines import ...`."""
    if name == "ExplanationEngine":
        from .explainer import ExplanationEngine

        return ExplanationEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ExplanationEngine"]
