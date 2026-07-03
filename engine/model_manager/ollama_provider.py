"""Local LLM provider via Ollama HTTP API. Pattern reused (standalone, no import)
from navakanth001/agent_os/cinematic_model_router.py's OllamaProvider/OllamaConfig -
reimplemented here per MODULE_BOUNDARIES.md rule 7 (engine.model_manager may import
engine.kernel only, no cross-repo dependency)."""
from __future__ import annotations

import time

import requests


class OllamaNotReachableError(RuntimeError):
    pass


class OllamaProvider:
    def __init__(
        self,
        model: str = "gemma2:9b",
        base_url: str = "http://localhost:11434",
        timeout_s: float = 120.0,
        temperature: float = 0.7,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout_s = timeout_s
        self.temperature = temperature
        self.last_call_duration_s: float = 0.0
        self.last_call_tokens: int = 0

    def generate(self, prompt: str, system: str = "") -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        if system:
            payload["system"] = system
        start = time.monotonic()
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate", json=payload, timeout=self.timeout_s
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise OllamaNotReachableError(
                f"Ollama not reachable at {self.base_url} for model '{self.model}' "
                f"- install from ollama.com and run `ollama pull {self.model}`. "
                f"Underlying error: {e}"
            ) from e
        self.last_call_duration_s = time.monotonic() - start
        data = resp.json()
        self.last_call_tokens = int(data.get("eval_count", 0)) + int(
            data.get("prompt_eval_count", 0)
        )
        return data["response"]
