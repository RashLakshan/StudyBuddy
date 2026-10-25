"""
app.py – Streamlit user interface for Study Buddy AI.

Features:
  • Clean, user-friendly layout with intuitive sidebar controls.
  • Interactive quizzes with single-selection checkboxes and instant feedback.
  • Progressive question loading (next question loads after answering).
  • Automatic saving of quiz results to the Quiz Progress feature.
  • Upload and management of study notes (TXT & PDF).
  • Study plans and tool-call execution trace inspector.
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
    st.session_state.chat_display = []    # Renderable chat message objects
if "tool_traces" not in st.session_state:
    st.session_state.tool_traces = []     # Tool execution trace from last turn


# ── Helper: safe filename ─────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Strip path components and dangerous characters from a filename."""
    name = os.path.basename(name)
    name = re.sub(r"[^\w\s.\-]", "_", name)
    name = name.strip(". ")
    return name or "upload"


# ── Helper: upload a note file ────────────────────────────────────────────────

def _handle_upload(uploaded_file) -> str:
    """Save an uploaded file to the notes directory. Returns status message."""
    max_bytes = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = uploaded_file.read()
    if len(content) > max_bytes:
        return (
            f"❌ File is too large ({len(content) / 1024 / 1024:.1f} MB). "
            f"Maximum allowed size is {config.MAX_UPLOAD_SIZE_MB} MB."
        )

    if not content.strip():
        return "❌ The uploaded file appears to be empty."

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        return f"❌ Unsupported file type '{ext}'. Only TXT and PDF files are accepted."

    safe_name = _safe_filename(uploaded_file.name)
    dest_path = os.path.join(config.NOTES_DIR, safe_name)

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


# ── Helper: parse quiz questions from markdown ────────────────────────────────

