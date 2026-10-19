from pathlib import Path
import streamlit as st
from agent.engine import run_agent

st.set_page_config(page_title="BugPilot AI", page_icon="🛠️", layout="wide")
st.title(" BugPilot AI — Autonomous Debugging Agent")
st.write("Analyze a repository, plan debugging actions, attempt a controlled repair, and verify it. Supports Python and C.")
st.warning("Safety: run this only on projects you trust. Tests execute project code with your user permissions; this prototype is not a security sandbox. Make a Git commit or backup before running it.")

default_path = str((Path(__file__).parent / "demo_buggy_project").resolve())
repo_path = st.text_input("Path to a local repository", value=default_path)

# Language selection
col_lang, col_attempts, col_ollama = st.columns(3)
with col_lang:
    language_choice = st.selectbox(
        "Language",
        ["Auto-detect", "Python", "C"],
        help="Auto-detect will analyze file extensions to determine the primary language"
    )
    language = None if language_choice == "Auto-detect" else language_choice.lower()

with col_attempts:
    max_attempts = st.slider("Maximum repair attempts", 1, 5, 3)

with col_ollama:
    use_ollama = st.checkbox("Use local Ollama model if available (optional)", value=False)

if use_ollama:
    st.caption("Requires Ollama running locally and a model pulled, e.g. `ollama pull qwen2.5-coder:7b`. Built-in repair rules remain available.")

if st.button(" Analyze and debug", type="primary", use_container_width=True):
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
            result = run_agent(root, max_attempts=max_attempts, use_ollama=use_ollama, progress=progress, language=language)
            st.session_state["last_result"] = result
            st.session_state["last_repo"] = str(root.resolve())
        except Exception as exc:
            st.exception(exc)

result = st.session_state.get("last_result")
if result:
    st.divider()
    st.subheader("Result")
    status = result["status"]
    detected_lang = result.get("language", "unknown")

    # Display status message
    if status == "REPAIRED_TESTS_PASS":
        st.success("Candidate patch passed verification. Review the diff before committing.")
    elif status == "NO_REPRODUCIBLE_FAILURE":
        if detected_lang == "python":
            st.info("The test suite passed before any repair. No bug was reproduced.")
        elif detected_lang == "c":
            st.info("The C code compiles successfully. No syntax errors detected.")
        else:
            st.info("No reproducible failure was found.")
    elif status == "UNSUPPORTED_LANGUAGE":
        st.error(f"Language '{detected_lang}' is not yet supported. Supported: python, c")
    else:
        st.error("The agent could not verify a repair. Original code was restored after failed candidates.")

    # Display metrics
    col_a, col_b, col_c = st.columns(3)

    if detected_lang == "python":
        col_a.metric("Python files", len(result["analysis"].get("files", [])))
        col_a.metric("Functions found", len(result["analysis"].get("functions", [])))
    elif detected_lang == "c":
        col_a.metric("C files", len(result["analysis"].get("files", [])))
        col_a.metric("Compiler diagnostics", len(result["analysis"].get("diagnostics", [])))
    else:
        col_a.metric("Files", len(result["analysis"].get("files", [])))

    col_b.metric("Repair attempts", len(result.get("attempts", [])))

    # Final verification result
    if detected_lang == "python":
        final_pass = result.get("final", {}).get("passed", False)
        col_c.metric("Final tests", "PASS" if final_pass else "FAIL")
    elif detected_lang == "c":
        final_compiled = result.get("final", {}).get("compiled", False)
        col_c.metric("Final compilation", "SUCCESS" if final_compiled else "FAILED")
    else:
        col_c.metric("Status", status)

    # Display planner action sequence
    with st.expander("Planner action sequence", expanded=True):
        st.code(" → ".join(result.get("plan", [])))

    # Display agent event log
    with st.expander("Agent event log", expanded=True):
        st.markdown("\n".join("- " + item for item in result["log"]))

    # Display baseline output
    if detected_lang == "python":
        with st.expander("Baseline test output"):
            st.code(result.get("baseline", {}).get("output", "(no output)") or "(no output)")
    elif detected_lang == "c":
        with st.expander("Baseline compilation output"):
            st.code(result.get("baseline", {}).get("output", "(no output)") or "(no output)")

    # Display fault localization results
    with st.expander("Fault localization results"):
        suspicious = result.get("suspicious", [])
        if suspicious:
            st.json(suspicious)
        else:
            st.write("No suspicious locations identified.")

    # Display repair attempt details
    with st.expander("Repair attempt details"):
        attempts = result.get("attempts", [])
        if attempts:
            st.json(attempts)
        else:
            st.write("No repair attempts were made.")

    # Display final output
    if detected_lang == "python":
        with st.expander("Final test output"):
            st.code(result.get("final", {}).get("output", "(no output)") or "(no output)")
    elif detected_lang == "c":
        with st.expander("Final compilation output"):
            st.code(result.get("final", {}).get("output", "(no output)") or "(no output)")

    # Display appropriate warning
    if detected_lang == "python":
        st.caption("A passing test suite is evidence, not proof, that the patch is correct. Inspect changes and add tests for edge cases.")
    elif detected_lang == "c":
        st.caption("Successful compilation is evidence, not proof, that the patch is correct. Test the program thoroughly and inspect changes for logical correctness.")
