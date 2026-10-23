# Viva Questions & Answers – Study Buddy AI

Beginner-friendly answers to common examination and viva questions.

---

## 1. What is an AI agent?

An AI agent is a program that can **perceive** its environment (e.g., a user's question), **reason** about what to do, **take actions** (e.g., call a tool), and **produce a result** — possibly across multiple steps.

Unlike a simple chatbot that only generates text, an AI agent can:
- Decide which tools to use
- Execute those tools
- Use the results to form a better answer

In Study Buddy AI, the agent reads a student's question, decides whether to search notes, save a score, or retrieve progress, then returns a grounded answer.

---

## 2. Why use LangGraph?

LangGraph makes it easy to build agents that follow a **graph of steps** — like a flowchart. It handles:
- **State management**: keeping track of the conversation and tool results
- **Conditional routing**: deciding "did the model want to call a tool, or is it done?"
- **Loop safety**: enforcing a recursion limit so the agent cannot run forever

Without LangGraph, we would have to manually write the loop, state updates, and routing logic.

---

## 3. Why use Ollama?

Ollama lets us run large language models **locally on our own computer**. This means:
- **No internet required** — the app works offline
- **No API costs** — we are not paying per token
- **Privacy** — student notes never leave the machine
- **Easy model management** — `ollama pull llama3.2` downloads the model; `ollama serve` starts it

---

## 4. What is tool calling?

Tool calling (also called "function calling") is a feature of some LLMs where the model can output a structured **request to call a Python function** instead of just writing text.

For example, when the user says *"search my notes for Python functions"*, the LLM outputs:
```json
{"name": "search_notes", "args": {"query": "Python functions"}}
```

LangGraph then **executes** the real `search_notes()` Python function and feeds the result back to the model, which uses it to write a helpful response.

---

## 5. What is a graph state?

The **graph state** is a Python dictionary (`AgentState`) that is passed through every node in the LangGraph workflow. It holds:
```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```

`messages` contains the entire conversation history — human messages, AI responses, and tool results. Every node can read from and add to the state. The `add_messages` reducer ensures new messages are **appended**, not replaced.

---

## 6. What does conditional routing do?

Conditional routing means the graph decides **which node to visit next** based on the current state, rather than always following a fixed path.

In our agent:
```
assistant node → tools_condition →
    if tool_calls present  → tools node
    if no tool_calls       → END
```

The built-in `tools_condition` function checks the last message. If the LLM requested tools, it routes to the tools node. When the LLM is finished, it routes to END. This creates a natural question → think → act → answer loop.

---

## 7. What is the purpose of ToolNode?

`ToolNode` is a LangGraph built-in that:
1. Reads the `tool_calls` from the last `AIMessage`
2. Finds the matching Python function from our registered tools
3. Calls the function with the arguments the LLM provided
4. Returns the function's output as a `ToolMessage`

We pass `ALL_TOOLS = [list_notes, search_notes, ...]` to `ToolNode`, which handles all the dispatch automatically.

---

## 8. How does the tool result return to the LLM?

After `ToolNode` executes a tool, it adds a `ToolMessage` to the state:

```
State.messages = [
    HumanMessage("Search my notes for Python functions"),
    AIMessage(tool_calls=[{"name": "search_notes", "args": {...}}]),
    ToolMessage(content="Found: Variables store data..."),  ← added by ToolNode
]
```

The graph then routes back to the `assistant` node. The LLM receives **all** messages including the `ToolMessage`, so it sees the search result and can generate a grounded response.

---

## 9. Why use JSON storage?

JSON (JavaScript Object Notation) files are:
- **Simple** — easy to read and write in Python with the built-in `json` module
- **Human-readable** — you can open the file in any text editor
- **Persistent** — data survives after the app restarts
- **Portable** — no database server required

For this assignment, JSON files are sufficient. A production app might use SQLite or a proper database.

---

## 10. What is persistent storage?

Persistent storage means data is **saved to disk** so it survives when the program stops and restarts.

In Study Buddy AI:
- Quiz results are saved to `data/progress.json`
- Study plans are saved to `data/study_plans.json`

When the app starts, it reads these files, so the student's history is always available even after closing and reopening the browser.

---

## 11. How does note searching work?

Note searching uses **keyword matching** (not AI/semantic search):

1. Split the query into individual words (e.g., "Python functions" → ["python", "functions"])
2. Read each note file (TXT: read as text; PDF: extract text with PyPDF)
3. Split the note into sentence-like passages
4. Check if any passage contains any query keyword (case-insensitive)
5. Return matching passages with the source filename

This approach is simple, fast, and requires no vector database or embedding model.

---

## 12. How does the agent perform a multi-step task?

Example: *"Search my Python notes and save my quiz score of 4/5"*

```
Turn 1:
  Human → "Search my Python notes and save quiz score 4/5"
  LLM   → tool_call: search_notes(query="Python")
  Tool  → Returns relevant passages from notes
  LLM   → tool_call: record_quiz_result(topic="Python", score=4, total=5)
  Tool  → Saves to progress.json, returns "✅ Saved!"
  LLM   → Final response: "I found X in your notes and saved your score."
```

The loop runs up to `MAX_GRAPH_STEPS` times. Each iteration, the LLM sees all previous tool results and decides whether to call another tool or provide the final answer.

---

## 13. How is the execution trace generated?

The execution trace is recorded in two ways:

**1. `storage.append_trace()` calls in agent.py**:
Every time the LLM requests a tool call, a JSON entry is written to `logs/agent_trace.jsonl`:
```json
{"timestamp": "...", "node": "assistant", "event": "tool_call_requested", "tool_name": "search_notes"}
```

**2. Streamlit extraction from messages**:
After the graph finishes, `extract_tool_calls_from_messages()` reads the LangChain `AIMessage` and `ToolMessage` objects to extract tool names, arguments, and results — which are then displayed in the UI expander.

---

## 14. How are errors handled?

| Error Situation | Handling |
|---|---|
| Ollama not running | Assistant node catches the exception, returns a friendly error message |
| Invalid tool arguments | Tool functions raise `ValueError`; the tool returns `"❌ Error: ..."` |
| Missing notes directory | `list_notes` returns "No notes available" |
| Corrupted JSON file | `storage._read_json()` returns the default empty structure |
| PDF with no text (scanned) | Returns empty string; search reports no extractable text |
| Agent loop limit exceeded | LangGraph raises `RecursionError`, caught in `run_agent()` |

---

## 15. What are the limitations of this project?

1. **Keyword search**: Cannot find synonyms or semantically related content (e.g., "code" won't find "programming").
2. **No OCR**: Scanned image PDFs cannot be searched.
3. **Tool-calling reliability**: Llama 3.2 may not always call tools reliably for complex or ambiguous requests.
4. **Session history only**: Conversation history resets when the Streamlit app restarts.
5. **Single user**: No authentication; all data is shared if multiple users access the same machine.
6. **Local resources**: Large PDFs or many notes may slow down searches.
7. **No embedding search**: This is intentional simplicity, not a limitation of the architecture.

---

## Demo Script (3–5 minutes)

### Step 1: Start the Application (30 sec)
```powershell
.venv\Scripts\Activate.ps1
streamlit run app.py
```
Show the browser interface.

### Step 2: Upload a Note (30 sec)
- Click "Browse files" in the sidebar
- Upload a Python notes `.txt` file
- Show it appearing in the "Available Notes" list

### Step 3: Search the Note (45 sec)
Type in chat: *"Search my uploaded notes for information about functions"*
- Point out the tool trace expander showing `search_notes` was called
- Show the agent's grounded response

### Step 4: Generate a Quiz (45 sec)
Type: *"Create 3 multiple-choice questions based on those search results"*
- Show the AI generating questions from the actual note content

### Step 5: Save a Quiz Score (30 sec)
Type: *"Save my score: I got 2 out of 3 correct on the Functions quiz"*
- Show the `record_quiz_result` tool call in the trace
- Show the success confirmation

### Step 6: View Progress (30 sec)
Type: *"Show my saved quiz progress"*
- Show `get_progress` tool call and the saved result

### Step 7: Create and Save a Study Plan (30 sec)
Type: *"Create a 3-day study plan for Python functions and save it"*
- Show `save_study_plan` call and the sidebar updating with the new plan

### Step 8: Show Data Persistence (30 sec)
- Open `data/progress.json` in VS Code
- Show the saved quiz record with timestamp
- Mention that this survives a restart
