"""
tests/test_sovereign_core.py — J.A.R.V.I.S. Mark 108 (Sovereign Core) Verification Suite
========================================================================================
Tests the 4 Sovereign Pillars:
1. Autonomous Self-Coding & Sandboxed Smoke-Testing (`SovereignSkillSynthesizer`)
2. Runtime Self-Healing & Security Boundary Protection (`SovereignSelfHealer`)
3. Multi-Agent Sub-Mind Deliberation Council (`SovereignDeliberationCouncil`)
4. Adaptive Hardware Equilibrium & State Consolidation (`SovereignEquilibriumDaemon`)
"""

from pathlib import Path
from core.sovereign_core import (
    MARK_VERSION,
    LEGACY_RELEASE_BASELINE,
    SovereignDeliberationCouncil,
    SovereignDocumentBridge,
    SovereignEquilibriumDaemon,
    SovereignSelfHealer,
    SovereignSkillSynthesizer,
)
from core.skills_engine import ACTIONS_DIR, skills_engine


def test_pillar_1_autonomous_skill_synthesis_and_hot_load():
    """Verifies JARVIS Mark 108 can synthesize, AST-validate, smoke-test, and hot-load a new skill."""
    skill_name = "sovereign_unit_converter"
    sample_code = '''"""Autonomously synthesized unit converter skill for Mark 108."""

def sovereign_unit_converter(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    km = float(params.get("kilometers", 1.0))
    miles = round(km * 0.621371, 4)
    return f"{km} km = {miles} miles [Sovereign Skill Verified]"
'''
    res = SovereignSkillSynthesizer.synthesize_missing_capability(
        skill_name=skill_name,
        description="Converts kilometers to miles with 4-decimal precision.",
        custom_code=sample_code,
    )
    assert res["status"] == "VERIFIED"

    ok, msg = SovereignSkillSynthesizer.validate_and_smoke_test_skill(
        skill_name, dry_run_params={"kilometers": 10.0}
    )
    assert ok is True, msg

    output = skills_engine.run_skill(skill_name, skill_args={"kilometers": 10.0})
    assert "6.2137 miles" in output

    # Clean up temporary test skill file
    test_skill_path = ACTIONS_DIR / f"{skill_name}.py"
    if test_skill_path.exists():
        test_skill_path.unlink()


def test_pillar_1_self_healer_security_guard():
    """Verifies SovereignSelfHealer refuses to auto-patch protected security modules."""
    res = SovereignSelfHealer.diagnose_and_heal(
        module_stem="security_shield",
        error_text="Simulated security exception",
    )
    assert res["healed"] is False
    assert "protected" in res["message"].lower()


def test_pillar_2_sovereign_document_bridge(tmp_path: Path):
    """Verifies SovereignDocumentBridge builds and QA-verifies a .docx with equations and tables."""
    md = (
        "# Sovereign Quantum Telemetry\n\n"
        "The entanglement fidelity is $\\mathcal{F} = \\frac{1 + 3p}{4}$ across all nodes.\n\n"
        "| **Node ID** | **Fidelity** |\n"
        "| :--- | :---: |\n"
        "| **Alpha-1** | *99.94%* |\n"
    )
    out_file = tmp_path / "Sovereign_Telemetry.docx"
    built_path, qa = SovereignDocumentBridge.build_verified_docx(
        md,
        meta={"output_path": out_file, "title": "Sovereign Quantum Telemetry", "render_page1_png": False},
    )
    assert built_path.exists()
    assert qa["passed"] is True


def test_pillar_3_deliberation_council():
    """Verifies all 4 cognitive sub-minds reach consensus."""
    verdict = SovereignDeliberationCouncil.deliberate(
        "Architect a fault-tolerant distributed storage layer",
        context={"priority": "high"},
    )
    assert verdict["version"] == MARK_VERSION
    assert verdict["consensus_approved"] is True
    assert len(verdict["verdicts"]) == 4
    assert verdict["aggregate_confidence"] >= 0.95


def test_pillar_4_equilibrium_daemon():
    """Verifies hardware telemetry sampling and sovereign state persistence."""
    state = SovereignEquilibriumDaemon.consolidate_state()
    assert state["kernel"] == MARK_VERSION
    assert state["stabilized_release"] == LEGACY_RELEASE_BASELINE
    assert "operating_regime" in state["telemetry"]
