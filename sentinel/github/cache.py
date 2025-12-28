"""File-based cache for GitHub API responses."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional


class FileCache:
    """File-based cache for API responses."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize file cache.

        Args:
            base_path: Base path for cache. Defaults to ~/.cache/sentinel.
        """
        if base_path is None:
            from sentinel.config import get_cache_dir

            base_path = get_cache_dir()
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _make_key(self, repo: str, milestone: str, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key.

        Args:
            repo: Repository slug.
            milestone: Milestone slug.
            endpoint: API endpoint.
            params: Request parameters.

        Returns:
            Cache key string.
        """
        # Hash params for uniqueness
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"{repo}/{milestone}/{endpoint}_{params_hash}.json"

    def get(self, key: str) -> Optional[Dict]:
        """Get cached data.

        Args:
            key: Cache key.

        Returns:
            Cached data or None if not found.
        """
        path = self.base_path / key
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def set(self, key: str, data: Dict):
        """Set cached data.

        Args:
            key: Cache key.
            data: Data to cache.
        """
        path = self.base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
