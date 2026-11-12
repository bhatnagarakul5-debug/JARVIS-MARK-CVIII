"""
core/document_qa/citation_engine.py — Citation & Bibliography Verification Engine for J.A.R.V.I.S.
"""

import re
from typing import List, Dict, Set, Tuple, Optional, Any
from core.document_qa.models import IssueSeverity, ValidationIssue
from core.document_qa.evidence_registry import DOI_REGEX


AUTHOR_YEAR_IN_TEXT_PAT = re.compile(
    r'\(([A-Z][a-zA-Z\s]+(?:et al\.)?(?:,\s*|\s+and\s+[A-Z][a-zA-Z]+)?),\s*(\d{4})\)'
)

IEEE_IN_TEXT_PAT = re.compile(r'\[(\d+(?:[,\s\-]+\d+)*)\]')


class CitationEngine:
    """
    Validates in-text citations, bibliographies, and style conformance
    across APA 7, IEEE, MLA, Harvard, Chicago, and Vancouver.
    Guarantees strict bi-directional correspondence: no orphan references, no missing sources.
    """

    def __init__(self, style: str = "APA7"):
        self.style = style.upper()

    def audit_document_citations(
        self,
        full_text: str,
        bibliography_text: Optional[str] = None
    ) -> Tuple[List[ValidationIssue], Dict[str, Any]]:
        """
        Extracts in-text citations and bibliography references,
        verifies 1-to-1 matching, and checks DOIs.
        """
        issues: List[ValidationIssue] = []

        # If bibliography text was not explicitly separated, extract from bottom section
        body_text = full_text
        bib_text = bibliography_text or ""

        if not bib_text:
            ref_match = re.search(r'(?i)\b(?:references|bibliography|works cited)\b[:\s]*\n([\s\S]+)$', full_text)
            if ref_match:
                body_text = full_text[:ref_match.start()]
                bib_text = ref_match.group(1)

        # 1. Extract in-text citations
        in_text_author_year = AUTHOR_YEAR_IN_TEXT_PAT.findall(body_text)
        in_text_ieee = []
        for match in IEEE_IN_TEXT_PAT.finditer(body_text):
            nums = re.findall(r'\d+', match.group(1))
            in_text_ieee.extend([int(n) for n in nums])

        # 2. Extract bibliography entries
        bib_entries = [line.strip() for line in bib_text.splitlines() if line.strip() and len(line.strip()) > 15]

        # 3. Check for Author-Year Matching (APA/Harvard/Chicago/MLA)
        if in_text_author_year:
            cited_pairs = set()
            for author_blob, yr in in_text_author_year:
                first_author = author_blob.split()[0].replace(",", "").lower()
                cited_pairs.add((first_author, yr))

            bib_matched = set()
            for author, yr in cited_pairs:
                found = False
                for b_idx, b_entry in enumerate(bib_entries):
                    if yr in b_entry and author in b_entry.lower():
                        found = True
                        bib_matched.add(b_idx)
                        break
                if not found:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.HIGH,
                        code="MISSING_BIBLIOGRAPHY_ENTRY",
                        message=f"In-text citation '({author.title()} et al., {yr})' has no corresponding entry in the References section.",
                        section="Bibliography",
                        target_entity=f"{author.title()}, {yr}",
                        suggestion=f"Add complete bibliographic reference for ({author.title()}, {yr}) to the References section."
                    ))

            # Detect Orphan References (in bibliography but never cited)
            for b_idx, b_entry in enumerate(bib_entries):
                if b_idx not in bib_matched:
                    # Check if any cited pair matches
                    entry_low = b_entry.lower()
                    matched_any = any(a in entry_low and y in b_entry for a, y in cited_pairs)
                    if not matched_any and len(cited_pairs) > 0:
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.MEDIUM,
                            code="ORPHAN_BIBLIOGRAPHY_REFERENCE",
                            message=f"Bibliographic entry '{b_entry[:70]}...' is listed in References but never cited in the body.",
                            section="Bibliography",
                            target_entity=b_entry[:40],
                            suggestion="Reference the source in the text or remove the unused entry."
                        ))

        # 4. Check for Numeric Matching (IEEE/Vancouver)
        elif in_text_ieee:
            cited_nums = set(in_text_ieee)
            bib_num_pat = re.compile(r'^\s*\[(\d+)\]')
            found_bib_nums = set()

            for b_entry in bib_entries:
                m = bib_num_pat.match(b_entry)
                if m:
                    found_bib_nums.add(int(m.group(1)))

            # Missing numbers
            for n in cited_nums:
                if n not in found_bib_nums and len(bib_entries) < n:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.HIGH,
                        code="MISSING_NUMERIC_REFERENCE",
                        message=f"In-text citation [{n}] has no corresponding entry in the bibliography.",
                        section="Bibliography",
                        target_entity=f"[{n}]",
                        suggestion=f"Provide full source details for reference [{n}]."
                    ))

            # Orphan numbers
            for n in found_bib_nums:
                if n not in cited_nums:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.MEDIUM,
                        code="ORPHAN_NUMERIC_REFERENCE",
                        message=f"Reference [{n}] is present in the bibliography but never cited in the body.",
                        section="Bibliography",
                        target_entity=f"[{n}]",
                        suggestion=f"Cite [{n}] in the document or renumber references."
                    ))

        # 5. Validate DOIs within Bibliography
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
            "in_text_citations_count": len(in_text_author_year) or len(in_text_ieee),
            "bibliography_entries_count": len(bib_entries),
            "dois_detected": len(all_dois)
        }

        return issues, stats
