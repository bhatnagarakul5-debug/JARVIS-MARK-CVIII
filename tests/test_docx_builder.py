"""
tests/test_docx_builder.py — Comprehensive Test Suite for Pure Word (.docx) Builder
===================================================================================
Verifies all 8 builder bug fixes, OMML math compilation, AST source order,
bibliography splitting & auto-linking, acronym-safe title casing, word-boundary
header truncation, document properties, TOC/page numbers, and the Post-Build QA Gate.
"""

import datetime
import re
from pathlib import Path

import docx
import pytest
from docx.oxml.ns import qn

from actions.docx_builder import (
    acronym_safe_title_case,
    build_docx,
    derive_clean_titles,
    normalize_markdown_text,
    truncate_header_title,
    verify_docx_quality,
)


SYNTHETIC_FIXTURE_MD = r"""# Executive Architecture of IBM and NASA AI Systems

This opening paragraph introduces **Quantum Error Correction** and *Fault-Tolerant SDN* fabrics with `inline_code_config()` and a clickable reference to [IBM Quantum Research](https://research.ibm.com). The state fidelity is governed by $\mathcal{F} = \langle \psi | \rho | \psi \rangle$ across all logical qubits.---## 1. Mathematical Formulation & Surface Code Thresholds

Below we derive the logical error suppression rate using the partition function and surface code distance $d$:

$$\Lambda = \sum_{i=1}^{n} \frac{\alpha_i + \beta_i}{\sqrt{2\pi\sigma^2}} \cdot \exp\left(-\frac{d}{2\xi}\right)$$

### 1.1 Sub-System Latency Hierarchy

#### 1.1.1 Cryogenic Control Plane

**Core Sub-Label A:**
- Primary cryo-CMOS controller stage
  - Nested sub-stage 1A: **4K resonator multiplex**
  - Nested sub-stage 1B: *10mK Josephson parametric amplifier*
- Secondary room-temperature FPGA readout

**Core Sub-Label B:**
1. Syndrome extraction cycle ($t_{\text{cycle}} \leq 450\text{ ns}$)
   1. Ancilla initialization
   2. CNOT parity check gates
2. Minimum-weight perfect matching (MWPM) decoder dispatch

> **Key Architectural Note:** Always isolate the *cryogenic readout bus* from thermal transients exceeding $\Delta T > 15\text{ mK}$.

---

## 2. Comparative Hardware Benchmark Table

| **Architecture Tier** | **Logical Qubits** | *Gate Fidelity* | **Syndrome Throughput** |
| :--- | :---: | :---: | :--- |
| **IBM Heron R2** | 156 | *99.91%* | `1.45 MHz` |
| **NASA Ames SDN Node** | 128 | *99.84%* | `1.12 MHz` |
| **Sovereign Core QPU** | 512 | **99.98%** | `4.80 MHz` |

## 3. System Orchestration Flow Diagram

```text
+-----------------------+       +------------------------+       +----------------------+
|   USER INTENT LAYER   | ----> |   AST TOKEN COMPILER   | ----> |   OMML MATH ENGINE   |
+-----------------------+       +------------------------+       +----------------------+
                                            |
                                            v
                                +------------------------+
                                |   POST-BUILD QA GATE   |
                                +------------------------+
```

## 4. Telemetry & Fault Recovery Protocol

The fault recovery loop continuously monitors $\frac{\partial \mathcal{L}}{\partial \theta}$ across distributed nodes to prevent decoherence cascades.

## 5. Bibliography & References

1. Bravyi, S., Cross, A. W., Gambetta, J. M., Maslov, D., Rall, P., & Yoder, T. J. (2024). High-threshold and low-overhead fault-tolerant quantum memory. Nature, 627(8005), 778-782. https://doi.org/10.1038/s41586-024-07107-72. Preskill, J. (2018). Quantum Computing in the NISQ era and beyond. Quantum, 2, 79. 10.22331/q-2018-08-06-793. Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., & Polosukhin, I. (2017). Attention is all you need. arXiv:1706.03762
"""


