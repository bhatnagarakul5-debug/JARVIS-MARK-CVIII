"""
core/document_qa/claim_verifier.py — Claim-Level Fact Verification & Epistemic Classifier for J.A.R.V.I.S.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from core.document_qa.models import (
    Claim, ClaimType, ClaimStatus, IssueSeverity, ValidationIssue
)
from core.document_qa.evidence_registry import EvidenceRegistry


PREDICTION_MARKERS = [
    r"\bwill\b", r"\bexpect(?:ed|s)?\b", r"\bproject(?:ed|s)?\b", r"\bforecast(?:ed|s)?\b",
    r"\banticipat(?:ed|es)?\b", r"\bestimat(?:ed|es)?\b", r"\bby\s+20(?:3[0-9]|4[0-9]|5[0-9])\b",
    r"\bpredict(?:ed|s)?\b"
]

INTERPRETATION_MARKERS = [
    r"\bsuggests?\b", r"\bindicates?\b", r"\bimplies?\b", r"\bargues?\b",
    r"\bdemonstrates?\b", r"\binterprets?\b", r"\bfrom\s+our\s+analysis\b"
]

PROPOSED_MODEL_MARKERS = [
    r"\bwe\s+propose\b", r"\bour\s+model\b", r"\bproposed\s+framework\b",
    r"\bjarvis\s+formulation\b", r"\banalytical\s+model\s+proposed\b"
]


class ClaimVerifier:
    """
    Extracts, classifies, and verifies factual claims against the Evidence Registry.
    Guarantees strict separation between historical facts, predictions, interpretations,
    and proposed analytical models.
    """

    def __init__(self, registry: Optional[EvidenceRegistry] = None):
        self.registry = registry or EvidenceRegistry()
        self.claims: List[Claim] = []
        self._claim_counter: int = 1

    def extract_and_classify_claims(self, text: str, section: Optional[str] = None) -> List[Claim]:
        """
        Extracts material claims from text sentences, classifies their epistemic type,
        and matches them against registered evidence.
        """
        extracted: List[Claim] = []
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)

        for sent in sentences:
            clean_s = sent.strip()
            if not clean_s or len(clean_s) < 20:
                continue

            # Check if sentence contains material statements (numbers, dates, entities, assertions)
            has_metric = bool(re.search(r'\b(?:\$?\d+(?:\.\d+)?%?|\d{4})\b', clean_s))
            has_assertion = any(k in clean_s.lower() for k in (
                "acquired", "founded", "increased", "decreased", "reached", "demonstrated",
                "concluded", "propose", "proposed", "hypothesis", "expect", "predict",
                "assume", "recommend", "scales", "framework", "architecture"
            ))

            if not (has_metric or has_assertion):
                continue

            ctype = self.classify_claim_type(clean_s)
            c_id = f"C{self._claim_counter}"
            self._claim_counter += 1

            claim = Claim(
                claim_id=c_id,
                text=clean_s,
                claim_type=ctype,
                section=section
            )
            self.verify_claim(claim)
            self.claims.append(claim)
            extracted.append(claim)

        return extracted

    def classify_claim_type(self, sentence: str) -> ClaimType:
        """Classifies the epistemic nature of the claim."""
        low = sentence.lower()

        for pat in PROPOSED_MODEL_MARKERS:
            if re.search(pat, low):
                return ClaimType.PROPOSED_MODEL

        for pat in PREDICTION_MARKERS:
            if re.search(pat, low):
                return ClaimType.PREDICTION

        for pat in INTERPRETATION_MARKERS:
            if re.search(pat, low):
                return ClaimType.INTERPRETATION

        if any(k in low for k in ("we recommend", "should implement", "must consider", "actionable step")):
            return ClaimType.RECOMMENDATION

        if any(k in low for k in ("assuming that", "assume", "hypothesis", "under the premise")):
            return ClaimType.HYPOTHESIS

        return ClaimType.FACT

    def verify_claim(self, claim: Claim) -> ClaimStatus:
        """
        Verifies an individual claim against all sources in the registry.
        Detects conflicting evidence and guards against predictions being stated as facts.
        """
        if claim.claim_type == ClaimType.PROPOSED_MODEL:
            claim.status = ClaimStatus.NOT_APPLICABLE
            claim.confidence = 1.0
            claim.reasoning = "JARVIS proposed analytical model; labeled as author formulation."
            return claim.status

        if claim.claim_type in (ClaimType.PREDICTION, ClaimType.HYPOTHESIS):
            claim.status = ClaimStatus.VERIFIED if claim.confidence > 0.6 else ClaimStatus.PARTIALLY_VERIFIED
            claim.reasoning = f"Epistemic status verified as {claim.claim_type.value}; not treated as historical fact."
            return claim.status

        # If no sources exist yet in registry
        if not self.registry.sources:
            claim.status = ClaimStatus.UNVERIFIED
            claim.confidence = 0.3
            claim.reasoning = "No primary or secondary sources registered in Evidence Registry."
            return claim.status

        # Search matching evidence across sources
        matching_sources = []
        conflicting_sources = []

        claim_years = set(re.findall(r'\b(?:19|20)\d{2}\b', claim.text))
        claim_metrics = set(re.findall(r'\b\d+(?:\.\d+)?\b', claim.text)) - claim_years

        for s_id, s in self.registry.sources.items():
            s_text = s.extracted_text.lower()
            if not s_text:
                continue

            # Check overlap
            claim_words = [w for w in re.findall(r'[a-z]{4,}', claim.text.lower()) if w not in ("which", "that", "there", "their", "about", "under", "total")]
            overlap = sum(1 for w in claim_words if w in s_text)
            overlap_ratio = overlap / max(1, len(claim_words))

            if overlap_ratio >= 0.35:
                s_years = set(re.findall(r'\b(?:19|20)\d{2}\b', s_text))
                s_metrics = set(re.findall(r'\b\d+(?:\.\d+)?\b', s_text)) - s_years

                # Check metric and year concordance
                if claim_metrics and s_metrics and not (claim_metrics & s_metrics):
                    conflicting_sources.append(s_id)
                elif claim_years and s_years and not (claim_years & s_years):
                    conflicting_sources.append(s_id)
                elif (claim_metrics & s_metrics) or (claim_years & s_years):
                    matching_sources.append(s_id)
                else:
                    matching_sources.append(s_id)

        if matching_sources:
            claim.evidence_ids = matching_sources
            if conflicting_sources:
                claim.status = ClaimStatus.CONFLICTING_EVIDENCE
                claim.conflicting_notes = f"Discrepancy detected against sources: {conflicting_sources}"
                claim.confidence = 0.5
                claim.reasoning = f"Supported by {matching_sources} but contradicted by {conflicting_sources}."
            else:
                claim.status = ClaimStatus.VERIFIED
                claim.confidence = 0.95
                claim.reasoning = f"Direct concordance found with source(s): {matching_sources}."
        elif conflicting_sources:
            claim.status = ClaimStatus.CONFLICTING_EVIDENCE
            claim.conflicting_notes = f"Numerical conflict with registered source(s): {conflicting_sources}"
            claim.confidence = 0.2
            claim.reasoning = f"Numerical values contradict sources: {conflicting_sources}."
        else:
            claim.status = ClaimStatus.UNVERIFIED
            claim.confidence = 0.4
            claim.reasoning = "No registered source text corroborated this specific assertion."

        return claim.status

    def audit_claims(self) -> List[ValidationIssue]:
        """Audits all claims and generates validation issues for unverified or conflicting assertions."""
        issues: List[ValidationIssue] = []

        for c in self.claims:
            if c.status == ClaimStatus.CONFLICTING_EVIDENCE:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HIGH,
                    code="CONFLICTING_EVIDENCE_CLAIM",
                    message=f"Claim '{c.text[:80]}...' has conflicting numerical evidence: {c.conflicting_notes}",
                    section=c.section,
                    target_entity=c.claim_id,
                    suggestion="Explicitly state the disagreement in the text or reconcile values with primary filings."
                ))

            elif c.status == ClaimStatus.UNVERIFIED and c.claim_type == ClaimType.FACT:
                # If claim contains specific metrics or dates, flag as high/medium
                has_hard_metric = bool(re.search(r'\b(?:\$\d+|\d+%)', c.text))
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HIGH if has_hard_metric else IssueSeverity.MEDIUM,
                    code="UNVERIFIED_FACTUAL_CLAIM",
                    message=f"Factual assertion '{c.text[:80]}...' could not be verified against registered evidence.",
                    section=c.section,
                    target_entity=c.claim_id,
                    suggestion="Ground claim with an authoritative source or rephrase with appropriate uncertainty."
                ))

        return issues
