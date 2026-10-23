# Study Buddy AI 📚

A **local-first AI tutoring application** that helps students learn from their own study notes using a locally installed LLM (Ollama + Llama 3.2). Built with LangGraph, LangChain, and Streamlit — **no internet or paid API required**.

---

## Problem Statement

Students often have large collections of study notes but struggle to:
- Quickly find and review key concepts.
- Test their knowledge effectively.
- Build structured revision plans.
- Track their quiz performance over time.

Study Buddy AI solves this by providing an intelligent, interactive tutor that works **entirely offline** using the student's own uploaded notes.

---

## Features

| Feature | Description |
|---|---|
| 📄 Note Uploads | Upload TXT and PDF notes via the web interface |
| 🔍 Note Search | Keyword-based search across all uploaded notes |
| 🤖 AI Tutoring | Conversational tutoring grounded in your notes |
| ❓ Quiz Generation | Multiple-choice quizzes based on note content |
| 📊 Progress Tracking | Save and retrieve quiz scores persistently |
| 📅 Study Plans | Generate and save day-by-day revision plans |
| 🔄 Multi-step Tasks | Agent performs multiple tool calls autonomously |
| 📝 Execution Trace | See exactly which tools the agent called |
| 🔒 Local-only | All inference runs on your machine via Ollama |

---

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM | Ollama (`llama3.2:latest`) |
| Agent Framework | LangGraph |
| LLM Integration | LangChain Core + langchain-ollama |
| User Interface | Streamlit |
| PDF Reading | PyPDF |
| Data Storage | JSON files |
| Testing | pytest |

---

## System Requirements

- **OS**: Windows 10 / 11 (also works on macOS / Linux)
- **RAM**: 8 GB minimum, 16 GB recommended
- **Disk**: 3 GB free (for the Llama 3.2 model)
- **Python**: 3.10 or higher
- **Ollama**: Installed and running

---

## Installation (Windows)

### 1. Verify Prerequisites

```powershell
# Check Python version (must be 3.10+)
python --version

# Check Ollama is installed and llama3.2 is available
ollama list
```

Expected output should include `llama3.2:latest`.

### 2. Clone / Download the Project

```powershell
cd d:\Learning
# If using git:
git clone <repo-url> StudyBuddy
cd StudyBuddy

# Or if you already have the files, just navigate here:
cd d:\Learning\StudyBuddy
```

### 3. Create and Activate Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> **Note**: If PowerShell blocks the script, run:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Verify Ollama is Running

```powershell
# In a separate terminal window:
ollama serve

# Verify the model is available:
ollama list
```

You should see `llama3.2:latest` in the list.

### 6. Start the Application

```powershell
# Make sure .venv is active, then:
streamlit run app.py
```

The browser will open automatically at `http://localhost:8501`.

---

## Quick Start

1. **Upload a note**: In the sidebar, click "Browse files" and upload a `.txt` or `.pdf` file.
2. **Ask a question**: Type in the chat box, e.g.:
   - *"What topics are covered in my Python notes?"*
   - *"Search my notes for information about functions"*
   - *"Create a quiz based on my uploaded notes"*
   - *"Save my Python Basics quiz result: 4 out of 5"*
   - *"Show my progress"*
   - *"Create and save a 3-day study plan for Python"*

---

## Example Prompts

```
List all my study notes
Search my notes for information about recursion
Summarise the key concepts from my Python notes
Create 5 multiple-choice questions based on my notes
Save my Data Structures quiz result: 7 out of 10
Show me my Python progress
Create a 3-day revision plan for Python and save it
```

---

## Project Structure

```
study-buddy-agent/
│
├── app.py              ← Streamlit user interface
├── agent.py            ← LangGraph agent workflow
├── tools.py            ← Five study tools (list, search, quiz, progress, plan)
├── storage.py          ← JSON storage helpers
├── config.py           ← Centralised configuration
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
├── .gitignore          ← Git exclusions
├── pytest.ini          ← Test configuration
│
├── data/
│   ├── notes/          ← Uploaded study notes (TXT, PDF)
│   ├── progress.json   ← Saved quiz results
│   └── study_plans.json ← Saved study plans
│
├── logs/
│   └── agent_trace.jsonl ← Tool execution trace log
│
├── tests/
│   ├── test_tools.py   ← Tool unit tests
│   ├── test_storage.py ← Storage unit tests
│   └── test_agent.py   ← Agent/graph tests (+ live integration)
│
└── docs/
    ├── architecture.md ← System design and graph description
    ├── test_results.md ← Actual test outcomes
    ├── report.md       ← Assignment report draft
    └── viva_questions.md ← Exam preparation
```

