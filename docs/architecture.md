# Architecture – Study Buddy AI

## Overview

Study Buddy AI is a single-agent application built with LangGraph. It takes natural-language input from a student, reasons about which tools to use, executes those tools (real Python functions), and returns a grounded response.

All model inference runs locally via Ollama. No data leaves the student's machine.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    STUDENT (Browser)                     │
│                                                         │
│   Chat input  ◄──────────────────────  AI Response     │
│   Note Upload                           Progress View   │
│   Study Plan View                       Tool Trace      │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP (localhost:8501)
┌───────────────────────────▼─────────────────────────────┐
│                   STREAMLIT APP  (app.py)                │
│                                                         │
│  • Session state: conversation history                  │
│  • File uploader → data/notes/                          │
│  • Calls run_agent(user_message, history)               │
│  • Displays tool execution traces                       │
└───────────────────────────┬─────────────────────────────┘
                            │ Python function call
┌───────────────────────────▼─────────────────────────────┐
│               LANGGRAPH AGENT  (agent.py)                │
│                                                         │
│  ┌─────────┐   tool calls?   ┌──────────┐              │
│  │assistant│ ──── yes ──────►│  tools   │              │
│  │  node   │ ◄── results ────│  node    │              │
│  └────┬────┘                 └──────────┘              │
│       │ no tool calls                                   │
│       ▼                                                 │
│     END  (return final AIMessage)                       │
└───────────────────────────┬─────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌───────────────┐
│   Ollama     │  │   Python Tools   │  │  JSON Storage │
│ llama3.2     │  │   (tools.py)     │  │  (storage.py) │
│ localhost:   │  │                  │  │               │
│   11434      │  │  list_notes      │  │ progress.json │
│              │  │  search_notes    │  │ study_plans   │
│ Temperature: │  │  record_quiz     │  │   .json       │
│   0.1        │  │  get_progress    │  │               │
│              │  │  save_study_plan │  │ agent_trace   │
└──────────────┘  └──────────────────┘  │   .jsonl      │
                                        └───────────────┘
```

---

## LangGraph State

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

The state holds **only one field**: the conversation messages. `add_messages` is a LangGraph reducer that **appends** new messages rather than replacing the list. This ensures the full conversation and all tool results are preserved across multiple graph iterations.

---

## Graph Nodes

### 1. `assistant` Node

- **Input**: Current `AgentState` (all messages so far)
- **Action**: Prepends the system prompt, calls `ChatOllama.invoke()` with the messages
- **Output**: An `AIMessage` (with or without `tool_calls`)
- **Error handling**: If the LLM call fails, returns a user-friendly error `AIMessage`

### 2. `tools` Node

- **Type**: LangGraph built-in `ToolNode`
- **Input**: The last `AIMessage` which contains `tool_calls`
- **Action**: Executes each requested tool function with the provided arguments
- **Output**: One `ToolMessage` per tool call, containing the tool's return value
- **Note**: Tool results are real Python function return values, never fabricated

---

## Routing

```python
graph_builder.add_conditional_edges(
    "assistant",
    tools_condition,  # LangGraph built-in
)
```

`tools_condition` checks the last message in state:
- If it has `.tool_calls` → route to `"tools"` node
- Otherwise → route to `END`

After the tools node runs, it always returns to `"assistant"` so the LLM can incorporate the results.

---

## Execution Loop

```
START
  │
  ▼
[assistant] ──tool_calls?──► [tools] ──► [assistant] ──tool_calls?──► ...
  │
  no tool calls
  │
  ▼
END
```

The loop is bounded by `recursion_limit=MAX_GRAPH_STEPS` (default: 20). This prevents infinite loops even if the model keeps requesting tool calls.

---

## Tool Trace Logging

Every tool call requested by the model is recorded in `logs/agent_trace.jsonl`:

```json
{"timestamp": "2025-01-01T10:00:00Z", "node": "assistant", "event": "tool_call_requested", "tool_name": "search_notes", "args": {"query": "Python functions"}}
```

The Streamlit UI also extracts and displays tool traces from the LangChain message objects after each agent turn.

---

## Data Flow (Multi-Step Example)

**User**: "Search my Python notes and save my quiz score of 4/5."

```
1. HumanMessage → assistant node
2. LLM decides to call search_notes(query="Python")
3. → tools node → search_notes() → reads data/notes/*.txt, *.pdf
4. ToolMessage(content="Found: Variables, Functions...") → assistant node
5. LLM incorporates results, decides to call record_quiz_result(topic, 4, 5)
6. → tools node → record_quiz_result() → writes data/progress.json
7. ToolMessage(content="✅ Saved!") → assistant node
8. LLM generates final response (no more tool calls)
9. → END → reply returned to Streamlit
```

---

## Configuration

All configurable values live in `config.py`:

| Setting | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.2:latest` | LLM model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `LLM_TEMPERATURE` | `0.1` | Low = more factual responses |
| `MAX_GRAPH_STEPS` | `20` | Recursion limit (loop guard) |
| `MAX_UPLOAD_SIZE_MB` | `10` | File size limit |
| `MAX_SEARCH_RESULTS` | `5` | Search passage limit |
| `MAX_PASSAGE_CHARS` | `600` | Max chars per passage |
| `MAX_QUERY_LENGTH` | `200` | Max search query length |

---

## File Dependency Map

```
app.py
 ├── agent.py      (run_agent, extract_tool_calls_from_messages)
 │     ├── tools.py         (ALL_TOOLS)
 │     │     ├── config.py
 │     │     └── storage.py
 │     ├── config.py
 │     └── storage.py       (append_trace)
 └── storage.py    (get_progress_records, get_study_plans)
```

---

## Security Design

- Uploaded files are saved as binary data only — never executed.
- Note contents are passed to the LLM as user-role context, not system prompt injections.
- Tool functions validate all inputs before use.
- Directory traversal is prevented by `os.path.basename()` on uploaded filenames.
- No external network calls are made (except to `localhost:11434` for Ollama).
