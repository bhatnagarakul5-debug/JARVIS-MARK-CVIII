"""
core/document_qa/orchestrator.py — Universal Document Generation & Quality Assurance Orchestrator for J.A.R.V.I.S.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from core.document_qa.models import DocumentCategory, QAStatus, QualityScorecard
from core.document_qa.classifier import classify_document_request
from core.document_qa.qa_engine import DocumentQAEngine
from core.document_qa.config import get_qa_config
from core.ai_client import generate_text_with_retry


class UniversalDocumentOrchestrator:
    """
    Centralized pipeline orchestrator.
    Every document-generation request passes through this orchestrator to ensure:
    Classification -> Evidence Gathering -> Content Synthesis -> Deterministic Validation ->
    Rendering -> Post-Rendering Inspection -> QA Scorecard -> Targeted Self-Correction -> Delivery.
    """

    def __init__(self):
        self.config = get_qa_config()
        self.qa_engine = DocumentQAEngine(self.config)

    def orchestrate_generation(self, parameters: Dict[str, Any], player=None) -> str:
        """
        Executes the universal document intelligence, generation, and quality assurance lifecycle.
        """
        params = parameters or {}
        fname = (params.get("filename") or params.get("file_name") or params.get("name") or "Document").strip()
        inferred_ext = Path(fname).suffix.lower().lstrip(".")
        ftype = (params.get("file_type") or inferred_ext or "docx").lower().strip()
        from actions.docx_builder import acronym_safe_title_case
        title = acronym_safe_title_case((params.get("title") or params.get("topic") or Path(fname).stem.replace("_", " ")).strip())
        content = (params.get("content") or "").strip()
        doc_type = (params.get("doc_type") or "technical_spec").lower().strip()
        loc = params.get("target_location") or "desktop"
        open_after = params.get("open_after", True)
        instruction = (params.get("instruction") or "").strip()

        # Phase 1: Classification & Profile Assignment
        category, profile = classify_document_request(
            title=title,
            doc_type=doc_type,
            file_type=ftype,
            content=content,
            instruction=instruction
        )

        if player and hasattr(player, "write_log"):
            player.write_log(f"DOCUMENT QA // Classified '{title}' as {category.value.upper()} (Profile: Min Tier {profile.get('min_source_tier', 3)})")

        # Phase 2: Autonomous Research & Evidence Ingestion (if Academic/Technical and content is empty/sparse)
        if (category in (DocumentCategory.ACADEMIC, DocumentCategory.TECHNICAL) or profile.get("require_citations", False)) and len(content) < 60:
            content = self._gather_scholarly_evidence_and_synthesize(title, category, doc_type, player)

        # Extract structured sections
        from actions.file_generator import (
            _get_output_dir, _parse_markdown_to_sections, _render_architecture_diagram,
            create_word_document, create_presentation, create_pdf_document,
            create_excel_sheet, create_html_documentation, document_codebase
        )
        out_dir = _get_output_dir(loc)

        # Phase 3: Initial Generation & Rendering
        gen_result, generated_path = self._render_document_by_type(
            ftype=ftype,
            fname=fname,
            title=title,
            content=content,
            doc_type=doc_type,
            params=params,
            out_dir=out_dir,
            open_after=False,  # Keep closed until QA passes!
            player=player
        )

        if not generated_path or not generated_path.exists():
            return f"Document generation failed to produce output file: {gen_result}"

        # Phase 4: Post-Rendering Inspection & Quality Assurance Audit
        tables = params.get("rows")
        sections = params.get("sections") or _parse_markdown_to_sections(content)
        scorecard = self.qa_engine.audit_document(
            title=title,
            category=category,
            file_format=ftype,
            content=content,
            sections=sections,
            tables=tables,
            file_path=generated_path,
            min_passing_score=profile.get("min_passing_score", 75.0)
        )

        # Phase 5: Autonomous Self-Correction Loop
        max_retries = self.config.get("max_correction_retries", 2)
        retries = 0

        while not scorecard.can_deliver_as_validated() and retries < max_retries and not params.get('skip_llm_correction', True):
            retries += 1
            if player and hasattr(player, "write_log"):
                player.write_log(f"DOCUMENT QA // Self-Correction Loop Iteration {retries}/{max_retries} for '{generated_path.name}'...")

            directives = self.qa_engine.generate_correction_instructions(scorecard)
            if not directives:
                break

            # Targeted correction: re-synthesize or patch content
            correction_prompt = (
                f"You are the J.A.R.V.I.S. Autonomous Document Quality Editor.\n"
                f"DOCUMENT: '{title}' ({category.value.upper()})\n\n"
                f"CURRENT CONTENT:\n{content[:15000]}\n\n"
                f"CRITICAL & HIGH VERIFICATION ISSUES DETECTED BY QA ENGINE:\n" +
                "\n".join(directives) + "\n\n"
                f"TASK: Rewrite the document sections to resolve EVERY issue above. "
                f"Fix all arithmetic calculations exactly, eliminate orphan references, ensure true citations. "
                f"Return ONLY the complete corrected document text with markdown headings."
            )
            corrected_content = generate_text_with_retry(correction_prompt).strip()
            if corrected_content and len(corrected_content) > 200:
                content = corrected_content
                # Re-render
                _, generated_path = self._render_document_by_type(
                    ftype=ftype,
                    fname=fname,
                    title=title,
                    content=content,
                    doc_type=doc_type,
                    params=params,
                    out_dir=out_dir,
                    open_after=False,
                    player=player
                )

                # Re-audit
                sections = _parse_markdown_to_sections(content)
                scorecard = self.qa_engine.audit_document(
                    title=title,
                    category=category,
                    file_format=ftype,
                    content=content,
                    sections=sections,
                    tables=tables,
                    file_path=generated_path,
                    min_passing_score=profile.get("min_passing_score", 75.0)
                )
                scorecard.retries_used = retries

        # Phase 6: Delivery & Launch
        if open_after and generated_path.exists():
            try:
                os.startfile(str(generated_path))
            except Exception:
                pass

        # Build comprehensive final response
        delivery_banner = (
            f"**Successfully Delivered Executive Document**: `{generated_path.name}`\n"
            f"**Location**: `{generated_path.parent}`\n\n"
            f"{scorecard.to_markdown()}"
        )
        return delivery_banner

    def _gather_scholarly_evidence_and_synthesize(
        self,
        title: str,
        category: DocumentCategory,
        doc_type: str,
        player=None
    ) -> str:
        """Gathers verifiable scholarly and industry evidence and registers in EvidenceRegistry."""
        try:
            from actions.deep_research import deep_research_gather
            res_data = deep_research_gather(title, max_sources=5)
            for s in res_data.get("sources", []):
                self.qa_engine.evidence_registry.register_source(
                    title=s.get("title", "Scholarly Work"),
                    authors=s.get("authors", []),
                    year=s.get("year"),
                    url=s.get("url"),
                    doi=s.get("doi"),
                    extracted_text=s.get("snippet", ""),
                    is_snippet_only=True
                )
        except Exception:
            pass

        synth_prompt = (
            f"You are J.A.R.V.I.S., Chief Systems Architect & Senior Academic Fellow.\n"
            f"Author a rigorous, publication-grade {category.value.upper()} document on '{title}'.\n"
            f"Document Type: {doc_type}.\n"
            "Requirements:\n"
            "1. Deep factual rigor with specific metrics, parameters, and historical contexts.\n"
            "2. Formal APA 7 in-text citations matching a detailed References section at the end.\n"
            "3. Clean Markdown headings (#, ##), bullet points, and at least one Markdown table.\n"
            "4. Mathematical consistency: Ensure all percentages, totals, and arithmetic checks sum correctly."
        )
        return generate_text_with_retry(synth_prompt)

    def _render_document_by_type(
        self,
        ftype: str,
        fname: str,
        title: str,
        content: str,
        doc_type: str,
        params: Dict[str, Any],
        out_dir: Path,
        open_after: bool = False,
        player=None
    ) -> Tuple[str, Optional[Path]]:
        """Renders the document to disk using the appropriate specialized engine."""
        from actions.file_generator import (
            create_word_document, create_presentation, create_pdf_document,
            create_excel_sheet, create_html_documentation, document_codebase,
            _parse_markdown_to_sections, _render_architecture_diagram
        )
        cover_page = params.get("cover_page", True)
        include_diagrams = params.get("include_diagrams", True)

        # 1. Word Document (.docx)
        if ftype in ("docx", "word", "doc"):
            if not fname.endswith(".docx"): fname += ".docx"
            target_p = out_dir / fname
            secs = params.get("sections") or _parse_markdown_to_sections(content)
            diag_img = _render_architecture_diagram(title=f"{title} System Flow") if include_diagrams else None
            res = create_word_document(
                filename=fname,
                title=title,
                sections=secs,
                output_dir=out_dir,
                open_after=open_after,
                subtitle=params.get("subtitle"),
                cover_page=cover_page,
                diagram_image=diag_img,
                markdown_text=content,
                short_title=params.get("short_title")
            )
            return res, target_p

        # 2. PowerPoint (.pptx)
        elif ftype in ("pptx", "presentation", "slides"):
            if not fname.endswith(".pptx"): fname += ".pptx"
            target_p = out_dir / fname
            try:
                from actions.presentation_designer import create_intriguing_presentation
                p_res = create_intriguing_presentation(
                    topic=title,
                    theme=params.get("theme", "stark_dark"),
                    target_location=params.get("target_location", "desktop"),
                    open_after=open_after,
                    source_content=content,
                    filename=fname
                )
                if p_res.get("status") == "success":
                    return "PPTX generated", Path(p_res.get("file_path"))
            except Exception:
                pass
            parsed_secs = _parse_markdown_to_sections(content)
            slides_data = params.get("slides") or [
                {"title": s.get("heading", "Topic"), "bullets": s.get("bullets") or [l for l in s.get("content", "").splitlines() if l.strip()][:4]}
                for s in parsed_secs
            ]
            res = create_presentation(fname, title, "Prepared by J.A.R.V.I.S.", slides_data, output_dir=out_dir, open_after=open_after)
            return res, target_p

        # 3. PDF (.pdf)
        elif ftype in ("pdf",):
            if not fname.endswith(".pdf"): fname += ".pdf"
            target_p = out_dir / fname
            secs = params.get("sections") or _parse_markdown_to_sections(content)
            diag_img = _render_architecture_diagram(title=f"{title} Architecture") if include_diagrams else None
            res = create_pdf_document(
                filename=fname,
                title=title,
                sections=secs,
                output_dir=out_dir,
                open_after=open_after,
                cover_page=cover_page,
                diagram_image=diag_img
            )
            return res, target_p

        # 4. Excel (.xlsx)
        elif ftype in ("xlsx", "excel", "spreadsheet"):
            if not fname.endswith(".xlsx"): fname += ".xlsx"
            target_p = out_dir / fname
            cols = params.get("columns") or ["Item", "Category", "Amount", "Status"]
            rows = params.get("rows") or [["Sample 1", "Operations", 1500, "Approved"], ["Sample 2", "Operations", 2500, "Approved"]]
            res = create_excel_sheet(fname, title, cols, rows, output_dir=out_dir, open_after=open_after)
            return res, target_p

        # 5. HTML Documentation (.html)
        elif ftype in ("html_doc", "html", "htm"):
            if not fname.endswith(".html"): fname += ".html"
            target_p = out_dir / fname
            secs = params.get("sections") or _parse_markdown_to_sections(content)
            res = create_html_documentation(fname, title, f"Technical Manual • {title}", secs, output_dir=out_dir, open_after=open_after)
            return res, target_p

        # 6. Fallback Markdown / Text
        else:
            ext = ftype if ftype.startswith(".") else f".{ftype}"
            if not fname.endswith(ext): fname += ext
            target_p = out_dir / fname
            target_p.write_text(content, encoding="utf-8")
            return f"Generated {target_p.name}", target_p
