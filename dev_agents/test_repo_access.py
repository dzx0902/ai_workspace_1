from pathlib import Path

import pytest

from scripts import config
from scripts.path_router import PathPolicyError, repo_path


def test_read_repo_accepts_nested_relative_path(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(config, "READ_REPOS_ROOT", tmp_path)

    assert repo_path("courses/project") == (tmp_path / "courses/project").resolve()


def test_repo_rejects_traversal(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(config, "READ_REPOS_ROOT", tmp_path)

    with pytest.raises(PathPolicyError):
        repo_path("../outside")


def test_writable_repo_uses_separate_root(monkeypatch, tmp_path: Path):
    read_root = tmp_path / "drive"
    write_root = tmp_path / "allowed"
    monkeypatch.setattr(config, "READ_REPOS_ROOT", read_root)
    monkeypatch.setattr(config, "WRITE_REPOS_ROOT", write_root)

    assert repo_path("demo", writable=True) == (write_root / "demo").resolve()
