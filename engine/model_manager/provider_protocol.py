"""LlmProvider protocol - every compiler talks to this interface only, never to a
concrete provider class. ModelManager.resolve() picks which implementation backs it;
compilers never know or care which one they got."""
from __future__ import annotations

from typing import Any, Protocol
from pathlib import Path


class LlmProvider(Protocol):
    model: str
    last_call_duration_s: float
    last_call_tokens: int

    def generate(self, prompt: str, system: str = "") -> str:
        ...


class VoiceRequest:
    def __init__(
        self,
        text: str,
        voice_id: str | None = None,
        language: str | None = None,
        style: float | None = None,
        emotion: str | None = None,
        speed: float | None = None,
        output_format: str | None = None,
        streaming: bool = False,
    ) -> None:
        self.text = text
        self.voice_id = voice_id
        self.language = language
        self.style = style
        self.emotion = emotion
        self.speed = speed
        self.output_format = output_format
        self.streaming = streaming


class VoiceResponse:
    def __init__(
        self,
        audio_path: Path,
        provider: str,
        voice: str,
        duration: float,
        latency: float,
        cost: float = 0.0,
        credits_used: int = 0,
        sample_rate: int | None = None,
        file_size: int = 0,
    ) -> None:
        self.audio_path = audio_path
        self.provider = provider
        self.voice = voice
        self.duration = duration
        self.latency = latency
        self.cost = cost
        self.credits_used = credits_used
        self.sample_rate = sample_rate
        self.file_size = file_size

    def __getattr__(self, name: str) -> Any:
        return getattr(self.audio_path, name)

    def __fspath__(self) -> str:
        return str(self.audio_path)

    def __str__(self) -> str:
        return str(self.audio_path)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, VoiceResponse):
            return self.audio_path == other.audio_path
        if isinstance(other, (Path, str)):
            return str(self.audio_path) == str(other)
        return False


class VoiceProvider(Protocol):
    def synthesize(self, request: str | VoiceRequest, out_path: Path) -> VoiceResponse:
        ...

