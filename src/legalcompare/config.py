"""Configuration loading: merges config.yaml (tunable settings) with .env (secrets).

Usage:
    from legalcompare.config import get_config
    cfg = get_config()
    threshold = cfg["alignment"]["fuzzy_match_threshold"]
    api_key = cfg["secrets"]["anthropic_api_key"]
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Repo root = two levels up from this file (src/legalcompare/config.py -> repo/).
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    """Load and cache the merged configuration."""
    load_dotenv(REPO_ROOT / ".env")  # no-op if .env is absent

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f) or {}

    # Allow an env var to override the model id without editing config.yaml.
    model_override = os.getenv("LEGALCOMPARE_MODEL")
    if model_override:
        cfg.setdefault("comparison", {})["model"] = model_override

    # Secrets are never written to config.yaml; they come from the environment.
    cfg["secrets"] = {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    }
    cfg["repo_root"] = str(REPO_ROOT)
    return cfg
