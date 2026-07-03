"""PathResolver - WORKSPACE_SPEC.md. No module outside this file may build an
absolute path via string concatenation or a hardcoded drive letter."""
from __future__ import annotations

from pathlib import Path

ROOT_MARKER = ".nac-root"


class NacRootNotFoundError(RuntimeError):
    """Raised when no .nac-root marker is found walking up from start_path."""


class PathResolver:
    def __init__(self) -> None:
        self._root: Path | None = None

    def find_root(self, start_path: Path) -> Path:
        current = Path(start_path).resolve()
        while True:
            if (current / ROOT_MARKER).is_file():
                self._root = current
                return current
            if current.parent == current:
                raise NacRootNotFoundError(
                    f"No {ROOT_MARKER} found walking up from {start_path}"
                )
            current = current.parent

    def resolve(self, relative: str) -> Path:
        if self._root is None:
            raise NacRootNotFoundError("find_root() must be called before resolve()")
        return self._root / Path(relative)

    def root(self) -> Path:
        if self._root is None:
            raise NacRootNotFoundError("find_root() must be called before root()")
        return self._root
