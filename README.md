# BugPilot AI — Autonomous Debugging Agent

A beginner-friendly prototype combining Python AST analysis, pytest-based verification, a custom BFS state-space planner, controlled repair candidates, rollback, and a Streamlit dashboard.

## Requirements
- Python 3.11 or 3.12
- Internet is needed only to install Python dependencies; built-in repair rules work offline afterward.
- Optional: Ollama and a local code model for LLM-assisted repair.

## Windows setup (PowerShell)
```powershell
cd path\to\bugpilot_ai_agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest demo_buggy_project -q
streamlit run app.py
```
If PowerShell blocks activation, use Command Prompt instead:
```bat
.venv\Scripts\activate.bat
```

## Linux / WSL setup
```bash
cd /path/to/bugpilot_ai_agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest demo_buggy_project -q
streamlit run app.py
```

## Demo
The included `demo_buggy_project` intentionally fails because `average([])` raises `ZeroDivisionError`, while the test expects `ValueError`. The built-in repair rule adds explicit empty-input validation. Run the app, keep the default repository path, and click **Analyze and debug**.

## Optional Ollama
1. Install Ollama from its official website and start it.
2. Run `ollama pull qwen2.5-coder:7b` in a terminal.
3. In the dashboard, enable the Ollama option.

The current prototype calls the local Ollama HTTP endpoint. The built-in rules are still the primary fallback. This is not a general-purpose automatic repair system.

## What is genuinely implemented?
- **State-space planning:** `agent/planner.py` represents debugging stages as immutable states and uses breadth-first search to find a valid action sequence.
- **Program analysis:** `agent/analyzer.py` parses Python files with `ast` and reports functions, syntax errors, and simple suspicious patterns.
- **Fault localization:** traceback paths receive a higher heuristic score than generic static patterns.
- **Test-driven repair:** `agent/engine.py` runs a baseline suite, applies a candidate, reruns tests, and reverts failures.
- **Dashboard:** `app.py` displays events, planner actions, test output, suspicious locations, and repair history.

## Important limitations
- The planner currently plans a fixed set of abstract debugging stages. It is a real BFS search, but it does not yet optimize among many alternative repair plans.
- Built-in repair patterns are narrow. LLM-generated code can be wrong.
- A passing existing test suite does not prove a patch is correct.
- `subprocess` plus a timeout is not a security sandbox. Use only trusted code. For untrusted repositories, run inside a properly configured disposable container/VM with restricted network, CPU, memory, filesystem, and privileges.
- Make a Git commit or backup before allowing any tool to change files.

## Suggested next upgrades
1. Record repository snapshots and unified diffs for every attempt.
2. Use coverage data to rank suspicious lines.
3. Add multiple candidate repairs and cost-based search over candidate states.
4. Add Docker-based isolation before supporting unknown repositories.
5. Add a benchmark set and compare with a one-shot LLM baseline.
