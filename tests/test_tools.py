"""
tests/test_tools.py – Automated tests for the five Study Buddy tools.

Uses temporary directories so no real student data is modified.
Does NOT require a live Ollama connection.
"""

import os
import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """
    Redirect all storage and notes paths to a temporary directory.
    This prevents tests from touching real student data.
    """
    import config

    notes_dir      = tmp_path / "notes"
    data_dir       = tmp_path / "data"
    logs_dir       = tmp_path / "logs"
    progress_file  = data_dir / "progress.json"
    plans_file     = data_dir / "study_plans.json"
    trace_file     = logs_dir / "agent_trace.jsonl"

    notes_dir.mkdir()
    data_dir.mkdir()
    logs_dir.mkdir()

    monkeypatch.setattr(config, "NOTES_DIR",         str(notes_dir))
    monkeypatch.setattr(config, "DATA_DIR",          str(data_dir))
    monkeypatch.setattr(config, "PROGRESS_FILE",     str(progress_file))
    monkeypatch.setattr(config, "STUDY_PLANS_FILE",  str(plans_file))
    monkeypatch.setattr(config, "AGENT_TRACE_FILE",  str(trace_file))


@pytest.fixture()
def sample_txt_note():
    """Create a sample TXT note in the notes directory."""
    import config
    note_path = os.path.join(config.NOTES_DIR, "python_basics.txt")
    content = (
        "Python is a high-level programming language.\n"
        "Variables store data values.\n"
        "A function is a block of reusable code.\n"
        "Lists are ordered, mutable collections.\n"
        "Dictionaries store key-value pairs.\n"
    )
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(content)
    return note_path


# ── Tool 1: list_notes ────────────────────────────────────────────────────────

class TestListNotes:

    def test_list_notes_empty(self):
        """list_notes returns a helpful message when no notes exist."""
        from tools import list_notes
        result = list_notes.invoke({})
        assert "No study notes" in result or "no notes" in result.lower()

    def test_list_notes_with_txt(self, sample_txt_note):
        """list_notes includes the uploaded TXT filename."""
        from tools import list_notes
        result = list_notes.invoke({})
        assert "python_basics.txt" in result

    def test_list_notes_excludes_gitkeep(self):
        """list_notes ignores .gitkeep and other unsupported files."""
        import config
        # Create an unsupported file
        bad_path = os.path.join(config.NOTES_DIR, ".gitkeep")
        with open(bad_path, "w") as f:
            f.write("")
        from tools import list_notes
        result = list_notes.invoke({})
        assert ".gitkeep" not in result


# ── Tool 2: search_notes ─────────────────────────────────────────────────────

class TestSearchNotes:

    def test_search_no_notes(self):
        """search_notes returns appropriate message when no notes exist."""
        from tools import search_notes
        result = search_notes.invoke({"query": "python"})
        assert "no study notes" in result.lower() or "no notes" in result.lower() or "upload" in result.lower()

    def test_search_finds_keyword(self, sample_txt_note):
        """search_notes finds content matching the query keyword."""
        from tools import search_notes
        result = search_notes.invoke({"query": "function"})
        assert "function" in result.lower()
        assert "python_basics.txt" in result

    def test_search_no_match(self, sample_txt_note):
        """search_notes reports no match when keyword is absent from notes."""
        from tools import search_notes
        result = search_notes.invoke({"query": "quantum physics xyzabc"})
        assert "no content" in result.lower() or "not found" in result.lower() or "no" in result.lower()

    def test_search_empty_query(self, sample_txt_note):
        """search_notes rejects an empty query."""
        from tools import search_notes
        result = search_notes.invoke({"query": ""})
        assert "non-empty" in result.lower() or "empty" in result.lower() or "provide" in result.lower()

    def test_search_query_too_long(self, sample_txt_note):
        """search_notes rejects a query exceeding MAX_QUERY_LENGTH."""
        import config
        from tools import search_notes
        long_query = "word " * (config.MAX_QUERY_LENGTH // 5 + 10)
        result = search_notes.invoke({"query": long_query})
        assert "too long" in result.lower() or "long" in result.lower()

    def test_search_case_insensitive(self, sample_txt_note):
        """search_notes is case-insensitive."""
        from tools import search_notes
        result_lower = search_notes.invoke({"query": "python"})
        result_upper = search_notes.invoke({"query": "PYTHON"})
        # Both should return results (not 'no content found')
        assert "python_basics.txt" in result_lower
        assert "no content" not in result_upper.lower()

    def test_search_pdf_note(self):
        """search_notes extracts and searches text from a PDF note."""
        import config
        try:
            import pypdf  # noqa: F401
        except ImportError:
            pytest.skip("pypdf not installed")

        # Create a minimal valid PDF containing extractable text
        minimal_pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
            b"4 0 obj\n<< /Length 55 >>\nstream\n"
            b"BT\n/F1 12 Tf\n100 700 Td\n(Photosynthesis converts sunlight into energy.) Tj\nET\n"
            b"endstream\nendobj\n"
            b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000244 00000 n \n"
            b"0000000350 00000 n \n"
            b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n424\n%%EOF\n"
        )
        pdf_path = os.path.join(config.NOTES_DIR, "test_note.pdf")
        with open(pdf_path, "wb") as f:
            f.write(minimal_pdf)

        from tools import search_notes
        result = search_notes.invoke({"query": "photosynthesis"})
        # Either found the text or reported the file
        assert "photosynthesis" in result.lower() or "test_note.pdf" in result


# ── Tool 3: record_quiz_result ────────────────────────────────────────────────

