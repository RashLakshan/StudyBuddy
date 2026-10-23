"""
tests/test_storage.py – Tests for storage.py helper functions.

Uses temporary directories so real student data is never touched.
"""

import json
import os
import pytest


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Redirect all storage paths to a temporary directory."""
    import config

    data_dir = tmp_path / "data"
    logs_dir = tmp_path / "logs"
    data_dir.mkdir()
    logs_dir.mkdir()

    monkeypatch.setattr(config, "DATA_DIR",          str(data_dir))
    monkeypatch.setattr(config, "PROGRESS_FILE",     str(data_dir / "progress.json"))
    monkeypatch.setattr(config, "STUDY_PLANS_FILE",  str(data_dir / "study_plans.json"))
    monkeypatch.setattr(config, "AGENT_TRACE_FILE",  str(logs_dir / "agent_trace.jsonl"))


# ── Quiz progress ─────────────────────────────────────────────────────────────

class TestAppendQuizRecord:

    def test_valid_record_saved(self):
        """Valid quiz record is saved and returned correctly."""
        from storage import append_quiz_record, get_progress_records
        rec = append_quiz_record("Python", 4, 5)
        assert rec["topic"] == "Python"
        assert rec["score"] == 4
        assert rec["total"] == 5
        assert rec["percentage"] == 80.0
        assert "timestamp" in rec

        records = get_progress_records()
        assert len(records) == 1

    def test_multiple_records_preserved(self):
        """Multiple quiz records accumulate without overwriting."""
        from storage import append_quiz_record, get_progress_records
        append_quiz_record("Topic A", 3, 5)
        append_quiz_record("Topic B", 5, 5)
        records = get_progress_records()
        assert len(records) == 2

    def test_score_exceeds_total_raises(self):
        """Score greater than total raises ValueError."""
        from storage import append_quiz_record
        with pytest.raises(ValueError, match="between 0 and"):
            append_quiz_record("Math", 6, 5)

    def test_negative_score_raises(self):
        """Negative score raises ValueError."""
        from storage import append_quiz_record
        with pytest.raises(ValueError):
            append_quiz_record("Math", -1, 5)

    def test_zero_total_raises(self):
        """Total of zero raises ValueError."""
        from storage import append_quiz_record
        with pytest.raises(ValueError, match="positive"):
            append_quiz_record("Math", 0, 0)

    def test_empty_topic_raises(self):
        """Empty topic raises ValueError."""
        from storage import append_quiz_record
        with pytest.raises(ValueError, match="empty"):
            append_quiz_record("   ", 3, 5)

    def test_topic_filter(self):
        """get_progress_records filters by topic substring."""
        from storage import append_quiz_record, get_progress_records
        append_quiz_record("Python Functions", 4, 5)
        append_quiz_record("Data Structures", 3, 5)

        filtered = get_progress_records("Python")
        assert len(filtered) == 1
        assert filtered[0]["topic"] == "Python Functions"

    def test_empty_filter_returns_all(self):
        """Empty filter string returns all records."""
        from storage import append_quiz_record, get_progress_records
        append_quiz_record("Alpha", 2, 5)
        append_quiz_record("Beta", 4, 5)
        assert len(get_progress_records("")) == 2

    def test_percentage_calculation(self):
        """Percentage is calculated correctly."""
        from storage import append_quiz_record
        rec = append_quiz_record("Test", 1, 3)
        assert rec["percentage"] == round(1 / 3 * 100, 1)

    def test_persistence_across_reads(self):
        """Data persists when the progress file is read again from disk."""
        import config
        from storage import append_quiz_record, _read_json
        append_quiz_record("Persist Test", 5, 5)
        raw = _read_json(config.PROGRESS_FILE, {"records": []})
        topics = [r["topic"] for r in raw["records"]]
        assert "Persist Test" in topics


class TestInvalidJson:

    def test_corrupted_progress_file_returns_default(self, tmp_path, monkeypatch):
        """Corrupted progress.json returns empty default without crashing."""
        import config
        bad_file = tmp_path / "data" / "progress.json"
        bad_file.parent.mkdir(exist_ok=True)
        bad_file.write_text("NOT VALID JSON", encoding="utf-8")
        monkeypatch.setattr(config, "PROGRESS_FILE", str(bad_file))

        from storage import load_progress
        data = load_progress()
        assert data == {"records": []}

    def test_corrupted_plans_file_returns_default(self, tmp_path, monkeypatch):
        """Corrupted study_plans.json returns empty default without crashing."""
        import config
        bad_file = tmp_path / "data" / "study_plans.json"
        bad_file.parent.mkdir(exist_ok=True)
        bad_file.write_text("{broken json", encoding="utf-8")
        monkeypatch.setattr(config, "STUDY_PLANS_FILE", str(bad_file))

        from storage import load_study_plans
        data = load_study_plans()
        assert data == {"plans": []}

    def test_missing_progress_file_returns_default(self):
        """Missing progress file returns default without crashing."""
        from storage import load_progress
        data = load_progress()
        assert "records" in data


# ── Study plans ───────────────────────────────────────────────────────────────

class TestStudyPlans:

    def test_valid_plan_saved(self):
        """Valid study plan is saved and retrievable."""
        from storage import append_study_plan, get_study_plans
        rec = append_study_plan("Python Week 1", "Day 1: Variables\nDay 2: Loops")
        assert rec["topic"] == "Python Week 1"
        assert "timestamp" in rec

        plans = get_study_plans()
        assert len(plans) == 1

    def test_multiple_plans(self):
        """Multiple plans accumulate."""
        from storage import append_study_plan, get_study_plans
        append_study_plan("Topic A", "Plan A details")
        append_study_plan("Topic B", "Plan B details")
        assert len(get_study_plans()) == 2

    def test_empty_topic_raises(self):
        """Empty topic raises ValueError."""
        from storage import append_study_plan
        with pytest.raises(ValueError, match="empty"):
            append_study_plan("", "Some plan")

    def test_empty_plan_raises(self):
        """Empty plan raises ValueError."""
        from storage import append_study_plan
        with pytest.raises(ValueError, match="empty"):
            append_study_plan("Topic", "")

    def test_plan_filter(self):
        """get_study_plans filters by topic substring."""
        from storage import append_study_plan, get_study_plans
        append_study_plan("Python Advanced", "Day 1: Decorators")
        append_study_plan("JavaScript Basics", "Day 1: Variables")

        filtered = get_study_plans("Python")
        assert len(filtered) == 1
        assert filtered[0]["topic"] == "Python Advanced"

    def test_unicode_preserved(self):
        """Unicode (Sinhala) characters are preserved in storage."""
        from storage import append_study_plan, get_study_plans
        sinhala_topic = "පයිතන් මූලික කරුණු"
        sinhala_plan = "දිනය 1: විචල්‍ය"
        append_study_plan(sinhala_topic, sinhala_plan)
        plans = get_study_plans()
        assert plans[0]["topic"] == sinhala_topic
        assert plans[0]["plan"] == sinhala_plan


# ── Trace logging ─────────────────────────────────────────────────────────────

class TestAppendTrace:

    def test_trace_written(self):
        """append_trace writes a valid JSON line to the trace file."""
        import config
        from storage import append_trace

        append_trace({"node": "test", "event": "unit_test", "tool_name": "list_notes"})

        assert os.path.exists(config.AGENT_TRACE_FILE)
        with open(config.AGENT_TRACE_FILE, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        entry = json.loads(line)
        assert entry["node"] == "test"
        assert entry["event"] == "unit_test"
        assert "timestamp" in entry

    def test_multiple_traces_appended(self):
        """Multiple trace entries are appended, not overwritten."""
        from storage import append_trace
        append_trace({"event": "first"})
        append_trace({"event": "second"})

        import config
        with open(config.AGENT_TRACE_FILE, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 2
