
from pathlib import Path
import subprocess
import sys

from agent.analyzer import analyze_repository, rank_suspicious

root = Path("demo_buggy_project").resolve()

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        str(root),
        "-q",
        "--tb=long",
    ],
    capture_output=True,
    text=True,
    cwd=str(root.parent),
)

test_output = result.stdout + "\n" + result.stderr

print("TEST EXIT CODE:", result.returncode)
print("\n--- REAL TEST OUTPUT ---")
print(test_output)

analysis = analyze_repository(root)
ranked = rank_suspicious(root, analysis, test_output)

print("\n--- SUSPICIOUS LOCATIONS ---")
for item in ranked:
    print(item)
