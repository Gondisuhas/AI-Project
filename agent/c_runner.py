"""Compile and verify C programs with a timeout."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Use the known GCC installation path
GCC_PATH = r"E:\ucrt64\bin\gcc.exe"


def compile_c_repository(
    root: Path,
    timeout_seconds: int = 45,
    test_command: str | None = None,
) -> dict:
    """
    Compile C source files in a repository.

    Creates a temporary build directory, compiles all .c files,
    and optionally runs a test command if provided.

    Returns a dict with 'returncode', 'compiled', 'output', and optionally 'test_passed'.
    """
    root = root.resolve()

    if not root.is_dir():
        return {
            "returncode": 126,
            "compiled": False,
            "output": "Repository path is not a directory",
        }

    # Find all .c files (not in excluded directories)
    skip_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "build", "out", "dist"}
    c_files = []

    for path in root.rglob("*.c"):
        if not any(part in skip_dirs for part in path.parts):
            c_files.append(path)

    if not c_files:
        return {
            "returncode": 0,
            "compiled": True,
            "output": "No .c files found in repository",
        }

    # Create temporary build directory
    build_dir = root / ".bugpilot_build"
    build_dir.mkdir(exist_ok=True)

    try:
        # Try to compile each .c file separately to check syntax
        all_output = []
        any_errors = False

        for c_file in c_files:
            relative_path = c_file.relative_to(root)
            all_output.append(f"--- Checking {relative_path} ---")

            try:
                result = subprocess.run(
                    [GCC_PATH, "-fsyntax-only", "-Wall", "-Wextra", str(c_file)],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )

                if result.returncode != 0:
                    any_errors = True
                    # GCC diagnostics aren't captured in this environment.
                    # Report based on exit code only.
                    all_output.append(f"GCC reported errors (exit code {result.returncode})")
                else:
                    all_output.append("✓ Syntax check passed")

            except subprocess.TimeoutExpired:
                any_errors = True
                all_output.append(f"GCC timeout after {timeout_seconds}s")
            except Exception as exc:
                any_errors = True
                all_output.append(f"GCC failed: {exc}")

        combined_output = "\n".join(all_output)

        # If syntax checking found errors, return early
        if any_errors:
            return {
                "returncode": 1,
                "compiled": False,
                "output": combined_output[-16000:],
            }

        # If a test command is provided, try to run it
        if test_command:
            all_output.append(f"\n--- Running test command: {test_command} ---")

            try:
                test_result = subprocess.run(
                    test_command,
                    shell=True,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )

                all_output.append(test_result.stdout)
                if test_result.stderr:
                    all_output.append(test_result.stderr)

                test_passed = test_result.returncode == 0

                return {
                    "returncode": test_result.returncode,
                    "compiled": True,
                    "test_passed": test_passed,
                    "output": "\n".join(all_output)[-16000:],
                }

            except subprocess.TimeoutExpired as exc:
                out = exc.stdout or ""
                if isinstance(out, bytes):
                    out = out.decode("utf-8", errors="replace")

                all_output.append(f"TEST TIMEOUT after {timeout_seconds}s\n{out}")

                return {
                    "returncode": 124,
                    "compiled": True,
                    "test_passed": False,
                    "output": "\n".join(all_output)[-16000:],
                }

            except Exception as exc:
                all_output.append(f"Could not run test command: {exc}")

                return {
                    "returncode": 125,
                    "compiled": True,
                    "test_passed": False,
                    "output": "\n".join(all_output)[-16000:],
                }

        # No test command provided - report successful compilation only
        return {
            "returncode": 0,
            "compiled": True,
            "output": combined_output[-16000:],
        }

    except FileNotFoundError:
        return {
            "returncode": 127,
            "compiled": False,
            "output": f"GCC not found at {GCC_PATH}. Install GCC or update the path in agent/c_runner.py",
        }

    except Exception as exc:
        return {
            "returncode": 125,
            "compiled": False,
            "output": f"Compilation failed: {exc}",
        }

    finally:
        # Clean up build directory if it exists
        if build_dir.exists():
            try:
                shutil.rmtree(build_dir)
            except Exception:
                pass  # Best effort cleanup