def test_acronym_safe_title_casing_and_prompt_stripping():
    """Bug #5: Acronym-safe title casing preserves IBM, NASA, AI, SDN and strips prompt prefixes."""
    raw_prompt = "Create a highly detailed word document on ibm and nasa ai sdn orchestration in the cloud"
    full_t, short_t = derive_clean_titles(raw_prompt)
    assert "IBM" in full_t
    assert "NASA" in full_t
    assert "AI" in full_t
    assert "SDN" in full_t
    assert "On Ibm" not in full_t
    assert " and " in full_t
    assert " in the " in full_t
    assert not full_t.lower().startswith("create a")
    assert len(short_t) <= 48


def test_running_header_word_boundary_truncation():
    """Bug #6: Running header truncates on a word boundary with an ellipsis, never mid-word."""
    long_title = "Highly Detailed Industrial Quantum Error Correction Architecture for Distributed Supercomputing"
    truncated = truncate_header_title(long_title, max_chars=38)
    assert len(truncated) <= 38
    assert truncated.endswith("…")
    assert "Indu…" not in truncated
    assert truncated == "Highly Detailed Industrial Quantum…"


def test_full_synthetic_fixture_build_and_qa_gate(tmp_path: Path):
    """Tests all features together on the synthetic fixture and saves Page 1 PNG."""
    out_docx = tmp_path / "Synthetic_Full_Fixture.docx"
    artifact_png = Path("C:/Users/Akul/OneDrive/Desktop/Developer Work/Jarvis-Mark-XL/scratch/final_qa_artifacts/docx_builder_page1.png")

    meta = {
        "output_path": out_docx,
        "title": "please write a comprehensive report on ibm and nasa ai sdn quantum error correction",
        "author": "Akul Bhatnagar",
        "render_page1_png": True,
        "page1_png_path": artifact_png,
    }

    saved_path = build_docx(SYNTHETIC_FIXTURE_MD, meta)
    assert saved_path.exists()
    assert saved_path.stat().st_size > 10_000
    assert artifact_png.exists() and artifact_png.stat().st_size > 5_000

    # 1. Verify QA Gate passes with zero issues
    qa = verify_docx_quality(saved_path)
    assert qa["passed"] is True, f"QA gate failed: {qa['issues']}"

    doc = docx.Document(str(saved_path))

    # 2. Verify Document Core Properties (Bug #7)
    cp = doc.core_properties
    assert cp.author == "Akul Bhatnagar"
    assert "IBM" in cp.title and "NASA" in cp.title and "AI" in cp.title and "SDN" in cp.title
    assert cp.comments == ""
    assert "python-docx" not in (cp.author or "").lower()
    assert "python-docx" not in (cp.comments or "").lower()
    assert cp.created.year >= datetime.datetime.now(datetime.timezone.utc).year

    # 3. Verify Zero Hardcoded Persona / Boilerplate (Bug #8)
    all_visible_text = "\n".join(p.text for p in doc.paragraphs)
    for phrase in ("Good day, Sir", "Tony Stark", "CONFIDENTIAL"):
        assert phrase not in all_visible_text

    # 4. Verify Running Header & Native Page Number Footer (Bug #6 & TOC/Footer requirement)
    hdr_txt = doc.sections[0].header.paragraphs[0].text
    assert len(hdr_txt) <= 48
    assert not hdr_txt.endswith("Indu")

    footer_xml = doc.sections[0].footer._element.xml
    assert "PAGE" in footer_xml and "NUMPAGES" in footer_xml

    # 5. Verify TOC was automatically inserted (document has 5 H2 headings >= 4)
    body_xml = doc._body._body.xml
    assert "TOC" in body_xml

    # 6. Verify Real Word OMML Equations (<m:oMath> and <m:oMathPara>) (Bug #3)
    omath_nodes = doc._body._body.findall(f".//{qn('m:oMath')}")
    omath_para_nodes = doc._body._body.findall(f".//{qn('m:oMathPara')}")
    assert len(omath_nodes) >= 4, "Expected inline and block OMML equations"
    assert len(omath_para_nodes) >= 1, "Expected display OMML equation paragraph"

    # 7. Verify Table Cell Formatting (no literal **bold** or *italic* in cells) (Bug #2)
    assert len(doc.tables) >= 1
    benchmark_tbl = None
    for tbl in doc.tables:
        if len(tbl.rows) >= 4 and len(tbl.columns) == 4:
            benchmark_tbl = tbl
            break
    assert benchmark_tbl is not None, "Expected 4x4 comparative benchmark table"
    cell_0_0_text = benchmark_tbl.cell(1, 0).text
    assert "**" not in cell_0_0_text
    assert "IBM Heron R2" in cell_0_0_text
    assert any(r.bold for r in benchmark_tbl.cell(1, 0).paragraphs[0].runs)

    # 8. Verify Flow Diagram Code Block preserved multi-line newlines (Bug #1)
    code_tables = [t for t in doc.tables if len(t.rows) == 1 and len(t.columns) == 1 and "USER INTENT LAYER" in t.cell(0, 0).text]
    assert len(code_tables) == 1
    flow_txt = code_tables[0].cell(0, 0).text
    assert flow_txt.count("\n") >= 4, "Flow diagram should preserve multi-line structure"

    # 9. Verify Source Order of Sub-Labels and Nested Lists (Bug #4)
    para_texts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    idx_label_a = next(i for i, t in enumerate(para_texts) if "Core Sub-Label A:" in t)
    idx_item_1a = next(i for i, t in enumerate(para_texts) if "4K resonator multiplex" in t)
    idx_label_b = next(i for i, t in enumerate(para_texts) if "Core Sub-Label B:" in t)
    idx_syndrome = next(i for i, t in enumerate(para_texts) if "Syndrome extraction cycle" in t)
    assert idx_label_a < idx_item_1a < idx_label_b < idx_syndrome

    # 10. Verify Glued Bibliography Split into 3 Hanging-Indented Entries with Hyperlinks (Bug #1 & Bibliography req)
    bib_idx = next(i for i, p in enumerate(doc.paragraphs) if "Bibliography & References" in p.text and p.style.name.startswith("Heading"))
    bib_paras = [p for p in doc.paragraphs[bib_idx + 1 :] if p.text.strip()]
    assert len(bib_paras) == 3, f"Expected 3 split bibliography entries, got {len(bib_paras)}: {[p.text for p in bib_paras]}"
    for bp in bib_paras:
        assert bp.paragraph_format.left_indent > 0
        assert bp.paragraph_format.first_line_indent < 0
        # Each entry must contain a clickable w:hyperlink element
        hyperlinks = bp._p.findall(f".//{qn('w:hyperlink')}")
        assert len(hyperlinks) >= 1, f"Expected clickable DOI/arXiv hyperlink in bibliography entry: {bp.text}"


def test_newline_lost_before_builder_and_literal_backslash_n(tmp_path: Path):
    """Explicitly tests 'newline lost before the builder' and 'literal \\n in the input'."""
    corrupted_input = (
        "# SDN Control Plane\\n\\n"
        "First paragraph explaining SDN orchestration).---## 2. Second Section\\n"
        "Line A of section two.\\n\\n"
        "Line B of section two with inline math $E = \\frac{h c}{\\lambda}$.\\n"
        "- Bullet item 1\\n"
        "- Bullet item 2"
    )
    out_docx = tmp_path / "Normalized_Input.docx"
    saved = build_docx(corrupted_input, {"output_path": out_docx, "title": "SDN Control Plane", "render_page1_png": False})

    qa = verify_docx_quality(saved)
    assert qa["passed"] is True, f"QA gate failed on literal \\n input: {qa['issues']}"

    doc = docx.Document(str(saved))
    texts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    joined = "\n".join(texts)
    assert "\\n" not in joined
    assert "---" not in joined
    assert "##" not in joined
    assert any("First paragraph explaining SDN orchestration)." in t for t in texts)
    assert any("Line A of section two." in t for t in texts)
    assert any("Line B of section two" in t for t in texts)
