"""
core/document_qa/models.py — Data models, enums, and scorecard structures for J.A.R.V.I.S. Document QA.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class DocumentCategory(str, Enum):
    ACADEMIC = "academic"
    BUSINESS = "business"
    FINANCIAL = "financial"
    PROFESSIONAL = "professional"
    TECHNICAL = "technical"
    CREATIVE_PRESENTATION = "creative_presentation"
    SPREADSHEET = "spreadsheet"
    GENERAL = "general"


class SourceTier(int, Enum):
    TIER_1_PRIMARY = 1      # Official filings, government pub, primary docs, SEC/EDGAR, RFCs
    TIER_2_SCHOLARLY = 2    # Peer-reviewed journal, IEEE, ArXiv, OpenAlex, CrossRef indexed
    TIER_3_JOURNALISTIC = 3 # Bloomberg, Reuters, WSJ, FT, authoritative industry press
    TIER_4_SECONDARY = 4    # Community blogs, Wikipedia, medium posts, discussions
    TIER_5_UNVERIFIED = 5   # Unsupported snippets, hallucinated links, unverified forums


class ClaimType(str, Enum):
    FACT = "fact"
    INTERPRETATION = "interpretation"
    PREDICTION = "prediction"
    ASSUMPTION = "assumption"
    HYPOTHESIS = "hypothesis"
    RECOMMENDATION = "recommendation"
    PROPOSED_MODEL = "proposed_model"


class ClaimStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    UNVERIFIED = "UNVERIFIED"
    OUTDATED = "OUTDATED"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"  # Blocks VALIDATED status (fabrications, math errors, file corruption)
    HIGH = "HIGH"          # Blocks VALIDATED status (unsupported claims, broken citations)
    MEDIUM = "MEDIUM"      # Warning (formatting inconsistencies, weak attribution)
    LOW = "LOW"            # Advisory (minor styling or cosmetic spacing)


class QAStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATION_IN_PROGRESS = "VALIDATION_IN_PROGRESS"
    NEEDS_REVISION = "NEEDS_REVISION"
    REQUIRES_USER_REVIEW = "REQUIRES_USER_REVIEW"
    VALIDATED = "VALIDATED"


@dataclass
class SourceEvidence:
    source_id: str
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    publication_date: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    category: str = "general"
    tier: SourceTier = SourceTier.TIER_3_JOURNALISTIC
    authority_level: str = "Medium"
    extracted_text: str = ""
    verified: bool = False
    is_snippet_only: bool = False
    doi_verified: bool = False
    journal_or_publisher: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = int(self.tier)
        return d


@dataclass
class Claim:
    claim_id: str
    text: str
    claim_type: ClaimType = ClaimType.FACT
    evidence_ids: List[str] = field(default_factory=list)
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    confidence: float = 0.0
    reasoning: str = ""
    conflicting_notes: Optional[str] = None
    section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "claim_type": self.claim_type.value,
            "evidence_ids": self.evidence_ids,
            "status": self.status.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "conflicting_notes": self.conflicting_notes,
            "section": self.section
        }


@dataclass
class ValidationIssue:
    severity: IssueSeverity
    code: str
    message: str
    section: Optional[str] = None
    target_entity: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "section": self.section,
            "target_entity": self.target_entity,
            "suggestion": self.suggestion
        }


@dataclass
class QualityScorecard:
    document_title: str
    category: DocumentCategory
    file_format: str
    factual_reliability: float = 100.0
    source_integrity: float = 100.0
    citation_accuracy: float = 100.0
    technical_correctness: float = 100.0
    mathematical_accuracy: float = 100.0
    structural_completeness: float = 100.0
    formatting_quality: float = 100.0
    numerical_consistency: float = 100.0
    overall_score: float = 100.0
    status: QAStatus = QAStatus.DRAFT
    issues: List[ValidationIssue] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    sources: List[SourceEvidence] = field(default_factory=list)
    summary: str = ""
    file_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    retries_used: int = 0

    def compute_overall_score(self) -> float:
        """Computes weighted composite score across all validation dimensions."""
        weights = {
            "factual_reliability": 0.20,
            "source_integrity": 0.15,
            "citation_accuracy": 0.15,
            "technical_correctness": 0.15,
            "mathematical_accuracy": 0.15,
            "structural_completeness": 0.08,
            "formatting_quality": 0.07,
            "numerical_consistency": 0.05
        }
        composite = (
            self.factual_reliability * weights["factual_reliability"] +
            self.source_integrity * weights["source_integrity"] +
            self.citation_accuracy * weights["citation_accuracy"] +
            self.technical_correctness * weights["technical_correctness"] +
            self.mathematical_accuracy * weights["mathematical_accuracy"] +
            self.structural_completeness * weights["structural_completeness"] +
            self.formatting_quality * weights["formatting_quality"] +
            self.numerical_consistency * weights["numerical_consistency"]
        )
        self.overall_score = round(max(0.0, min(100.0, composite)), 1)
        return self.overall_score

    def determine_status(self, min_passing_score: float = 75.0) -> QAStatus:
        """
        Enforces HARD VALIDATION GATES:
        A document scoring 95/100 but containing a fabricated source or mathematical failure
        MUST NEVER receive VALIDATED status.
        """
        has_critical = any(i.severity == IssueSeverity.CRITICAL for i in self.issues)
        has_high = any(i.severity == IssueSeverity.HIGH for i in self.issues)

        if has_critical:
            self.status = QAStatus.NEEDS_REVISION
        elif has_high:
            self.status = QAStatus.REQUIRES_USER_REVIEW
        elif self.overall_score < min_passing_score:
            self.status = QAStatus.NEEDS_REVISION
        else:
            self.status = QAStatus.VALIDATED

        return self.status

    def can_deliver_as_validated(self) -> bool:
        """Returns True only if no critical or high severity blocking issues remain."""
        return self.status == QAStatus.VALIDATED

    def to_markdown(self) -> str:
        """Formats the scorecard into a publication-grade markdown summary."""
        status_icons = {
            QAStatus.VALIDATED: "🟢 VALIDATED",
            QAStatus.REQUIRES_USER_REVIEW: "🟡 REQUIRES USER REVIEW",
            QAStatus.NEEDS_REVISION: "🔴 NEEDS REVISION",
            QAStatus.DRAFT: "⚪ DRAFT",
            QAStatus.VALIDATION_IN_PROGRESS: "🔄 VALIDATION IN PROGRESS"
        }
        st_text = status_icons.get(self.status, str(self.status.value))

        md = [
            f"### 🛡️ J.A.R.V.I.S. Autonomous Document Quality Scorecard",
            f"**Document**: `{self.document_title}` | **Format**: `{self.file_format.upper()}` | **Category**: `{self.category.value.upper()}`",
            f"**QA Verdict**: **{st_text}** | **Overall QA Score**: **{self.overall_score}/100**",
            "",
            "| Quality Assessment Dimension | Score | Status | Weight |",
            "| :--- | :---: | :---: | :---: |",
            f"| Factual Reliability | {self.factual_reliability:.1f}% | {'✓' if self.factual_reliability >= 80 else '⚠'} | 20% |",
            f"| Source Integrity | {self.source_integrity:.1f}% | {'✓' if self.source_integrity >= 80 else '⚠'} | 15% |",
            f"| Citation Accuracy | {self.citation_accuracy:.1f}% | {'✓' if self.citation_accuracy >= 80 else '⚠'} | 15% |",
            f"| Technical Correctness | {self.technical_correctness:.1f}% | {'✓' if self.technical_correctness >= 80 else '⚠'} | 15% |",
            f"| Mathematical & Data Accuracy | {self.mathematical_accuracy:.1f}% | {'✓' if self.mathematical_accuracy >= 80 else '⚠'} | 15% |",
            f"| Structural Completeness | {self.structural_completeness:.1f}% | {'✓' if self.structural_completeness >= 80 else '⚠'} | 8% |",
            f"| Formatting & Layout Integrity | {self.formatting_quality:.1f}% | {'✓' if self.formatting_quality >= 80 else '⚠'} | 7% |",
            f"| Numerical Consistency | {self.numerical_consistency:.1f}% | {'✓' if self.numerical_consistency >= 80 else '⚠'} | 5% |",
            ""
        ]

        if self.issues:
            md.append("#### 📋 Detected Issues & Verification Flags:")
            for issue in self.issues[:8]:
                badge = {
                    IssueSeverity.CRITICAL: "🚨 [CRITICAL]",
                    IssueSeverity.HIGH: "⚠️ [HIGH]",
                    IssueSeverity.MEDIUM: "⚡ [MEDIUM]",
                    IssueSeverity.LOW: "ℹ️ [LOW]"
                }.get(issue.severity, "[ISSUE]")
                loc = f" in `{issue.section}`" if issue.section else ""
                md.append(f"- **{badge}** {issue.code}{loc}: {issue.message}")
                if issue.suggestion:
                    md.append(f"  *Resolution: {issue.suggestion}*")
            if len(self.issues) > 8:
                md.append(f"- *...and {len(self.issues) - 8} more minor items recorded in audit log.*")
            md.append("")

        if self.summary:
            md.append(f"> **Auditor Summary**: {self.summary}")

        return "\n".join(md)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_title": self.document_title,
            "category": self.category.value,
            "file_format": self.file_format,
            "factual_reliability": self.factual_reliability,
            "source_integrity": self.source_integrity,
            "citation_accuracy": self.citation_accuracy,
            "technical_correctness": self.technical_correctness,
            "mathematical_accuracy": self.mathematical_accuracy,
            "structural_completeness": self.structural_completeness,
            "formatting_quality": self.formatting_quality,
            "numerical_consistency": self.numerical_consistency,
            "overall_score": self.overall_score,
            "status": self.status.value,
            "issues": [i.to_dict() for i in self.issues],
            "claims_count": len(self.claims),
            "sources_count": len(self.sources),
            "summary": self.summary,
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "retries_used": self.retries_used
        }
