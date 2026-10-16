from pathlib import Path
import sys

# Make the demo project importable whether pytest is launched from this folder or its parent.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
