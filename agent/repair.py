"""Repair candidate generation: local LLM if configured, plus safe demo heuristics."""
import os
from pathlib import Path
import re
import requests

def ollama_candidate(file_path: Path, source: str, failure: str) -> str | None:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    prompt = f"""You are a cautious Python bug-fixing assistant. Return ONLY the complete corrected contents of this one Python file. Do not use markdown fences. Make the smallest fix supported by the evidence.\n\nFile: {file_path.name}\nTest failure:\n{failure[-5000:]}\n\nCurrent file:\n```python\n{source}\n```"""
    try:
        response = requests.post(f"{base}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=90)
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        text = re.sub(r"^```(?:python)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text if text else None
    except Exception:
        return None

def built_in_candidates(path: Path, source: str) -> list[tuple[str, str]]:
    """Small illustrative rules. These are not a general-purpose repair engine."""
    candidates = []
    if path.name == "math_utils.py" and "sum(values) / len(values)" in source:
        candidates.append(("Handle empty input in average", source.replace("return sum(values) / len(values)", "if not values:\n        raise ValueError('values must not be empty')\n    return sum(values) / len(values)")))
    if "if len(items) < 0:" in source:
        candidates.append(("Correct impossible negative-length check", source.replace("if len(items) < 0:", "if len(items) == 0:")))
    if "return total / count" in source and "if count == 0" not in source:
        candidates.append(("Guard against division by zero", source.replace("return total / count", "if count == 0:\n        raise ValueError('count must not be zero')\n    return total / count")))
    return candidates
