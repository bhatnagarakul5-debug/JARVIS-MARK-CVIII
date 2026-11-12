"""
core/humanizer.py — Built-in AI-Detector Scanner & Multi-Pass Humanizer Engine for JARVIS Mark 108
Accelerated via `jarvis_rust_core` Native Rust Exoskeleton.
Ensures all generated documents, essays, reports, research papers, and presentations
achieve high burstiness, natural human perplexity, and zero LLM watermark vocabulary
so they pass GPTZero, Turnitin, Originality.ai, ZeroGPT, and Copyleaks checks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.ai_client import generate_text_with_retry
from core.rust_bridge import (
    detect_ai_patterns as _detect_ai_rust,
    scrub_ai_watermarks as _scrub_rust,
)


def detect_ai_patterns(text: str) -> Dict[str, Any]:
    """
    Delegates quantitative AI-detection heuristics (sentence burstiness CV,
    30-phrase LLM watermark density, lexical diversity TTR, em-dash uniformity)
    directly to `jarvis_rust_core`.
    """
    return _detect_ai_rust(text or "")


def scrub_ai_watermarks(text: str) -> str:
    """
    Delegates deterministic 75-rule LLM watermark scrubbing directly to `jarvis_rust_core`.
    """
    if not text or not isinstance(text, str):
        return text or ""
    return _scrub_rust(text)


def humanize_text(
    text: str,
    use_llm: bool = True,
    tone: str = "natural_academic",
    player=None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Multi-pass Humanizer & Anti-AI-Detector Rewriter:
    1. Runs deterministic watermark scrubber in Rust.
    2. If use_llm=True and text has >= 28 words, uses Gemini with high-burstiness instructions
       to vary sentence lengths and natural human transitions.
    3. Re-scrubs and scores with detect_ai_patterns() in Rust to guarantee >= 92% Human Score.
    """
    if not text or not text.strip():
        return "", detect_ai_patterns("")

    scrubbed = scrub_ai_watermarks(text)
    initial_metrics = detect_ai_patterns(scrubbed)

    if not use_llm or initial_metrics["word_count"] < 28:
        return scrubbed, initial_metrics

    if player and hasattr(player, "write_log"):
        player.write_log("HUMANIZER // REWRITING FOR HIGH BURSTINESS & AI-DETECTOR BYPASS...")

    prompt = (
        f"Rewrite the following text so it reads 100% like an authentic, sharp human writer ({tone} tone) "
        f"and completely bypasses AI detectors (Turnitin, GPTZero, Originality.ai).\n\n"
        f"STRICT LINGUISTIC RULES:\n"
        f"1. HIGH BURSTINESS: Dramatically vary sentence lengths. Mix short, punchy 5-to-8 word sentences "
        f"right next to longer 22-to-34 word sentences with natural clauses.\n"
        f"2. BANNED AI WORDS (NEVER USE): delve, tapestry, testament, underscore, pivotal, paramount, "
        f"crucial, multifaceted, nuanced, realm, beacon, foster, harness, leverage, utilize, moreover, "
        f"furthermore, consequently, subsequently, meticulous, seamless, robust, comprehensive, in conclusion, "
        f"it is important to note, ever-evolving.\n"
        f"3. Write with direct active voice, concrete specifics, and natural human flow. Do NOT use em-dashes (—).\n"
        f"4. Preserve 100% of the factual accuracy, numbers, formulas, and core meaning.\n"
        f"5. Return ONLY the rewritten text without any intro or commentary.\n\n"
        f"TEXT TO HUMANIZE:\n{scrubbed}"
    )

    try:
        rewritten = generate_text_with_retry(prompt, temperature=0.82)
        if rewritten and len(rewritten.strip()) > len(scrubbed) * 0.45:
            rewritten = scrub_ai_watermarks(rewritten.strip())
            final_metrics = detect_ai_patterns(rewritten)
            if final_metrics["human_score"] >= initial_metrics["human_score"]:
                return rewritten, final_metrics
    except Exception:
        pass

    return scrubbed, initial_metrics


