import re
from pathlib import Path


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    text = text.strip("-")
    return text


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)
