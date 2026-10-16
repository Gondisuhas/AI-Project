
"""Coordinates state-space planning, fault localization, repair, and verification."""

import ast
import shutil
from dataclasses import replace
from pathlib import Path

from .analyzer import analyze_repository, rank_suspicious
from .planner import (
    DebugState,
    bfs_plan,
    plan_next_action,
    verification_transition,
)
from .runner import run_tests
from .repair import built_in_candidates, ollama_candidate


def run_agent(
    root: Path,
    max_attempts: int = 3,
    use_ollama: bool = False,
    progress=None,
) -> dict:
    """Debug a repository using planned actions and test-driven verification."""

    root = Path(root).resolve()

    if not root.is_dir():
        raise ValueError("Repository path must be an existing directory")

    max_attempts = max(0, int(max_attempts))
    log = []

    def say(message):
        log.append(message)
        if progress:
            progress(message)

    state = DebugState()
    initial_plan = bfs_plan(state)

    say("Initial BFS plan: " + " -> ".join(initial_plan))

    analysis = {}
    baseline = None
    final = None
    suspicious = []
    candidate_pool = []
    candidate_index = 0
    attempts = []
    current_candidate = None
    original_source = None
    backup = None

    def result(status):
        return {
            "status": status,
            "analysis": analysis,
            "baseline": baseline,
            "final": final,
            "suspicious": suspicious,
            "attempts": attempts,
            "log": log,
            "plan": initial_plan,
            "final_state": state,
        }

    def is_test_file(path):
        relative_parts = path.relative_to(root).parts
        return (
            path.name.startswith("test_")
            or any(part.casefold() == "tests" for part in relative_parts)
        )

    def build_candidates():
        """Build and rank candidate patches using current evidence."""
        nonlocal candidate_pool

        scores = {}

        for item in suspicious:
            filename = str(item.get("file", "")).replace("\\", "/").casefold()
            score = float(item.get("score", 0.0))
            scores[filename] = max(scores.get(filename, 0.0), score)

        for relative_file in analysis.get("files", []):
            path = root / relative_file

            if is_test_file(path):
                continue

            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                say(f"Skipping unreadable file {relative_file}: {exc}")
                continue

            normalized = Path(relative_file).as_posix().casefold()

            matching_scores = [
                score
                for filename, score in scores.items()
                if filename == normalized
                or filename.endswith("/" + normalized)
            ]
            file_score = max(matching_scores, default=0.0)

            file_candidates = []

            try:
                for label, candidate in built_in_candidates(path, source):
                    if not candidate or candidate == source:
                        continue

                    try:
                        ast.parse(candidate, filename=str(path))
                    except SyntaxError:
                        say(f"Discarded invalid Python candidate for {relative_file}.")
                        continue

                    file_candidates.append(
                        (path, label, candidate, "built-in rule", file_score)
                    )

            except Exception as exc:
                say(f"Built-in repair generation failed for {relative_file}: {exc}")

            # Ollama is used for this file only when built-in rules find no fix.
            if use_ollama and not file_candidates:
                try:
                    candidate = ollama_candidate(
                        path,
                        source,
                        baseline.get("output", ""),
                    )

                    if candidate and candidate != source:
                        ast.parse(candidate, filename=str(path))
                        file_candidates.append(
                            (
                                path,
                                "LLM-generated candidate",
                                candidate,
                                "Ollama",
                                file_score,
                            )
                        )

                except SyntaxError:
                    say(f"Discarded invalid Ollama candidate for {relative_file}.")
                except Exception as exc:
                    say(f"Ollama failed for {relative_file}: {exc}")

            candidate_pool.extend(file_candidates)

        candidate_pool.sort(key=lambda item: item[4], reverse=True)
        say(f"Generated {len(candidate_pool)} candidate patch(es).")

    # The planner now selects each next action based on the current state.
    while not state.verified:
        action = plan_next_action(state)

        if action is None:
            say("Planner found no valid next action.")
            break

        say(f"Planner action: {action}")

        if action == "analyze_repository":
            say("Analyzing repository with Python AST...")
            analysis = analyze_repository(root)

            say(
                f"Found {len(analysis['files'])} Python files and "
                f"{len(analysis['functions'])} functions."
            )

            if analysis.get("syntax_errors"):
                say(
                    f"Warning: found {len(analysis['syntax_errors'])} "
                    "syntax error(s)."
                )

            state = replace(state, analyzed=True)

        elif action == "localize_fault":
            say("Running baseline test suite...")
            baseline = run_tests(root)

            say(
                "Baseline tests: "
                + ("PASS" if baseline["passed"] else "FAIL")
            )

            if baseline["passed"]:
                say("No reproducible test failure was found.")
                final = baseline
                return result("NO_REPRODUCIBLE_FAILURE")

            suspicious = rank_suspicious(
                root,
                analysis,
                baseline.get("output", ""),
            )

            say(f"Ranked {len(suspicious)} suspicious location(s).")
            state = replace(state, localized=True)

        elif action == "generate_candidate":
            if len(attempts) >= max_attempts:
                say("Maximum repair attempt limit reached.")
                break

            if candidate_index >= len(candidate_pool):
                build_candidates()

            if candidate_index >= len(candidate_pool):
                say("No supported repair candidate remains.")
                break

            current_candidate = candidate_pool[candidate_index]
            candidate_index += 1

            path, label, candidate, origin, score = current_candidate

            say(
                f"Selected candidate: '{label}' for "
                f"{path.relative_to(root)} (score {score})."
            )

            state = replace(state, candidate_ready=True)

        elif action == "apply_patch":
            if current_candidate is None:
                say("No candidate is available to apply.")
                state = replace(state, candidate_ready=False)
                continue

            path, label, candidate, origin, score = current_candidate
            relative_file = str(path.relative_to(root))
            original_source = path.read_text(encoding="utf-8")
            backup = path.with_suffix(path.suffix + ".bugpilot_backup")

            try:
                ast.parse(candidate, filename=str(path))
                shutil.copy2(path, backup)
                path.write_text(candidate, encoding="utf-8")

                attempts.append({
                    "attempt": len(attempts) + 1,
                    "file": relative_file,
                    "label": label,
                    "origin": origin,
                    "fault_localization_score": score,
                    "passed": None,
                    "decision": "applied; awaiting verification",
                })

                say(f"Applied candidate to {relative_file}.")
                state = replace(state, patch_applied=True)

            except Exception as exc:
                if backup is not None and backup.exists():
                    shutil.copy2(backup, path)
                    backup.unlink(missing_ok=True)

                say(f"Could not apply candidate: {exc}")

                attempts.append({
                    "attempt": len(attempts) + 1,
                    "file": relative_file,
                    "label": label,
                    "origin": origin,
                    "fault_localization_score": score,
                    "passed": False,
                    "decision": f"rejected: {exc}",
                })

                state = replace(
                    state,
                    candidate_ready=False,
                    patch_applied=False,
                    failed_attempts=state.failed_attempts + 1,
                )

                current_candidate = None
                original_source = None
                backup = None

        elif action == "run_verification":
            if current_candidate is None or original_source is None:
                say("Cannot verify: candidate or original source is missing.")
                break

            path = current_candidate[0]
            record = attempts[-1]

            say("Running verification tests...")
            test_result = run_tests(root)

            record["passed"] = test_result["passed"]
            record["test_output"] = test_result.get("output", "")

            if test_result["passed"]:
                record["decision"] = "accepted: test suite passed"
                final = test_result
                state = verification_transition(state, passed=True)

                say("Verification passed. Patch retained.")
                return result("REPAIRED_TESTS_PASS")

            record["decision"] = "rejected: tests failed; reverted"
            say("Verification failed. Restoring original source.")

            try:
                if backup is not None and backup.exists():
                    shutil.copy2(backup, path)
                else:
                    path.write_text(original_source, encoding="utf-8")
            finally:
                if backup is not None:
                    backup.unlink(missing_ok=True)

            state = verification_transition(state, passed=False)

            current_candidate = None
            original_source = None
            backup = None

            say(
                f"Replanning after failure "
                f"{state.failed_attempts}/{max_attempts}."
            )

        else:
            say(f"Unsupported planner action: {action}")
            break

    # A failed or exhausted repair cycle must finish with a final test run.
    say("Running final verification tests...")
    final = run_tests(root)

    if final["passed"]:
        say("Final tests passed.")
        return result("TESTS_PASS_AFTER_ATTEMPTS")

    say("Agent stopped without a verified repair.")
    return result("UNRESOLVED")
