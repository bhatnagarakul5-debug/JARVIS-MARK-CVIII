"""
core/document_qa/classifier.py — Document Type Classifier & Validation Profile Resolver for J.A.R.V.I.S.
"""

import re
from typing import Dict, Any, Tuple
from core.document_qa.models import DocumentCategory
from core.document_qa.config import get_category_profile


CLASSIFICATION_RULES = [
    (
        DocumentCategory.SPREADSHEET,
        [r"\bxlsx\b", r"\bspreadsheet\b", r"\bexcel\b", r"\bworkbook\b", r"\bledger\b", r"\btracker\b", r"\bdata\s*sheet\b"]
    ),
    (
        DocumentCategory.CREATIVE_PRESENTATION,
        [r"\bpptx\b", r"\bpresentation\b", r"\bpitch\s*deck\b", r"\bslides\b", r"\bkeynote\b", r"\bdeck\b", r"\bcompany\s*profile\b"]
    ),
    (
        DocumentCategory.FINANCIAL,
        [r"\bfinancial\b", r"\bbudget\b", r"\bvaluation\b", r"\bdcf\b", r"\bbalance\s*sheet\b", r"\bcash\s*flow\b",
         r"\bforecast\b", r"\bprojections?\b", r"\bexpense\b", r"\bebitda\b", r"\bcagr\b", r"\bearnings\b", r"\bquarterly\s*financial\b"]
    ),
    (
        DocumentCategory.ACADEMIC,
        [r"\bresearch\s*paper\b", r"\bthesis\b", r"\bdissertation\b", r"\bliterature\s*review\b", r"\bacademic\b",
         r"\blab\s*report\b", r"\bscientific\b", r"\bpeer\s*review\b", r"\bjournal\b", r"\bcase\s*study\b", r"\bstudy\s*guide\b"]
    ),
    (
        DocumentCategory.PROFESSIONAL,
        [r"\bresume\b", r"\bcv\b", r"\bcurriculum\s*vitae\b", r"\bcover\s*letter\b", r"\bmemo\b", r"\bmemorandum\b",
         r"\bsop\b", r"\bstandard\s*operating\s*procedure\b", r"\bpolicy\s*doc\b"]
    ),
    (
        DocumentCategory.TECHNICAL,
        [r"\barchitecture\b", r"\btechnical\s*spec\b", r"\bapi\b", r"\bsystem\s*spec\b", r"\bmanual\b",
         r"\bcodebase\b", r"\bsoftware\b", r"\bengineering\b", r"\bdeveloper\s*guide\b", r"\bproject_doc\b", r"\bhtmldoc\b"]
    ),
    (
        DocumentCategory.BUSINESS,
        [r"\bbusiness\b", r"\bstrategic\b", r"\bproposal\b", r"\bmarket\s*research\b", r"\bswot\b",
         r"\bfeasibility\b", r"\bmanagement\s*report\b", r"\bexecutive\s*brief\b", r"\bexecutive\s*summary\b"]
    )
]


def classify_document_request(
    title: str = "",
    doc_type: str = "",
    file_type: str = "",
    content: str = "",
    instruction: str = ""
) -> Tuple[DocumentCategory, Dict[str, Any]]:
    """
    Classifies a document request into an appropriate DocumentCategory
    and resolves its tailored validation profile.
    """
    blob = f"{title} {doc_type} {file_type} {instruction} {content[:1000]}".lower()
    clean_ftype = file_type.lower().strip().lstrip(".")

    # Direct file type cues
    if clean_ftype in ("xlsx", "xls", "csv") or doc_type in ("spreadsheet", "excel"):
        cat = DocumentCategory.SPREADSHEET
        return cat, get_category_profile(cat.value)

    if clean_ftype in ("pptx", "ppt") or doc_type in ("presentation", "slides", "deck"):
        cat = DocumentCategory.CREATIVE_PRESENTATION
        return cat, get_category_profile(cat.value)

    # Regex heuristic matching
    for category, patterns in CLASSIFICATION_RULES:
        for pat in patterns:
            if re.search(pat, blob, re.IGNORECASE):
                return category, get_category_profile(category.value)

    # Fallback by doc_type
    if doc_type in ("full_manual", "architecture", "api_reference", "technical_spec"):
        cat = DocumentCategory.TECHNICAL
    elif doc_type in ("executive_brief",):
        cat = DocumentCategory.BUSINESS
    elif doc_type in ("readme",):
        cat = DocumentCategory.TECHNICAL
    else:
        cat = DocumentCategory.GENERAL

    return cat, get_category_profile(cat.value)
