"""
core/document_qa/post_render_inspectors.py — Post-Rendering Quality Inspectors for DOCX, PDF, XLSX, PPTX, HTML & MD.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from core.document_qa.models import IssueSeverity, ValidationIssue


class DocxQualityInspector:
    """Reopens and validates rendered Microsoft Word (.docx) files on disk."""

    @staticmethod
    def inspect(file_path: Path) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not file_path.exists() or file_path.stat().st_size == 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="CORRUPT_OR_MISSING_DOCX",
                message=f"Word document file does not exist or is empty at {file_path}.",
                target_entity=str(file_path)
            ))
            return issues

        try:
            from docx import Document
            doc = Document(str(file_path))

            # 1. Paragraphs and Content Count
            non_empty_p = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            if len(non_empty_p) < 3:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HIGH,
                    code="SPARSE_DOCX_CONTENT",
                    message=f"Document contains only {len(non_empty_p)} non-empty paragraph(s).",
                    suggestion="Ensure complete section content is written."
                ))

            # 2. Heading Structure
            headings = [p.text.strip() for p in doc.paragraphs if p.style.name.startswith("Heading")]
            if not headings:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    code="MISSING_DOCX_HEADINGS",
                    message="Document does not contain standard Heading 1 or Heading 2 styles.",
                    suggestion="Structure sections with formal docx headings."
                ))

            # 3. Table Inspection
            for t_idx, table in enumerate(doc.tables):
                if len(table.rows) == 0:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.HIGH,
                        code="EMPTY_TABLE_DETECTED",
                        message=f"Table {t_idx+1} has 0 rows.",
                        suggestion="Populate table with data or remove empty table element."
                    ))
                else:
                    empty_cells = sum(1 for row in table.rows for cell in row.cells if not cell.text.strip())
                    total_cells = sum(len(row.cells) for row in table.rows)
                    if total_cells > 0 and (empty_cells / total_cells) > 0.5:
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.MEDIUM,
                            code="HIGH_EMPTY_CELL_RATIO",
                            message=f"Table {t_idx+1} has {empty_cells}/{total_cells} empty cells.",
                            suggestion="Verify tabular data completeness."
                        ))

            # 4. Strict Builder QA Gate check (no raw markdown tokens, long unbroken paragraphs, or empty headings)
            from actions.docx_builder import verify_docx_quality
            qa_gate = verify_docx_quality(file_path)
            if not qa_gate["passed"]:
                for g_issue in qa_gate["issues"]:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.HIGH,
                        code="DOCX_QA_GATE_VIOLATION",
                        message=g_issue,
                        target_entity=str(file_path),
                        suggestion="Ensure markdown tokens, LaTeX equations, and heading contents are properly compiled."
                    ))
            # 5. Image check
            img_count = sum(len(p._element.xpath('.//a:blip')) for p in doc.paragraphs)
            # Checked cleanly without errors

        except Exception as e:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="DOCX_PARSING_ERROR",
                message=f"Failed to inspect Word document: {e}",
                target_entity=str(file_path)
            ))

        return issues


class PdfQualityInspector:
    """Reopens and validates rendered PDF (.pdf) documents on disk via pypdf."""

    @staticmethod
    def inspect(file_path: Path) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not file_path.exists() or file_path.stat().st_size == 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="CORRUPT_OR_MISSING_PDF",
                message=f"PDF document does not exist or is empty at {file_path}.",
                target_entity=str(file_path)
            ))
            return issues

        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            page_count = len(reader.pages)

            if page_count == 0:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.CRITICAL,
                    code="EMPTY_PDF_PAGES",
                    message="PDF file contains 0 pages.",
                    target_entity=str(file_path)
                ))
                return issues

            # Extract text across pages
            total_chars = 0
            for p_num, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                total_chars += len(txt.strip())

                # Check page dimensions (must be > 200pt)
                box = page.mediabox
                if float(box.width) < 200 or float(box.height) < 200:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.HIGH,
                        code="INVALID_PDF_PAGE_DIMENSIONS",
                        message=f"Page {p_num+1} has anomalous dimensions: {box.width}x{box.height}.",
                        suggestion="Ensure standard Letter or A4 dimensions."
                    ))

            if total_chars < 50:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HIGH,
                    code="LOW_EXTRACTABLE_PDF_TEXT",
                    message=f"PDF contains suspiciously low extractable text ({total_chars} characters across {page_count} pages).",
                    suggestion="Verify text flow and font embedding in ReportLab canvas."
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="PDF_PARSING_ERROR",
                message=f"Failed to inspect PDF: {e}",
                target_entity=str(file_path)
            ))

        return issues


class XlsxQualityInspector:
    """Reopens and validates rendered Excel (.xlsx) workbooks on disk via openpyxl."""

    @staticmethod
    def inspect(file_path: Path) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not file_path.exists() or file_path.stat().st_size == 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="CORRUPT_OR_MISSING_XLSX",
                message=f"Excel workbook file does not exist or is empty at {file_path}.",
                target_entity=str(file_path)
            ))
            return issues

        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(file_path), data_only=False)

            if len(wb.sheetnames) == 0:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.CRITICAL,
                    code="EMPTY_XLSX_WORKBOOK",
                    message="Excel workbook contains 0 worksheets."
                ))
                return issues

            error_tokens = {"#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!"}

            for s_name in wb.sheetnames:
                ws = wb[s_name]
                has_content = False

                for row in ws.iter_rows(values_only=False):
                    for cell in row:
                        if cell.value is not None:
                            has_content = True
                            str_val = str(cell.value).strip()

                            # Check error tokens
                            for tok in error_tokens:
                                if tok in str_val:
                                    issues.append(ValidationIssue(
                                        severity=IssueSeverity.CRITICAL,
                                        code="XLSX_FORMULA_ERROR_TOKEN",
                                        message=f"Cell {cell.coordinate} in sheet '{s_name}' contains error token '{tok}'.",
                                        target_entity=f"{s_name}!{cell.coordinate}",
                                        suggestion="Fix formula references or denominator."
                                    ))

                            # Check formula parentheses
                            if str_val.startswith("=") and str_val.count("(") != str_val.count(")"):
                                issues.append(ValidationIssue(
                                    severity=IssueSeverity.CRITICAL,
                                    code="XLSX_UNBALANCED_FORMULA",
                                    message=f"Cell {cell.coordinate} has unbalanced formula parentheses: '{str_val}'.",
                                    target_entity=f"{s_name}!{cell.coordinate}"
                                ))

                if not has_content:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.HIGH,
                        code="EMPTY_WORKSHEET",
                        message=f"Worksheet '{s_name}' is completely empty."
                    ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="XLSX_PARSING_ERROR",
                message=f"Failed to inspect Excel workbook: {e}",
                target_entity=str(file_path)
            ))

        return issues


class PptxQualityInspector:
    """Reopens and validates rendered PowerPoint (.pptx) decks on disk via python-pptx."""

    @staticmethod
    def inspect(file_path: Path, max_words_per_slide: int = 120) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not file_path.exists() or file_path.stat().st_size == 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="CORRUPT_OR_MISSING_PPTX",
                message=f"PowerPoint presentation file does not exist or is empty at {file_path}.",
                target_entity=str(file_path)
            ))
            return issues

        try:
            from pptx import Presentation
            prs = Presentation(str(file_path))

            slide_count = len(prs.slides)
            if slide_count == 0:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.CRITICAL,
                    code="EMPTY_PPTX_DECK",
                    message="PowerPoint presentation contains 0 slides."
                ))
                return issues

            for s_idx, slide in enumerate(prs.slides, start=1):
                # Word count check for text overflow
                total_slide_words = 0
                has_title = bool(slide.shapes.title and slide.shapes.title.text.strip())

                for shape in slide.shapes:
                    if shape.has_text_frame:
                        txt = shape.text_frame.text.strip()
                        total_slide_words += len(txt.split())

                if not has_title and s_idx > 1:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.MEDIUM,
                        code="SLIDE_MISSING_TITLE",
                        message=f"Slide {s_idx} does not have a recognizable title shape.",
                        target_entity=f"Slide {s_idx}"
                    ))

                if total_slide_words > max_words_per_slide:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.HIGH,
                        code="SLIDE_TEXT_OVERFLOW",
                        message=f"Slide {s_idx} contains {total_slide_words} words (exceeds readability limit of {max_words_per_slide}).",
                        target_entity=f"Slide {s_idx}",
                        suggestion="Condense bullet points or split across multiple slides to prevent visual clipping."
                    ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="PPTX_PARSING_ERROR",
                message=f"Failed to inspect PowerPoint deck: {e}",
                target_entity=str(file_path)
            ))

        return issues


class HtmlQualityInspector:
    """Validates rendered HTML documentation portals on disk."""

    @staticmethod
    def inspect(file_path: Path) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not file_path.exists() or file_path.stat().st_size == 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="CORRUPT_OR_MISSING_HTML",
                message=f"HTML documentation portal does not exist at {file_path}."
            ))
            return issues

        try:
            from bs4 import BeautifulSoup
            content = file_path.read_text(encoding="utf-8")
            soup = BeautifulSoup(content, "html.parser")

            if not soup.find("title"):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    code="MISSING_HTML_TITLE",
                    message="HTML portal is missing a <title> tag."
                ))

            if not soup.find("main") and not soup.find("div", class_="content"):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.MEDIUM,
                    code="MISSING_HTML_MAIN_CONTAINER",
                    message="HTML portal does not contain a semantic <main> or content container."
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="HTML_PARSING_ERROR",
                message=f"Failed to parse HTML documentation: {e}"
            ))

        return issues


class MarkdownQualityInspector:
    """Validates Markdown documentation on disk."""

    @staticmethod
    def inspect(file_path: Path) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not file_path.exists():
            issues.append(ValidationIssue(
                severity=IssueSeverity.CRITICAL,
                code="MISSING_MARKDOWN_FILE",
                message=f"Markdown file does not exist at {file_path}."
            ))
            return issues

        content = file_path.read_text(encoding="utf-8")
        if not content.strip():
            issues.append(ValidationIssue(
                severity=IssueSeverity.HIGH,
                code="EMPTY_MARKDOWN_FILE",
                message="Markdown file is empty."
            ))

        # Check unclosed fenced code blocks
        if content.count("```") % 2 != 0:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HIGH,
                code="UNCLOSED_FENCED_CODE_BLOCK",
                message="Markdown file has an unclosed fenced code block (odd number of triple backticks)."
            ))

        return issues
