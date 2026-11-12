"""
core/document_qa/math_validator.py — Deterministic Mathematical & Computational Validator for J.A.R.V.I.S.
"""

import re
import ast
from typing import List, Dict, Any, Optional, Tuple
import sympy as sp
from core.document_qa.models import IssueSeverity, ValidationIssue


class MathValidator:
    """
    Performs deterministic computational checks across equations, arithmetic statements,
    tabular totals, and spreadsheet formulas using SymPy and exact numeric recalculation.
    """

    def __init__(self):
        self.equations_checked: int = 0
        self.tables_checked: int = 0

    def validate_arithmetic_statements(self, text: str, section: Optional[str] = None) -> List[ValidationIssue]:
        """
        Scans text for explicit arithmetic statements:
        e.g. '10M + 5M = 14M' or 'costs of $6M subtracted from $10M left $5M' or
        'Total revenue of 100 with costs 60 resulted in net 50'.
        """
        issues: List[ValidationIssue] = []

        # 1. Pattern: A + B = C or A - B = C or A * B = C
        simple_eq_pat = re.compile(
            r'([\$€£]?\s*[\d,]+(?:\.\d+)?)\s*([\+\-\*\/])\s*([\$€£]?\s*[\d,]+(?:\.\d+)?)\s*(?:=|is|results in|yields|yielded|equaled|equals)\s*([\$€£]?\s*[\d,]+(?:\.\d+)?)',
            re.IGNORECASE
        )

        for match in simple_eq_pat.finditer(text):
            raw_a, op, raw_b, raw_c = match.groups()
            try:
                val_a = float(re.sub(r'[^\d.-]', '', raw_a))
                val_b = float(re.sub(r'[^\d.-]', '', raw_b))
                val_c = float(re.sub(r'[^\d.-]', '', raw_c))

                expected = None
                if op == '+': expected = val_a + val_b
                elif op == '-': expected = val_a - val_b
                elif op == '*': expected = val_a * val_b
                elif op == '/': expected = val_a / val_b if val_b != 0 else None

                if expected is not None:
                    # Allow 0.5% floating point margin
                    diff = abs(expected - val_c)
                    rel_err = diff / max(abs(expected), 1e-6)
                    if rel_err > 0.01 and diff > 0.05:
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.CRITICAL,
                            code="DETERMINISTIC_ARITHMETIC_ERROR",
                            message=f"Arithmetic discrepancy: '{match.group(0)}' is mathematically invalid. Expected {expected:.2f}, but found {val_c:.2f}.",
                            section=section,
                            target_entity=match.group(0),
                            suggestion=f"Correct calculated value from {val_c} to {expected:.2f}."
                        ))
            except Exception:
                continue

        # 2. Percentage Sum Checks: Component breakdowns summing to 100%
        pct_matches = [float(p) for p in re.findall(r'\b(\d+(?:\.\d+)?)\s*%', text)]
        # If there is an explicit statement like "breakdown of X: A%, B%, C%"
        if "breakdown" in text.lower() or "distribution" in text.lower() or "share" in text.lower():
            if len(pct_matches) >= 3 and len(pct_matches) <= 8:
                tot_pct = sum(pct_matches)
                if abs(tot_pct - 100.0) > 3.0 and tot_pct < 180.0:  # clearly meant to sum to 100%
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.HIGH,
                        code="PERCENTAGE_SUM_MISMATCH",
                        message=f"Percentage component breakdown sums to {tot_pct:.1f}% instead of 100.0%.",
                        section=section,
                        suggestion="Normalize percentage values to ensure parts sum to 100%."
                    ))

        return issues

    def validate_table_totals(self, table_rows: List[List[Any]], section: Optional[str] = None) -> List[ValidationIssue]:
        """
        Validates tables where a row or column represents a 'Total' or 'Sum'.
        Independently sums preceding numbers and flags mathematical errors.
        """
        issues: List[ValidationIssue] = []
        if not table_rows or len(table_rows) < 3:
            return issues

        self.tables_checked += 1
        headers = [str(c).strip().lower() for c in table_rows[0]]

        # Check for Total row (typically the last row)
        last_row = table_rows[-1]
        first_cell = str(last_row[0]).strip().lower() if last_row else ""
        if "total" in first_cell or "sum" in first_cell:
            # Check numeric columns
            num_cols = len(last_row)
            for c_idx in range(1, num_cols):
                raw_tot = str(last_row[c_idx]).replace("$", "").replace(",", "").replace("%", "").strip()
                try:
                    reported_total = float(raw_tot)
                except ValueError:
                    continue

                # Recalculate sum of rows 1..N-1
                calculated_sum = 0.0
                valid_num_count = 0
                for r_idx in range(1, len(table_rows) - 1):
                    val_cell = str(table_rows[r_idx][c_idx]).replace("$", "").replace(",", "").replace("%", "").strip()
                    try:
                        calculated_sum += float(val_cell)
                        valid_num_count += 1
                    except ValueError:
                        pass

                if valid_num_count >= 2:
                    diff = abs(calculated_sum - reported_total)
                    if diff > 0.05 and (diff / max(abs(calculated_sum), 1e-6)) > 0.005:
                        col_name = headers[c_idx] if c_idx < len(headers) else f"Column {c_idx+1}"
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.CRITICAL,
                            code="TABLE_TOTAL_MISMATCH",
                            message=f"Total mismatch in '{col_name}': Table reports {reported_total:.2f}, but recalculation yields {calculated_sum:.2f}.",
                            section=section,
                            target_entity=f"Table Column: {col_name}",
                            suggestion=f"Update table total for '{col_name}' to {calculated_sum:.2f}."
                        ))

        return issues

    def validate_spreadsheet_formulas(self, workbook_data: Dict[str, Any], section: Optional[str] = None) -> List[ValidationIssue]:
        """
        Validates openpyxl spreadsheet formulas, broken cell references, and zero-error tolerances.
        """
        issues: List[ValidationIssue] = []
        error_tokens = {"#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!"}

        sheets = workbook_data.get("sheets", {})
        for s_name, rows in sheets.items():
            for r_idx, row in enumerate(rows, start=1):
                for c_idx, cell in enumerate(row, start=1):
                    str_cell = str(cell).strip()
                    # 1. Error tokens
                    for tok in error_tokens:
                        if tok in str_cell:
                            issues.append(ValidationIssue(
                                severity=IssueSeverity.CRITICAL,
                                code="SPREADSHEET_FORMULA_ERROR",
                                message=f"Sheet '{s_name}' cell ({r_idx}, {c_idx}) contains formula error token '{tok}'.",
                                section=section,
                                target_entity=f"{s_name}!R{r_idx}C{c_idx}",
                                suggestion=f"Fix referenced range or denominator in cell formula to eliminate {tok}."
                            ))

                    # 2. Formula syntax checks
                    if str_cell.startswith("="):
                        if str_cell.count("(") != str_cell.count(")"):
                            issues.append(ValidationIssue(
                                severity=IssueSeverity.CRITICAL,
                                code="UNBALANCED_FORMULA_PARENS",
                                message=f"Sheet '{s_name}' cell ({r_idx}, {c_idx}) has unbalanced parentheses: '{str_cell}'.",
                                section=section,
                                target_entity=f"{s_name}!R{r_idx}C{c_idx}",
                                suggestion="Balance open and closing parentheses."
                            ))

        return issues

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
            else:
                return False, f"Expressions are not equivalent (difference = {diff})."
        except Exception as e:
            return False, f"Could not parse symbolic expressions: {e}"
