"""Utility functions."""

import re
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug.

    Args:
        text: Text to slugify.

    Returns:
        Filesystem-safe slug.
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    # Remove leading/trailing hyphens
    text = text.strip("-")
    return text


def ensure_dir(path: Path):
    """Ensure directory exists, creating if needed.

    Args:
        path: Directory path.
    """
    path.mkdir(parents=True, exist_ok=True)