class TestRecordQuizResult:

    def test_valid_record(self):
        """record_quiz_result saves a valid quiz result successfully."""
        from tools import record_quiz_result
        result = record_quiz_result.invoke({"topic": "Python Basics", "score": 4, "total": 5})
        assert "saved" in result.lower() or "✅" in result
        assert "Python Basics" in result

    def test_score_zero_is_valid(self):
        """A score of 0 is valid."""
        from tools import record_quiz_result
        result = record_quiz_result.invoke({"topic": "Math", "score": 0, "total": 10})
        assert "saved" in result.lower() or "✅" in result

    def test_perfect_score_is_valid(self):
        """A score equal to total is valid (100%)."""
        from tools import record_quiz_result
        result = record_quiz_result.invoke({"topic": "History", "score": 10, "total": 10})
        assert "saved" in result.lower() or "✅" in result

    def test_score_exceeds_total(self):
        """record_quiz_result rejects score > total."""
        from tools import record_quiz_result
        result = record_quiz_result.invoke({"topic": "Math", "score": 8, "total": 5})
        assert "❌" in result or "error" in result.lower() or "invalid" in result.lower() or "between" in result.lower()

    def test_negative_score(self):
        """record_quiz_result rejects negative scores."""
        from tools import record_quiz_result
        result = record_quiz_result.invoke({"topic": "Math", "score": -1, "total": 5})
        assert "❌" in result or "error" in result.lower() or "between" in result.lower()

    def test_zero_total(self):
        """record_quiz_result rejects total of 0."""
        from tools import record_quiz_result
        result = record_quiz_result.invoke({"topic": "Math", "score": 0, "total": 0})
        assert "❌" in result or "error" in result.lower() or "positive" in result.lower()

    def test_empty_topic(self):
        """record_quiz_result rejects an empty topic."""
        from tools import record_quiz_result
        result = record_quiz_result.invoke({"topic": "", "score": 3, "total": 5})
        assert "❌" in result or "empty" in result.lower()

    def test_record_persists(self):
        """Saved records persist across separate get_progress calls."""
        from tools import record_quiz_result, get_progress
        record_quiz_result.invoke({"topic": "Science", "score": 7, "total": 10})
        progress = get_progress.invoke({"topic": "Science"})
        assert "Science" in progress
        assert "7" in progress


# ── Tool 4: get_progress ─────────────────────────────────────────────────────

class TestGetProgress:

    def test_no_records(self):
        """get_progress returns an informative message when no records exist."""
        from tools import get_progress
        result = get_progress.invoke({"topic": None})
        assert "no quiz" in result.lower() or "no records" in result.lower() or "saved" in result.lower()

    def test_returns_all_records(self):
        """get_progress returns all saved records when no filter is applied."""
        from tools import record_quiz_result, get_progress
        record_quiz_result.invoke({"topic": "Topic A", "score": 3, "total": 5})
        record_quiz_result.invoke({"topic": "Topic B", "score": 4, "total": 5})
        result = get_progress.invoke({"topic": None})
        assert "Topic A" in result
        assert "Topic B" in result

    def test_topic_filter(self):
        """get_progress filters records by topic substring."""
        from tools import record_quiz_result, get_progress
        record_quiz_result.invoke({"topic": "Python Functions", "score": 5, "total": 5})
        record_quiz_result.invoke({"topic": "Data Structures", "score": 3, "total": 5})
        result = get_progress.invoke({"topic": "Python"})
        assert "Python Functions" in result
        assert "Data Structures" not in result

    def test_empty_topic_returns_all(self):
        """Passing empty string for topic returns all records."""
        from tools import record_quiz_result, get_progress
        record_quiz_result.invoke({"topic": "Topic X", "score": 2, "total": 5})
        result = get_progress.invoke({"topic": ""})
        assert "Topic X" in result

    def test_percentage_shown(self):
        """get_progress displays percentage correctly."""
        from tools import record_quiz_result, get_progress
        record_quiz_result.invoke({"topic": "Algebra", "score": 4, "total": 5})
        result = get_progress.invoke({"topic": "Algebra"})
        assert "80" in result  # 4/5 = 80%


# ── Tool 5: save_study_plan ───────────────────────────────────────────────────

class TestSaveStudyPlan:

    def test_valid_plan(self):
        """save_study_plan saves a plan and returns confirmation."""
        from tools import save_study_plan
        result = save_study_plan.invoke({
            "topic": "Python Week 1",
            "plan": "Day 1: Variables\nDay 2: Loops\nDay 3: Functions"
        })
        assert "saved" in result.lower() or "✅" in result
        assert "Python Week 1" in result

    def test_empty_topic(self):
        """save_study_plan rejects an empty topic."""
        from tools import save_study_plan
        result = save_study_plan.invoke({"topic": "", "plan": "Some plan"})
        assert "❌" in result or "empty" in result.lower()

    def test_empty_plan(self):
        """save_study_plan rejects an empty plan."""
        from tools import save_study_plan
        result = save_study_plan.invoke({"topic": "Maths", "plan": ""})
        assert "❌" in result or "empty" in result.lower()

    def test_plan_persists_after_reload(self):
        """Saved plans survive a reload of the storage module."""
        from tools import save_study_plan
        import storage

        save_study_plan.invoke({
            "topic": "Chemistry",
            "plan": "Day 1: Atoms and molecules"
        })

        # Reload from file to confirm persistence
        plans = storage.get_study_plans()
        topics = [p["topic"] for p in plans]
        assert "Chemistry" in topics

    def test_multiple_plans_saved(self):
        """Multiple plans for different topics can coexist."""
        from tools import save_study_plan
        import storage

        save_study_plan.invoke({"topic": "Biology", "plan": "Day 1: Cells"})
        save_study_plan.invoke({"topic": "Physics", "plan": "Day 1: Mechanics"})

        plans = storage.get_study_plans()
        topics = [p["topic"] for p in plans]
        assert "Biology" in topics
        assert "Physics" in topics
