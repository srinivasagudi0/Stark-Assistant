import json
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI
from stark_assistant.config import settings
from stark_assistant.core import memory


# -------------------------------------------------
# Unified NLU Result (lives HERE, by design)
# -------------------------------------------------

@dataclass
class NLUResult:
    """
    Single unified result returned by OpenAI NLU.

    type:
      - "ANSWER"
      - "ACTION"
    """
    type: str
    answer: Optional[str] = None
    intent: Optional[str] = None
    filename: Optional[str] = None
    content: Optional[str] = None
    detail: Optional[str] = None  # e.g., short|detailed for summaries
    include_ctx_in_filename: Optional[bool] = None


# -------------------------------------------------
# OpenAI Client
# -------------------------------------------------

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _auth_error_response() -> NLUResult:
    return NLUResult(
        type="ANSWER",
        answer="Authentication with OpenAI failed (401). Please set OPENAI_API_KEY.",
    )


# -------------------------------------------------
# Main NLU Entry Point
# -------------------------------------------------

def check(command: str, context_hint: Optional[str] = None) -> NLUResult:
    """
    Classifies user input as ACTION or ANSWER using OpenAI
    and returns a structured NLUResult.
    """

    base_rules = """
You are a strict intent classifier for a personal AI assistant.

Your task:
- Decide if the user's input is an ACTION or an ANSWER.
- ACTION means a side-effect (file operations or summarization).
- ANSWER means informational, chat, or explanation.

Rules:
- Respond ONLY with valid JSON.
- Do NOT explain.
- Do NOT include extra text.

Allowed ACTION intents:
WRITE, READ, APPEND, DELETE, SUMMARIZE

If data is missing, use null.

When answering you are personality is like J.A.R.V.I.S from Iron Man

JSON formats:

ANSWER:
{
  "type": "ANSWER",
  "answer": "Glad to hear that, sir. Let me know how I can help."
}

ACTION:
{
  "type": "ACTION",
  "intent": "WRITE|READ|APPEND|DELETE|SUMMARIZE",
  "filename": "string or null",
  "content": "string or null",
  "detail": "short|detailed|null",
  "include_ctx_in_filename": true|false|null
}
"""

    context_block = f"\n\nContext to remember:\n{context_hint}\n" if context_hint else ""
    system_prompt = base_rules + context_block

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": command},
            ],
        )
    except Exception as e:
        status = getattr(e, "status_code", None) or getattr(e, "http_status", None)
        if status == 401:
            return _auth_error_response()
        return NLUResult(
            type="ANSWER",
            answer="Sorry sir, I couldn't understand that.",
        )

    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Safe fallback
        return NLUResult(
            type="ANSWER",
            answer="Sorry sir, I couldn't understand that."
        )

    return NLUResult(
        type=data.get("type"),
        answer=data.get("answer"),
        intent=data.get("intent"),
        filename=data.get("filename"),
        content=data.get("content"),
        detail=data.get("detail"),
        include_ctx_in_filename=data.get("include_ctx_in_filename"),
    )
