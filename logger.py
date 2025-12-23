import logging
from pathlib import Path

# -------------------------------------------------
# Log directory and file
# -------------------------------------------------
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "assistant.log"

# -------------------------------------------------
# Logging configuration (FILE ONLY)
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)

# -------------------------------------------------
# Shared logger instance
# -------------------------------------------------
logger = logging.getLogger("stark_assistant")
