"""
tests/test_ui.py – Unit tests for Study Buddy AI user interface helpers.

Tests cover:
  • parse_quiz_questions with diverse question/answer formats.
  • _safe_filename security sanitisation.
  • _extract_quiz_topic extraction.
  • _on_quiz_option_toggle single-selection logic.
"""

import streamlit as st
import pytest

from app import (
    _extract_quiz_topic,
    _on_quiz_option_toggle,
    _safe_filename,
    parse_quiz_questions,
)


class TestQuizParsing:

    def test_parse_standard_numbered_quiz(self):
        text = (
            "Here is a quiz on Python Basics:\n\n"
            "1. What is the file extension for Python files?\n"
            "A) .pt\n"
            "B) .py\n"
            "C) .python\n"
            "D) .pyt\n\n"
            "2. Which keyword is used to define a function?\n"
            "A) func\n"
            "B) def\n"
            "C) function\n"
            "D) define\n\n"
            "Answers:\n"
            "1. B\n"
            "2. B\n"
        )
        intro, qs = parse_quiz_questions(text)
        assert len(qs) == 2
        assert qs[0]["num"] == 1
        assert "extension" in qs[0]["question"].lower()
        assert len(qs[0]["options"]) == 4
        assert qs[0]["answer"] == "B"

        assert qs[1]["num"] == 2
        assert qs[1]["answer"] == "B"

    def test_parse_markdown_quiz(self):
        text = (
            "### Python Practice\n\n"
            "**1. Which structure is mutable?**\n"
            "- A) List\n"
            "- B) Tuple\n"
            "- C) String\n"
            "- D) Integer\n\n"
            "**Answers:**\n"
            "1. A\n"
        )
        intro, qs = parse_quiz_questions(text)
        assert len(qs) == 1
        assert qs[0]["num"] == 1
        assert "mutable" in qs[0]["question"].lower()
        assert qs[0]["answer"] == "A"

    def test_parse_single_question_inline(self):
        text = (
            "What is 2 + 2?\n"
            "A) 3\n"
            "B) 4\n"
            "C) 5\n"
            "D) 6\n\n"
            "Answer Key: 1 - B"
        )
        intro, qs = parse_quiz_questions(text)
        assert len(qs) == 1
        assert qs[0]["num"] == 1
        assert qs[0]["answer"] == "B"

    def test_parse_non_quiz_text_returns_empty(self):
        text = "Python was created by Guido van Rossum and released in 1991."
        intro, qs = parse_quiz_questions(text)
        assert qs == []
        assert intro == text

    def test_parse_quiz_with_inline_answers(self):
        text = (
            "1. What is the keyword for function?\n"
            "A) func\n"
            "B) def\n"
            "C) define\n"
            "D) lambda\n"
            "Answer: B\n\n"
            "2. What is the extension for python?\n"
            "A) .pt\n"
            "B) .py\n"
            "C) .pyt\n"
            "D) .p\n"
            "Answer: B"
        )
        intro, qs = parse_quiz_questions(text)
        assert len(qs) == 2
        assert qs[0]["answer"] == "B"
        assert qs[1]["answer"] == "B"

    def test_parse_quiz_comma_answers(self):
        text = (
            "1. First?\n"
            "A) Alpha\n"
            "B) Beta\n"
            "C) Gamma\n"
            "D) Delta\n\n"
            "2. Second?\n"
            "A) One\n"
            "B) Two\n"
            "C) Three\n"
            "D) Four\n\n"
            "Answers: C, A"
        )
        intro, qs = parse_quiz_questions(text)
        assert len(qs) == 2
        assert qs[0]["answer"] == "C"
        assert qs[1]["answer"] == "A"

    def test_safe_filename(self):
        assert _safe_filename("../../etc/passwd.txt") == "passwd.txt"
        assert _safe_filename("my note!#$%.pdf") == "my note____.pdf"
        assert _safe_filename("...").endswith("upload") or _safe_filename("...") == "upload"

    def test_extract_quiz_topic(self):
        assert _extract_quiz_topic("", "Quiz me on Python Basics") == "Python Basics"
        assert _extract_quiz_topic("Quiz on Chapter 01", "") == "Chapter 01"
        assert _extract_quiz_topic("Here is a quiz on Python. It looks like the search found notes.") == "Python"
        assert _extract_quiz_topic("It seems like the note python_basics.txt contains info.", "Quiz me on Python") == "Python"
        assert isinstance(_extract_quiz_topic("Hello there", "Just chat"), str)


class TestQuizSingleSelectToggle:

    def test_single_selection_enforcement(self):
        msg_idx = 0
        q_idx = 0
        total_opts = 4

        # Initialise state: simulate user clicking option 1 (index 1)
        st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_1"] = True
        st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_0"] = False
        st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_2"] = False
        st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_3"] = False

        _on_quiz_option_toggle(msg_idx, q_idx, clicked_idx=1, total_opts=total_opts)
        assert st.session_state[f"quiz_sel_{msg_idx}_{q_idx}"] == 1

        # Now simulate user clicking option 2 (index 2)
        st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_2"] = True
        _on_quiz_option_toggle(msg_idx, q_idx, clicked_idx=2, total_opts=total_opts)

        assert st.session_state[f"quiz_sel_{msg_idx}_{q_idx}"] == 2
        # Verify previous selection 1 was unchecked
        assert st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_1"] is False
        assert st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_0"] is False
        assert st.session_state[f"quiz_chk_{msg_idx}_{q_idx}_3"] is False