---

## Agent Architecture

```
Student
  │
  ▼
[Streamlit UI]  ──────── chat input, note upload, progress viewer
  │
  ▼
[LangGraph Agent]
  │
  ├─► [assistant node]  ← ChatOllama (llama3.2)
  │         │
  │    tool_calls?
  │         │
  │    yes  ▼
  │   [tools node]  ──► list_notes / search_notes / record_quiz_result
  │         │                   get_progress / save_study_plan
  │         │
  │    tool results returned
  │         │
  │    ◄────┘  (loop until no more tool calls)
  │
  └─► Final AI response
  │
  ▼
[JSON Storage]   data/progress.json, data/study_plans.json
[Trace Log]      logs/agent_trace.jsonl
```

---

## Tools Reference

| Tool | Purpose | Inputs |
|---|---|---|
| `list_notes` | List available study notes | None |
| `search_notes` | Keyword search in TXT/PDF notes | `query: str` |
| `record_quiz_result` | Save quiz score | `topic, score, total` |
| `get_progress` | Retrieve quiz history | `topic (optional)` |
| `save_study_plan` | Persist a study plan | `topic, plan` |

---

## Data Storage

- **`data/progress.json`** – Array of quiz records with topic, score, total, percentage, and timestamp.
- **`data/study_plans.json`** – Array of saved plans with topic, plan text, and timestamp.
- **`logs/agent_trace.jsonl`** – JSON Lines file recording every tool call and agent step.

All data is stored locally. Nothing is sent to external servers.

---

## Running Tests

```powershell
# Activate virtual environment first
.venv\Scripts\Activate.ps1

# Run all automated tests (no Ollama required)
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_tools.py -v
pytest tests/test_storage.py -v
pytest tests/test_agent.py -v

# Run live Ollama integration tests (requires running Ollama)
$env:STUDY_BUDDY_LIVE_TEST = "1"
pytest tests/test_agent.py::TestLiveAgent -v
```

---

## Troubleshooting

### "Connection refused" or Ollama error
```powershell
# Start Ollama in a separate terminal
ollama serve
# Then restart the Streamlit app
```

### Model not found
```powershell
ollama pull llama3.2
```

### PowerShell execution policy error
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Import errors
```powershell
# Make sure venv is activated
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### PDF shows no text
Some PDFs are scanned images — PyPDF cannot extract text from them. Use a text-based PDF or a TXT file instead.

---

## Known Limitations

1. **Keyword search only** – Not semantic/vector search. Exact keyword matches required.
2. **No OCR** – Scanned image PDFs are not supported.
3. **Llama 3.2 tool calling** – The model's tool-calling reliability depends on prompt phrasing. Complex multi-step tasks may occasionally require rephrasing.
4. **Single session history** – Conversation history is reset when the app restarts.
5. **No authentication** – Not suitable for multi-user deployment.

---

## Group Contribution Table

| Member | Student ID | Responsibilities | Tasks Completed |
|---|---|---|---|
| [Name A] | [ID] | Tools, storage, tests | tools.py, storage.py, test_tools.py, test_storage.py |
| [Name B] | [ID] | LangGraph agent, integration | agent.py, test_agent.py |
| [Name C] | [ID] | Streamlit UI, documentation | app.py, README.md, docs/ |

*Fill in actual names, IDs, and completed tasks before submission.*

---

## AI Tool Usage Disclosure

This project was developed with the assistance of Google Antigravity (AI coding assistant) for:
- Initial code scaffolding and structure.
- Documentation templates.

All code was reviewed, tested, and verified by the team. The AI did not replace human understanding of the implementation.

---

## Git Setup

```powershell
git init
git add .
git commit -m "Initial Study Buddy AI implementation"
git remote add origin <your-repo-url>
git push -u origin main
```

> ⚠️ The `.gitignore` excludes personal notes, quiz data, logs, and the virtual environment.