def parse_quiz_questions(full_text: str) -> tuple[str, list[dict]]:
    """
    Parse multiple-choice questions from text, extracting questions, options,
    and answer keys.

    Returns:
        (intro_text, list_of_question_dicts)
        where each question dict contains:
            num: int
            question: str
            options: [{'letter': 'A', 'text': 'A) ...'}, ...]
            answer: 'A' (str) or None
    """
    if not re.search(r"\b[A-D][.:\-)—]\s+", full_text):
        return full_text, []

    # 1. Extract answers if present (e.g. 'Answers: 1. A, 2. B' or '1: A')
    answers = {}
    ans_sec = re.search(
        r"(?:\n|^)\s*[*_#\s]*(?:Answers\b|Answer\s+Key\b|Solutions?\b)[*_#\s:]+\s*(.*)",
        full_text,
        re.IGNORECASE | re.DOTALL,
    )
    if ans_sec:
        for m in re.finditer(
            r"(?:(?:Question\s*)?(\d+)[\s.:\-)—]+\(?([A-D])\)?(?:\b|[.:\-)—]))",
            ans_sec.group(1),
            re.IGNORECASE,
        ):
            answers[int(m.group(1))] = m.group(2).upper()
        if not answers:
            # Fallback for unnumbered list of answers e.g. A, B, C or 1-A
            raw_letters = re.findall(r"\b([A-D])\b", ans_sec.group(1).upper())
            for idx, letter in enumerate(raw_letters, 1):
                answers[idx] = letter
        main_content = full_text[: ans_sec.start()].strip()
    else:
        main_content = full_text.strip()

    questions = []
    # Match numbered questions: e.g. 1. ... 2. ...
    q_pattern = r"(?:\n|^)\s*[*_#\s]*(?:Question\s*)?(\d+)[\s.:\-)—*#_]+\s*(.+?)(?=(?:\n\s*[*_#\s]*(?:Question\s*)?\d+[\s.:\-)—*#_]+)|$)"
    q_numbered = list(re.finditer(q_pattern, main_content, re.DOTALL | re.IGNORECASE))

    if len(q_numbered) >= 1 and re.search(r"\b[A-D][.:\-)—]\s+", q_numbered[0].group(2)):
        intro = main_content[: q_numbered[0].start()].strip()
        for qm in q_numbered:
            num = int(qm.group(1))
            block = qm.group(2).strip()

            # Check for inline answer inside the question block
            inline_ans = re.search(
                r"(?:^|\n)\s*[*_#\s]*(?:Answer|Correct(?:\s+Answer)?|Key)\s*[:\-—]\s*\(?([A-D])\)?",
                block,
                re.IGNORECASE,
            )
            q_ans = answers.get(num)
            if inline_ans:
                if not q_ans:
                    q_ans = inline_ans.group(1).upper()
                block = block[: inline_ans.start()].strip()

            a_match = re.search(r"(?:^|\s|\n)(?:[-*]?\s*)A[.:\-)—]\s+", block)
            if a_match:
                q_text = block[: a_match.start()].strip("*_ \n#")
                opt_str = block[a_match.start() :]
                parts = re.split(r"\s*(?:^|\s|\n)(?:[-*]?\s*)([A-D])[.:\-)—]\s+", opt_str)
                opts = []
                for i in range(1, len(parts), 2):
                    letter = parts[i].upper()
                    otext = parts[i + 1].strip()
                    if i + 2 >= len(parts):
                        paras = [p.strip() for p in otext.split("\n\n") if p.strip()]
                        otext = paras[0] if paras else otext
                    opts.append({"letter": letter, "text": f"{letter}) {otext}"})
                if len(opts) >= 2:
                    questions.append({
                        "num": num,
                        "question": q_text,
                        "options": opts,
                        "answer": q_ans,
                    })
        if questions:
            return intro, questions

    # Fallback: single unnumbered question
    inline_ans = re.search(
        r"(?:^|\n)\s*[*_#\s]*(?:Answer|Correct(?:\s+Answer)?|Key)\s*[:\-—]\s*\(?([A-D])\)?",
        main_content,
        re.IGNORECASE,
    )
    fallback_ans = answers.get(1)
    if inline_ans:
        if not fallback_ans:
            fallback_ans = inline_ans.group(1).upper()
        main_content = main_content[: inline_ans.start()].strip()

    a_match = re.search(r"(?:^|\n|\s{2,}|\b)(?:[-*]?\s*)A[.:\-)—]\s+", main_content)
    if a_match:
        pre_a = main_content[: a_match.start()].strip()
        opt_str = main_content[a_match.start() :].strip()
        paras = [p.strip() for p in pre_a.split("\n\n") if p.strip()]
        if len(paras) > 1:
            intro = "\n\n".join(paras[:-1])
            q_text = paras[-1]
        elif len(paras) == 1:
            lines = [l.strip() for l in paras[0].split("\n") if l.strip()]
            if len(lines) > 1 and lines[-1].endswith("?"):
                intro = "\n\n".join(lines[:-1])
                q_text = lines[-1]
            else:
                intro = ""
                q_text = paras[0]
        else:
            intro = ""
            q_text = ""

        num_m = re.match(r"^(?:Question\s*)?(\d+)[\s.:\-)—]+\s*(.*)", q_text, re.DOTALL | re.IGNORECASE)
        q_num = int(num_m.group(1)) if num_m else 1
        if num_m:
            q_text = num_m.group(2).strip()

        parts = re.split(r"\s*(?:^|\s|\n)(?:[-*]?\s*)([A-D])[.:\-)—]\s+", opt_str)
        opts = []
        for i in range(1, len(parts), 2):
            letter = parts[i].upper()
            otext = parts[i + 1].strip()
            if i + 2 >= len(parts):
                paras_opt = [p.strip() for p in otext.split("\n\n") if p.strip()]
                otext = paras_opt[0] if paras_opt else otext
            opts.append({"letter": letter, "text": f"{letter}) {otext}"})

        if len(opts) >= 2:
            questions.append({
                "num": q_num,
                "question": q_text.strip("*_ #\n"),
                "options": opts,
                "answer": answers.get(q_num) or fallback_ans,
            })
            return intro, questions

    return full_text, []


# ── Helper: extract quiz topic ────────────────────────────────────────────────

def _extract_quiz_topic(intro: str, user_prompt: str = "") -> str:
    """Extract a clean, concise topic name for saving quiz progress."""
    for text in [user_prompt, intro]:
        if not text:
            continue
        m = re.search(r"(?:quiz\s+(?:me\s+)?on|quiz\s+about|topic:?)\s+([^.,!?:;\n]{2,30})", text, re.IGNORECASE)
        if m:
            topic = m.group(1).strip(" .:-")
            words = topic.split()
            if len(words) > 3:
                topic = " ".join(words[:3])
            if topic and len(topic) <= 40:
                return topic.title()
    for f in _list_note_files():
        base = os.path.splitext(f)[0]
        combined = f"{user_prompt} {intro}".lower()
        if base.lower() in combined:
            return base
    return "Study Notes Quiz"


# ── Callback: mutually exclusive checkbox toggle ──────────────────────────────

