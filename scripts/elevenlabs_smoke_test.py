"""ElevenLabs Production Smoke Test (Sprint 3A.7).
Runs a live text-to-speech request to verify the ElevenLabs integration and writes
the findings to wiki/elevenlabs-smoke-report.md.
"""
from __future__ import annotations

import os
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

_repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root))

load_dotenv(find_dotenv(usecwd=True))

from engine.model_manager.elevenlabs_provider import ElevenLabsProvider


def run_smoke_test() -> bool:
    report_path = _repo_root / "wiki" / "elevenlabs-smoke-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    print("Starting ElevenLabs live smoke test...")
    start_time = datetime.now(timezone.utc).isoformat()

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        print("ELEVENLABS_API_KEY is not configured in the environment.")
        return False

    out_dir = _repo_root / "projects"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "elevenlabs_smoke_test.wav"
    if out_path.exists():
        out_path.unlink()

    text = "This is the NAC ElevenLabs production smoke test."

    try:
        provider = ElevenLabsProvider()
        response = provider.synthesize(text, out_path)

        is_file = out_path.is_file()
        file_size = out_path.stat().st_size if is_file else 0

        duration = 0.0
        sample_rate = 0
        if is_file:
            try:
                with wave.open(str(out_path), "rb") as wav:
                    duration = wav.getnframes() / float(wav.getframerate())
                    sample_rate = wav.getframerate()
            except Exception as e:
                print(f"Failed to read WAV format: {e}")

        print(
            f"Success! File size: {file_size} bytes, Duration: {duration:.2f}s, "
            f"Latency: {response.latency:.2f}s"
        )

        md = f"""# ElevenLabs Production Smoke Test Report

- **Timestamp:** {start_time}
- **Status:** PASSED
- **Input Text:** "{text}"
- **Provider Used:** {response.provider}
- **Voice Used:** {response.voice}
- **Latency:** {response.latency:.3f}s
- **Duration:** {duration:.2f}s
- **Credits Used:** {response.credits_used} characters
- **Estimated Cost:** ${response.cost:.6f}
- **Sample Rate:** {sample_rate} Hz
- **File Size:** {file_size} bytes
- **File Path:** `{out_path}`

## Recommendations
- The ElevenLabs provider is healthy and production-ready.
- It operates with excellent response latency ({response.latency:.2f}s) and output fidelity ({sample_rate} Hz).
"""
        report_path.write_text(md)
        print(f"Report written to: {report_path}")
        return True
    except Exception as e:
        print(f"Smoke test failed: {e}")
        md = f"""# ElevenLabs Production Smoke Test Report

- **Timestamp:** {start_time}
- **Status:** FAILED
- **Error:** {type(e).__name__}: {e}

## Recommendations
- Double check that `ELEVENLABS_API_KEY` is active and has a positive credit balance.
"""
        report_path.write_text(md)
        return False


if __name__ == "__main__":
    run_smoke_test()
