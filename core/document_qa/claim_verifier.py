"""
core/document_qa/claim_verifier.py — Claim-Level Fact Verification & Epistemic Classifier for J.A.R.V.I.S. Mark 108
Accelerated via `jarvis_rust_core` Native Rust Exoskeleton.
"""

import re
from typing import List, Optional
from core.document_qa.models import (
    Claim, ClaimType, ClaimStatus, IssueSeverity, ValidationIssue
)
from core.document_qa.evidence_registry import EvidenceRegistry
from core.rust_bridge import (
    classify_claim_type as _classify_rust,
    extract_material_sentences as _extract_sentences_rust,
    verify_claim_concordance as _verify_concordance_rust,
)


class ClaimVerifier:
    """
    Extracts, classifies, and verifies factual claims against the Evidence Registry
    using the `jarvis_rust_core` Native Rust Exoskeleton.
    """

    def __init__(self, registry: Optional[EvidenceRegistry] = None):
        self.registry = registry or EvidenceRegistry()
        self.claims: List[Claim] = []
        self._claim_counter: int = 1

    def extract_and_classify_claims(self, text: str, section: Optional[str] = None) -> List[Claim]:
        """
        Extracts material claims from text sentences via `jarvis_rust_core`,
        classifies their epistemic type, and matches them against registered evidence.
        """
        extracted: List[Claim] = []
        for clean_s in _extract_sentences_rust(text or ""):
            ctype = self.classify_claim_type(clean_s)
            c_id = f"C{self._claim_counter}"
            self._claim_counter += 1

            claim = Claim(
                claim_id=c_id,
                text=clean_s,
                claim_type=ctype,
                section=section,
            )
            self.verify_claim(claim)
            self.claims.append(claim)
            extracted.append(claim)

        return extracted

    def classify_claim_type(self, sentence: str) -> ClaimType:
        """Classifies the epistemic nature of the claim via `jarvis_rust_core`."""
        label = _classify_rust(sentence or "")
        mapping = {
            "proposed_model": ClaimType.PROPOSED_MODEL,
            "prediction": ClaimType.PREDICTION,
            "interpretation": ClaimType.INTERPRETATION,
            "recommendation": ClaimType.RECOMMENDATION,
            "hypothesis": ClaimType.HYPOTHESIS,
            "fact": ClaimType.FACT,
        }
        return mapping.get(label, ClaimType.FACT)

    def verify_claim(self, claim: Claim) -> ClaimStatus:
        """
        Verifies an individual claim against all sources in the registry via `jarvis_rust_core`.
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

        if not self.registry.sources:
            claim.status = ClaimStatus.UNVERIFIED
            claim.confidence = 0.3
            claim.reasoning = "No primary or secondary sources registered in Evidence Registry."
            return claim.status

        sources_list = [
            (s_id, s.extracted_text or "")
            for s_id, s in self.registry.sources.items()
            if s.extracted_text
        ]
        status_s, conf, ev_ids, conf_notes, reason = _verify_concordance_rust(
            claim.text, sources_list
        )

        status_map = {
            "verified": ClaimStatus.VERIFIED,
            "conflicting_evidence": ClaimStatus.CONFLICTING_EVIDENCE,
            "unverified": ClaimStatus.UNVERIFIED,
        }
        claim.status = status_map.get(status_s, ClaimStatus.UNVERIFIED)
        claim.confidence = conf
        claim.evidence_ids = ev_ids
        if conf_notes:
            claim.conflicting_notes = conf_notes
        claim.reasoning = reason
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
                    suggestion="Explicitly state the disagreement in the text or reconcile values with primary filings.",
                ))

            elif c.status == ClaimStatus.UNVERIFIED and c.claim_type == ClaimType.FACT:
                has_hard_metric = bool(re.search(r"\b(?:\$\d+|\d+%)", c.text))
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HIGH if has_hard_metric else IssueSeverity.MEDIUM,
                    code="UNVERIFIED_FACTUAL_CLAIM",
                    message=f"Factual assertion '{c.text[:80]}...' could not be verified against registered evidence.",
                    section=c.section,
                    target_entity=c.claim_id,
                    suggestion="Ground claim with an authoritative source or rephrase with appropriate uncertainty.",
                ))

        return issues
