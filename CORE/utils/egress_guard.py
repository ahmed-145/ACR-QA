"""Egress guard — blocks outbound HTTP calls in offline mode.

When ACRQA_MODE=offline (or ACRQA_OFFLINE=1), monkey-patches httpx.Client
and httpx.AsyncClient so any outbound request raises EgressBlockedError.

Usage (auto-wired via ACRQA_MODE in CORE/main.py):
    from CORE.utils.egress_guard import install, uninstall, is_installed
    install()   # block all external calls
    uninstall() # re-enable
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})
_ORIGINAL_HTTPX_CLIENT_SEND: Any = None
_ORIGINAL_HTTPX_ASYNC_SEND: Any = None
_INSTALLED = False


class EgressBlockedError(RuntimeError):
    """Raised when an outbound HTTP call is attempted in offline mode."""


def _blocked_send(self: Any, request: Any, **kwargs: Any) -> Any:  # type: ignore[return]
    """Replacement for httpx.Client.send that blocks external hosts."""
    from urllib.parse import urlparse

    host = urlparse(str(request.url)).hostname or ""
    if host not in _ALLOWED_HOSTS:
        raise EgressBlockedError(
            f"[egress-guard] Outbound call to {request.url} blocked in offline mode. "
            "Set ACRQA_MODE=cloud or ACRQA_MODE=hybrid to allow external calls."
        )
    # localhost calls are allowed — delegate to original
    return _ORIGINAL_HTTPX_CLIENT_SEND(self, request, **kwargs)


async def _blocked_async_send(self: Any, request: Any, **kwargs: Any) -> Any:  # type: ignore[return]
    """Replacement for httpx.AsyncClient.send that blocks external hosts."""
    from urllib.parse import urlparse

    host = urlparse(str(request.url)).hostname or ""
    if host not in _ALLOWED_HOSTS:
        raise EgressBlockedError(f"[egress-guard] Async outbound call to {request.url} blocked in offline mode.")
    return await _ORIGINAL_HTTPX_ASYNC_SEND(self, request, **kwargs)


def install() -> None:
    """Install egress guard — blocks all non-localhost HTTP calls."""
    global _INSTALLED, _ORIGINAL_HTTPX_CLIENT_SEND, _ORIGINAL_HTTPX_ASYNC_SEND
    if _INSTALLED:
        return
    try:
        import httpx

        _ORIGINAL_HTTPX_CLIENT_SEND = httpx.Client.send
        _ORIGINAL_HTTPX_ASYNC_SEND = httpx.AsyncClient.send
        httpx.Client.send = _blocked_send  # type: ignore[method-assign]
        httpx.AsyncClient.send = _blocked_async_send  # type: ignore[method-assign]
        logger.info("[egress-guard] httpx blocked (offline mode)")
    except ImportError:
        logger.warning("[egress-guard] httpx not installed — egress guard not active")
    _INSTALLED = True


def uninstall() -> None:
    """Remove egress guard — restore normal HTTP behaviour."""
    global _INSTALLED, _ORIGINAL_HTTPX_CLIENT_SEND, _ORIGINAL_HTTPX_ASYNC_SEND
    if not _INSTALLED:
        return
    try:
        import httpx

        if _ORIGINAL_HTTPX_CLIENT_SEND is not None:
            httpx.Client.send = _ORIGINAL_HTTPX_CLIENT_SEND  # type: ignore[method-assign]
        if _ORIGINAL_HTTPX_ASYNC_SEND is not None:
            httpx.AsyncClient.send = _ORIGINAL_HTTPX_ASYNC_SEND  # type: ignore[method-assign]
    except ImportError:
        pass
    _ORIGINAL_HTTPX_CLIENT_SEND = None
    _ORIGINAL_HTTPX_ASYNC_SEND = None
    _INSTALLED = False


def is_installed() -> bool:
    return _INSTALLED


def maybe_install() -> None:
    """Install only if ACRQA_MODE=offline or ACRQA_OFFLINE=1."""
    mode = os.getenv("ACRQA_MODE", "cloud").lower()
    offline_flag = os.getenv("ACRQA_OFFLINE", "0") == "1"
    if mode == "offline" or offline_flag:
        install()
        logger.info("[egress-guard] Offline mode active — external HTTP calls are blocked")
