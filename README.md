# BugPilot AI

**AI-Assisted Software Bug Diagnosis, Repair, and Verification**

BugPilot AI is a project that analyzes software repositories, identifies potential bugs, proposes repairs, and verifies changes using available tests and compiler diagnostics.

## Features

- **Repository Analysis:** Inspect a project directory for source files and potential issues.
- **Python Support:** Analyze Python repositories and use the existing debugging and repair workflow.
- **C Language Support:** Discover C source files, run GCC diagnostics, and generate candidate repairs for supported bug patterns.
- **Repair Verification:** Validate repair candidates and run available tests or compilation checks.
- **State-Space Planning:** Track debugging stages and plan the repair workflow.
- **Streamlit Dashboard:** Use the existing dashboard in `app.py`.
- **Web Frontend:** Access the HTML interface and local API server in the `frontend` directory.
- **Optional Ollama Integration:** Use a locally running Ollama model where supported by the implementation.

## Project Structure

```text
bugpilot_ai_agent/
├── agent/
│   ├── analyzer.py
│   ├── c_analyzer.py
│   ├── c_repair.py
│   ├── c_runner.py
│   ├── compiler_config.py
│   ├── language_detector.py
│   ├── planner.py
│   ├── repair.py
│   └── runner.py
├── frontend/
│   ├── index.html
│   └── server.py
├── app.py
├── test_c_support.py
├── pytest.ini
└── README.md
```

The exact files may vary as development continues.

## Requirements

- Python 3.11 or a compatible Python version
- pip
- Git
- GCC for C compilation and diagnostics
- Streamlit for the dashboard
- Ollama only if using the optional local-model integration

## Installation

Clone the repository and enter the project directory:

```powershell
git clone https://github.com/Gondisuhas/AI-Project.git
cd AI-Project
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project's dependencies if a `requirements.txt` file is present:

```powershell
pip install -r requirements.txt
```

If there is no dependency file, install the dependencies required by the modules you intend to use.

## Configure GCC

Check whether GCC is available:

```powershell
gcc --version
```

If GCC is installed but is not on your PATH, configure its executable path for the current PowerShell session:

```powershell
$env:BUGPILOT_GCC = "E:\ucrt64\bin\gcc.exe"
```

The compiler configuration must be imported by the relevant C modules for this setting to take effect.

## Run the Streamlit Dashboard

From the project root:

```powershell
streamlit run app.py
```

Open the local URL printed in the terminal.

## Run the Web Frontend

From the project root:

```powershell
python frontend/server.py
```

Open:

http://localhost:8090/

The frontend server exposes the `/api/analyze` endpoint. Use the repository path and options supported by the current frontend implementation.

## Run Tests

Run the test suite from the project root:

```powershell
python -m pytest -q
```

## How the Workflow Works

1. The user provides a repository path.
2. BugPilot identifies the supported programming language and source files.
3. The analyzer inspects the repository and reports potential problems.
4. The planner tracks the debugging and repair stages.
5. The repair module generates candidate fixes for supported bug patterns.
6. The relevant verification process checks candidate code.
7. Test or compilation results help determine whether the candidate succeeds.

## Current Limitations

- Automatic repair is limited to supported patterns and is not guaranteed to fix every bug.
- Compiler availability and configuration affect C analysis and verification.
- Support for additional programming languages requires language-specific analysis and execution logic.
- Running untrusted repositories or code can be dangerous. Use isolated environments for untrusted projects; a timeout alone is not a security sandbox.
- Optional local-model features require the appropriate model and service configuration.

## Repository

GitHub: https://github.com/Gondisuhas/AI-Project

Frontend source:
- `frontend/index.html`
- `frontend/server.py`

## Disclaimer

BugPilot AI is a development project intended to assist with debugging. Always review proposed changes and verify them with appropriate tests before using them in production.
