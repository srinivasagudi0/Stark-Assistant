import os
from pathlib import Path
from typing import Tuple

_SAFE_SUFFIX = ".safe"


class FilePermissionError(Exception):
    pass


class InvalidFilenameError(Exception):
    pass


def _validate_filename(filename: str) -> Path:
    if not filename or filename.lower() == "null":
        raise InvalidFilenameError("Invalid or missing filename.")
    path = Path(filename).expanduser().resolve()
    if path.is_dir():
        raise InvalidFilenameError(f"'{path}' is a directory, not a file.")
    return path


def _check_exists_and_perms(path: Path, mode: str) -> None:
    """Validate existence and permissions for the given mode.

    mode: "r", "w", "a"
    """
    if mode in ("r", "a") and not path.exists():
        raise FileNotFoundError(f"File '{path}' does not exist.")

    if mode == "r" and not os.access(path, os.R_OK):
        raise FilePermissionError(f"No read permission for '{path}'.")
    if mode == "a" and not os.access(path, os.W_OK):
        raise FilePermissionError(f"No write permission for '{path}'.")
    if mode == "w":
        parent = path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
        if not os.access(parent, os.W_OK):
            raise FilePermissionError(f"No write permission in '{parent}'.")


def _safe_target(path: Path, allow_overwrite: bool) -> Tuple[Path, bool]:
    if allow_overwrite:
        return path, False
    if path.exists():
        safe_path = path.with_suffix(path.suffix + _SAFE_SUFFIX)
        return safe_path, True
    return path, False


def _is_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
        return b"\0" in chunk
    except Exception:
        return True


def execute(intent: str, filename: str | None, content: str | None, *,
            allow_overwrite: bool = False,
            append_if_missing: bool = False) -> str:
    """
    Executes a file-related action based on intent.

    intent   : WRITE | READ | APPEND | DELETE | SUMMARIZE
    filename : target file
    content  : text for WRITE / APPEND

    Safety defaults:
    - No overwrite unless allow_overwrite=True
    - APPEND fails if missing unless append_if_missing=True
    """

    try:
        path = _validate_filename(filename or "")
    except InvalidFilenameError as e:
        return f"Failed: {e}"

    # -------- WRITE --------
    if intent == "WRITE":
        if content is None:
            return "No content provided to write."
        try:
            target, collided = _safe_target(path, allow_overwrite)
            _check_exists_and_perms(target, "w")
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            if collided:
                return f"Collision avoided. Wrote to '{target}'."
            return f"Successfully wrote to '{target}'."
        except (FilePermissionError, InvalidFilenameError) as e:
            return f"Failed: {e}"
        except Exception as e:
            return f"Failed to write file: {e}"

    # -------- READ --------
    if intent == "READ":
        try:
            _check_exists_and_perms(path, "r")
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, FilePermissionError, InvalidFilenameError) as e:
            return f"Failed: {e}"
        except Exception as e:
            return f"Failed to read file: {e}"

    # -------- APPEND --------
    if intent == "APPEND":
        if content is None:
            return "No content provided to append."
        try:
            if not path.exists():
                if not append_if_missing:
                    return f"Failed: File '{path}' does not exist (append disallowed)."
                _check_exists_and_perms(path, "w")
            else:
                _check_exists_and_perms(path, "a")
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully appended to '{path}'."
        except (FileNotFoundError, FilePermissionError, InvalidFilenameError) as e:
            return f"Failed: {e}"
        except Exception as e:
            return f"Failed to append file: {e}"

    # -------- DELETE --------
    if intent == "DELETE":
        try:
            _check_exists_and_perms(path, "a")
            os.remove(path)
            return f"Deleted '{path}'."
        except (FileNotFoundError, FilePermissionError, InvalidFilenameError) as e:
            return f"Failed: {e}"
        except Exception as e:
            return f"Failed to delete file: {e}"

    # -------- SUMMARIZE --------
    if intent == "SUMMARIZE":
        try:
            _check_exists_and_perms(path, "r")
            if _is_binary(path):
                return f"Failed: '{path}' appears to be binary or unreadable for summarization."
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except (FileNotFoundError, FilePermissionError, InvalidFilenameError) as e:
            return f"Failed: {e}"
        except Exception as e:
            return f"Failed to read file for summary: {e}"

    return f"Unknown intent: {intent}"
