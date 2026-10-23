"""
tools.py – The five Study Buddy AI tools.

Each tool is a plain Python function decorated with @tool from LangChain.
The agent's LangGraph workflow calls these functions; the LLM does NOT
fabricate their results.

Tools:
    1. list_notes        – List available study notes.
    2. search_notes      – Keyword search inside TXT / PDF notes.
    3. record_quiz_result – Save a quiz score to JSON storage.
    4. get_progress      – Retrieve saved quiz records.
    5. save_study_plan   – Persist a study plan to JSON storage.
"""

import logging
import os
import re
from typing import Optional

from langchain_core.tools import tool

import config
import storage

logger = logging.getLogger(__name__)

# ── Helper: read a single note file ─────────────────────────────────────────

def _read_note_text(filepath: str) -> str:
    """
    Return the text content of a TXT or PDF note file.

    Returns an empty string when extraction fails or the file is empty.
    Raises ValueError for unsupported extensions.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError as exc:
            logger.error("Cannot read TXT file %s: %s", filepath, exc)
            return ""

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(filepath)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages)
            if not text.strip():
                logger.warning("PDF %s produced no extractable text (possibly scanned).", filepath)
            return text
        except Exception as exc:
            logger.error("Cannot extract PDF text from %s: %s", filepath, exc)
            return ""

    raise ValueError(f"Unsupported file extension: {ext}")


def _list_note_files() -> list[str]:
    """Return filenames (not full paths) of supported notes in NOTES_DIR."""
    if not os.path.isdir(config.NOTES_DIR):
        return []
    files = []
    for filename in sorted(os.listdir(config.NOTES_DIR)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in config.ALLOWED_EXTENSIONS:
            files.append(filename)
    return files


# ── Tool 1: list_notes ───────────────────────────────────────────────────────

@tool
def list_notes() -> str:
    """
    List all available study notes (TXT and PDF files).

    Returns a formatted list of filenames, or a message if no notes exist.
    Call this tool when the user asks what notes are available.
    """
    files = _list_note_files()
    if not files:
        return (
            "No study notes are available yet. "
            "Please upload a TXT or PDF file using the sidebar."
        )
    lines = [f"  {i+1}. {name}" for i, name in enumerate(files)]
    return "Available study notes:\n" + "\n".join(lines)


# ── Tool 2: search_notes ─────────────────────────────────────────────────────

@tool
def search_notes(query: str) -> str:
    """
    Search the contents of all available study notes for a query.

    Performs simple keyword matching (case-insensitive).
    Returns relevant text passages and their source filenames.
    Use this tool when the user asks questions about their study notes
    or wants to find specific information in uploaded documents.

    Args:
        query: The search terms or question to look for in the notes.
    """
    # Validate query
    query = query.strip()
    if not query:
        return "Please provide a non-empty search query."
    if len(query) > config.MAX_QUERY_LENGTH:
        return (
            f"Query is too long (max {config.MAX_QUERY_LENGTH} characters). "
            "Please shorten your search terms."
        )

    files = _list_note_files()
    if not files:
        return (
            "No study notes are available to search. "
            "Please upload a TXT or PDF file first."
        )

    # Tokenise the query into individual keywords
    keywords = [w.lower() for w in re.split(r"\W+", query) if len(w) >= 2]
    if not keywords:
        return "Please provide at least one meaningful search keyword."

    results = []

    for filename in files:
        filepath = os.path.join(config.NOTES_DIR, filename)
        try:
            text = _read_note_text(filepath)
        except ValueError as exc:
            logger.warning("Skipping unsupported file %s: %s", filename, exc)
            continue

        if not text.strip():
            logger.warning("No extractable text in %s.", filename)
            continue

        # Split into ~sentence-length passages
        passages = re.split(r"(?<=[.!?])\s+|\n{2,}", text)

        for passage in passages:
            passage_lower = passage.lower()
            if any(kw in passage_lower for kw in keywords):
                trimmed = passage.strip()[: config.MAX_PASSAGE_CHARS]
                if trimmed:
                    results.append((filename, trimmed))
                if len(results) >= config.MAX_SEARCH_RESULTS:
                    break

        if len(results) >= config.MAX_SEARCH_RESULTS:
            break

    if not results:
        return (
            f"No content matching '{query}' was found in your study notes. "
            "Try different keywords or upload relevant notes."
        )

    output_parts = [f"Search results for '{query}':\n"]
    for i, (src, passage) in enumerate(results, 1):
        output_parts.append(f"[{i}] Source: {src}\n{passage}\n")

    return "\n".join(output_parts)


# ── Tool 3: record_quiz_result ───────────────────────────────────────────────

@tool
def record_quiz_result(topic: str, score: int, total: int) -> str:
    """
    Save a quiz result to persistent storage.

    Use this tool when the user reports their quiz score so it can be
    saved and retrieved later to track learning progress.

    Args:
        topic: The subject or topic of the quiz (e.g. 'Python Basics').
        score: The number of correct answers the student got.
        total: The total number of questions in the quiz.
    """
    try:
        record = storage.append_quiz_record(topic, score, total)
        return (
            f"✅ Quiz result saved successfully!\n"
            f"  Topic     : {record['topic']}\n"
            f"  Score     : {record['score']} / {record['total']}\n"
            f"  Percentage: {record['percentage']}%\n"
            f"  Saved at  : {record['timestamp']}"
        )
    except ValueError as exc:
        return f"❌ Could not save quiz result: {exc}"
    except OSError as exc:
        logger.error("Storage error saving quiz result: %s", exc)
        return f"❌ Storage error: could not save the quiz result ({exc})."


# ── Tool 4: get_progress ─────────────────────────────────────────────────────

@tool
def get_progress(topic: Optional[str] = None) -> str:
    """
    Retrieve saved quiz results from persistent storage.

    Use this tool when the user asks to see their learning progress,
    quiz history, or past scores.

    Args:
        topic: Optional topic filter. When provided, only records whose
               topic contains this text (case-insensitive) are returned.
               Pass None or an empty string to return all records.
    """
    topic_filter = (topic or "").strip()

    try:
        records = storage.get_progress_records(topic_filter)
    except Exception as exc:
        logger.error("Error reading progress: %s", exc)
        return f"❌ Could not retrieve progress: {exc}"

    if not records:
        if topic_filter:
            return (
                f"No quiz records found for topic '{topic_filter}'. "
                "Try a different topic name or leave blank to see all records."
            )
        return (
            "No quiz records saved yet. "
            "Complete a quiz and use record_quiz_result to save your score."
        )

    lines = [
        f"📊 Quiz Progress"
        + (f" (filtered by '{topic_filter}')" if topic_filter else "")
        + f" – {len(records)} record(s):\n"
    ]
    for i, rec in enumerate(records, 1):
        lines.append(
            f"  {i}. [{rec.get('timestamp', 'N/A')}] "
            f"{rec.get('topic', 'N/A')} – "
            f"{rec.get('score')}/{rec.get('total')} "
            f"({rec.get('percentage')}%)"
        )

    return "\n".join(lines)


# ── Tool 5: save_study_plan ──────────────────────────────────────────────────

@tool
def save_study_plan(topic: str, plan: str) -> str:
    """
    Save a study plan to persistent storage.

    Use this tool when the user asks to save a study plan so it can
    be retrieved in future sessions.

    Args:
        topic: The subject this study plan covers (e.g. 'Python Week 1').
        plan:  The full text of the study plan (day-by-day tasks, etc.).
    """
    try:
        record = storage.append_study_plan(topic, plan)
        preview = record["plan"][:120].replace("\n", " ")
        return (
            f"✅ Study plan saved successfully!\n"
            f"  Topic  : {record['topic']}\n"
            f"  Preview: {preview}{'...' if len(record['plan']) > 120 else ''}\n"
            f"  Saved at: {record['timestamp']}"
        )
    except ValueError as exc:
        return f"❌ Could not save study plan: {exc}"
    except OSError as exc:
        logger.error("Storage error saving study plan: %s", exc)
        return f"❌ Storage error: could not save the study plan ({exc})."


# ── Exported tool list ───────────────────────────────────────────────────────

ALL_TOOLS = [
    list_notes,
    search_notes,
    record_quiz_result,
    get_progress,
    save_study_plan,
]
