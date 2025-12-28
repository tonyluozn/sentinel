"""Configuration utilities."""

from pathlib import Path


def get_cache_dir() -> Path:
    """Get cache directory path (~/.cache/sentinel).

    Returns:
        Path to cache directory.
    """
    cache_home = Path.home() / ".cache"
    cache_dir = cache_home / "sentinel"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_data_dir() -> Path:
    """Get data directory path (project-relative data/).

    Returns:
        Path to data directory.
    """
    # Assume we're in the project root
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_runs_dir() -> Path:
    """Get runs directory path (project-relative runs/).

    Returns:
        Path to runs directory.
    """
    runs_dir = Path("runs")
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir
