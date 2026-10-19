import os
import shutil
from pathlib import Path

_fallback = Path(r"E:\ucrt64\bin\gcc.exe")

GCC_PATH = (
    os.getenv("BUGPILOT_GCC")
    or shutil.which("gcc")
    or shutil.which("gcc.exe")
    or (str(_fallback) if _fallback.is_file() else None)
)
