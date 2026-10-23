"""
config.py – Centralised configuration for Study Buddy AI.

All paths are resolved relative to this file's directory so the app
works regardless of the terminal's current working directory.
"""

import os

# ── Project root ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Ollama / LLM settings ───────────────────────────────────────────────────
OLLAMA_MODEL = "llama3.2:latest"
OLLAMA_BASE_URL = "http://localhost:11434"
LLM_TEMPERATURE = 0.1          # Low temperature for factual study assistance
LLM_TIMEOUT = 120              # Seconds before raising a timeout error

# ── Notes directory ─────────────────────────────────────────────────────────
NOTES_DIR = os.path.join(BASE_DIR, "data", "notes")

# ── Persistent JSON storage ─────────────────────────────────────────────────
DATA_DIR        = os.path.join(BASE_DIR, "data")
PROGRESS_FILE   = os.path.join(DATA_DIR, "progress.json")
STUDY_PLANS_FILE = os.path.join(DATA_DIR, "study_plans.json")

# ── Logging / trace ─────────────────────────────────────────────────────────
LOGS_DIR        = os.path.join(BASE_DIR, "logs")
AGENT_TRACE_FILE = os.path.join(LOGS_DIR, "agent_trace.jsonl")

# ── Upload / search limits ───────────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB   = 10          # Maximum file upload size in megabytes
MAX_SEARCH_RESULTS   = 5           # Maximum number of passages returned
MAX_PASSAGE_CHARS    = 600         # Maximum characters per returned passage
MAX_QUERY_LENGTH     = 200         # Maximum characters in a search query
MAX_TOPIC_LENGTH     = 100         # Maximum characters in a topic string
MAX_PLAN_LENGTH      = 5000        # Maximum characters in a study plan

# ── LangGraph recursion safeguard ────────────────────────────────────────────
MAX_GRAPH_STEPS = 20               # Maximum nodes the graph may visit per run

# ── Allowed upload extensions ────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {".txt", ".pdf"}

# ── Ensure all required directories and default storage files exist ──────────
def ensure_directories() -> None:
    """Create required directories and default JSON files if absent."""
    for directory in [NOTES_DIR, LOGS_DIR, DATA_DIR]:
        os.makedirs(directory, exist_ok=True)

    # Create .gitkeep placeholders so git tracks empty directories
    for keep_path in [
        os.path.join(NOTES_DIR, ".gitkeep"),
        os.path.join(LOGS_DIR, ".gitkeep"),
    ]:
        if not os.path.exists(keep_path):
            with open(keep_path, "w") as f:
                f.write("")

    # Initialise JSON storage files with empty defaults
    _init_json(PROGRESS_FILE, {"records": []})
    _init_json(STUDY_PLANS_FILE, {"plans": []})


def _init_json(filepath: str, default: dict) -> None:
    """Write *default* to *filepath* only if the file does not exist."""
    if not os.path.exists(filepath):
        import json
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)


# Run once when the module is imported
ensure_directories()
