"""Relay settings: models, budgets, degrade ladder, paths."""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RELAY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = RELAY_ROOT.parent
DATA_DIR = RELAY_ROOT / "data"
INDEX_DIR = DATA_DIR / "index"
PROBES_DIR = DATA_DIR / "probes"
RESULTS_DIR = DATA_DIR / "results"
PAPERS_RAW_DIR = RELAY_ROOT / "papers" / "raw"
MANIFEST_PATH = RELAY_ROOT / "papers" / "manifest.json"
RESULTS_CSV = RESULTS_DIR / "results.csv"

# ---------------------------------------------------------------------------
# Models (Groq-hosted)
# ---------------------------------------------------------------------------
DRAFT_MODEL = os.environ.get("RELAY_DRAFT_MODEL", "openai/gpt-oss-120b")
SMALL_MODEL = os.environ.get("RELAY_SMALL_MODEL", "openai/gpt-oss-20b")

GROQ_API_BASE = os.environ.get("GROQ_API_BASE", "https://api.groq.com/openai/v1")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

STANDIN_HOST = os.environ.get("RELAY_STANDIN_HOST", "127.0.0.1")
STANDIN_PORT = int(os.environ.get("RELAY_STANDIN_PORT", "8765"))
STANDIN_BASE = os.environ.get(
    "RELAY_STANDIN_BASE", f"http://{STANDIN_HOST}:{STANDIN_PORT}/v1"
)

# ---------------------------------------------------------------------------
# Budget / rate limits (defaults; probe_limits.py overwrites measured values)
# ---------------------------------------------------------------------------
# Free-tier placeholders — replace with measured Table-1 values after probing.
LIMIT_RPM = int(os.environ.get("RELAY_LIMIT_RPM", "30"))
LIMIT_TPM = int(os.environ.get("RELAY_LIMIT_TPM", "6000"))
LIMIT_RPD = int(os.environ.get("RELAY_LIMIT_RPD", "1000"))
LIMIT_TPD = int(os.environ.get("RELAY_LIMIT_TPD", "200000"))
LIMIT_IN_FLIGHT = int(os.environ.get("RELAY_LIMIT_IN_FLIGHT", "5"))

# Low-consumption mode ONLY after this fraction of any tracked budget is used.
# Below this: ladder level 0 (full quality). At/above: degrade ladder engages.
BUDGET_DEGRADE_THRESHOLD = float(os.environ.get("RELAY_BUDGET_DEGRADE_THRESHOLD", "0.80"))

# Map usage in [threshold, 1.0] onto ladder levels 1..5 (even bands).
# Level 0: usage < 80%
# Level 1: skip rewrite
# Level 2: skip LLM verify
# Level 3: shrink retrieval
# Level 4: extractive answer
# Level 5: honest try-later
LADDER_LEVELS_AFTER_THRESHOLD = (1, 2, 3, 4, 5)

# ---------------------------------------------------------------------------
# Timeouts / retries / admission
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_S = float(os.environ.get("RELAY_REQUEST_TIMEOUT_S", "60"))
USER_GIVE_UP_S = float(os.environ.get("RELAY_USER_GIVE_UP_S", "20"))
QUEUE_WAIT_S = float(os.environ.get("RELAY_QUEUE_WAIT_S", "5"))
MAX_RETRIES = int(os.environ.get("RELAY_MAX_RETRIES", "2"))
RETRY_BACKOFF_S = float(os.environ.get("RELAY_RETRY_BACKOFF_S", "0.75"))
MAX_RETRIEVAL_LOOPS = 1  # one optional second fetch when hits are weak

# ---------------------------------------------------------------------------
# Retrieval presets (Table 3 — at least three)
# ---------------------------------------------------------------------------
RETRIEVAL_SETTINGS: dict[str, dict] = {
    "A_small_topk3_norerank": {
        "piece_size": 400,
        "overlap": 60,
        "top_k": 3,
        "re_rank": False,
    },
    "B_medium_topk5_rerank": {
        "piece_size": 800,
        "overlap": 120,
        "top_k": 5,
        "re_rank": True,
    },
    "C_large_topk8_rerank": {
        "piece_size": 1200,
        "overlap": 160,
        "top_k": 8,
        "re_rank": True,
    },
}
DEFAULT_RETRIEVAL_SETTING = "B_medium_topk5_rerank"

# When ladder ≥ 3, shrink to this preset's top_k / no re-rank regardless of chosen setting.
SHRUNK_TOP_K = 2
SHRUNK_RE_RANK = False

# ---------------------------------------------------------------------------
# Token caps (spend only where they buy correctness)
# ---------------------------------------------------------------------------
CLASSIFY_MAX_TOKENS = 64
DRAFT_MAX_TOKENS = 700
REWRITE_MAX_TOKENS = 700
VERIFY_MAX_TOKENS = 128
