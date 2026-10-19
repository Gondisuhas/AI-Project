"""Detect the primary programming language of a repository."""

from pathlib import Path


def detect_language(root: Path) -> str:
    """
    Detect whether a repository is primarily Python or C.

    Returns 'python', 'c', or 'unknown'.
    """
    root = root.resolve()

    if not root.is_dir():
        return "unknown"

    # Count source files by extension
    python_count = 0
    c_count = 0

    # Excluded directories (same as analyzer.py)
    skip_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
    }

    for path in root.rglob("*"):
        # Skip excluded directories
        if any(part in skip_dirs for part in path.parts):
            continue

        if not path.is_file():
            continue

        suffix = path.suffix.lower()

        if suffix == ".py":
            python_count += 1
        elif suffix in (".c", ".h"):
            c_count += 1

    # Determine primary language
    if python_count > 0 and python_count >= c_count:
        return "python"
    elif c_count > 0:
        return "c"
    else:
        return "unknown"


def validate_language_choice(language: str) -> bool:
    """Check if a language choice is supported."""
    return language in ("python", "c")
