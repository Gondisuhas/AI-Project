"""Coordinates repository inspection, planning, patch attempts and verification."""
from pathlib import Path
import shutil
from .analyzer import analyze_repository, rank_suspicious
from .planner import DebugState, bfs_plan
from .runner import run_tests
from .repair import built_in_candidates, ollama_candidate

def run_agent(root: Path, max_attempts: int = 3, use_ollama: bool = False, progress=None) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Repository path must be an existing directory")
    log = []
    def say(message):
        log.append(message)
        if progress:
            progress(message)
    plan = bfs_plan(DebugState())
    say("Planner found action sequence: " + " → ".join(plan))
    say("Analyzing repository with Python AST...")
    analysis = analyze_repository(root)
    say(f"Found {len(analysis['files'])} Python files and {len(analysis['functions'])} functions.")
    if analysis["syntax_errors"]:
        say(f"Warning: found {len(analysis['syntax_errors'])} syntax error(s).")
    say("Running baseline test suite...")
    baseline = run_tests(root)
    say("Baseline tests: " + ("PASS" if baseline["passed"] else "FAIL"))
    if baseline["passed"]:
        return {"status": "NO_REPRODUCIBLE_FAILURE", "analysis": analysis, "baseline": baseline, "final": baseline, "attempts": [], "log": log, "plan": plan}
    suspicious = rank_suspicious(root, analysis, baseline["output"])
    say(f"Fault-localization heuristic ranked {len(suspicious)} suspicious location(s).")
    attempts = []
    # The demo rules may propose candidates in any project, but only known small patterns are changed.
    candidate_pool = []
    for rel in analysis["files"]:
        p = root / rel
        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for label, candidate in built_in_candidates(p, src):
            candidate_pool.append((p, label, candidate, "built-in rule"))
        if use_ollama and not candidate_pool:
            candidate = ollama_candidate(p, src, baseline["output"])
            if candidate and candidate != src:
                candidate_pool.append((p, "LLM-generated candidate", candidate, "Ollama"))
    if not candidate_pool:
        say("No supported repair rule produced a candidate. No source files were changed.")
    for index, (path, label, candidate, origin) in enumerate(candidate_pool[:max_attempts], start=1):
        original = path.read_text(encoding="utf-8")
        backup = path.with_suffix(path.suffix + ".bugpilot_backup")
        shutil.copy2(path, backup)
        record = {"attempt": index, "file": str(path.relative_to(root)), "label": label, "origin": origin}
        try:
            # Reject syntactically invalid candidates before writing them.
            import ast
            ast.parse(candidate, filename=str(path))
            path.write_text(candidate, encoding="utf-8")
            say(f"Attempt {index}: applied '{label}' to {record['file']}; running tests...")
            test_result = run_tests(root)
            record["passed"] = test_result["passed"]
            record["test_output"] = test_result["output"]
            if test_result["passed"]:
                record["decision"] = "accepted: test suite passed"
                say(f"Attempt {index}: tests passed. Patch retained.")
                backup.unlink(missing_ok=True)
                attempts.append(record)
                return {"status": "REPAIRED_TESTS_PASS", "analysis": analysis, "baseline": baseline, "final": test_result, "suspicious": suspicious, "attempts": attempts, "log": log, "plan": plan}
            record["decision"] = "rejected: tests still fail; reverted"
            path.write_text(original, encoding="utf-8")
            say(f"Attempt {index}: tests failed; reverted patch.")
        except Exception as exc:
            path.write_text(original, encoding="utf-8")
            record["passed"] = False
            record["decision"] = f"rejected: {exc}; reverted"
            say(f"Attempt {index}: candidate rejected ({exc}); reverted.")
        finally:
            backup.unlink(missing_ok=True)
        attempts.append(record)
    final = run_tests(root)
    status = "UNRESOLVED" if not final["passed"] else "TESTS_PASS_AFTER_ATTEMPTS"
    say("Agent stopped: attempt limit reached or no supported candidate remained.")
    return {"status": status, "analysis": analysis, "baseline": baseline, "final": final, "suspicious": suspicious, "attempts": attempts, "log": log, "plan": plan}
