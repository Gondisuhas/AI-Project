"""C repository analysis using GCC diagnostics."""

import re
import subprocess
from pathlib import Path

# Use the known GCC installation path
GCC_PATH = r"E:\ucrt64\bin\gcc.exe"

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "build",
    "out",
    "dist",
}


def c_files(root: Path) -> list[Path]:
    """Find C source and header files, skipping generated directories."""
    root = root.resolve()

    files = []
    for pattern in ("*.c", "*.h"):
        for path in root.rglob(pattern):
            if not any(part in SKIP_DIRS for part in path.parts):
                files.append(path)

    return files


def run_gcc_diagnostics(file_path: Path, root: Path) -> dict:
    """
    Run GCC with syntax checking and warnings to get diagnostics.

    Returns a dict with 'success', 'errors', and 'warnings'.
    """
    try:
        result = subprocess.run(
            [GCC_PATH, "-fsyntax-only", "-Wall", "-Wextra", str(file_path)],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )

        # Note: GCC writes diagnostics to stderr, but in this MSYS2
        # environment GCC output isn't captured through subprocess.
        # We use exit code as primary indicator. Non-zero exit = errors.
        # If GCC cannot find standard headers (e.g., stdio.h), it may
        # return non-zero even for valid code — this is an environment
        # limitation, not necessarily a code error.
        errors = []
        warnings = []

        # When GCC exits non-zero, we know there's at least one error.
        # We don't have the exact line/message from GCC in this environment,
        # so we report it generically with the file and line 0.
        if result.returncode != 0:
            # General error indication (line number unavailable from GCC)
            errors.append({
                "file": str(file_path),
                "line": 0,
                "column": 0,
                "message": f"GCC detected syntax/compilation errors (exit code {result.returncode})",
            })

        return {
            "success": result.returncode == 0,
            "errors": errors,
            "warnings": warnings,
            "output": f"GCC exit code: {result.returncode}",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "errors": [{"file": str(file_path), "line": 0, "column": 0, "message": "GCC timeout after 15 seconds"}],
            "warnings": [],
            "output": "GCC timeout",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "errors": [{"file": str(file_path), "line": 0, "column": 0, "message": f"GCC not found at {GCC_PATH}"}],
            "warnings": [],
            "output": f"GCC not found at {GCC_PATH}",
        }
    except Exception as exc:
        return {
            "success": False,
            "errors": [{"file": str(file_path), "line": 0, "column": 0, "message": f"GCC failed: {exc}"}],
            "warnings": [],
            "output": str(exc),
        }


def analyze_c_repository(root: Path) -> dict:
    """
    Analyze a C repository by discovering files and running GCC diagnostics.

    Returns a dict with 'files', 'diagnostics', 'syntax_errors', and 'suspicious'.
    """
    root = root.resolve()
    files = c_files(root)

    all_diagnostics = []
    syntax_errors = []
    suspicious = []

    for path in files:
        relative_file = str(path.relative_to(root))

        diagnostics = run_gcc_diagnostics(path, root)

        # Store per-file diagnostics
        all_diagnostics.append({
            "file": relative_file,
            "success": diagnostics["success"],
            "error_count": len(diagnostics["errors"]),
            "warning_count": len(diagnostics["warnings"]),
        })

        # Collect syntax errors
        for error in diagnostics["errors"]:
            syntax_errors.append({
                "file": relative_file,
                "line": error["line"],
                "error": error["message"],
            })

        # Mark error locations as suspicious
        for error in diagnostics["errors"]:
            suspicious.append({
                "file": relative_file,
                "line": error["line"],
                "reason": f"Compiler error: {error['message']}",
            })

        # Mark warning locations as less suspicious
        for warning in diagnostics["warnings"]:
            suspicious.append({
                "file": relative_file,
                "line": warning["line"],
                "reason": f"Compiler warning: {warning['message']}",
            })

    return {
        "files": [str(path.relative_to(root)) for path in files],
        "diagnostics": all_diagnostics,
        "syntax_errors": syntax_errors,
        "suspicious": suspicious,
    }


def rank_suspicious_c(
    root: Path,
    analysis: dict,
    compilation_output: str = "",
) -> list[dict]:
    """
    Rank suspicious lines for C code based on compiler diagnostics.

    Compiler errors get highest priority, warnings get medium priority.
    """
    root = root.resolve()
    ranked = []

    # Start with locations from static analysis
    for item in analysis.get("suspicious", []):
        # Compiler errors are highest priority
        if "Compiler error:" in item.get("reason", ""):
            score = 10.0
            evidence = "GCC error"
        # Compiler warnings are medium priority
        elif "Compiler warning:" in item.get("reason", ""):
            score = 5.0
            evidence = "GCC warning"
        else:
            score = 1.0
            evidence = "Static analysis"

        ranked.append({
            **item,
            "score": score,
            "evidence": evidence,
        })

    # Parse any additional errors from compilation output
    if compilation_output:
        diagnostic_pattern = re.compile(
            r"^([^:]+):(\d+):(\d+):\s+error:\s+(.+)$",
            re.MULTILINE
        )

        for match in diagnostic_pattern.finditer(compilation_output):
            filename, line, _, message = match.groups()

            # Convert to relative path if possible
            try:
                path = Path(filename)
                if path.is_absolute():
                    relative_file = str(path.relative_to(root))
                else:
                    relative_file = filename
            except (ValueError, OSError):
                relative_file = filename

            ranked.append({
                "file": relative_file,
                "line": int(line),
                "reason": f"Compilation error: {message.strip()}",
                "score": 10.0,
                "evidence": "GCC compilation output",
            })

    # Remove duplicates, keeping the highest score for each location
    unique = {}
    for item in ranked:
        key = (item["file"], item["line"])

        if key not in unique or item["score"] > unique[key]["score"]:
            unique[key] = item

    return sorted(
        unique.values(),
        key=lambda item: item["score"],
        reverse=True,
    )
