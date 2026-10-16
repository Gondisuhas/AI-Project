"""Run tests with a timeout. Only use this on repositories you trust."""
import os
import subprocess
import sys
from pathlib import Path

def run_tests(root: Path, timeout_seconds: int = 45) -> dict:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"], cwd=root, env=env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout_seconds, check=False
        )
        return {"returncode": result.returncode, "passed": result.returncode == 0, "output": result.stdout[-16000:]}
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        return {"returncode": 124, "passed": False, "output": f"TEST TIMEOUT after {timeout_seconds}s\n{out}"}
    except Exception as exc:
        return {"returncode": 125, "passed": False, "output": f"Could not run tests: {exc}"}
