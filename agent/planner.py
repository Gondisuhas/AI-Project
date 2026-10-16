
"""State-space planner for debugging and automated repair."""

from collections import deque
from dataclasses import dataclass, replace
from typing import Callable


@dataclass(frozen=True)
class DebugState:
    analyzed: bool = False
    localized: bool = False
    candidate_ready: bool = False
    patch_applied: bool = False
    verified: bool = False
    failed_attempts: int = 0


@dataclass(frozen=True)
class Action:
    name: str
    precondition: Callable[[DebugState], bool]
    effect: Callable[[DebugState], DebugState]


# Actions describe valid transitions between debugging states.
ACTIONS = [
    Action(
        "analyze_repository",
        lambda s: not s.analyzed,
        lambda s: replace(s, analyzed=True),
    ),
    Action(
        "localize_fault",
        lambda s: s.analyzed and not s.localized,
        lambda s: replace(s, localized=True),
    ),
    Action(
        "generate_candidate",
        lambda s: (
            s.localized
            and not s.candidate_ready
            and not s.verified
        ),
        lambda s: replace(s, candidate_ready=True),
    ),
    Action(
        "apply_patch",
        lambda s: s.candidate_ready and not s.patch_applied,
        lambda s: replace(s, patch_applied=True),
    ),
    Action(
        "run_verification",
        lambda s: s.patch_applied and not s.verified,
        lambda s: replace(s, verified=True),
    ),
]


def bfs_plan(
    initial: DebugState,
    goal: Callable[[DebugState], bool] | None = None,
) -> list[str]:
    """Find the shortest valid action sequence using breadth-first search."""

    if goal is None:
        goal = lambda state: state.verified

    queue = deque([(initial, [])])
    visited = {initial}

    while queue:
        state, path = queue.popleft()

        if goal(state):
            return path

        for action in ACTIONS:
            if not action.precondition(state):
                continue

            next_state = action.effect(state)

            if next_state not in visited:
                visited.add(next_state)
                queue.append((next_state, path + [action.name]))

    return []


def verification_transition(
    state: DebugState,
    passed: bool,
    max_attempts: int = 3,
) -> DebugState:
    """Update the debugging state using the actual test result.

    A successful test run reaches the verified state.
    A failed run records the attempt and resets the patch-generation stage
    so another candidate can be considered.
    """

    if not state.patch_applied:
        raise ValueError(
            "Cannot record verification before a patch has been applied."
        )

    if passed:
        return replace(state, verified=True)

    failed_count = state.failed_attempts + 1

    return replace(
        state,
        candidate_ready=False,
        patch_applied=False,
        verified=False,
        failed_attempts=failed_count,
    )


def plan_next_action(state: DebugState) -> str | None:
    """Choose the next valid action from the current state."""

    if state.verified:
        return None

    plan = bfs_plan(state)

    return plan[0] if plan else None
