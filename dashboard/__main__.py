"""`py -3 -m dashboard` - dev entry point for the Sprint 2A Director Studio."""
from __future__ import annotations

import os
import webbrowser

import uvicorn


def main() -> None:
    port = int(os.environ.get("NAC_STUDIO_PORT", "8420"))
    url = f"http://localhost:{port}"
    print(f"NAC Director Studio starting at {url}")
    webbrowser.open(url)
    uvicorn.run("dashboard.server:app", host="127.0.0.1", port=port, reload=True)


if __name__ == "__main__":
    main()
