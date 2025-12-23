import os
from pathlib import Path

# OpenAI key pulled from environment for safety; defaults to empty string.
OPENAI_API_KEY = 'YOUR_API_KEY_HERE'

# Default text file for summarization fallback (e.g., The Princess Bride).
DEFAULT_SUMMARY_FILE = os.getenv(
    "DEFAULT_SUMMARY_FILE",
    str(Path(__file__).resolve().parent.parent / "data" / "princess_bride.txt"),
)
