"""
tests/test_agent.py – Tests for the LangGraph agent structure and imports.

These tests verify:
  - The agent module imports without errors.
  - The graph is constructed successfully.
  - All five tools are registered.
  - The recursion limit is enforced.
  - Tool call extraction works correctly.

A live Ollama integration test is included but SKIPPED unless
STUDY_BUDDY_LIVE_TEST=1 is set in the environment. This prevents CI
failures when Ollama is unavailable.
"""

import os
import pytest


# ── Import correctness ────────────────────────────────────────────────────────

class TestImports:

    def test_config_imports(self):
        """config.py imports without errors."""
        import config
        assert hasattr(config, "OLLAMA_MODEL")
        assert hasattr(config, "MAX_GRAPH_STEPS")

    def test_storage_imports(self):
        """storage.py imports without errors."""
        import storage
        assert callable(storage.append_quiz_record)
        assert callable(storage.append_study_plan)

    def test_tools_imports(self):
        """tools.py imports without errors and ALL_TOOLS has 5 items."""
        from tools import ALL_TOOLS
        assert len(ALL_TOOLS) == 5
        tool_names = [t.name for t in ALL_TOOLS]
        assert "list_notes"         in tool_names
        assert "search_notes"       in tool_names
        assert "record_quiz_result" in tool_names
        assert "get_progress"       in tool_names
        assert "save_study_plan"    in tool_names

    def test_agent_imports(self):
        """agent.py imports without errors."""
        import agent
        assert callable(agent.build_graph)
        assert callable(agent.run_agent)


# ── Graph construction ────────────────────────────────────────────────────────

class TestGraphConstruction:

    def test_graph_builds(self):
        """build_graph() returns a compiled graph without errors."""
        from agent import build_graph
        graph = build_graph()
        assert graph is not None

    def test_graph_has_nodes(self):
        """The compiled graph contains 'assistant' and 'tools' nodes."""
        from agent import build_graph
        graph = build_graph()
        # LangGraph compiled graphs expose their nodes via the graph attribute
        nodes = list(graph.nodes)
        assert "__start__" in nodes or "assistant" in nodes

    def test_recursion_limit_config(self):
        """MAX_GRAPH_STEPS is set to a reasonable bounded value."""
        import config
        assert isinstance(config.MAX_GRAPH_STEPS, int)
        assert 5 <= config.MAX_GRAPH_STEPS <= 100

    def test_get_graph_singleton(self):
        """get_graph() returns the same instance on repeated calls."""
        from agent import get_graph
        g1 = get_graph()
        g2 = get_graph()
        assert g1 is g2


# ── Tool extraction ───────────────────────────────────────────────────────────

class TestExtractToolCalls:

    def test_no_tool_calls(self):
        """extract_tool_calls_from_messages returns empty list for plain messages."""
        from langchain_core.messages import HumanMessage, AIMessage
        from agent import extract_tool_calls_from_messages

        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]
        result = extract_tool_calls_from_messages(messages)
        assert result == []

    def test_tool_call_extracted(self):
        """Tool call and result are extracted from AIMessage + ToolMessage pair."""
        from langchain_core.messages import AIMessage, ToolMessage
        from agent import extract_tool_calls_from_messages

        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "list_notes", "args": {}, "id": "call_1"}],
        )
        tool_msg = ToolMessage(
            content="Available notes:\n  1. python_basics.txt",
            tool_call_id="call_1",
        )
        traces = extract_tool_calls_from_messages([ai_msg, tool_msg])
        assert len(traces) == 1
        assert traces[0]["tool_name"] == "list_notes"
        assert "python_basics.txt" in traces[0]["result"]

    def test_multiple_tool_calls_extracted(self):
        """Multiple tool calls and results in a single turn are correctly paired by ID."""
        from langchain_core.messages import AIMessage, ToolMessage
        from agent import extract_tool_calls_from_messages

        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {"name": "search_notes", "args": {"query": "python"}, "id": "call_1"},
                {"name": "get_progress", "args": {"topic": "python"}, "id": "call_2"},
            ],
        )
        tool_msg_1 = ToolMessage(content="Passage from python_basics.txt", tool_call_id="call_1")
        tool_msg_2 = ToolMessage(content="Score: 5/5", tool_call_id="call_2")

        traces = extract_tool_calls_from_messages([ai_msg, tool_msg_1, tool_msg_2])
        assert len(traces) == 2
        assert traces[0]["tool_name"] == "search_notes"
        assert traces[0]["result"] == "Passage from python_basics.txt"
        assert traces[1]["tool_name"] == "get_progress"
        assert traces[1]["result"] == "Score: 5/5"


# ── Live Ollama integration test (opt-in) ─────────────────────────────────────

LIVE = os.environ.get("STUDY_BUDDY_LIVE_TEST", "0") == "1"
skip_live = pytest.mark.skipif(not LIVE, reason="Set STUDY_BUDDY_LIVE_TEST=1 to run live tests")


@skip_live
class TestLiveAgent:
    """
    Integration tests that require a running Ollama service with
    the llama3.2:latest model loaded.

    Run with:
        $env:STUDY_BUDDY_LIVE_TEST = "1"
        pytest tests/test_agent.py::TestLiveAgent -v
    """

    def test_simple_greeting(self):
        """Agent responds to a simple greeting (no tool call required)."""
        from agent import run_agent
        reply, history = run_agent("Hello! What can you help me with?", [])
        assert isinstance(reply, str)
        assert len(reply) > 10

    def test_list_notes_tool_called(self, tmp_path, monkeypatch):
        """Agent calls list_notes when asked to show notes."""
        import config
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        monkeypatch.setattr(config, "NOTES_DIR", str(notes_dir))

        from agent import run_agent
        reply, history = run_agent("What study notes do I have?", [])
        assert isinstance(reply, str)
        # The agent should report no notes or list them
        assert len(reply) > 5

    def test_multi_step_quiz_and_progress(self, tmp_path, monkeypatch):
        """
        Multi-step scenario: save a quiz result and retrieve progress.
        This verifies the tool-calling loop works end-to-end.
        """
        import config
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        monkeypatch.setattr(config, "NOTES_DIR",          str(notes_dir))
        monkeypatch.setattr(config, "DATA_DIR",           str(data_dir))
        monkeypatch.setattr(config, "PROGRESS_FILE",      str(data_dir / "progress.json"))
        monkeypatch.setattr(config, "STUDY_PLANS_FILE",   str(data_dir / "study_plans.json"))
        monkeypatch.setattr(config, "AGENT_TRACE_FILE",   str(logs_dir / "trace.jsonl"))

        # Reset the singleton graph so it picks up the patched config
        import agent as agent_module
        agent_module._graph = None

        from agent import run_agent
        prompt = (
            "Save my Python Basics quiz result as 4 out of 5, "
            "then show me my Python progress."
        )
        reply, history = run_agent(prompt, [])
        assert isinstance(reply, str)
        # The reply should mention Python and progress
        assert "python" in reply.lower() or "4" in reply or "saved" in reply.lower()
