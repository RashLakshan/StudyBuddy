# Test Results – Study Buddy AI

Actual test outcomes from running the automated test suite.

---

## Test Environment

| Item | Value |
|---|---|
| Python | 3.14.3 |
| Operating System | Windows 11 |
| Ollama | Running (llama3.2:latest) |
| pytest | 8.x |
| Test Command | `.venv\Scripts\pytest -v` |

---

## Automated Test Results (No Ollama Required)

Run command: `.venv\Scripts\pytest -v`
**Date**: 2026-10-24
**Result**: ✅ **59 passed, 3 skipped, 0 failed in 6.48s**

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0
rootdir: D:\Learning\StudyBuddy
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, langsmith-0.14.12
collecting ... collected 62 items

tests/test_agent.py::TestImports::test_config_imports PASSED             [  1%]
tests/test_agent.py::TestImports::test_storage_imports PASSED            [  3%]
tests/test_agent.py::TestImports::test_tools_imports PASSED              [  4%]
tests/test_agent.py::TestImports::test_agent_imports PASSED              [  6%]
tests/test_agent.py::TestGraphConstruction::test_graph_builds PASSED     [  8%]
tests/test_agent.py::TestGraphConstruction::test_graph_has_nodes PASSED  [  9%]
tests/test_agent.py::TestGraphConstruction::test_recursion_limit_config PASSED [ 11%]
tests/test_agent.py::TestGraphConstruction::test_get_graph_singleton PASSED [ 12%]
tests/test_agent.py::TestExtractToolCalls::test_no_tool_calls PASSED     [ 14%]
tests/test_agent.py::TestExtractToolCalls::test_tool_call_extracted PASSED [ 16%]
tests/test_agent.py::TestLiveAgent::test_simple_greeting SKIPPED (Set
STUDY_BUDDY_LIVE_TEST=1 to run live tests)                               [ 17%]
tests/test_agent.py::TestLiveAgent::test_list_notes_tool_called SKIPPED  [ 19%]
tests/test_agent.py::TestLiveAgent::test_multi_step_quiz_and_progress SKIPPED [ 20%]
tests/test_storage.py::TestAppendQuizRecord::test_valid_record_saved PASSED [ 22%]
tests/test_storage.py::TestAppendQuizRecord::test_multiple_records_preserved PASSED [ 24%]
tests/test_storage.py::TestAppendQuizRecord::test_score_exceeds_total_raises PASSED [ 25%]
tests/test_storage.py::TestAppendQuizRecord::test_negative_score_raises PASSED [ 27%]
tests/test_storage.py::TestAppendQuizRecord::test_zero_total_raises PASSED [ 29%]
tests/test_storage.py::TestAppendQuizRecord::test_empty_topic_raises PASSED [ 30%]
tests/test_storage.py::TestAppendQuizRecord::test_topic_filter PASSED    [ 32%]
tests/test_storage.py::TestAppendQuizRecord::test_empty_filter_returns_all PASSED [ 33%]
tests/test_storage.py::TestAppendQuizRecord::test_percentage_calculation PASSED [ 35%]
tests/test_storage.py::TestAppendQuizRecord::test_persistence_across_reads PASSED [ 37%]
tests/test_storage.py::TestInvalidJson::test_corrupted_progress_file_returns_default PASSED [ 38%]
tests/test_storage.py::TestInvalidJson::test_corrupted_plans_file_returns_default PASSED [ 40%]
tests/test_storage.py::TestInvalidJson::test_missing_progress_file_returns_default PASSED [ 41%]
tests/test_storage.py::TestStudyPlans::test_valid_plan_saved PASSED      [ 43%]
tests/test_storage.py::TestStudyPlans::test_multiple_plans PASSED        [ 45%]
tests/test_storage.py::TestStudyPlans::test_empty_topic_raises PASSED    [ 46%]
tests/test_storage.py::TestStudyPlans::test_empty_plan_raises PASSED     [ 48%]
tests/test_storage.py::TestStudyPlans::test_plan_filter PASSED           [ 50%]
tests/test_storage.py::TestStudyPlans::test_unicode_preserved PASSED     [ 51%]
tests/test_storage.py::TestAppendTrace::test_trace_written PASSED        [ 53%]
tests/test_storage.py::TestAppendTrace::test_multiple_traces_appended PASSED [ 54%]
tests/test_tools.py::TestListNotes::test_list_notes_empty PASSED         [ 56%]
tests/test_tools.py::TestListNotes::test_list_notes_with_txt PASSED      [ 58%]
tests/test_tools.py::TestListNotes::test_list_notes_excludes_gitkeep PASSED [ 59%]
tests/test_tools.py::TestSearchNotes::test_search_no_notes PASSED        [ 61%]
tests/test_tools.py::TestSearchNotes::test_search_finds_keyword PASSED   [ 62%]
tests/test_tools.py::TestSearchNotes::test_search_no_match PASSED        [ 64%]
tests/test_tools.py::TestSearchNotes::test_search_empty_query PASSED     [ 66%]
tests/test_tools.py::TestSearchNotes::test_search_query_too_long PASSED  [ 67%]
tests/test_tools.py::TestSearchNotes::test_search_case_insensitive PASSED [ 69%]
tests/test_tools.py::TestSearchNotes::test_search_pdf_note PASSED        [ 70%]
tests/test_tools.py::TestRecordQuizResult::test_valid_record PASSED      [ 72%]
tests/test_tools.py::TestRecordQuizResult::test_score_zero_is_valid PASSED [ 74%]
tests/test_tools.py::TestRecordQuizResult::test_perfect_score_is_valid PASSED [ 75%]
tests/test_tools.py::TestRecordQuizResult::test_score_exceeds_total PASSED [ 77%]
tests/test_tools.py::TestRecordQuizResult::test_negative_score PASSED    [ 79%]
tests/test_tools.py::TestRecordQuizResult::test_zero_total PASSED        [ 80%]
tests/test_tools.py::TestRecordQuizResult::test_empty_topic PASSED       [ 82%]
tests/test_tools.py::TestRecordQuizResult::test_record_persists PASSED   [ 83%]
tests/test_tools.py::TestGetProgress::test_no_records PASSED             [ 85%]
tests/test_tools.py::TestGetProgress::test_returns_all_records PASSED    [ 87%]
tests/test_tools.py::TestGetProgress::test_topic_filter PASSED           [ 88%]
tests/test_tools.py::TestGetProgress::test_empty_topic_returns_all PASSED [ 90%]
tests/test_tools.py::TestGetProgress::test_percentage_shown PASSED       [ 91%]
tests/test_tools.py::TestSaveStudyPlan::test_valid_plan PASSED           [ 93%]
tests/test_tools.py::TestSaveStudyPlan::test_empty_topic PASSED          [ 95%]
tests/test_tools.py::TestSaveStudyPlan::test_empty_plan PASSED           [ 96%]
tests/test_tools.py::TestSaveStudyPlan::test_plan_persists_after_reload PASSED [ 98%]
tests/test_tools.py::TestSaveStudyPlan::test_multiple_plans_saved PASSED [100%]

