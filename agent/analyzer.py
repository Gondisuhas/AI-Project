
"""Python repository analysis and traceback-based fault localization."""

import ast
import re
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
}


def python_files(root: Path) -> list[Path]:
    """Find Python files while skipping common generated directories."""
    root = root.resolve()

    return [
        path
        for path in root.rglob("*.py")
        if not any(part in SKIP_DIRS for part in path.parts)
    ]


def analyze_repository(root: Path) -> dict:
    """Inspect Python files for functions, syntax errors, and code patterns."""
    root = root.resolve()
    files = python_files(root)

    functions = []
    syntax_errors = []
    suspicious = []

    for path in files:
        relative_file = str(path.relative_to(root))

        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append({
                        "file": relative_file,
                        "name": node.name,
                        "line": node.lineno,
                    })

                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                    suspicious.append({
                        "file": relative_file,
                        "line": node.lineno,
                        "reason": (
                            "Division operation: inspect denominator "
                            "and zero handling"
                        ),
                    })

                if isinstance(node, ast.Compare) and any(
                    isinstance(op, (ast.Eq, ast.NotEq))
                    for op in node.ops
                ):
                    suspicious.append({
                        "file": relative_file,
                        "line": node.lineno,
                        "reason": (
                            "Equality comparison: inspect if relevant "
                            "to the failing test"
                        ),
                    })

                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    suspicious.append({
                        "file": relative_file,
                        "line": node.lineno,
                        "reason": "Bare except: may hide errors",
                    })

        except (SyntaxError, UnicodeDecodeError) as exc:
            syntax_errors.append({
                "file": relative_file,
                "error": str(exc),
            })

    return {
        "files": [str(path.relative_to(root)) for path in files],
        "functions": functions,
        "syntax_errors": syntax_errors,
        "suspicious": suspicious,
    }


def _relative_source_path(filename: str, root: Path) -> str | None:
    """Convert an existing traceback filename to a repository-relative path."""
    path = Path(filename)

    # Pytest can print repository-relative paths using Windows separators.
    if not path.is_absolute():
        path = root / path

    try:
        resolved = path.resolve()
        return str(resolved.relative_to(root))
    except (ValueError, OSError):
        return None


def rank_suspicious(
    root: Path,
    analysis: dict,
    test_output: str,
) -> list[dict]:
    """Rank suspicious lines using AST hints and traceback evidence.

    Scores are heuristic priorities, not probabilities or proof of a bug.
    """
    root = root.resolve()
    ranked = []

    # Candidates found by static analysis.
    for item in analysis.get("suspicious", []):
        ranked.append({
            **item,
            "score": 1.0,
            "evidence": "Static analysis",
        })

    output = test_output or ""

    # Standard Python traceback format:
    # File "C:\\project\\module.py", line 10, in function
    standard_traceback = re.compile(
        r'File\s+["\']([^"\']+\.py)["\'],\s*line\s+(\d+)'
    )

    # Pytest assertion/traceback format:
    # C:\\project\\module.py:10: ...
    # project/module.py:10: ...
    pytest_location = re.compile(
        r'(?P<file>(?:[A-Za-z]:[\\/])?[^:\r\n]*?\.py)'
        r':(?P<line>\d+)(?=[:\s])'
    )

    locations = []

    for match in standard_traceback.finditer(output):
        locations.append((match.group(1), int(match.group(2))))

    for match in pytest_location.finditer(output):
        locations.append((
            match.group("file"),
            int(match.group("line")),
        ))

    seen_locations = set()

    for filename, line_number in locations:
        key = (filename, line_number)

        if key in seen_locations:
            continue

        seen_locations.add(key)

        relative_file = _relative_source_path(filename, root)

        if relative_file is None:
            continue

        path_parts = Path(relative_file).parts
        is_test_file = (
            Path(relative_file).name.startswith("test_")
            or "tests" in path_parts
        )

        ranked.append({
            "file": relative_file,
            "line": line_number,
            "reason": "Appears in test traceback",
            "score": 5.0 if is_test_file else 10.0,
            "evidence": "Test traceback",
        })

    # Keep the highest-scoring candidate for each file and line.
    unique = {}

    for item in ranked:
        key = (item["file"], item["line"])

        if (
            key not in unique
            or item["score"] > unique[key]["score"]
        ):
            unique[key] = item

    return sorted(
        unique.values(),
        key=lambda item: item["score"],
        reverse=True,
    )