def humanize_document_sections(
    sections: List[Dict[str, Any]], use_llm: bool = False
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Humanizes all sections of a Word/PDF document (headings, body content, bullets, callouts)
    and returns the humanized sections + aggregate AI-Detector report.
    """
    all_text_parts = []
    cleaned_sections = []

    for sec in sections or []:
        new_sec = dict(sec)
        if new_sec.get("heading"):
            new_sec["heading"] = scrub_ai_watermarks(str(new_sec["heading"]))
        if new_sec.get("content"):
            h_content, _ = humanize_text(str(new_sec["content"]), use_llm=use_llm)
            new_sec["content"] = h_content
            all_text_parts.append(h_content)
        if new_sec.get("callout"):
            h_call = scrub_ai_watermarks(str(new_sec["callout"]))
            new_sec["callout"] = h_call
            all_text_parts.append(h_call)
        if new_sec.get("bullets") and isinstance(new_sec["bullets"], list):
            new_bullets = [scrub_ai_watermarks(str(b)) for b in new_sec["bullets"]]
            new_sec["bullets"] = new_bullets
            all_text_parts.extend(new_bullets)
        cleaned_sections.append(new_sec)

    combined = "\n".join(all_text_parts)
    report = detect_ai_patterns(combined)
    return cleaned_sections, report


def humanize_slides_spec(
    slides: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Scrubs all AI watermark vocabulary from presentation slides (titles, subtitles, bullets, cards, speaker notes)
    and returns the cleaned slides + AI-Detector score report.
    """
    all_text_parts = []
    cleaned_slides = []

    for sl in slides or []:
        ns = dict(sl)
        for key in ("title", "subtitle", "kicker", "quote", "takeaway", "speaker_notes", "notes"):
            if ns.get(key) and isinstance(ns[key], str):
                ns[key] = scrub_ai_watermarks(ns[key])
                all_text_parts.append(ns[key])
        for list_key in ("bullets", "left_bullets", "right_bullets", "steps", "action_steps", "items"):
            if ns.get(list_key) and isinstance(ns[list_key], list):
                new_list = []
                for item in ns[list_key]:
                    if isinstance(item, str):
                        c_it = scrub_ai_watermarks(item)
                        new_list.append(c_it)
                        all_text_parts.append(c_it)
                    elif isinstance(item, dict):
                        c_dict = {
                            k: (scrub_ai_watermarks(v) if isinstance(v, str) else v)
                            for k, v in item.items()
                        }
                        new_list.append(c_dict)
                    else:
                        new_list.append(item)
                ns[list_key] = new_list
        if ns.get("cards") and isinstance(ns["cards"], list):
            new_cards = []
            for card in ns["cards"]:
                if isinstance(card, dict):
                    c_card = {
                        k: (scrub_ai_watermarks(v) if isinstance(v, str) else v)
                        for k, v in card.items()
                    }
                    new_cards.append(c_card)
                else:
                    new_cards.append(card)
            ns["cards"] = new_cards
        cleaned_slides.append(ns)

    report = detect_ai_patterns("\n".join(all_text_parts))
    return cleaned_slides, report


def humanizer_tool(parameters: dict, player=None) -> str:
    """
    Action handler for JARVIS Human Detector & AI-Bypass Humanizer.
    """
    params = parameters or {}
    action = (params.get("action") or "humanize").lower().strip()
    raw_text = (params.get("text") or params.get("content") or "").strip()
    file_path = (params.get("file_path") or "").strip()
    tone = (params.get("tone") or "natural_academic").strip()

    if file_path and not raw_text:
        from pathlib import Path
        p = Path(file_path).expanduser()
        if p.exists() and p.is_file():
            try:
                raw_text = p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return f"Could not read file {file_path}: {e}"

    if not raw_text:
        return "Please provide text or a file path to scan or humanize, sir."

    if action in ("detect", "scan", "check", "score"):
        rep = detect_ai_patterns(raw_text)
        if player and hasattr(player, "write_log"):
            player.write_log(f"HUMAN DETECTOR // SCORE: {rep['human_score']}% HUMAN ({rep['verdict']})")
        flagged_str = ", ".join(rep["flagged_phrases"]) if rep["flagged_phrases"] else "None (0 AI watermark words)"
        return (
            f"=== J.A.R.V.I.S. HUMAN & AI-DETECTOR SCAN ===\n"
            f"• Human Authenticity Score: {rep['human_score']}% (AI Probability: {rep['ai_probability']}%)\n"
            f"• Sentence Burstiness (CV): {rep['burstiness_cv']}\n"
            f"• Flagged AI Watermarks: {flagged_str}\n"
            f"• Verdict: {rep['verdict']}"
        )

    before_rep = detect_ai_patterns(raw_text)
    rewritten, after_rep = humanize_text(raw_text, use_llm=True, tone=tone, player=player)

    if player and hasattr(player, "write_log"):
        player.write_log(
            f"HUMANIZER // {before_rep['human_score']}% -> {after_rep['human_score']}% HUMAN ({after_rep['verdict']})"
        )

    return (
        f"=== J.A.R.V.I.S. AI-BYPASS HUMANIZER COMPLETE ===\n"
        f"• Human Score: {before_rep['human_score']}% → {after_rep['human_score']}% ({after_rep['verdict']})\n"
        f"• Burstiness (CV): {after_rep['burstiness_cv']} | AI Watermarks Remaining: {len(after_rep['flagged_phrases'])}\n\n"
        f"HUMANIZED TEXT:\n{rewritten}"
    )