def _on_quiz_option_toggle(msg_idx: int, q_idx: int, clicked_idx: int, total_opts: int):
    """
    Enforces single-selection among checkboxes for a quiz question.
    Checking an option unchecks all other options for that question.
    """
    chk_key = f"quiz_chk_{msg_idx}_{q_idx}_{clicked_idx}"
    sel_key = f"quiz_sel_{msg_idx}_{q_idx}"

    if st.session_state.get(chk_key):
        st.session_state[sel_key] = clicked_idx
        for i in range(total_opts):
            if i != clicked_idx:
                st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_{i}"] = False
    else:
        if st.session_state.get(sel_key) == clicked_idx:
            st.session_state[sel_key] = None


# ── Helper: clear conversation and quiz states ────────────────────────────────

def _clear_chat():
    """Reset all conversation history and quiz selection states."""
    st.session_state.messages = []
    st.session_state.chat_display = []
    st.session_state.tool_traces = []
    for k in list(st.session_state.keys()):
        if k.startswith("quiz_") or k.startswith("chk_"):
            del st.session_state[k]


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
            icon = "📑" if nf.lower().endswith(".pdf") else "📄"
            st.markdown(f"{icon} `{nf}`")
    else:
        st.info("No notes uploaded yet. Upload a TXT or PDF above.")

    st.divider()

    # ── Quiz progress viewer ──────────────────────────────────────────────────
    st.subheader("🏆 Quiz Progress")
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
            st.caption(f"…and {len(records) - 5} earlier quiz records.")
    else:
        st.info("No quiz results saved yet. Take a quiz to track progress!")

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
    if st.button("🗑️ Clear Chat", use_container_width=True):
        _clear_chat()
        st.rerun()

    st.caption(f"Model: `{config.OLLAMA_MODEL}`")


# ── Main Area ─────────────────────────────────────────────────────────────────

# ── Empty state / Quick action hero banner ─────────────────────────────────────
if not st.session_state.chat_display:
    st.title("🎓 Study Buddy AI")
    st.markdown(
        "Welcome! I'm your local AI tutor. Upload your study notes in the sidebar, "
        "then ask me to **summarise**, **quiz** you, **track progress**, or "
        "**create study plans** – all processed locally on your machine."
    )
    st.write("")

    st.markdown("##### ⚡ Quick Prompts")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Quiz me on my notes", use_container_width=True):
            st.session_state["pending_prompt"] = (
                "Create a 3-question multiple-choice quiz based on my study notes."
            )
            st.rerun()
        if st.button("🔍 What notes do I have?", use_container_width=True):
            st.session_state["pending_prompt"] = "What study notes are uploaded?"
            st.rerun()
    with col2:
        if st.button("📅 Create a study plan", use_container_width=True):
            st.session_state["pending_prompt"] = (
                "Create a realistic study plan based on my study notes and save it."
            )
            st.rerun()
        if st.button("📊 Show my quiz progress", use_container_width=True):
            st.session_state["pending_prompt"] = "Show me my saved quiz progress."
            st.rerun()

    st.divider()
else:
    st.title("🎓 Study Buddy AI")


