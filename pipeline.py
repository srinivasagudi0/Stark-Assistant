from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from stark_assistant.core.openai_nlu import check
from stark_assistant.executor.executor import execute
from stark_assistant.logger import logger
from stark_assistant.core import memory
from stark_assistant.config import settings
from openai import OpenAI


def _apply_ctx_to_filename(filename: str, include_ctx: bool, context_hint: str | None) -> str:
    if not include_ctx or not context_hint:
        return filename
    ctx_snippet = "-ctx"
    path = Path(filename)
    return str(path.with_name(path.stem + ctx_snippet + path.suffix))


def _need_permission(intent: str) -> bool:
    return intent in {"WRITE", "APPEND", "DELETE"}


def _local_summary(text: str, detail: Optional[str]) -> str:
    """Lightweight offline summary when API is unavailable or fails."""
    max_len = 120 if detail != "detailed" else 240
    words = text.split()
    snippet = " ".join(words[:max_len])
    suffix = "" if len(words) <= max_len else " ..."
    return f"Summary: {snippet}{suffix}"


def _summarize_text(text: str, detail: Optional[str]) -> str:
    """Summarize text; falls back to local summarizer when API missing or errors (except 401)."""
    if not settings.OPENAI_API_KEY:
        return _local_summary(text, detail)
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        style = "concise" if detail != "detailed" else "detailed"
        prompt = f"Provide a {style} summary of the following text: \n{text}"
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": "You summarize documents accurately."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        status = getattr(e, "status_code", None) or getattr(e, "http_status", None)
        if status == 401:
            return "Failed: OpenAI authentication (401). Configure OPENAI_API_KEY."
        return _local_summary(text, detail)


def _handle_pending_permission(command: str, state: dict) -> Optional[tuple[str, str | None, str | None]]:
    """Process yes/no responses for pending destructive actions."""
    pending_intent = state.get("pending_intent")
    pending_filename = state.get("pending_filename")
    if not pending_intent:
        return None

    answer = command.strip().lower()
    include_ctx = "ctx" in answer or "context" in answer or state.get("pending_include_ctx", False)

    if answer in {"yes", "y", "confirm", "ok", "okay"}:
        filename = pending_filename
        content = state.get("pending_content")
        context_hint = memory.build_context_hint(state)
        filename = _apply_ctx_to_filename(filename, include_ctx, context_hint)
        result = execute(pending_intent, filename, content, allow_overwrite=False, append_if_missing=False)
        for k in ["pending_intent", "pending_filename", "pending_content", "pending_include_ctx"]:
            state.pop(k, None)
        memory.save_state(state)
        return result, pending_intent, filename

    if answer in {"no", "n", "cancel"}:
        for k in ["pending_intent", "pending_filename", "pending_content", "pending_include_ctx"]:
            state.pop(k, None)
        memory.save_state(state)
        return "Operation cancelled.", pending_intent, pending_filename

    # Unclear response: cancel to avoid stuck pending state
    for k in ["pending_intent", "pending_filename", "pending_content", "pending_include_ctx"]:
        state.pop(k, None)
    memory.save_state(state)
    return "Please re-issue the command with yes/no to proceed.", pending_intent, pending_filename


def process_command(command: str) -> str:
    logger.info(f"COMMAND | {command}")

    state = memory.load_state()

    # Handle pending permission confirmations early
    pending_result = _handle_pending_permission(command, state)
    if pending_result is not None:
        outcome, intent_used, filename_used = pending_result
        memory.record_turn(command, SimpleNamespace(type="ACTION", intent=intent_used, filename=filename_used), outcome)
        return outcome

    context_hint = memory.build_context_hint(state)
    nlu_result = check(command, context_hint=context_hint)

    # ---------- ANSWER ----------
    if nlu_result.type == "ANSWER":
        logger.info(f"ANSWER | {nlu_result.answer}")
        memory.record_turn(command, nlu_result, nlu_result.answer)
        return nlu_result.answer

    # ---------- ACTION ----------
    if nlu_result.type == "ACTION":

        intent = nlu_result.intent
        requested_filename = nlu_result.filename  # keep original request for summary
        filename = memory.resolve_filename(state, nlu_result.filename)
        content = nlu_result.content
        include_ctx_flag = bool(nlu_result.include_ctx_in_filename) if nlu_result.include_ctx_in_filename is not None else False

        # ---- MEMORY READ (fallback) ----
        if not filename:
            if state.get("last_filename"):
                filename = state["last_filename"]
                logger.info(f"MEMORY | resolved filename={filename}")
            else:
                msg = "Which file should I use, sir?"
                memory.record_turn(command, nlu_result, msg)
                return msg

        # ---- SUMMARIZE HANDLING ----
        if intent == "SUMMARIZE":
            target = filename or settings.DEFAULT_SUMMARY_FILE
            raw_text = execute("SUMMARIZE", target, None)
            if raw_text.lower().startswith("failed"):
                memory.record_turn(command, nlu_result, raw_text)
                return raw_text
            summary = _summarize_text(raw_text, nlu_result.detail)
            memory.record_turn(command, nlu_result, summary)
            return summary

        # ---- PERMISSION CHECKS ----
        if _need_permission(intent):
            prompt = f"Confirm {intent} on '{filename}'. Include context in filename? (yes/no)"
            state["pending_intent"] = intent
            state["pending_filename"] = filename
            state["pending_content"] = content
            state["pending_include_ctx"] = include_ctx_flag
            memory.save_state(state)
            memory.record_turn(command, nlu_result, prompt)
            return prompt

        # ---- EXECUTION ----
        allow_overwrite = False
        append_if_missing = False
        result = execute(intent, filename, content, allow_overwrite=allow_overwrite, append_if_missing=append_if_missing)

        # ---- MEMORY WRITE (only after success) ----
        if not result.lower().startswith("failed"):
            nlu_result.filename = filename  # ensure stored
            memory.record_turn(command, nlu_result, result)

        logger.info(
            f"ACTION | intent={intent} file={Path(filename).name if filename else 'none'} status={'ok' if not result.lower().startswith('failed') else 'failed'}"
        )

        return result

    # ---------- UNKNOWN ----------
    logger.warning("UNKNOWN | Unable to process command")
    fallback = "Sorry sir, I couldn't understand that."
    memory.record_turn(command, nlu_result, fallback)
    return fallback
