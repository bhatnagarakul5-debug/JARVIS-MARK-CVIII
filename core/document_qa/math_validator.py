"""
core/document_qa/math_validator.py — Deterministic Mathematical & Computational Validator for J.A.R.V.I.S. Mark 108
Accelerated via `jarvis_rust_core` Native Rust Exoskeleton.
"""

from typing import List, Dict, Any, Optional, Tuple
import sympy as sp
from core.document_qa.models import IssueSeverity, ValidationIssue
from core.rust_bridge import (
    validate_arithmetic,
    validate_table_totals as validate_table_totals_rust,
    validate_spreadsheet_cells as validate_spreadsheet_cells_rust,
)


def _map_severity(sev_str: str) -> IssueSeverity:
    s = (sev_str or "").lower()
    if s == "critical":
        return IssueSeverity.CRITICAL
    if s == "high":
        return IssueSeverity.HIGH
    if s == "medium":
        return IssueSeverity.MEDIUM
    return IssueSeverity.LOW


class MathValidator:
    """
    Performs deterministic computational checks across equations, arithmetic statements,
    tabular totals, and spreadsheet formulas using the Native Rust Exoskeleton and SymPy.
    """

    def __init__(self):
        self.equations_checked: int = 0
        self.tables_checked: int = 0

    def validate_arithmetic_statements(self, text: str, section: Optional[str] = None) -> List[ValidationIssue]:
        """
        Delegates inline arithmetic & percentage breakdown checks directly to `jarvis_rust_core`.
        """
        raw_issues = validate_arithmetic(text or "")
        return [
            ValidationIssue(
                severity=_map_severity(sev),
                code=code,
                message=msg,
                section=section,
                target_entity=target or None,
                suggestion=sugg,
            )
            for sev, code, msg, target, sugg in raw_issues
        ]

    def validate_table_totals(self, table_rows: List[List[Any]], section: Optional[str] = None) -> List[ValidationIssue]:
        """
        Delegates tabular 'Total'/'Sum' row verification directly to `jarvis_rust_core`.
        """
        if not table_rows or len(table_rows) < 3:
            return []
        self.tables_checked += 1
        raw_issues = validate_table_totals_rust(table_rows)
        return [
            ValidationIssue(
                severity=_map_severity(sev),
                code=code,
                message=msg.replace("but sum of rows is", "but recalculation yields"),
                section=section,
                target_entity=f"Table Column: {target}" if target else None,
                suggestion=sugg,
            )
            for sev, code, msg, target, sugg in raw_issues
        ]

    def validate_spreadsheet_formulas(self, workbook_data: Dict[str, Any], section: Optional[str] = None) -> List[ValidationIssue]:
        """
        Delegates openpyxl spreadsheet formula and error-token validation directly to `jarvis_rust_core`.
        """
        sheets = (workbook_data or {}).get("sheets", {})
        raw_issues = validate_spreadsheet_cells_rust(sheets)
        return [
            ValidationIssue(
                severity=_map_severity(sev),
                code=code,
                message=msg,
                section=section,
                target_entity=target or None,
                suggestion=sugg,
            )
            for sev, code, msg, target, sugg in raw_issues
        ]

    def verify_symbolic_equation(self, eq_left: str, eq_right: str) -> Tuple[bool, str]:
        """
        Uses SymPy to verify symbolic mathematical equivalence:
        Determines whether eq_left - eq_right simplifies to zero.
        """
        try:
            expr_l = sp.sympify(eq_left)
            expr_r = sp.sympify(eq_right)
            diff = sp.simplify(expr_l - expr_r)
            if diff == 0:
                self.equations_checked += 1
                return True, "Symbolic mathematical equivalence verified via SymPy."
            return False, f"Expressions are not equivalent (difference = {diff})."
        except Exception as e:
            return False, f"Could not parse symbolic expressions: {e}"
