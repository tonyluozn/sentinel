import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from sentinel.config import get_cache_dir


class FileCache:
    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = get_cache_dir()
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _make_key(self, repo: str, milestone: str, endpoint: str, params: Dict[str, Any]) -> str:
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"{repo}/{milestone}/{endpoint}_{params_hash}.json"

    def get(self, key: str) -> Optional[Dict]:
        path = self.base_path / key
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def set(self, key: str, data: Dict):
        path = self.base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
