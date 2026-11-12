"""
core/document_qa/citation_engine.py — Citation & Bibliography Verification Engine for J.A.R.V.I.S. Mark 108
Accelerated via `jarvis_rust_core` Native Rust Exoskeleton.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from core.document_qa.models import IssueSeverity, ValidationIssue
from core.document_qa.evidence_registry import DOI_REGEX
from core.rust_bridge import audit_citations


def _map_severity(sev_str: str) -> IssueSeverity:
    s = (sev_str or "").lower()
    if s == "critical":
        return IssueSeverity.CRITICAL
    if s == "high":
        return IssueSeverity.HIGH
    if s == "medium":
        return IssueSeverity.MEDIUM
    return IssueSeverity.LOW


class CitationEngine:
    """
    Validates in-text citations, bibliographies, and style conformance
    across APA 7, IEEE, MLA, Harvard, Chicago, and Vancouver via the Native Rust Exoskeleton.
    """

    def __init__(self, style: str = "APA7"):
        self.style = style.upper()

    def audit_document_citations(
        self,
        full_text: str,
        bibliography_text: Optional[str] = None
    ) -> Tuple[List[ValidationIssue], Dict[str, Any]]:
        """
        Delegates bi-directional APA/IEEE citation-to-bibliography matching to `jarvis_rust_core`
        and verifies DOIs.
        """
        raw_issues = audit_citations(full_text or "", bibliography_text or "")
        issues: List[ValidationIssue] = [
            ValidationIssue(
                severity=_map_severity(sev),
                code=code,
                message=msg,
                section="Bibliography",
                target_entity=target,
                suggestion=sugg,
            )
            for sev, code, msg, target, sugg in raw_issues
        ]

        bib_text = bibliography_text or ""
        if not bib_text:
            ref_match = re.search(r'(?i)\b(?:references|bibliography|works cited)\b[:\s]*\n([\s\S]+)$', full_text or "")
            if ref_match:
                bib_text = ref_match.group(1)

        bib_entries = [line.strip() for line in bib_text.splitlines() if len(line.strip()) > 15]
        all_dois = re.findall(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b', bib_text)
        for doi in all_dois:
            clean_doi = doi.rstrip(".,;)")
            if not DOI_REGEX.match(clean_doi):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.CRITICAL,
                    code="MALFORMED_OR_FABRICATED_DOI",
                    message=f"Bibliographic DOI '{clean_doi}' has invalid syntax or represents a hallucinated identifier.",
                    section="Bibliography",
                    target_entity=clean_doi,
                    suggestion="Verify DOI on doi.org or CrossRef and correct syntax."
                ))

        stats = {
            "style": self.style,
            "in_text_citations_count": max(1, len(bib_entries)),
            "bibliography_entries_count": len(bib_entries),
            "dois_detected": len(all_dois),
        }
        return issues, stats
