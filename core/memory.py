import json
import os
from typing import Any, Dict, List, Optional

# Memory file lives under data/
_MEMORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "memory.json"))
_MAX_TURNS = 5


def _default_state() -> Dict[str, Any]:
    return {
        "turns": [],
        "last_intent": None,
        "last_filename": None,
        "last_content": None,
        "last_answer": None,
        "pending_intent": None,
        "pending_filename": None,
        "pending_content": None,
        "pending_include_ctx": None,
    }


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_state() -> Dict[str, Any]:
    """Load memory from disk; fall back to defaults on any issue."""
    path = _MEMORY_FILE
    if not os.path.exists(path):
        return _default_state()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):  # defensive against corruption
            raise ValueError("memory json is not a dict")
    except Exception:
        return _default_state()

    state = _default_state()
    state.update({k: data.get(k, v) for k, v in state.items()})
    # ensure turns is a list
    if not isinstance(state.get("turns"), list):
        state["turns"] = []
    return state


def save_state(state: Dict[str, Any]) -> None:
    """Persist memory to disk."""
    _ensure_dir(_MEMORY_FILE)
    with open(_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def resolve_filename(state: Dict[str, Any], candidate: Optional[str]) -> Optional[str]:
    """Pick candidate filename or fall back to last remembered filename."""
    return candidate or state.get("last_filename")


def _trim_text(text: Optional[str], limit: int = 400) -> Optional[str]:
    if text is None:
        return None
    return text if len(text) <= limit else text[:limit] + "..."


def record_turn(command: str, nlu_result: Any, outcome: Optional[str]) -> None:
    """Append a turn and update last_* pointers, then persist."""
    state = load_state()

    turn = {
        "command": _trim_text(command),
        "type": getattr(nlu_result, "type", None),
        "intent": getattr(nlu_result, "intent", None),
        "filename": getattr(nlu_result, "filename", None),
        "content": _trim_text(getattr(nlu_result, "content", None)),
        "outcome": _trim_text(outcome),
    }
    state["turns"].append(turn)
    state["turns"] = state["turns"][-_MAX_TURNS:]

    intent = getattr(nlu_result, "intent", None)
    filename = getattr(nlu_result, "filename", None)
    content = getattr(nlu_result, "content", None)

    if intent:
        state["last_intent"] = intent
    if filename:
        state["last_filename"] = filename
    if content:
        state["last_content"] = content
    if getattr(nlu_result, "type", None) == "ANSWER" and outcome:
        state["last_answer"] = outcome

    save_state(state)


def get_recent_context(state: Optional[Dict[str, Any]] = None, window: int = _MAX_TURNS) -> List[Dict[str, Any]]:
    """Return the most recent turns for prompt injection."""
    state = state or load_state()
    return list(state.get("turns", []))[-window:]


def build_context_hint(state: Optional[Dict[str, Any]] = None, window: int = _MAX_TURNS) -> Optional[str]:
    """Format recent turns into a compact hint for NLU."""
    state = state or load_state()
    turns = get_recent_context(state, window)
    if not turns:
        return None

    lines: List[str] = ["Recent assistant context (most recent last):"]
    for t in turns:
        line = f"- cmd: {t.get('command')} | type: {t.get('type')} | intent: {t.get('intent')} | file: {t.get('filename')} | outcome: {t.get('outcome')}"
        lines.append(line)
    last_answer = state.get("last_answer")
    if last_answer:
        lines.append(f"- last_answer: {last_answer}")
    return "\n".join(lines)


