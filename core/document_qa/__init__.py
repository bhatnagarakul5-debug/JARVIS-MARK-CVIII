"""
core/document_qa — J.A.R.V.I.S. Universal Document Intelligence, Generation & Quality Assurance Engine.
"""

from core.document_qa.models import (
    DocumentCategory,
    SourceTier,
    ClaimType,
    ClaimStatus,
    IssueSeverity,
    QAStatus,
    SourceEvidence,
    Claim,
    ValidationIssue,
    QualityScorecard
)
from core.document_qa.config import get_qa_config, get_category_profile, update_qa_config
from core.document_qa.evidence_registry import EvidenceRegistry
from core.rust_bridge import (
    classify_document_request,
    ClaimVerifier,
    MathValidator,
    CitationEngine,
)
from core.document_qa.post_render_inspectors import (
    DocxQualityInspector,
    PdfQualityInspector,
    XlsxQualityInspector,
    PptxQualityInspector,
    HtmlQualityInspector,
    MarkdownQualityInspector
)
from core.document_qa.qa_engine import DocumentQAEngine
from core.document_qa.orchestrator import UniversalDocumentOrchestrator

__all__ = [
    "UniversalDocumentOrchestrator",
    "DocumentQAEngine",
    "DocumentCategory",
    "SourceTier",
    "ClaimType",
    "ClaimStatus",
    "IssueSeverity",
    "QAStatus",
    "SourceEvidence",
    "Claim",
    "ValidationIssue",
    "QualityScorecard",
    "get_qa_config",
    "get_category_profile",
    "update_qa_config",
    "classify_document_request",
    "EvidenceRegistry",
    "ClaimVerifier",
    "MathValidator",
    "CitationEngine",
    "DocxQualityInspector",
    "PdfQualityInspector",
    "XlsxQualityInspector",
    "PptxQualityInspector",
    "HtmlQualityInspector",
    "MarkdownQualityInspector"
]
