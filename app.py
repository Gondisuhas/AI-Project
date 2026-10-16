from pathlib import Path
import streamlit as st
from agent.engine import run_agent
from agent.analyzer import analyze_repository

st.set_page_config(page_title="BugPilot AI", page_icon="🛠️", layout="wide")
st.title("🛠️ BugPilot AI — Autonomous Debugging Agent")
st.write("Analyze a Python repository, plan debugging actions, attempt a controlled repair, and verify it with tests.")
st.warning("Safety: run this only on projects you trust. Tests execute project code with your user permissions; this prototype is not a security sandbox. Make a Git commit or backup before running it.")

default_path = str((Path(__file__).parent / "demo_buggy_project").resolve())
repo_path = st.text_input("Path to a local Python repository", value=default_path)
col1, col2 = st.columns(2)
with col1:
    max_attempts = st.slider("Maximum repair attempts", 1, 5, 3)
with col2:
    use_ollama = st.checkbox("Use local Ollama model if available (optional)", value=False)
if use_ollama:
    st.caption("Requires Ollama running locally and a model pulled, e.g. `ollama pull qwen2.5-coder:7b`. Built-in repair rules remain available.")
if st.button("🚀 Analyze and debug", type="primary", use_container_width=True):
    root = Path(repo_path).expanduser()
    if not root.is_dir():
        st.error("That folder does not exist. Enter a valid local repository path.")
    else:
        events = st.empty()
        messages = []
        def progress(msg):
            messages.append("• " + msg)
            events.markdown("\n\n".join(messages[-12:]))
        try:
            result = run_agent(root, max_attempts=max_attempts, use_ollama=use_ollama, progress=progress)
            st.session_state["last_result"] = result
            st.session_state["last_repo"] = str(root.resolve())
        except Exception as exc:
            st.exception(exc)

result = st.session_state.get("last_result")
if result:
    st.divider()
    st.subheader("Result")
    status = result["status"]
    if status == "REPAIRED_TESTS_PASS":
        st.success("Candidate patch passed the complete pytest suite. Review the diff before committing.")
    elif status == "NO_REPRODUCIBLE_FAILURE":
        st.info("The test suite passed before any repair. No bug was reproduced.")
    else:
        st.error("The agent could not verify a repair. Original code was restored after failed candidates.")
    a, b, c = st.columns(3)
    a.metric("Python files", len(result["analysis"]["files"]))
    a.metric("Functions found", len(result["analysis"]["functions"]))
    b.metric("Repair attempts", len(result.get("attempts", [])))
    c.metric("Final tests", "PASS" if result["final"]["passed"] else "FAIL")
    with st.expander("Planner action sequence", expanded=True):
        st.code(" → ".join(result.get("plan", [])))
    with st.expander("Agent event log", expanded=True):
        st.markdown("\n".join("- " + item for item in result["log"]))
    with st.expander("Baseline test output"):
        st.code(result["baseline"]["output"] or "(no output)")
    with st.expander("Fault localization results"):
        st.json(result.get("suspicious", []))
    with st.expander("Repair attempt details"):
        st.json(result.get("attempts", []))
    with st.expander("Final test output"):
        st.code(result["final"]["output"] or "(no output)")
    st.caption("A passing test suite is evidence, not proof, that the patch is correct. Inspect changes and add tests for edge cases.")