# ── Chat history display ──────────────────────────────────────────────────────
for msg_idx, entry in enumerate(st.session_state.chat_display):
    with st.chat_message(entry["role"]):
        if entry.get("tools"):
            tool_badges = " • ".join(f"`{t}`" for t in entry["tools"])
            st.caption(f"🔧 Tools used: {tool_badges}")

        if entry["role"] == "user":
            st.markdown(entry["content"])
        else:
            intro, questions = parse_quiz_questions(entry["content"])

            if not questions:
                st.markdown(entry["content"])
            else:
                if intro:
                    st.markdown(intro)

                total_qs = len(questions)

                # Count answered questions and awarded points
                answered_count = sum(
                    1 for q_i in range(total_qs)
                    if st.session_state.get(f"quiz_sel_{msg_idx}_{q_i}") is not None
                )
                scored_count = sum(
                    1 for q_i, q in enumerate(questions)
                    if st.session_state.get(f"quiz_sel_{msg_idx}_{q_i}") is not None
                    and q.get("answer")
                    and q["options"][st.session_state.get(f"quiz_sel_{msg_idx}_{q_i}")]["letter"] == q.get("answer")
                )

                st.markdown(f"#### 📝 Quiz: {total_qs} Questions (1 Point Each)")
                st.caption(
                    f"⭐ **Current Score:** {scored_count} / {total_qs} Points • "
                    f"**Answered:** {answered_count} of {total_qs}"
                )
                st.progress(answered_count / total_qs if total_qs > 0 else 0.0)

                # Display all questions simultaneously
                for q_idx in range(total_qs):
                    q = questions[q_idx]
                    sel_key = f"quiz_sel_{msg_idx}_{q_idx}"
                    sel_idx = st.session_state.get(sel_key)

                    with st.container(border=True):
                        st.markdown(f"**Question {q['num']} (1 Point): {q['question']}**")

                        # Checkboxes with single-selection enforcement
                        for opt_idx, opt in enumerate(q["options"]):
                            chk_key = f"quiz_chk_{msg_idx}_{q_idx}_{opt_idx}"
                            if chk_key not in st.session_state:
                                st.session_state[chk_key] = (sel_idx == opt_idx)

                            st.checkbox(
                                opt["text"],
                                key=chk_key,
                                on_change=_on_quiz_option_toggle,
                                args=(msg_idx, q_idx, opt_idx, len(q["options"])),
                                disabled=(sel_idx is not None),
                            )

                        # Immediate feedback: award points or display correct answer
                        if sel_idx is not None:
                            selected_letter = q["options"][sel_idx]["letter"]
                            correct_letter = q.get("answer")

                            if correct_letter:
                                if selected_letter == correct_letter:
                                    st.success("✅ **Correct! +1 Point awarded!**")
                                else:
                                    correct_opt_text = next(
                                        (o["text"] for o in q["options"] if o["letter"] == correct_letter),
                                        f"Option {correct_letter}",
                                    )
                                    st.error(f"❌ **Incorrect (0 Points).** The correct answer is **{correct_opt_text}**.")
                            else:
                                st.info(f"Selected: **{q['options'][sel_idx]['text']}**")

                # When all questions are answered: auto-save score to Quiz Progress
                if answered_count == total_qs and total_qs > 0:
                    pct = round(scored_count / total_qs * 100, 1)

                    with st.container(border=True):
                        st.markdown(f"### 🏆 Quiz Complete!")
                        st.markdown(f"You scored **{scored_count} / {total_qs} Points** ({pct}%)")

                        # Automatically save score to Quiz Progress
                        save_key = f"quiz_saved_{msg_idx}"
                        if not st.session_state.get(save_key):
                            user_prompt = entry.get("user_prompt", "")
                            topic = _extract_quiz_topic(intro, user_prompt)
                            try:
                                storage.append_quiz_record(topic=topic, score=scored_count, total=total_qs)
                                st.session_state[save_key] = True
                                st.success(
                                    f"✅ Quiz progress automatically saved to records under **{topic}** "
                                    f"({scored_count}/{total_qs} Points)!"
                                )
                            except Exception as exc:
                                logger.error("Auto-save quiz progress failed: %s", exc)
                        else:
                            st.caption("✅ Saved to Quiz Progress.")

                        # Retake quiz button
                        if st.button("🔄 Retake Quiz", key=f"retake_{msg_idx}"):
                            for q_i in range(total_qs):
                                st.session_state.pop(f"quiz_sel_{msg_idx}_{q_i}", None)
                                for opt_i in range(len(questions[q_i]["options"])):
                                    st.session_state.pop(f"quiz_chk_{msg_idx}_{q_i}_{opt_i}", None)
                            st.session_state.pop(f"quiz_saved_{msg_idx}", None)
                            st.rerun()


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


# ── Chat input handling ───────────────────────────────────────────────────────
chat_prompt = st.chat_input("Ask me anything about your studies… (e.g. 'Search my notes and quiz me')")

active_prompt = None
if chat_prompt:
    active_prompt = chat_prompt.strip()
elif st.session_state.get("pending_prompt"):
    active_prompt = st.session_state.pop("pending_prompt")

if active_prompt:
    # Display user query
    with st.chat_message("user"):
        st.markdown(active_prompt)
    st.session_state.chat_display.append({"role": "user", "content": active_prompt})

    # Run agent
    with st.chat_message("assistant"):
        with st.spinner("Study Buddy is thinking…"):
            try:
                reply, updated_messages = run_agent(
                    active_prompt,
                    st.session_state.messages,
                )
                traces = extract_tool_calls_from_messages(updated_messages)
                st.session_state.tool_traces = traces
                st.session_state.messages = updated_messages

                st.markdown(reply)
                display_entry = {
                    "role": "assistant",
                    "content": reply,
                    "user_prompt": active_prompt,
                }
                if traces:
                    display_entry["tools"] = [t["tool_name"] for t in traces]
                st.session_state.chat_display.append(display_entry)

            except Exception as exc:
                error_msg = (
                    f"⚠️ An unexpected error occurred: {exc}\n\n"
                    "Please ensure Ollama is running: `ollama serve`"
                )
                st.error(error_msg)
                logger.exception("Unexpected error in chat handler.")

    st.rerun()
