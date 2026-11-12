"""
core/document_qa/qa_engine.py — Autonomous Quality Assurance, Scorecard & Self-Correction Engine for J.A.R.V.I.S.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.document_qa.models import (
    DocumentCategory, QAStatus, IssueSeverity, ValidationIssue,
    QualityScorecard, Claim, SourceEvidence
)
from core.document_qa.config import get_qa_config
from core.document_qa.evidence_registry import EvidenceRegistry
from core.document_qa.claim_verifier import ClaimVerifier
from core.document_qa.math_validator import MathValidator
from core.document_qa.citation_engine import CitationEngine
from core.document_qa.post_render_inspectors import (
    DocxQualityInspector, PdfQualityInspector, XlsxQualityInspector,
    PptxQualityInspector, HtmlQualityInspector, MarkdownQualityInspector
)


class DocumentQAEngine:
    """
    Independent Quality Assurance and Verification Arbiter.
    Conducts multi-dimensional evaluations, computes scorecards, enforces hard validation gates,
    and formulates targeted correction directives.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_qa_config()
        self.evidence_registry = EvidenceRegistry()
        self.claim_verifier = ClaimVerifier(self.evidence_registry)
        self.math_validator = MathValidator()
        self.citation_engine = CitationEngine(self.config.get("default_citation_style", "APA7"))

    def audit_document(
        self,
        title: str,
        category: DocumentCategory,
        file_format: str,
        content: str,
        sections: Optional[List[Dict[str, Any]]] = None,
        tables: Optional[List[List[Any]]] = None,
        file_path: Optional[Path] = None,
        min_passing_score: Optional[float] = None
    ) -> QualityScorecard:
        """Runs the full multi-dimensional QA inspection suite."""
        min_pass = min_passing_score or self.config.get("min_passing_score", 75.0)
        scorecard = QualityScorecard(
            document_title=title,
            category=category,
            file_format=file_format.lower().lstrip("."),
            file_path=str(file_path) if file_path else None
        )

        all_issues: List[ValidationIssue] = []

        # 1. Source & Evidence Integrity
        source_issues = self.evidence_registry.audit_sources()
        all_issues.extend(source_issues)
        s_deduct = sum(25 if i.severity == IssueSeverity.CRITICAL else 15 if i.severity == IssueSeverity.HIGH else 5 for i in source_issues)
        scorecard.source_integrity = max(0.0, 100.0 - s_deduct)

        # 2. Claim-Level Fact Verification
        self.claim_verifier.extract_and_classify_claims(content)
        claim_issues = self.claim_verifier.audit_claims()
        all_issues.extend(claim_issues)
        c_deduct = sum(25 if i.severity == IssueSeverity.CRITICAL else 12 if i.severity == IssueSeverity.HIGH else 4 for i in claim_issues)
        scorecard.factual_reliability = max(0.0, 100.0 - c_deduct)
        scorecard.claims = self.claim_verifier.claims

        # 3. Mathematical & Computational Validation
        math_issues = self.math_validator.validate_arithmetic_statements(content)
        if tables:
            math_issues.extend(self.math_validator.validate_table_totals(tables))
        all_issues.extend(math_issues)
        m_deduct = sum(30 if i.severity == IssueSeverity.CRITICAL else 15 if i.severity == IssueSeverity.HIGH else 5 for i in math_issues)
        scorecard.mathematical_accuracy = max(0.0, 100.0 - m_deduct)

        # 4. Citation & Bibliography Verification
        cat_profile = self.config.get("category_profiles", {}).get(category.value, {})
        if cat_profile.get("require_citations", False) or "references" in content.lower():
            cit_issues, _ = self.citation_engine.audit_document_citations(content)
            all_issues.extend(cit_issues)
            cit_deduct = sum(25 if i.severity == IssueSeverity.CRITICAL else 15 if i.severity == IssueSeverity.HIGH else 6 for i in cit_issues)
            scorecard.citation_accuracy = max(0.0, 100.0 - cit_deduct)
        else:
            scorecard.citation_accuracy = 100.0

        # 5. Post-Rendering Inspection on Disk
        format_issues: List[ValidationIssue] = []
        if file_path and file_path.exists():
            ext = file_path.suffix.lower()
            if ext == ".docx":
                format_issues = DocxQualityInspector.inspect(file_path)
            elif ext == ".pdf":
                format_issues = PdfQualityInspector.inspect(file_path)
            elif ext == ".xlsx":
                format_issues = XlsxQualityInspector.inspect(file_path)
            elif ext == ".pptx":
                max_w = cat_profile.get("max_words_per_slide", 110)
                format_issues = PptxQualityInspector.inspect(file_path, max_words_per_slide=max_w)
            elif ext in (".html", ".htm"):
                format_issues = HtmlQualityInspector.inspect(file_path)
            elif ext in (".md", ".txt"):
                format_issues = MarkdownQualityInspector.inspect(file_path)

        all_issues.extend(format_issues)
        f_deduct = sum(25 if i.severity == IssueSeverity.CRITICAL else 12 if i.severity == IssueSeverity.HIGH else 4 for i in format_issues)
        scorecard.formatting_quality = max(0.0, 100.0 - f_deduct)

        # Structural completeness
        sec_count = len(sections) if sections else (content.count("\n# ") + content.count("\n## ") + 1)
        if sec_count < 2 and len(content) > 300:
            all_issues.append(ValidationIssue(
                severity=IssueSeverity.MEDIUM,
                code="POOR_SECTION_HIERARCHY",
                message=f"Document lacks sufficient section demarcation ({sec_count} section detected).",
                suggestion="Divide content into clear thematic sections with descriptive headings."
            ))
            scorecard.structural_completeness = 70.0
        else:
            scorecard.structural_completeness = 100.0

        # Populate scorecard
        scorecard.issues = all_issues
        scorecard.compute_overall_score()
        scorecard.determine_status(min_pass)

        # Build summary
        crit_count = sum(1 for i in all_issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in all_issues if i.severity == IssueSeverity.HIGH)
        if scorecard.status == QAStatus.VALIDATED:
            scorecard.summary = f"All {len(scorecard.claims)} claims, citations, and mathematical formulas verified with zero blocking flaws. Document conforms to {category.value.upper()} standards."
        elif crit_count > 0:
            scorecard.summary = f"Delivery blocked: Detected {crit_count} CRITICAL integrity flaw(s) (e.g. arithmetic discrepancy or citation failure)."
        elif high_count > 0:
            scorecard.summary = f"Review required: Found {high_count} HIGH severity verification item(s)."
        else:
            scorecard.summary = f"Document scored {scorecard.overall_score}/100, which is below the category threshold of {min_pass}."

        self._save_audit_log(scorecard)
        return scorecard

    def generate_correction_instructions(self, scorecard: QualityScorecard) -> List[str]:
        """
        Formulates targeted, actionable correction directives for CRITICAL and HIGH severity issues
        so the generation engine can perform surgical corrections without full regeneration.
        """
        directives: List[str] = []
        for issue in scorecard.issues:
            if issue.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH):
                directive = f"- [{issue.code}] in {issue.section or 'Document'}: {issue.message}"
                if issue.suggestion:
                    directive += f" -> Required Fix: {issue.suggestion}"
                directives.append(directive)
        return directives

    def _save_audit_log(self, scorecard: QualityScorecard):
        """Persists audit scorecard to disk."""
        if not self.config.get("log_audit_trail", True):
            return
        try:
            log_dir = Path(__file__).resolve().parent.parent.parent / self.config.get("audit_log_dir", "memory/document_qa_logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            slug = "".join(c if c.isalnum() else "_" for c in scorecard.document_title[:24]).strip("_")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"qa_audit_{slug}_{ts}.json"
            log_file.write_text(json.dumps(scorecard.to_dict(), indent=2), encoding="utf-8")
        except Exception:
            pass
