"""
core/document_qa/config.py — Centralized configuration manager for J.A.R.V.I.S. Document QA Engine.
"""

import json
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "document_qa_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "strict_mode": True,
    "max_correction_retries": 2,
    "min_passing_score": 75.0,
    "deterministic_math_validation": True,
    "post_render_inspection": True,
    "live_doi_verification": True,
    "allow_unverified_drafts": True,
    "default_citation_style": "APA7",
    "log_audit_trail": True,
    "audit_log_dir": "memory/document_qa_logs",
    "category_profiles": {
        "academic": {
            "min_source_tier": 2,
            "require_citations": True,
            "check_dois": True,
            "min_passing_score": 80.0,
            "require_peer_review_preference": True
        },
        "business": {
            "min_source_tier": 3,
            "require_citations": False,
            "check_kpis": True,
            "min_passing_score": 75.0,
            "require_executive_summary": True
        },
        "financial": {
            "min_source_tier": 1,
            "require_citations": False,
            "deterministic_math_validation": True,
            "formula_recalculation": True,
            "zero_error_tolerance": True,
            "min_passing_score": 85.0
        },
        "technical": {
            "min_source_tier": 2,
            "require_citations": True,
            "check_code_syntax": True,
            "check_architecture_diagrams": True,
            "min_passing_score": 75.0
        },
        "professional": {
            "min_source_tier": 3,
            "require_citations": False,
            "disallow_invented_qualifications": True,
            "min_passing_score": 75.0
        },
        "creative_presentation": {
            "min_source_tier": 4,
            "slide_overflow_check": True,
            "max_words_per_slide": 110,
            "min_passing_score": 70.0
        },
        "spreadsheet": {
            "min_source_tier": 3,
            "deterministic_math_validation": True,
            "formula_recalculation": True,
            "disallow_hardcoded_totals": True,
            "zero_error_tolerance": True,
            "min_passing_score": 85.0
        }
    }
}


def get_qa_config() -> Dict[str, Any]:
    """Retrieves document QA configuration, merging disk overrides with safe defaults."""
    if CONFIG_FILE.exists():
        try:
            disk_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            merged = DEFAULT_CONFIG.copy()
            merged.update(disk_data)
            return merged
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def get_category_profile(category_key: str) -> Dict[str, Any]:
    """Retrieves the QA profile for a specific document category."""
    cfg = get_qa_config()
    profiles = cfg.get("category_profiles", {})
    return profiles.get(category_key.lower(), {
        "min_source_tier": 3,
        "require_citations": False,
        "min_passing_score": 75.0
    })


def update_qa_config(new_settings: Dict[str, Any]) -> bool:
    """Updates configuration on disk."""
    try:
        cur = get_qa_config()
        cur.update(new_settings)
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cur, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False
