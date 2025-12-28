from pathlib import Path


def get_cache_dir() -> Path:
    cache_home = Path.home() / ".cache"
    cache_dir = cache_home / "sentinel"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_data_dir() -> Path:
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_runs_dir() -> Path:
    runs_dir = Path("runs")
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir
