"""
core/document_qa/classifier.py — Document Type Classifier & Validation Profile Resolver for J.A.R.V.I.S.
Powered by `jarvis_rust_core` Native Rust Document Category Classifier.
"""

from typing import Dict, Any, Tuple
from core.document_qa.models import DocumentCategory
from core.document_qa.config import get_category_profile
from core.rust_bridge import classify_document_category


def classify_document_request(
    title: str = "",
    doc_type: str = "",
    file_type: str = "",
    content: str = "",
    instruction: str = ""
) -> Tuple[DocumentCategory, Dict[str, Any]]:
    """
    Classifies a document request into an appropriate DocumentCategory
    and resolves its tailored validation profile via `jarvis_rust_core`.
    """
    cat_str = classify_document_category(
        title=title,
        doc_type=doc_type,
        file_type=file_type,
        content=content,
        instruction=instruction,
    )
    try:
        cat = DocumentCategory(cat_str)
    except ValueError:
        cat = DocumentCategory.GENERAL
    return cat, get_category_profile(cat.value)

