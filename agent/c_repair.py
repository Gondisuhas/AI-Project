"""Repair candidate generation for C code."""

import re
import subprocess
from pathlib import Path

# Use the known GCC installation path
GCC_PATH = r"E:\ucrt64\bin\gcc.exe"


def validate_c_candidate(file_path: Path, source: str) -> bool:
    """
    Validate a C source candidate by compiling it with GCC.

    Returns True if the code compiles without syntax errors.
    """
    try:
        result = subprocess.run(
            [GCC_PATH, "-fsyntax-only", "-x", "c", "-"],
            input=source,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def built_in_c_candidates(path: Path, source: str) -> list[tuple[str, str]]:
    """
    Generate conservative C repair candidates for explicitly supported patterns.

    These are NOT a general-purpose repair engine. They handle only a small
    number of common, testable bug patterns.

    Returns a list of (label, candidate_source) tuples.
    """
    candidates = []

    # Pattern 1: Missing semicolon after a simple statement
    # Match lines like: return 0  (no semicolon)
    #                   printf("hello")  (no semicolon)
    missing_semicolon = re.compile(
        r'^(\s*(?:return|printf|scanf|fprintf|int|char|float|double|void|break|continue)\s+[^;{}\n]+)\s*$',
        re.MULTILINE
    )

    matches = list(missing_semicolon.finditer(source))
    if matches:
        # Only apply if there's a clear syntax error pattern
        modified = source
        for match in reversed(matches):  # Work backwards to preserve positions
            line_content = match.group(1)
            # Don't add semicolon to function declarations or after preprocessor directives
            if not line_content.strip().startswith('#') and '(' not in line_content:
                modified = modified[:match.end(1)] + ';' + modified[match.end(1):]

        if modified != source:
            candidates.append(("Add missing semicolons", modified))

    # Pattern 2: Uninitialized variable that's used
    # This is conservative - only handles obvious cases like:
    # int x;
    # printf("%d", x);
    uninitialized_var = re.compile(
        r'(\s*int\s+(\w+)\s*;\s*\n\s*printf\([^)]*\2[^)]*\))',
        re.MULTILINE
    )

    match = uninitialized_var.search(source)
    if match:
        var_name = match.group(2)
        replacement = match.group(1).replace(
            f'int {var_name};',
            f'int {var_name} = 0;'
        )
        modified = source[:match.start()] + replacement + source[match.end():]
        candidates.append((f"Initialize variable '{var_name}' to 0", modified))

    # Pattern 3: Missing return statement in non-void function
    # Look for: int functionName() { ... } with no return statement
    missing_return = re.compile(
        r'(int\s+\w+\s*\([^)]*\)\s*\{[^}]*)(})',
        re.MULTILINE | re.DOTALL
    )

    for match in missing_return.finditer(source):
        function_body = match.group(1)
        # Check if there's already a return statement
        if 'return' not in function_body.lower():
            # Add return 0; before the closing brace
            modified = source[:match.start(2)] + '\n    return 0;\n' + source[match.start(2):]
            candidates.append(("Add missing return statement", modified))
            break  # Only fix one function at a time

    return candidates


def ollama_c_candidate(file_path: Path, source: str, failure: str) -> str | None:
    """
    Request a C code repair from a locally available Ollama model.

    This is optional and only used when built-in rules find no match.
    Returns None if Ollama is not available or fails.
    """
    import os
    import requests

    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

    prompt = f"""You are a cautious C bug-fixing assistant. Return ONLY the complete corrected contents of this one C file. Do not use markdown fences. Make the smallest fix supported by the evidence.

File: {file_path.name}
Compilation failure:
{failure[-5000:]}

Current file:
```c
{source}
```"""

    try:
        response = requests.post(
            f"{base}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=90
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()

        # Remove markdown fences if present
        text = re.sub(r"^```(?:c)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return text if text else None

    except Exception:
        return None