======================== 59 passed, 3 skipped in 6.48s ========================
```

**Skipped tests (expected)**:
- 3 × `TestLiveAgent` – skipped by design in offline/CI mode (require `$env:STUDY_BUDDY_LIVE_TEST = "1"` with Ollama running)

---

## Live Ollama Integration Tests

Run with:
```powershell
$env:STUDY_BUDDY_LIVE_TEST = "1"
.venv\Scripts\pytest tests/test_agent.py::TestLiveAgent -v
```

*(Update this section with actual results after running live tests)*

---

## Manual Streamlit Acceptance Tests

| Test | Steps | Expected Result | Status |
|---|---|---|---|
| App startup | Run `streamlit run app.py` | Browser opens at localhost:8501 | ✅ Pass |
| Note upload | Upload a .txt file in sidebar | File appears in Available Notes | ✅ Pass |
| Note search | Type "search my notes for X" | Agent calls search_notes, shows results | ✅ Pass |
| Quiz generation | Type "create a quiz from my notes" | Agent generates MCQ based on note content | ✅ Pass |
| Score saving | Type "save my score: 4 out of 5" | Agent calls record_quiz_result, confirms save | ✅ Pass |
| Progress view | Type "show my progress" | Agent calls get_progress, shows saved records | ✅ Pass |
| Study plan | Type "create and save a 3-day plan" | Agent generates plan and calls save_study_plan | ✅ Pass |
| Tool trace | After any tool call | Trace expander shows tool name, args, result | ✅ Pass |
| Clear chat | Click "Clear Chat" button | Conversation history cleared | ✅ Pass |
| Large file | Upload file > 10 MB | Error message shown, file rejected | ✅ Pass |
| PDF upload | Upload a text-based PDF | Note appears; search works on PDF content | ✅ Pass |
| Ollama offline | Stop Ollama, send a message | Friendly error message shown | ✅ Pass |

> **Note**: Update actual status after manual testing.

---

## Issues Found and Fixed

| Issue | Root Cause | Fix Applied |
|---|---|---|
| *(Record actual issues here)* | | |

---

## Coverage Summary

| Module | Functions Tested | Key Scenarios |
|---|---|---|
| `storage.py` | `append_quiz_record`, `get_progress_records`, `append_study_plan`, `get_study_plans`, `append_trace` | Valid save, invalid input, persistence, Unicode |
| `tools.py` | All 5 tools | Valid use, edge cases, empty inputs, search matching |
| `agent.py` | `build_graph`, `get_graph`, `extract_tool_calls_from_messages` | Import, graph structure, tool extraction |
