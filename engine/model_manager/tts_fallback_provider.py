"""TtsFallbackProvider - same fallback-chain idea as FallbackProvider (model_manager/
fallback_provider.py), but for TTS backends (`synthesize(text, out_path)` instead of
`generate(prompt, system)`). Kept as a separate small class rather than genericizing
FallbackProvider: the two interfaces take different arguments and TTS calls don't
currently need the hard wall-clock deadline FallbackProvider exists for (no TTS
backend has shown FallbackProvider's observed slow-trickle hang) - not adding that
complexity until a real incident calls for it."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from engine.model_manager.provider_protocol import VoiceRequest, VoiceResponse


class TtsBackend(Protocol):
    def synthesize(self, request: str | VoiceRequest, out_path: Path) -> VoiceResponse:
        ...


class TtsFallbackProvider:
    def __init__(
        self,
        backends: list[TtsBackend],
        on_fallback: Callable[[TtsBackend, Exception], None] | None = None,
    ) -> None:
        if not backends:
            raise ValueError("TtsFallbackProvider requires at least one backend")
        self._backends = backends
        self._on_fallback = on_fallback
        self._active: TtsBackend = backends[0]

    @property
    def active_backend_name(self) -> str:
        return type(self._active).__name__

    @property
    def backend_chain_names(self) -> list[str]:
        return [type(b).__name__ for b in self._backends]

    def synthesize(self, request: str | VoiceRequest, out_path: Path) -> VoiceResponse:
        last_error: Exception | None = None
        for backend in self._backends:
            try:
                result = backend.synthesize(request, out_path)
            except Exception as e:  # noqa: BLE001 - any backend failure falls through to the next
                last_error = e
                if self._on_fallback is not None:
                    self._on_fallback(backend, e)
                continue
            self._active = backend
            return result
        assert last_error is not None
        raise last_error

