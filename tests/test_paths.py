from pathlib import Path
import pytest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.kernel.paths import PathResolver, NacRootNotFoundError


def test_find_root_walks_up_to_marker(tmp_path):
    root = tmp_path / "project"
    (root / "engine" / "kernel").mkdir(parents=True)
    (root / ".nac-root").write_text("")
    start = root / "engine" / "kernel"
    resolver = PathResolver()
    assert resolver.find_root(start) == root


def test_find_root_raises_when_no_marker(tmp_path):
    resolver = PathResolver()
    with pytest.raises(NacRootNotFoundError):
        resolver.find_root(tmp_path)


def test_resolve_joins_root_and_relative(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / ".nac-root").write_text("")
    resolver = PathResolver()
    resolver.find_root(root)
    assert resolver.resolve("projects/demo") == root / "projects" / "demo"


def test_root_returns_cached_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / ".nac-root").write_text("")
    resolver = PathResolver()
    resolver.find_root(root)
    assert resolver.root() == root
