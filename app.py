"""
app.py – Streamlit user interface for Study Buddy AI.

Layout
──────
Sidebar:
  • Note upload (TXT / PDF)
  • Available notes list
  • Progress viewer
  • Study plans viewer
  • Clear chat button

Main area:
  • App title and description
  • Chat message history
  • Chat input
  • Expandable tool-call trace panel

All AI responses come from the LangGraph agent; the UI never fabricates them.
"""

import json
import logging
import os
import re

import streamlit as st

import config
import storage
from agent import extract_tool_calls_from_messages, run_agent
from tools import _list_note_files

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Study Buddy AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state initialisation ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []        # LangChain BaseMessage objects
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []    # {role, content} dicts for rendering
if "tool_traces" not in st.session_state:
    st.session_state.tool_traces = []     # List of tool-call info dicts


# ── Helper: safe filename ─────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Strip path components and dangerous characters from a filename."""
    name = os.path.basename(name)                     # No directory traversal
    name = re.sub(r"[^\w\s.\-]", "_", name)           # Keep safe chars only
    name = name.strip(". ")                            # No leading dots or spaces
    return name or "upload"


# ── Helper: upload a note file ────────────────────────────────────────────────

def _handle_upload(uploaded_file) -> str:
    """
    Save an uploaded file to the notes directory.

    Returns a status message.
    """
    # Size check
    max_bytes = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = uploaded_file.read()
    if len(content) > max_bytes:
        return (
            f"❌ File is too large ({len(content) / 1024 / 1024:.1f} MB). "
            f"Maximum allowed size is {config.MAX_UPLOAD_SIZE_MB} MB."
        )

    if not content.strip():
        return "❌ The uploaded file appears to be empty."

    # Extension check
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        return f"❌ Unsupported file type '{ext}'. Only TXT and PDF files are accepted."

    safe_name = _safe_filename(uploaded_file.name)
    dest_path = os.path.join(config.NOTES_DIR, safe_name)

    # Handle duplicates: rename with a counter
    if os.path.exists(dest_path):
        base, extension = os.path.splitext(safe_name)
        counter = 1
        while os.path.exists(dest_path):
            safe_name = f"{base}_{counter}{extension}"
            dest_path = os.path.join(config.NOTES_DIR, safe_name)
            counter += 1

    try:
        os.makedirs(config.NOTES_DIR, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(content)
        logger.info("Note uploaded: %s", dest_path)
        return f"✅ '{safe_name}' uploaded successfully."
    except OSError as exc:
        logger.error("Upload failed: %s", exc)
        return f"❌ Upload failed: {exc}"


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📚 Study Buddy AI")
    st.caption("Your local AI tutor – powered by Ollama & LangGraph")
    st.divider()

    # ── Upload section ────────────────────────────────────────────────────────
    st.subheader("📂 Upload Study Notes")
    uploaded = st.file_uploader(
        f"TXT or PDF (max {config.MAX_UPLOAD_SIZE_MB} MB)",
        type=["txt", "pdf"],
        key="file_uploader",
    )
    if uploaded:
        msg = _handle_upload(uploaded)
        if msg.startswith("✅"):
            st.success(msg)
        else:
            st.error(msg)

    # ── Available notes ───────────────────────────────────────────────────────
    st.subheader("📋 Available Notes")
    note_files = _list_note_files()
    if note_files:
        for nf in note_files:
            st.markdown(f"• `{nf}`")
    else:
        st.info("No notes uploaded yet.")

    st.divider()

    # ── Quiz progress viewer ──────────────────────────────────────────────────
    st.subheader("🏆 Quiz Progress")
    if st.button("Refresh Progress", key="refresh_progress"):
        st.session_state["_refresh_progress"] = True

    records = storage.get_progress_records()
    if records:
        for rec in records[-5:]:          # Show last 5 records
            pct = rec.get("percentage", 0)
            colour = "🟢" if pct >= 70 else "🟡" if pct >= 50 else "🔴"
            st.markdown(
                f"{colour} **{rec.get('topic', 'N/A')}** – "
                f"{rec.get('score')}/{rec.get('total')} ({pct}%)"
            )
        if len(records) > 5:
            st.caption(f"…and {len(records) - 5} more. Ask the agent for full history.")
    else:
        st.info("No quiz results saved yet.")

    st.divider()

    # ── Study plans viewer ────────────────────────────────────────────────────
    st.subheader("📅 Study Plans")
    plans = storage.get_study_plans()
    if plans:
        for plan in plans[-3:]:           # Show last 3 plans
            with st.expander(f"📌 {plan.get('topic', 'Plan')}"):
                st.text(plan.get("plan", "")[:500])
                if len(plan.get("plan", "")) > 500:
                    st.caption("(truncated – ask the agent for the full plan)")
    else:
        st.info("No study plans saved yet.")

    st.divider()

    # ── Controls ──────────────────────────────────────────────────────────────
    if st.button("🗑️ Clear Chat", key="clear_chat"):
        st.session_state.messages = []
        st.session_state.chat_display = []
        st.session_state.tool_traces = []
        st.rerun()

    st.caption(f"Model: `{config.OLLAMA_MODEL}`")
    st.caption(f"Notes dir: `{config.NOTES_DIR}`")


# ── Main area ─────────────────────────────────────────────────────────────────

st.title("🎓 Study Buddy AI")
st.markdown(
    "Welcome! I'm your local AI tutor. Upload your study notes in the sidebar, "
    "then ask me to **summarise**, **quiz** you, **track progress**, or "
    "**create study plans** – all processed locally on your machine."
)
st.divider()

# ── Chat history display ──────────────────────────────────────────────────────
for entry in st.session_state.chat_display:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])

# ── Tool-call trace expander ──────────────────────────────────────────────────
if st.session_state.tool_traces:
    with st.expander("🔍 Tool Execution Trace (last turn)", expanded=False):
        for i, trace in enumerate(st.session_state.tool_traces, 1):
            st.markdown(f"**Step {i}: `{trace.get('tool_name', 'unknown')}`**")
            args = trace.get("args", {})
            if args:
                st.json(args)
            result = trace.get("result")
            if result:
                st.code(result[:800], language="text")
            st.divider()

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input(
    "Ask me anything about your studies… "
    "(e.g. 'Search my Python notes and quiz me')"
)

if user_input:
    user_input = user_input.strip()
    if not user_input:
        st.warning("Please enter a message.")
    else:
        # Display the user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.chat_display.append({"role": "user", "content": user_input})

        # Run the agent
        with st.chat_message("assistant"):
            with st.spinner("Study Buddy is thinking…"):
                try:
                    reply, updated_messages = run_agent(
                        user_input,
                        st.session_state.messages,
                    )
                    # Extract tool traces from this turn
                    traces = extract_tool_calls_from_messages(updated_messages)
                    st.session_state.tool_traces = traces
                    st.session_state.messages = updated_messages

                    st.markdown(reply)
                    st.session_state.chat_display.append(
                        {"role": "assistant", "content": reply}
                    )

                    # Show inline trace summary if tools were called
                    if traces:
                        tool_names = ", ".join(
                            f"`{t['tool_name']}`" for t in traces
                        )
                        st.caption(f"🔧 Tools used: {tool_names}")

                except Exception as exc:
                    error_msg = (
                        f"⚠️ An unexpected error occurred: {exc}\n\n"
                        "Please ensure Ollama is running: `ollama serve`"
                    )
                    st.error(error_msg)
                    logger.exception("Unexpected error in chat handler.")

        # Rerun to update the sidebar (progress, plans may have changed)
        st.rerun()
