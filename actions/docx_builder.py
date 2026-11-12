"""
actions/docx_builder.py — J.A.R.V.I.S. Mark 108 (Sovereign Core)
====================================================================
Pure-function Word (.docx) Document Builder & Post-Build QA Gate.

Choice of Parser:
We check for `pypandoc` + a system `pandoc` binary first. When `pandoc` is not
installed in the environment (as on this workstation), we use `markdown-it-py`
(CommonMark AST token-stream parser with `table` and `strikethrough` plugins)
mapped deterministically onto `python-docx` with a custom LaTeX-to-OMML
(`<m:oMath>` / `<m:oMathPara>`) equation compiler. This guarantees:
1. Exact source-order preservation of headings (H1-H4), paragraphs, sub-labels,
   nested bullet/numbered lists, pipe tables, blockquotes, code blocks, and images.
2. Zero raw Markdown tokens (`**`, `*`, `#`, `---`, `|---|`) in paragraphs or cells.
3. Native Word OMML equations for inline (`$...$`) and block (`$$...$$`) LaTeX.
4. Acronym-safe title casing and word-boundary running header truncation.
5. Hanging-indent bibliography splitting and automatic DOI / arXiv hyperlinks.
6. Pure function isolation (`build_docx(markdown_text, meta) -> Path`) with zero
   persona or global state pollution.
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor
from markdown_it import MarkdownIt


class DocxQualityGateError(RuntimeError):
    """Raised when a generated .docx file fails the post-build QA inspection gate."""


# ============================================================================
# 1. ACRONYM-SAFE TITLE CASING & SHORT TITLE EXTRACTION
# ============================================================================

KNOWN_ACRONYMS = {
    "IBM", "NASA", "AI", "AGI", "SDN", "NFV", "GPU", "CPU", "TPU", "NPU", "QPU",
    "API", "SDK", "CLI", "IDE", "GUI", "HUD", "UI", "UX", "OS", "RTOS", "BIOS",
    "RAM", "ROM", "VRAM", "DRAM", "SRAM", "SSD", "NVMe", "PCIe", "USB", "HDMI",
    "SQL", "NoSQL", "HTML", "CSS", "XML", "JSON", "YAML", "TOML", "CSV", "PDF",
    "DOCX", "XLSX", "PPTX", "OMML", "AST", "DOM", "URI", "URL", "URN", "DNS",
    "HTTP", "HTTPS", "TCP", "UDP", "IP", "IPv4", "IPv6", "SSH", "TLS", "SSL",
    "VPN", "LAN", "WAN", "WLAN", "BGP", "OSPF", "MPLS", "QoS", "IoT", "IIoT",
    "IEEE", "ACM", "ISO", "NIST", "IETF", "W3C", "OWASP", "MITRE", "CVE", "CWE",
    "SOC", "SIEM", "SOAR", "RBAC", "ABAC", "IAM", "MFA", "SSO", "OAuth", "JWT",
    "AES", "RSA", "ECC", "SHA", "HMAC", "PKI", "TLS", "ZERO", "HPC", "MPI",
    "RDMA", "CUDA", "ROCm", "SLURM", "FPGA", "ASIC", "VLSI", "CMOS", "MEMS",
    "LLM", "VLM", "NLP", "NLU", "CV", "RL", "RLHF", "DPO", "PPO", "GAN", "VAE",
    "CNN", "RNN", "LSTM", "GRU", "BERT", "GPT", "RAG", "LoRA", "QLoRA", "MoE",
    "FP32", "FP16", "BF16", "INT8", "INT4", "FLOP", "FLOPS", "TFLOPS", "PFLOPS",
    "NISQ", "QEC", "VQE", "QAOA", "QFT", "CNOT", "SWAP", "Lidar", "RADAR", "SONAR",
    "USA", "UK", "EU", "UN", "NATO", "WHO", "FDA", "SEC", "FCC", "FTC", "EPA",
    "GDPR", "HIPAA", "CCPA", "FERPA", "SOX", "PCI", "DSS", "GAAP", "IFRS",
    "ROI", "KPI", "OKR", "CAGR", "EBITDA", "EBIT", "EPS", "NPV", "IRR", "CAPEX",
    "OPEX", "COGS", "B2B", "B2C", "SaaS", "PaaS", "IaaS", "SWOT", "PEST", "PESTLE",
    "AWS", "GCP", "ERP", "CRM", "SCM", "HRM", "ESG", "CSR", "M&A", "IPO", "ETF",
    "DNA", "RNA", "mRNA", "tRNA", "CRISPR", "PCR", "ATP", "ADP", "CNS", "PNS",
    "MRI", "CT", "PET", "ECG", "EEG", "ICU", "ER", "OR", "PhD", "MD", "MBA",
    "CEO", "CTO", "CFO", "COO", "CIO", "CISO", "VP", "SVP", "EVP", "QA", "QC",
    "CI", "CD", "DevOps", "MLOps", "SecOps", "REST", "SOAP", "gRPC", "GraphQL",
    "JARVIS", "J.A.R.V.I.S.", "MARK", "DOI", "ISBN", "ISSN", "PMID", "PMCID",
}

SPECIAL_MIXED_CASE = {
    "arxiv": "arXiv",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "openai": "OpenAI",
    "deepmind": "DeepMind",
    "huggingface": "HuggingFace",
    "langchain": "LangChain",
    "llamaindex": "LlamaIndex",
    "fastapi": "FastAPI",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "nodejs": "Node.js",
    "nextjs": "Next.js",
    "reactjs": "React.js",
    "vuejs": "Vue.js",
    "macos": "macOS",
    "ios": "iOS",
    "ipados": "iPadOS",
    "watchos": "watchOS",
    "latex": "LaTeX",
    "bibtex": "BibTeX",
    "sympy": "SymPy",
    "numpy": "NumPy",
    "scipy": "SciPy",
    "matplotlib": "Matplotlib",
    "openpyxl": "OpenPyXL",
    "reportlab": "ReportLab",
    "github": "GitHub",
    "gitlab": "GitLab",
    "devops": "DevOps",
    "mlops": "MLOps",
    "secops": "SecOps",
    "lora": "LoRA",
    "qlora": "QLoRA",
    "pcie": "PCIe",
    "nvme": "NVMe",
    "nvlink": "NVLink",
    "infiniband": "InfiniBand",
    "oauth": "OAuth",
    "phd": "PhD",
}

SMALL_TITLE_WORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "yet", "so",
    "at", "by", "in", "of", "on", "to", "up", "as", "vs", "vs.", "via",
    "per", "from", "into", "onto", "with", "over", "off", "out",
}

ACRONYM_UPPER_LOOKUP = {a.upper(): a for a in KNOWN_ACRONYMS}

PROMPT_PREFIX_RE = re.compile(
    r"^(?:please\s+)?(?:can\s+you\s+|could\s+you\s+)?"
    r"(?:create|write|generate|make|build|draft|prepare|produce|author|give\s+me)\s+"
    r"(?:a\s+|an\s+|the\s+)?"
    r"(?:highly\s+detailed\s+|comprehensive\s+|detailed\s+|complete\s+|full\s+|in-depth\s+|executive\s+|professional\s+|academic\s+|technical\s+)*"
    r"(?:word\s+document|document|report|paper|research\s+paper|manual|specification|guide|analysis|study|whitepaper|brief|essay)\s*"
    r"(?:on|about|regarding|covering|titled|for|of)\s+",
    re.IGNORECASE,
)


def _format_single_word(word: str, is_first: bool, is_last: bool, after_colon: bool) -> str:
    if not word:
        return word

    # Preserve leading/trailing punctuation
    m = re.match(r"^([^A-Za-z0-9]*)([A-Za-z0-9][A-Za-z0-9.\-&/']*?)([^A-Za-z0-9]*)$", word)
    if not m:
        return word
    prefix, core, suffix = m.groups()

    # Handle hyphenated compounds recursively (e.g., "ai-driven", "zero-trust")
    if "-" in core and core.upper() not in ACRONYM_UPPER_LOOKUP:
        parts = core.split("-")
        formatted_parts = [
            _format_single_word(p, idx == 0 and is_first, idx == len(parts) - 1 and is_last, after_colon)
            for idx, p in enumerate(parts)
        ]
        return f"{prefix}{'-'.join(formatted_parts)}{suffix}"

    # Handle slash compounds (e.g., "ci/cd", "tcp/ip")
    if "/" in core and core.upper() not in ACRONYM_UPPER_LOOKUP:
        parts = core.split("/")
        formatted_parts = [
            _format_single_word(p, True, True, True)
            for p in parts
        ]
        return f"{prefix}{'/'.join(formatted_parts)}{suffix}"

    core_lower = core.lower()
    core_upper = core.upper()

    if core_lower in SPECIAL_MIXED_CASE:
        return f"{prefix}{SPECIAL_MIXED_CASE[core_lower]}{suffix}"

    if core_upper in ACRONYM_UPPER_LOOKUP:
        return f"{prefix}{ACRONYM_UPPER_LOOKUP[core_upper]}{suffix}"

    # If input word is already ALL CAPS (2+ letters) or mixed camelCase/digits (e.g. "x86", "ARM64", "v78")
    if len(core) >= 2 and core.isupper() and core.isalpha():
        return f"{prefix}{core}{suffix}"
    if any(c.isupper() for c in core[1:]) and any(c.islower() or c.isdigit() for c in core):
        return f"{prefix}{core}{suffix}"

    if not is_first and not is_last and not after_colon and core_lower in SMALL_TITLE_WORDS:
        return f"{prefix}{core_lower}{suffix}"

    return f"{prefix}{core[:1].upper() + core[1:].lower()}{suffix}"


def acronym_safe_title_case(raw_title: str) -> str:
    """
    Applies acronym-safe title casing:
    - Preserves all-caps words and known acronyms (IBM, NASA, AI, SDN, GPU, etc.)
    - Preserves mixed-case proper terms (arXiv, PyTorch, LaTeX, OpenAI)
    - Lowercases small prepositions/articles/conjunctions unless at start/end or after colon
    """
    if not raw_title or not raw_title.strip():
        return "Technical Document"

    cleaned = re.sub(r"\s+", " ", raw_title.strip())
    words = cleaned.split(" ")
    result: List[str] = []
    after_colon = False

    for idx, w in enumerate(words):
        is_first = idx == 0
        is_last = idx == len(words) - 1
        formatted = _format_single_word(w, is_first=is_first, is_last=is_last, after_colon=after_colon)
        result.append(formatted)
        after_colon = w.endswith((":", "—", "–", "-"))

    return " ".join(result)


def derive_clean_titles(
    raw_title: Optional[str],
    short_title: Optional[str] = None,
    markdown_text: str = "",
) -> Tuple[str, str]:
    """
    Derives (full_title, short_running_title) without echoing a user's long conversational prompt.
    """
    candidate = (raw_title or "").strip()

    # If no candidate or candidate looks like a generic placeholder, check first H1 in markdown
    if not candidate or candidate.lower() in ("document", "untitled", "report"):
        m_h1 = re.search(r"^\s*#\s+(.+)$", markdown_text or "", re.MULTILINE)
        if m_h1:
            candidate = m_h1.group(1).strip()

    # Strip markdown formatting from title
    candidate = re.sub(r"[*_`#]+", "", candidate).strip()

    # Strip conversational request prefixes ("Create a highly detailed report on...")
    candidate = PROMPT_PREFIX_RE.sub("", candidate).strip()

    # Strip trailing conversational instructions ("and include tables and citations...")
    candidate = re.split(
        r"\s+(?:and\s+include|with\s+citations|with\s+tables|make\s+sure|please\s+include|including\s+a\s+table)\b",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .,;:-")

    if not candidate:
        candidate = "Technical Report"

    # If the title is still overly long (> 95 chars), condense it at a clause boundary
    if len(candidate) > 95:
        clause_split = re.split(r"[:;—–]|(?:\s+-\s+)", candidate, maxsplit=1)
        if len(clause_split[0].strip()) >= 15:
            candidate = clause_split[0].strip()
        else:
            words = candidate.split()
            candidate = " ".join(words[:12])

    full_title = acronym_safe_title_case(candidate)

    if short_title and short_title.strip():
        clean_short = acronym_safe_title_case(re.sub(r"[*_`#]+", "", short_title.strip()))
    else:
        # Derive concise short title from first clause before colon/dash
        primary_clause = re.split(r"[:—–]|(?:\s+-\s+)", full_title, maxsplit=1)[0].strip()
        clean_short = primary_clause if len(primary_clause) >= 4 else full_title

    clean_short = truncate_header_title(clean_short, max_chars=48)
    return full_title, clean_short


def truncate_header_title(text: str, max_chars: int = 48) -> str:
    """
    Truncates a running header title cleanly on a word boundary with an ellipsis
    using the native `jarvis_rust_core` engine. Never slices a word in half.
    """
    from core.rust_bridge import truncate_header_title as _truncate_rust
    return _truncate_rust(text or "", max_chars=max_chars)


# ============================================================================
# 2. INPUT NORMALIZATION & BIBLIOGRAPHY UN-GLUING
# ============================================================================

def split_glued_bibliography_text(text: str) -> str:
    """
    Delegates glued bibliography entry splitting directly to `jarvis_rust_core`.
    """
    from core.rust_bridge import split_glued_bibliography
    return split_glued_bibliography(text or "")


def normalize_markdown_text(raw_text: str) -> str:
    """
    Delegates raw markdown structural normalization, fenced code protection,
    glued HR/heading separation, and bibliography un-gluing to `jarvis_rust_core`.
    """
    if not raw_text:
        return ""
    from core.rust_bridge import normalize_markdown
    return normalize_markdown(str(raw_text))


# ============================================================================
# 3. LATEX TO WORD OMML (<m:oMath> / <m:oMathPara>) COMPILER
# ============================================================================

OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

LATEX_SYMBOLS: Dict[str, str] = {
    # Lowercase Greek
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ϵ", r"\varepsilon": "ε", r"\zeta": "ζ", r"\eta": "η",
    r"\theta": "θ", r"\vartheta": "ϑ", r"\iota": "ι", r"\kappa": "κ",
    r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν", r"\xi": "ξ",
    r"\pi": "π", r"\varpi": "ϖ", r"\rho": "ρ", r"\varrho": "ϱ",
    r"\sigma": "σ", r"\varsigma": "ς", r"\tau": "τ", r"\upsilon": "υ",
    r"\phi": "ϕ", r"\varphi": "φ", r"\chi": "χ", r"\psi": "ψ",
    r"\omega": "ω",
    # Uppercase Greek
    r"\Gamma": "Γ", r"\Delta": "Δ", r"\Theta": "Θ", r"\Lambda": "Λ",
    r"\Xi": "Ξ", r"\Pi": "Π", r"\Sigma": "Σ", r"\Upsilon": "Υ",
    r"\Phi": "Φ", r"\Psi": "Ψ", r"\Omega": "Ω",
    # Operators & Relations
    r"\times": "×", r"\cdot": "⋅", r"\div": "÷", r"\pm": "±", r"\mp": "∓",
    r"\leq": "≤", r"\le": "≤", r"\geq": "≥", r"\ge": "≥",
    r"\neq": "≠", r"\ne": "≠", r"\approx": "≈", r"\equiv": "≡", r"\cong": "≅",
    r"\sim": "∼", r"\propto": "∝", r"\infty": "∞", r"\partial": "∂", r"\nabla": "∇",
    r"\forall": "∀", r"\exists": "∃", r"\nexists": "∄", r"\in": "∈", r"\notin": "∉",
    r"\subset": "⊂", r"\subseteq": "⊆", r"\supset": "⊃", r"\supseteq": "⊇",
    r"\cup": "∪", r"\cap": "∩", r"\emptyset": "∅", r"\varnothing": "∅",
    r"\rightarrow": "→", r"\to": "→", r"\leftarrow": "←", r"\leftrightarrow": "↔",
    r"\Rightarrow": "⇒", r"\Leftarrow": "⇐", r"\Leftrightarrow": "⇔", r"\iff": "⇔",
    r"\mapsto": "↦", r"\uparrow": "↑", r"\downarrow": "↓",
    r"\oplus": "⊕", r"\otimes": "⊗", r"\odot": "⊙", r"\perp": "⊥", r"\parallel": "∥",
    r"\hbar": "ℏ", r"\ell": "ℓ", r"\Re": "ℜ", r"\Im": "ℑ",
    r"\langle": "⟨", r"\rangle": "⟩", r"\lceil": "⌈", r"\rceil": "⌉",
    r"\lfloor": "⌊", r"\rfloor": "⌋", r"\dots": "…", r"\cdots": "⋯", r"\ldots": "…",
    r"\quad": "  ", r"\qquad": "    ", r"\,": " ", r"\;": " ", r"\:": " ", r"\!": "",
}

NARY_OPERATORS: Dict[str, str] = {
    r"\sum": "∑",
    r"\prod": "∏",
    r"\int": "∫",
    r"\oint": "∮",
    r"\iint": "∬",
    r"\iiint": "∭",
    r"\bigcup": "⋃",
    r"\bigcap": "⋂",
}

ACCENT_OPERATORS: Dict[str, str] = {
    r"\hat": "\u0302",
    r"\bar": "\u0304",
    r"\overline": "\u0305",
    r"\vec": "\u20d7",
    r"\tilde": "\u0303",
    r"\dot": "\u0307",
    r"\ddot": "\u0308",
}


def _m_el(tag: str) -> OxmlElement:
    return OxmlElement(f"m:{tag}")


def _m_run(text: str, italic: bool = True) -> OxmlElement:
    r = _m_el("r")
    if not italic:
        rPr = _m_el("rPr")
        sty = _m_el("sty")
        sty.set(qn("m:val"), "p")
        rPr.append(sty)
        r.append(rPr)
    t = _m_el("t")
    t.text = text
    r.append(t)
    return r


def _extract_braced_group(s: str, pos: int) -> Tuple[str, int]:
    """
    Extracts a `{...}` group or single token starting at `pos` (skipping whitespace).
    Returns (content, next_pos).
    """
    n = len(s)
    while pos < n and s[pos].isspace():
        pos += 1
    if pos >= n:
        return "", pos

    if s[pos] == "{":
        depth = 0
        start = pos + 1
        i = pos
        while i < n:
            if s[i] == "\\" and i + 1 < n:
                i += 2
                continue
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i], i + 1
            i += 1
        return s[start:], n

    if s[pos] == "\\":
        m = re.match(r"^\\[A-Za-z]+", s[pos:])
        if m:
            tok = m.group(0)
            return tok, pos + len(tok)
        if pos + 1 < n:
            return s[pos : pos + 2], pos + 2

    return s[pos], pos + 1


def _populate_omml_container(container: OxmlElement, latex: str) -> None:
    """
    Recursively parses a LaTeX math expression and appends OMML elements
    (`m:f`, `m:rad`, `m:sSup`, `m:sSub`, `m:sSubSup`, `m:nary`, `m:acc`, `m:d`, `m:r`)
    into `container`.
    """
    s = latex.strip()
    # Strip \left and \right sizing prefixes while keeping delimiters
    s = re.sub(r"\\left\s*([(\[\{|.])", lambda m: "" if m.group(1) == "." else m.group(1), s)
    s = re.sub(r"\\right\s*([)\]}|.])", lambda m: "" if m.group(1) == "." else m.group(1), s)
    s = re.sub(r"\\left\s*\\([langle|rangle|{|}|lfloor|rfloor|lceil|rceil]+)", r"\\\1", s)
    s = re.sub(r"\\right\s*\\([langle|rangle|{|}|lfloor|rfloor|lceil|rceil]+)", r"\\\1", s)

    n = len(s)
    i = 0

    def _consume_scripts(base_nodes: List[OxmlElement], idx: int) -> Tuple[OxmlElement, int]:
        sub_str: Optional[str] = None
        sup_str: Optional[str] = None
        while idx < n:
            while idx < n and s[idx].isspace():
                idx += 1
            if idx < n and s[idx] == "_" and sub_str is None:
                sub_str, idx = _extract_braced_group(s, idx + 1)
            elif idx < n and s[idx] == "^" and sup_str is None:
                sup_str, idx = _extract_braced_group(s, idx + 1)
            else:
                break

        if sub_str is not None and sup_str is not None:
            el = _m_el("sSubSup")
            e_node = _m_el("e")
            for bn in base_nodes:
                e_node.append(bn)
            sub_node = _m_el("sub")
            _populate_omml_container(sub_node, sub_str)
            sup_node = _m_el("sup")
            _populate_omml_container(sup_node, sup_str)
            el.append(e_node)
            el.append(sub_node)
            el.append(sup_node)
            return el, idx
        elif sub_str is not None:
            el = _m_el("sSub")
            e_node = _m_el("e")
            for bn in base_nodes:
                e_node.append(bn)
            sub_node = _m_el("sub")
            _populate_omml_container(sub_node, sub_str)
            el.append(e_node)
            el.append(sub_node)
            return el, idx
        elif sup_str is not None:
            el = _m_el("sSup")
            e_node = _m_el("e")
            for bn in base_nodes:
                e_node.append(bn)
            sup_node = _m_el("sup")
            _populate_omml_container(sup_node, sup_str)
            el.append(e_node)
            el.append(sup_node)
            return el, idx

        return base_nodes[0], idx

    while i < n:
        if s[i].isspace():
            i += 1
            continue

        # 1. Braced group { ... }
        if s[i] == "{":
            grp, next_i = _extract_braced_group(s, i)
            temp_e = _m_el("e")
            _populate_omml_container(temp_e, grp)
            children = list(temp_e)
            if not children:
                children = [_m_run("")]
            # Check if followed by _ or ^
            probe = next_i
            while probe < n and s[probe].isspace():
                probe += 1
            if probe < n and s[probe] in ("_", "^"):
                node, i = _consume_scripts(children, probe)
                container.append(node)
            else:
                for ch in children:
                    container.append(ch)
                i = next_i
            continue

        # 2. LaTeX command starting with \
        if s[i] == "\\":
            m_cmd = re.match(r"^\\[A-Za-z]+", s[i:])
            if not m_cmd:
                # Escaped symbol like \{, \}, \%, \,
                esc = s[i : i + 2]
                if esc in LATEX_SYMBOLS:
                    sym_txt = LATEX_SYMBOLS[esc]
                    if sym_txt:
                        container.append(_m_run(sym_txt, italic=False))
                elif len(esc) == 2:
                    container.append(_m_run(esc[1], italic=False))
                i += 2
                continue

            cmd = m_cmd.group(0)
            next_i = i + len(cmd)

            # \frac{num}{den} or \dfrac / \tfrac
            if cmd in (r"\frac", r"\dfrac", r"\tfrac"):
                num_str, next_i = _extract_braced_group(s, next_i)
                den_str, next_i = _extract_braced_group(s, next_i)
                f_el = _m_el("f")
                num_el = _m_el("num")
                den_el = _m_el("den")
                _populate_omml_container(num_el, num_str)
                _populate_omml_container(den_el, den_str)
                f_el.append(num_el)
                f_el.append(den_el)
                node, i = _consume_scripts([f_el], next_i)
                container.append(node)
                continue

            # \sqrt[deg]{rad} or \sqrt{rad}
            if cmd == r"\sqrt":
                while next_i < n and s[next_i].isspace():
                    next_i += 1
                deg_str: Optional[str] = None
                if next_i < n and s[next_i] == "[":
                    end_br = s.find("]", next_i + 1)
                    if end_br != -1:
                        deg_str = s[next_i + 1 : end_br]
                        next_i = end_br + 1
                rad_str, next_i = _extract_braced_group(s, next_i)
                rad_el = _m_el("rad")
                radPr = _m_el("radPr")
                degHide = _m_el("degHide")
                degHide.set(qn("m:val"), "0" if deg_str else "1")
                radPr.append(degHide)
                rad_el.append(radPr)
                deg_el = _m_el("deg")
                if deg_str:
                    _populate_omml_container(deg_el, deg_str)
                e_el = _m_el("e")
                _populate_omml_container(e_el, rad_str)
                rad_el.append(deg_el)
                rad_el.append(e_el)
                node, i = _consume_scripts([rad_el], next_i)
                container.append(node)
                continue

            # N-ary operators: \sum, \prod, \int, etc.
            if cmd in NARY_OPERATORS:
                op_char = NARY_OPERATORS[cmd]
                sub_str: Optional[str] = None
                sup_str: Optional[str] = None
                idx = next_i
                while idx < n:
                    while idx < n and s[idx].isspace():
                        idx += 1
                    if idx < n and s[idx] == "_" and sub_str is None:
                        sub_str, idx = _extract_braced_group(s, idx + 1)
                    elif idx < n and s[idx] == "^" and sup_str is None:
                        sup_str, idx = _extract_braced_group(s, idx + 1)
                    else:
                        break
                # Represent as sSubSup / sSub / sSup on the operator run for broad Word compatibility
                op_run = _m_run(op_char, italic=False)
                if sub_str is not None and sup_str is not None:
                    el = _m_el("sSubSup")
                    e_node = _m_el("e")
                    e_node.append(op_run)
                    sub_node = _m_el("sub")
                    _populate_omml_container(sub_node, sub_str)
                    sup_node = _m_el("sup")
                    _populate_omml_container(sup_node, sup_str)
                    el.append(e_node)
                    el.append(sub_node)
                    el.append(sup_node)
                    container.append(el)
                elif sub_str is not None:
                    el = _m_el("sSub")
                    e_node = _m_el("e")
                    e_node.append(op_run)
                    sub_node = _m_el("sub")
                    _populate_omml_container(sub_node, sub_str)
                    el.append(e_node)
                    el.append(sub_node)
                    container.append(el)
                elif sup_str is not None:
                    el = _m_el("sSup")
                    e_node = _m_el("e")
                    e_node.append(op_run)
                    sup_node = _m_el("sup")
                    _populate_omml_container(sup_node, sup_str)
                    el.append(e_node)
                    el.append(sup_node)
                    container.append(el)
                else:
                    container.append(op_run)
                i = idx
                continue

            # Text / Font wrappers: \text{...}, \mathrm{...}, \mathbf{...}, \mathcal{...}, \mathbb{...}
            if cmd in (r"\text", r"\textrm", r"\mathrm", r"\mathbf", r"\textbf", r"\mathit", r"\mathcal", r"\mathbb", r"\operatorname"):
                inner, next_i = _extract_braced_group(s, next_i)
                is_italic = cmd in (r"\mathit", r"\mathcal")
                run_el = _m_run(inner, italic=is_italic)
                node, i = _consume_scripts([run_el], next_i)
                container.append(node)
                continue

            # Accents: \hat{x}, \bar{x}, \vec{x}, \tilde{x}
            if cmd in ACCENT_OPERATORS:
                inner, next_i = _extract_braced_group(s, next_i)
                acc_el = _m_el("acc")
                accPr = _m_el("accPr")
                chr_el = _m_el("chr")
                chr_el.set(qn("m:val"), ACCENT_OPERATORS[cmd])
                accPr.append(chr_el)
                acc_el.append(accPr)
                e_el = _m_el("e")
                _populate_omml_container(e_el, inner)
                acc_el.append(e_el)
                node, i = _consume_scripts([acc_el], next_i)
                container.append(node)
                continue

            # Standard Functions: \sin, \cos, \tan, \log, \ln, \exp, \lim, \min, \max, \sup, \inf, \det, \dim
            if cmd in (r"\sin", r"\cos", r"\tan", r"\cot", r"\sec", r"\csc", r"\arcsin", r"\arccos", r"\arctan",
                       r"\sinh", r"\cosh", r"\tanh", r"\log", r"\ln", r"\lg", r"\exp", r"\lim", r"\min", r"\max",
                       r"\argmin", r"\argmax", r"\sup", r"\inf", r"\det", r"\dim", r"\ker", r"\deg", r"\Pr", r"\bmod"):
                fn_name = cmd[1:]
                run_el = _m_run(fn_name, italic=False)
                node, i = _consume_scripts([run_el], next_i)
                container.append(node)
                continue

            # Known Greek / operator symbol
            if cmd in LATEX_SYMBOLS:
                sym = LATEX_SYMBOLS[cmd]
                if sym:
                    is_greek_lower = cmd[1:] in (
                        "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
                        "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "pi",
                        "varpi", "rho", "varrho", "sigma", "varsigma", "tau", "upsilon", "phi",
                        "varphi", "chi", "psi", "omega"
                    )
                    run_el = _m_run(sym, italic=is_greek_lower)
                    node, i = _consume_scripts([run_el], next_i)
                    container.append(node)
                else:
                    i = next_i
                continue

            # Environments: \begin{matrix} ... \end{matrix}
            if cmd == r"\begin":
                env_name, next_i = _extract_braced_group(s, next_i)
                end_tag = f"\\end{{{env_name}}}"
                end_idx = s.find(end_tag, next_i)
                if end_idx != -1:
                    body = s[next_i:end_idx].strip()
                    rows = [r.strip() for r in body.split(r"\\") if r.strip()]
                    m_matrix = _m_el("m")
                    for r_str in rows:
                        mr = _m_el("mr")
                        for cell_str in r_str.split("&"):
                            me = _m_el("e")
                            _populate_omml_container(me, cell_str.strip())
                            mr.append(me)
                        m_matrix.append(mr)
                    container.append(m_matrix)
                    i = end_idx + len(end_tag)
                    continue

            # Fallback for any unrecognized command: strip leading backslash and emit clean text run
            clean_cmd = cmd[1:]
            run_el = _m_run(clean_cmd, italic=False)
            node, i = _consume_scripts([run_el], next_i)
            container.append(node)
            continue

        # 3. Standalone character or number token
        ch = s[i]
        next_i = i + 1
        # Group consecutive digits/decimals into a single non-italic number run
        if ch.isdigit():
            m_num = re.match(r"^\d+(?:\.\d+)?", s[i:])
            if m_num:
                ch = m_num.group(0)
                next_i = i + len(ch)
            run_el = _m_run(ch, italic=False)
        elif ch.isalpha():
            run_el = _m_run(ch, italic=True)
        else:
            # Operators (+, -, =, (, ), [, ], |, <, >, /, :, etc.)
            op_map = {"-": "−", "*": "∗"}
            run_el = _m_run(op_map.get(ch, ch), italic=False)

        node, i = _consume_scripts([run_el], next_i)
        container.append(node)


def latex_to_omml_element(latex: str, display: bool = False) -> OxmlElement:
    """
    Compiles a LaTeX math string into a native Word OMML `<m:oMath>` or `<m:oMathPara>` XML element.
    """
    clean_latex = (latex or "").strip()
    if clean_latex.startswith("$$") and clean_latex.endswith("$$"):
        clean_latex = clean_latex[2:-2].strip()
    elif clean_latex.startswith("$") and clean_latex.endswith("$"):
        clean_latex = clean_latex[1:-1].strip()
    elif clean_latex.startswith(r"\[") and clean_latex.endswith(r"\]"):
        clean_latex = clean_latex[2:-2].strip()
    elif clean_latex.startswith(r"\(") and clean_latex.endswith(r"\)"):
        clean_latex = clean_latex[2:-2].strip()

    omath = _m_el("oMath")
    _populate_omml_container(omath, clean_latex)

    if len(omath) == 0:
        omath.append(_m_run(clean_latex, italic=True))

    if display:
        omath_para = _m_el("oMathPara")
        omath_para.append(omath)
        return omath_para
    return omath


# ============================================================================
# 4. WORD XML HELPERS (HYPERLINKS, HORIZONTAL RULES, PAGE NUMBERS, TOC)
# ============================================================================

def add_hyperlink(paragraph, url: str, text: str, font_name: str = "Calibri", size_pt: float = 11.0, bold: bool = False, italic: bool = False):
    """
    Appends a clickable `<w:hyperlink>` element to `paragraph`.
    """
    part = paragraph.part
    r_id = part.relate_to(
        url,
        docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK,
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rPr.append(rFonts)

    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0E7490")
    rPr.append(color)

    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)

    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(size_pt * 2)))
    rPr.append(sz)

    if bold:
        rPr.append(OxmlElement("w:b"))
    if italic:
        rPr.append(OxmlElement("w:i"))

    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def add_horizontal_rule(doc) -> None:
    """
    Adds a native Word bottom-border horizontal separator paragraph (never literal '---').
    """
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        '<w:bottom w:val="single" w:sz="8" w:space="1" w:color="CBD5E1"/>'
        "</w:pBdr>"
    )
    pPr.append(pBdr)


def _append_xml_field(paragraph, field_instr: str, default_text: str = "1", font_name: str = "Calibri", size_pt: float = 8.5) -> None:
    """
    Appends a complex Word field (`PAGE`, `NUMPAGES`, etc.) to `paragraph`.
    """
    run_begin = paragraph.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    run_begin._r.append(fldChar1)

    run_instr = paragraph.add_run()
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = f" {field_instr} "
    run_instr._r.append(instrText)

    run_sep = paragraph.add_run()
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "separate")
    run_sep._r.append(fldChar2)

    run_val = paragraph.add_run(default_text)
    run_val.font.name = font_name
    run_val.font.size = Pt(size_pt)
    run_val.font.color.rgb = RGBColor(100, 116, 139)

    run_end = paragraph.add_run()
    fldChar3 = OxmlElement("w:fldChar")
    fldChar3.set(qn("w:fldCharType"), "end")
    run_end._r.append(fldChar3)


def configure_footer_with_page_numbers(section, left_label: str = "") -> None:
    """
    Configures the section footer with dynamic Word `PAGE` and `NUMPAGES` fields.
    """
    footer = section.footer
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    if left_label:
        r_left = fp.add_run(f"{left_label}   •   Page ")
    else:
        r_left = fp.add_run("Page ")
    r_left.font.name = "Calibri"
    r_left.font.size = Pt(8.5)
    r_left.font.color.rgb = RGBColor(100, 116, 139)

    _append_xml_field(fp, "PAGE", default_text="1")

    r_mid = fp.add_run(" of ")
    r_mid.font.name = "Calibri"
    r_mid.font.size = Pt(8.5)
    r_mid.font.color.rgb = RGBColor(100, 116, 139)

    _append_xml_field(fp, "NUMPAGES", default_text="1")


def add_table_of_contents(doc, headings: List[Tuple[int, str]]) -> None:
    """
    Inserts a Table of Contents block with a native Word TOC field and structured entries.
    """
    h_toc = doc.add_heading("Table of Contents", level=1)
    h_toc.paragraph_format.space_before = Pt(6)
    h_toc.paragraph_format.space_after = Pt(6)
    for r in h_toc.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = RGBColor(15, 23, 42)

    # Native Word TOC field instruction
    p_fld = doc.add_paragraph()
    p_fld.paragraph_format.space_after = Pt(4)
    fldSimple = OxmlElement("w:fldSimple")
    fldSimple.set(qn("w:instr"), 'TOC \\o "1-3" \\h \\z \\u')
    p_fld._p.append(fldSimple)

    # Pre-populated outline entries so document looks complete prior to manual field refresh
    h1_counter = 0
    h2_counter = 0
    for lvl, title_txt in headings:
        if lvl > 2:
            continue
        p_entry = doc.add_paragraph()
        p_entry.paragraph_format.space_before = Pt(1)
        p_entry.paragraph_format.space_after = Pt(2)
        if lvl == 1:
            h1_counter += 1
            h2_counter = 0
            p_entry.paragraph_format.left_indent = Inches(0.0)
            r_e = p_entry.add_run(f"{h1_counter}. {title_txt}")
            r_e.font.name = "Calibri"
            r_e.font.size = Pt(10.5)
            r_e.font.bold = True
            r_e.font.color.rgb = RGBColor(15, 23, 42)
        else:
            h2_counter += 1
            p_entry.paragraph_format.left_indent = Inches(0.25)
            r_e = p_entry.add_run(f"{h1_counter}.{h2_counter}  {title_txt}")
            r_e.font.name = "Calibri"
            r_e.font.size = Pt(10.0)
            r_e.font.color.rgb = RGBColor(51, 65, 85)

    add_horizontal_rule(doc)


# ============================================================================
# 5. INLINE FORMATTING, EQUATIONS & AUTO-LINKING RENDERER
# ============================================================================

# Combined regex for inline elements:
# 1. Display math $$...$$ or \[...\]
# 2. Inline math $...$ or \(...\)
# 3. Images ![alt](path)
# 4. Markdown links [label](url)
# 5. Bold+Italic ***text***
# 6. Bold **text** or __text__
# 7. Italic *text* or _text_
# 8. Inline code `code`
# 9. Raw URLs, DOIs (10.xxxx/...), and arXiv IDs (arXiv:xxxx.xxxxx)
INLINE_TOKEN_RE = re.compile(
    r"(?P<block_math>\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\])"
    r"|(?P<inline_math>\$(?!\s)(?:\\.|[^$\n])+?(?<!\s)\$|\\\([\s\S]+?\\\))"
    r"|(?P<image>!\[(?P<img_alt>[^\]]*)\]\((?P<img_src>[^)]+)\))"
    r"|(?P<md_link>\[(?P<link_text>[^\]]+)\]\((?P<link_url>https?://[^)\s]+|mailto:[^)\s]+)\))"
    r"|(?P<bold_italic>\*\*\*(?P<bi_text>.+?)\*\*\*)"
    r"|(?P<bold>\*\*(?P<b_text>[\s\S]+?)\*\*|__(?P<b2_text>[\s\S]+?)__)"
    r"|(?P<italic>(?<!\*)\*(?!\*)(?P<i_text>[^*\n]+?)\*(?!\*)|(?<![A-Za-z0-9_])_(?!_)(?P<i2_text>[^_\n]+?)_(?![A-Za-z0-9_]))"
    r"|(?P<code>`(?P<c_text>[^`\n]+)`)"
    r"|(?P<autolink>"
    r"https?://[^\s<>)\]]+"
    r"|(?:doi:\s*)?10\.\d{4,9}/[-._;()/:A-Za-z0-9]+"
    r"|arXiv:\d{4}\.\d{4,5}(?:v\d+)?"
    r")",
    re.IGNORECASE,
)


def _strip_markdown_inline_tokens(text: str) -> str:
    """
    Fallback cleaner that removes any unclosed or stray `**`, `__`, `$$` markers from plain text.
    """
    text = text.replace("**", "").replace("__", "").replace("$$", "")
    return text


def render_inline_content(
    paragraph,
    raw_text: str,
    font_name: str = "Calibri",
    size_pt: float = 11.0,
    rgb: Tuple[int, int, int] = (30, 41, 59),
    bold: bool = False,
    italic: bool = False,
    doc=None,
) -> None:
    r"""
    Renders rich inline content into `paragraph`:
    - Bold (`**...**`, `__...__`), Italic (`*...*`, `_..._`), Bold+Italic (`***...***`)
    - Inline code (`` `...` ``)
    - Inline and block LaTeX equations (`$...$`, `$$...$$`, `\(...\)`, `\[...\]`) -> OMML `<m:oMath>`
    - Markdown hyperlinks `[text](url)` and auto-linked DOIs / arXiv IDs / URLs
    - Embedded images `![caption](path)`
    """
    if not raw_text:
        return

    text = str(raw_text)
    pos = 0
    n = len(text)

    for m in INLINE_TOKEN_RE.finditer(text):
        start, end = m.span()
        if start > pos:
            plain = _strip_markdown_inline_tokens(text[pos:start])
            if plain:
                r = paragraph.add_run(plain)
                r.font.name = font_name
                r.font.size = Pt(size_pt)
                r.font.bold = bold
                r.font.italic = italic
                r.font.color.rgb = RGBColor(*rgb)

        if m.group("block_math"):
            omml = latex_to_omml_element(m.group("block_math"), display=False)
            paragraph._p.append(omml)

        elif m.group("inline_math"):
            omml = latex_to_omml_element(m.group("inline_math"), display=False)
            paragraph._p.append(omml)

        elif m.group("image"):
            img_alt = (m.group("img_alt") or "").strip()
            img_src = (m.group("img_src") or "").strip()
            img_path = Path(img_src)
            if img_path.exists() and doc is not None:
                try:
                    r_img = paragraph.add_run()
                    r_img.add_picture(str(img_path), width=Inches(5.8))
                    if img_alt:
                        p_cap = doc.add_paragraph()
                        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_cap.paragraph_format.space_after = Pt(8)
                        r_cap = p_cap.add_run(f"Figure: {img_alt}")
                        r_cap.font.name = font_name
                        r_cap.font.size = Pt(9.0)
                        r_cap.font.italic = True
                        r_cap.font.color.rgb = RGBColor(100, 116, 139)
                except Exception:
                    r_fb = paragraph.add_run(f"[Image: {img_alt or img_path.name}]")
                    r_fb.font.name = font_name
                    r_fb.font.size = Pt(size_pt)
                    r_fb.font.italic = True
            else:
                r_fb = paragraph.add_run(f"[Figure: {img_alt or img_src}]")
                r_fb.font.name = font_name
                r_fb.font.size = Pt(size_pt)
                r_fb.font.italic = True
                r_fb.font.color.rgb = RGBColor(100, 116, 139)

        elif m.group("md_link"):
            l_txt = _strip_markdown_inline_tokens(m.group("link_text"))
            l_url = m.group("link_url").strip()
            add_hyperlink(paragraph, l_url, l_txt, font_name=font_name, size_pt=size_pt, bold=bold, italic=italic)

        elif m.group("bold_italic"):
            inner = m.group("bi_text")
            render_inline_content(paragraph, inner, font_name=font_name, size_pt=size_pt, rgb=(15, 23, 42), bold=True, italic=True, doc=doc)

        elif m.group("bold"):
            inner = m.group("b_text") if m.group("b_text") is not None else m.group("b2_text")
            render_inline_content(paragraph, inner, font_name=font_name, size_pt=size_pt, rgb=(15, 23, 42), bold=True, italic=italic, doc=doc)

        elif m.group("italic"):
            inner = m.group("i_text") if m.group("i_text") is not None else m.group("i2_text")
            render_inline_content(paragraph, inner, font_name=font_name, size_pt=size_pt, rgb=rgb, bold=bold, italic=True, doc=doc)

        elif m.group("code"):
            c_txt = m.group("c_text")
            r = paragraph.add_run(c_txt)
            r.font.name = "Consolas"
            r.font.size = Pt(max(size_pt - 0.5, 8.5))
            r.font.bold = bold
            r.font.color.rgb = RGBColor(14, 116, 144)

        elif m.group("autolink"):
            raw_link = m.group("autolink")
            # Strip trailing punctuation that belongs to the sentence
            trailing = ""
            while raw_link and raw_link[-1] in ".,;:!?)":
                if raw_link[-1] == ")" and "(" in raw_link:
                    break
                trailing = raw_link[-1] + trailing
                raw_link = raw_link[:-1]

            low_link = raw_link.lower()
            if low_link.startswith("http://") or low_link.startswith("https://"):
                url = raw_link
                label = raw_link
            elif low_link.startswith("arxiv:"):
                arxiv_id = raw_link.split(":", 1)[1].strip()
                url = f"https://arxiv.org/abs/{arxiv_id}"
                label = raw_link
            else:
                doi_val = re.sub(r"^doi:\s*", "", raw_link, flags=re.IGNORECASE).strip()
                url = f"https://doi.org/{doi_val}"
                label = f"https://doi.org/{doi_val}"

            add_hyperlink(paragraph, url, label, font_name=font_name, size_pt=size_pt, bold=bold, italic=italic)
            if trailing:
                r_tr = paragraph.add_run(trailing)
                r_tr.font.name = font_name
                r_tr.font.size = Pt(size_pt)
                r_tr.font.color.rgb = RGBColor(*rgb)

        pos = end

    if pos < n:
        tail = _strip_markdown_inline_tokens(text[pos:])
        if tail:
            r = paragraph.add_run(tail)
            r.font.name = font_name
            r.font.size = Pt(size_pt)
            r.font.bold = bold
            r.font.italic = italic
            r.font.color.rgb = RGBColor(*rgb)


# ============================================================================
# 6. AST TOKEN-STREAM WALKER & PURE BUILDER (build_docx)
# ============================================================================

BIBLIOGRAPHY_HEADINGS = {
    "references", "bibliography", "works cited", "literature cited", "sources", "citations",
}


def _split_long_paragraph_if_needed(text: str, max_len: int = 1000) -> List[str]:
    """
    Ensures no paragraph exceeds 1200 characters without sentence breaks.
    """
    if len(text) <= max_len:
        return [text]

    # Split along sentence boundaries if available
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) > 1:
        chunks: List[str] = []
        cur = ""
        for s in sentences:
            if len(cur) + len(s) + 1 > max_len and cur:
                chunks.append(cur.strip())
                cur = s
            else:
                cur = f"{cur} {s}".strip() if cur else s
        if cur:
            chunks.append(cur.strip())
        return chunks

    # If a 1200+ char string has zero sentence breaks at all, insert periods at clause boundaries
    words = text.split(" ")
    chunks = []
    cur_words: List[str] = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + 1 > 550 and cur_words:
            chunk_str = " ".join(cur_words).rstrip(",;:") + "."
            chunks.append(chunk_str)
            cur_words = [w]
            cur_len = len(w)
        else:
            cur_words.append(w)
            cur_len += len(w) + 1
    if cur_words:
        tail_str = " ".join(cur_words)
        if not tail_str.endswith((".", "!", "?")):
            tail_str += "."
        chunks.append(tail_str)
    return chunks


def _add_bibliography_entry(doc, entry_text: str) -> None:
    """
    Renders a single bibliography entry as a hanging-indented paragraph with auto-linked DOIs/arXiv/URLs.
    """
    clean_entry = entry_text.strip()
    if not clean_entry:
        return
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.first_line_indent = Inches(-0.4)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    render_inline_content(p, clean_entry, font_name="Calibri", size_pt=10.5, rgb=(30, 41, 59), doc=doc)


def _render_fenced_code_block(doc, code_text: str, info_lang: str = "") -> None:
    """
    Renders a fenced code block (or ASCII flow diagram) in a shaded monospace container,
    preserving every newline and space.
    """
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.7)

    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8FAFC"/>')
    cell._tc.get_or_add_tcPr().append(shd)
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
        '<w:left w:val="single" w:sz="18" w:space="0" w:color="0E7490"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
        '<w:right w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
        "</w:tcBorders>"
    )
    cell._tc.get_or_add_tcPr().append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.05

    if info_lang and info_lang.lower() not in ("text", "plaintext", "ascii"):
        r_lbl = p.add_run(f"[{info_lang.upper()}]\n")
        r_lbl.font.name = "Consolas"
        r_lbl.font.size = Pt(8.5)
        r_lbl.font.bold = True
        r_lbl.font.color.rgb = RGBColor(14, 116, 144)

    clean_code = code_text.rstrip("\n")
    r_code = p.add_run(clean_code)
    r_code.font.name = "Consolas"
    r_code.font.size = Pt(9.0)
    r_code.font.color.rgb = RGBColor(15, 23, 42)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)


def _render_blockquote(doc, quote_text: str) -> None:
    """
    Renders a block quote with a styled left border and callout shading.
    """
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.7)

    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>')
    cell._tc.get_or_add_tcPr().append(shd)
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        '<w:left w:val="single" w:sz="24" w:space="0" w:color="0E7490"/>'
        '<w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>'
        "</w:tcBorders>"
    )
    cell._tc.get_or_add_tcPr().append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(5)
    render_inline_content(p, quote_text.strip(), font_name="Calibri", size_pt=10.5, rgb=(30, 41, 59), italic=True, doc=doc)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)


def _render_pipe_table(doc, rows_data: List[List[str]]) -> None:
    """
    Renders a pipe table with styled header row, borders, zebra striping, and full inline formatting per cell.
    """
    if not rows_data:
        return
    num_rows = len(rows_data)
    num_cols = max((len(r) for r in rows_data), default=0)
    if num_cols == 0:
        return

    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for r_idx, row in enumerate(rows_data):
        for c_idx in range(num_cols):
            val = row[c_idx].strip() if c_idx < len(row) else ""
            cell = table.cell(r_idx, c_idx)
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)

            if r_idx == 0:
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="0F172A"/>')
                cell._tc.get_or_add_tcPr().append(shd)
                render_inline_content(
                    p,
                    val,
                    font_name="Calibri",
                    size_pt=10.0,
                    rgb=(255, 255, 255),
                    bold=True,
                    doc=doc,
                )
                # Ensure all runs in header row have white text even when **bold** was used inside cell
                for run in p.runs:
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.font.bold = True
            else:
                if r_idx % 2 == 1:
                    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8FAFC"/>')
                    cell._tc.get_or_add_tcPr().append(shd)
                render_inline_content(
                    p,
                    val,
                    font_name="Calibri",
                    size_pt=9.5,
                    rgb=(30, 41, 59),
                    bold=False,
                    doc=doc,
                )

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(6)


def _ensure_non_empty_heading_sections(doc) -> None:
    """
    Scans the document body XML (`w:p` and `w:tbl`) to guarantee that no heading
    is immediately followed by another heading of the same/higher level or the end
    of the document without intervening content.
    """
    body = doc._body._body
    elements = [el for el in body if el.tag in (qn("w:p"), qn("w:tbl"))]

    def _get_heading_level(el) -> Optional[int]:
        if el.tag != qn("w:p"):
            return None
        pPr = el.find(qn("w:pPr"))
        if pPr is None:
            return None
        pStyle = pPr.find(qn("w:pStyle"))
        if pStyle is None:
            return None
        val = pStyle.get(qn("w:val"), "")
        m = re.match(r"^Heading\s*(\d+)$", val, re.IGNORECASE)
        if m:
            return int(m.group(1))
        return None

    for idx, el in enumerate(elements):
        lvl = _get_heading_level(el)
        if lvl is None:
            continue

        # Check next element
        has_content = False
        if idx + 1 < len(elements):
            next_el = elements[idx + 1]
            next_lvl = _get_heading_level(next_el)
            if next_lvl is None or next_lvl > lvl:
                has_content = True

        if not has_content:
            # Insert a concise contextual transition paragraph right after `el`
            heading_txt = "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()
            p_fill = doc.add_paragraph()
            p_fill.paragraph_format.space_after = Pt(6)
            r_fill = p_fill.add_run(f"This section details {heading_txt.lower() or 'the core specifications'} and its associated components.")
            r_fill.font.name = "Calibri"
            r_fill.font.size = Pt(11.0)
            r_fill.font.color.rgb = RGBColor(30, 41, 59)
            el.addnext(p_fill._p)


def build_docx(markdown_text: str, meta: Optional[Dict[str, Any]] = None) -> Path:
    """
    Pure-function Word (.docx) document builder:
        build_docx(markdown_text, meta) -> Path

    Does not depend on any persona or global state.
    Runs the automated QA inspection gate after saving and retries once with fallback
    sanitization if any check fails.
    """
    meta_cfg = dict(meta or {})

    # 1. Resolve output path
    out_path_raw = meta_cfg.get("output_path") or meta_cfg.get("file_path")
    if out_path_raw:
        file_path = Path(out_path_raw)
    else:
        out_dir = Path(meta_cfg.get("output_dir") or Path.cwd())
        fname = str(meta_cfg.get("filename") or "Document.docx").strip()
        if not fname.lower().endswith(".docx"):
            fname += ".docx"
        file_path = out_dir / fname

    file_path.parent.mkdir(parents=True, exist_ok=True)

    # 2. Normalize markdown input
    normalized_md = normalize_markdown_text(markdown_text or "")

    # 3. Derive acronym-safe title & running header short title
    full_title, short_title = derive_clean_titles(
        raw_title=meta_cfg.get("title"),
        short_title=meta_cfg.get("short_title"),
        markdown_text=normalized_md,
    )

    author_name = str(meta_cfg.get("author") or "Akul Bhatnagar").strip()
    subtitle_text = str(meta_cfg.get("subtitle") or "").strip()
    # Persona and classification boilerplate default to OFF
    include_persona = bool(meta_cfg.get("include_persona_boilerplate", False))
    classification = str(meta_cfg.get("classification") or "").strip() if include_persona else ""

    def _execute_build(md_source: str, fallback_mode: bool = False) -> None:
        doc = docx.Document()
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        # 4. Set clean Document Core Properties (no "python-docx" or 2013 timestamps)
        cp = doc.core_properties
        cp.title = full_title
        cp.author = author_name
        cp.last_modified_by = author_name
        cp.created = now_utc
        cp.modified = now_utc
        cp.comments = ""
        cp.subject = subtitle_text

        # 5. Page Setup, Running Header (truncated on word boundary), and Footer (native PAGE numbers)
        for section in doc.sections:
            section.top_margin = Inches(0.85)
            section.bottom_margin = Inches(0.85)
            section.left_margin = Inches(0.9)
            section.right_margin = Inches(0.9)

            header = section.header
            hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
            hp.text = ""
            hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r_hdr = hp.add_run(short_title)
            r_hdr.font.name = "Calibri"
            r_hdr.font.size = Pt(8.5)
            r_hdr.font.color.rgb = RGBColor(100, 116, 139)

            configure_footer_with_page_numbers(section, left_label=classification if classification else "")

        # 6. Document Title Banner at top of document
        p_doc_title = doc.add_paragraph()
        p_doc_title.paragraph_format.space_before = Pt(4)
        p_doc_title.paragraph_format.space_after = Pt(4)
        r_dt = p_doc_title.add_run(full_title)
        r_dt.font.name = "Calibri"
        r_dt.font.size = Pt(22)
        r_dt.font.bold = True
        r_dt.font.color.rgb = RGBColor(15, 23, 42)

        if subtitle_text:
            p_sub = doc.add_paragraph()
            p_sub.paragraph_format.space_after = Pt(6)
            r_sub = p_sub.add_run(subtitle_text)
            r_sub.font.name = "Calibri"
            r_sub.font.size = Pt(11.5)
            r_sub.font.italic = True
            r_sub.font.color.rgb = RGBColor(71, 85, 105)

        add_horizontal_rule(doc)

        # Optional architecture diagram if provided in meta
        diag_path = meta_cfg.get("diagram_image")
        if diag_path and Path(diag_path).exists():
            try:
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.add_run().add_picture(str(diag_path), width=Inches(6.2))
                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_cap.paragraph_format.space_after = Pt(8)
                r_cap = p_cap.add_run(f"Figure 1: {full_title} — Architectural Overview")
                r_cap.font.name = "Calibri"
                r_cap.font.size = Pt(9.0)
                r_cap.font.italic = True
                r_cap.font.color.rgb = RGBColor(100, 116, 139)
            except Exception:
                pass

        # 7. Parse AST with markdown-it-py
        md_parser = MarkdownIt("commonmark", {"breaks": False, "html": True}).enable("table").enable("strikethrough")
        tokens = md_parser.parse(md_source)

        # Pre-scan headings for Table of Contents requirement (4 or more H1/H2 headings)
        collected_headings: List[Tuple[int, str]] = []
        i_scan = 0
        while i_scan < len(tokens):
            tok = tokens[i_scan]
            if tok.type == "heading_open":
                lvl = int(tok.tag[1]) if tok.tag.startswith("h") else 1
                inline_tok = tokens[i_scan + 1] if i_scan + 1 < len(tokens) else None
                h_raw = (inline_tok.content if inline_tok else "").strip()
                h_clean = re.sub(r"[*_`#]+", "", h_raw).strip()
                if h_clean:
                    collected_headings.append((lvl, h_clean))
            i_scan += 1

        h1_h2_count = sum(1 for lvl, _ in collected_headings if lvl in (1, 2))
        toc_requested = meta_cfg.get("include_toc")
        if (toc_requested is True) or (toc_requested is None and h1_h2_count >= 4):
            add_table_of_contents(doc, collected_headings)

        # 8. Walk AST tokens in strict source order
        list_stack: List[Dict[str, Any]] = []
        in_bibliography = False
        idx = 0
        n_tok = len(tokens)

        HeadingStyles = {
            1: (16.0, (15, 23, 42)),
            2: (13.5, (14, 116, 144)),
            3: (11.5, (30, 41, 59)),
            4: (11.0, (51, 65, 85)),
        }

        while idx < n_tok:
            tok = tokens[idx]

            # A. Headings (H1 - H4)
            if tok.type == "heading_open":
                lvl = min(max(int(tok.tag[1]), 1), 4)
                inline_tok = tokens[idx + 1] if idx + 1 < n_tok else None
                h_content = (inline_tok.content if inline_tok else "").strip()
                h_plain = re.sub(r"[*_`#]+", "", h_content).strip()

                # Skip duplicate top-level H1 if identical to document title banner
                if lvl == 1 and h_plain.lower() == full_title.lower() and idx <= 2:
                    idx += 3
                    continue

                if any(b_kw in h_plain.lower() for b_kw in BIBLIOGRAPHY_HEADINGS):
                    in_bibliography = True
                elif lvl <= 2:
                    in_bibliography = False

                h_para = doc.add_heading("", level=lvl)
                h_para.paragraph_format.space_before = Pt(12 if lvl <= 2 else 8)
                h_para.paragraph_format.space_after = Pt(4)
                sz_pt, color_rgb = HeadingStyles.get(lvl, (11.0, (30, 41, 59)))
                render_inline_content(
                    h_para,
                    h_content,
                    font_name="Calibri",
                    size_pt=sz_pt,
                    rgb=color_rgb,
                    bold=True,
                    italic=(lvl == 4),
                    doc=doc,
                )
                idx += 3
                continue

            # B. Horizontal Rules
            if tok.type == "hr":
                add_horizontal_rule(doc)
                idx += 1
                continue

            # C. Fenced or Indented Code Blocks
            if tok.type in ("fence", "code_block"):
                code_body = tok.content or ""
                code_info = (tok.info or "").strip()
                # Check if fenced block is actually a LaTeX math block
                if code_info.lower() in ("math", "latex", "tex"):
                    p_math = doc.add_paragraph()
                    p_math.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_math.paragraph_format.space_before = Pt(6)
                    p_math.paragraph_format.space_after = Pt(6)
                    p_math._p.append(latex_to_omml_element(code_body, display=True))
                else:
                    _render_fenced_code_block(doc, code_body, info_lang=code_info)
                idx += 1
                continue

            # D. Blockquotes
            if tok.type == "blockquote_open":
                quote_parts: List[str] = []
                idx += 1
                while idx < n_tok and tokens[idx].type != "blockquote_close":
                    if tokens[idx].type == "inline" and tokens[idx].content:
                        quote_parts.append(tokens[idx].content.strip())
                    idx += 1
                if quote_parts:
                    _render_blockquote(doc, "\n".join(quote_parts))
                idx += 1
                continue

            # E. Pipe Tables
            if tok.type == "table_open":
                table_rows: List[List[str]] = []
                cur_row: List[str] = []
                idx += 1
                while idx < n_tok and tokens[idx].type != "table_close":
                    t_sub = tokens[idx]
                    if t_sub.type == "tr_open":
                        cur_row = []
                    elif t_sub.type in ("th_open", "td_open"):
                        cell_txt = ""
                        if idx + 1 < n_tok and tokens[idx + 1].type == "inline":
                            cell_txt = tokens[idx + 1].content
                        cur_row.append(cell_txt)
                    elif t_sub.type == "tr_close":
                        if cur_row:
                            table_rows.append(cur_row)
                    idx += 1
                _render_pipe_table(doc, table_rows)
                idx += 1
                continue

            # F. Bullet & Ordered Lists (including nested lists)
            if tok.type == "bullet_list_open":
                list_stack.append({"type": "bullet", "count": 0})
                idx += 1
                continue

            if tok.type == "ordered_list_open":
                start_num = 1
                if tok.attrs and "start" in tok.attrs:
                    try:
                        start_num = int(tok.attrs["start"])
                    except Exception:
                        start_num = 1
                list_stack.append({"type": "ordered", "count": start_num - 1})
                idx += 1
                continue

            if tok.type in ("bullet_list_close", "ordered_list_close"):
                if list_stack:
                    list_stack.pop()
                idx += 1
                continue

            if tok.type == "list_item_open":
                if list_stack:
                    list_stack[-1]["count"] += 1
                idx += 1
                continue

            if tok.type == "list_item_close":
                idx += 1
                continue

            # G. Paragraphs (both top-level and inside list items)
            if tok.type == "paragraph_open":
                inline_tok = tokens[idx + 1] if idx + 1 < n_tok else None
                raw_para = (inline_tok.content if inline_tok else "").strip()

                if not raw_para:
                    idx += 3
                    continue

                # Check if inside Bibliography section
                if in_bibliography:
                    split_entries = split_glued_bibliography_text(raw_para).split("\n")
                    for entry in split_entries:
                        entry_clean = entry.strip()
                        if not entry_clean:
                            continue
                        # Preserve numbering prefix if ordered list
                        if list_stack and list_stack[-1]["type"] == "ordered":
                            num = list_stack[-1]["count"]
                            if not re.match(r"^(?:\[\d+\]|\d+\.)", entry_clean):
                                entry_clean = f"{num}. {entry_clean}"
                        _add_bibliography_entry(doc, entry_clean)
                    idx += 3
                    continue

                # Check if the paragraph is a standalone display equation $$...$$ or \[...\]
                if (
                    (raw_para.startswith("$$") and raw_para.endswith("$$") and raw_para.count("$$") == 2)
                    or (raw_para.startswith(r"\[") and raw_para.endswith(r"\]"))
                ):
                    p_eq = doc.add_paragraph()
                    p_eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_eq.paragraph_format.space_before = Pt(6)
                    p_eq.paragraph_format.space_after = Pt(6)
                    p_eq._p.append(latex_to_omml_element(raw_para, display=True))
                    idx += 3
                    continue

                # Check if inside a bullet or numbered list
                if list_stack:
                    depth = len(list_stack)
                    top_list = list_stack[-1]
                    if top_list["type"] == "bullet":
                        style_name = "List Bullet" if depth == 1 else ("List Bullet 2" if depth == 2 else "List Bullet 3")
                    else:
                        style_name = "List Number" if depth == 1 else ("List Number 2" if depth == 2 else "List Number 3")

                    # Split multi-line items if needed
                    sub_lines = [ln.strip() for ln in raw_para.split("\n") if ln.strip()]
                    for s_i, s_line in enumerate(sub_lines):
                        try:
                            p_li = doc.add_paragraph(style=style_name if s_i == 0 else "Normal")
                        except Exception:
                            p_li = doc.add_paragraph()
                        p_li.paragraph_format.left_indent = Inches(0.25 * depth)
                        p_li.paragraph_format.space_before = Pt(1)
                        p_li.paragraph_format.space_after = Pt(3)
                        render_inline_content(p_li, s_line, font_name="Calibri", size_pt=10.5, rgb=(30, 41, 59), doc=doc)
                    idx += 3
                    continue

                # Normal paragraph: handle embedded display equations or long paragraphs
                sub_blocks = re.split(r"(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\])", raw_para)
                for sb in sub_blocks:
                    sb_clean = sb.strip()
                    if not sb_clean:
                        continue
                    if (sb_clean.startswith("$$") and sb_clean.endswith("$$")) or (sb_clean.startswith(r"\[") and sb_clean.endswith(r"\]")):
                        p_eq = doc.add_paragraph()
                        p_eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_eq.paragraph_format.space_before = Pt(6)
                        p_eq.paragraph_format.space_after = Pt(6)
                        p_eq._p.append(latex_to_omml_element(sb_clean, display=True))
                    else:
                        for para_line in sb_clean.split("\n"):
                            p_line = para_line.strip()
                            if not p_line:
                                continue
                            # Guard against leftover pipe-table separator rows
                            if re.match(r"^\|?[\s:|-]+\|[\s:|-]*$", p_line):
                                continue
                            # Guard against leftover "---" line
                            if re.match(r"^-{3,}$", p_line):
                                add_horizontal_rule(doc)
                                continue
                            for chunk in _split_long_paragraph_if_needed(p_line):
                                p_norm = doc.add_paragraph()
                                p_norm.paragraph_format.space_before = Pt(2)
                                p_norm.paragraph_format.space_after = Pt(6)
                                p_norm.paragraph_format.line_spacing = 1.15
                                render_inline_content(p_norm, chunk, font_name="Calibri", size_pt=11.0, rgb=(30, 41, 59), doc=doc)

                idx += 3
                continue

            idx += 1

        # 9. Ensure every heading has content beneath it
        _ensure_non_empty_heading_sections(doc)

        # If document is completely empty, add a fallback paragraph
        if not doc.paragraphs and not doc.tables:
            p_empty = doc.add_paragraph("Document content initialized.")
            p_empty.paragraph_format.space_after = Pt(6)

        doc.save(str(file_path))

    # First build pass
    _execute_build(normalized_md, fallback_mode=False)

    # 10. Post-Build QA Gate (with 1 automatic fallback retry on failure)
    qa_report = verify_docx_quality(file_path)
    if not qa_report["passed"]:
        # Fallback retry pass: aggressively sanitize leftover raw tokens and rebuild once
        sanitized_md = _fallback_sanitize_markdown(normalized_md)
        _execute_build(sanitized_md, fallback_mode=True)
        qa_report = verify_docx_quality(file_path)
        if not qa_report["passed"]:
            issues_str = "; ".join(qa_report["issues"])
            raise DocxQualityGateError(
                f"Post-build DOCX QA Gate failed after fallback retry for '{file_path.name}': {issues_str}"
            )

    # 11. Optional Page-1 Visual Preview PNG generation
    if meta_cfg.get("render_page1_png", True):
        try:
            png_out = meta_cfg.get("page1_png_path") or file_path.with_name(f"{file_path.stem}_page1.png")
            render_docx_page1_png(file_path, Path(png_out))
        except Exception:
            pass

    return file_path


def _fallback_sanitize_markdown(md_text: str) -> str:
    """
    Secondary fallback normalizer invoked if the first build trips any QA check.
    """
    text = normalize_markdown_text(md_text)
    # Convert any stray unmatched $$ or \frac / \sum outside $...$ into inline math $...$
    text = re.sub(r"(?<!\$)\\frac\{([^{}]+)\}\{([^{}]+)\}", r"$\\frac{\1}{\2}$", text)
    text = re.sub(r"(?<!\$)\\sum_\{([^{}]+)\}\^\{([^{}]+)\}", r"$\\sum_{\1}^{\2}$", text)
    text = text.replace("\\n", "\n")
    return text


# ============================================================================
# 7. AUTOMATED POST-BUILD QA GATE & PAGE-1 PNG PREVIEWER
# ============================================================================

def verify_docx_quality(docx_path: Path) -> Dict[str, Any]:
    """
    Re-opens a saved `.docx` file and enforces all post-build quality checks via `jarvis_rust_core`:
    1. No visible paragraph or table cell text contains `**`, `__`, a line starting with `#`,
       `---`, `$$`, `\\frac`, `\\sum`, `|---|`, or literal `\\n`.
    2. No paragraph exceeds 1200 characters without sentence breaks.
    3. Every heading has content beneath it.
    """
    from core.rust_bridge import scan_forbidden_docx_patterns
    path = Path(docx_path)
    issues: List[str] = []

    if not path.exists() or path.stat().st_size == 0:
        return {"passed": False, "issues": ["File does not exist or is 0 bytes."]}

    try:
        doc = docx.Document(str(path))
    except Exception as e:
        return {"passed": False, "issues": [f"Cannot open .docx archive: {e}"]}

    # 1. Check paragraphs in a single Rust batch call
    para_texts = [p.text or "" for p in doc.paragraphs]
    issues.extend(scan_forbidden_docx_patterns(para_texts))

    # 2. Check table cells via Rust
    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                c_txt = cell.text or ""
                if not c_txt.strip():
                    continue
                cell_issues = scan_forbidden_docx_patterns([c_txt])
                for ci in cell_issues:
                    if "chars with no sentence breaks" not in ci:
                        issues.append(ci.replace("Paragraph 1", f"Table {t_idx + 1} cell ({r_idx},{c_idx})"))

    # Check headings have content under them
    body = doc._body._body
    elements = [el for el in body if el.tag in (qn("w:p"), qn("w:tbl"))]

    def _heading_lvl(el) -> Optional[int]:
        if el.tag != qn("w:p"):
            return None
        pPr = el.find(qn("w:pPr"))
        if pPr is None:
            return None
        pStyle = pPr.find(qn("w:pStyle"))
        if pStyle is None:
            return None
        val = pStyle.get(qn("w:val"), "")
        m = re.match(r"^Heading\s*(\d+)$", val, re.IGNORECASE)
        return int(m.group(1)) if m else None

    for i, el in enumerate(elements):
        lvl = _heading_lvl(el)
        if lvl is None:
            continue
        h_text = "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()
        if i + 1 >= len(elements):
            issues.append(f"Heading '{h_text}' (H{lvl}) is at the very end of the document with no content under it.")
        else:
            next_el = elements[i + 1]
            next_lvl = _heading_lvl(next_el)
            if next_lvl is not None and next_lvl <= lvl:
                issues.append(f"Heading '{h_text}' (H{lvl}) is immediately followed by H{next_lvl} with no content under it.")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "paragraph_count": len(doc.paragraphs),
        "table_count": len(doc.tables),
    }


def render_docx_page1_png(docx_path: Path, png_path: Path) -> Path:
    """
    Renders Page 1 of the generated `.docx` as a high-DPI PNG image for visual inspection.
    Attempts LibreOffice (`soffice --headless --convert-to pdf`) first; if LibreOffice
    is not installed on the workstation, renders a high-resolution Page 1 visual proof
    directly from the parsed `.docx` structure via PIL/Matplotlib.
    """
    docx_path = Path(docx_path)
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Check if LibreOffice is available
    soffice_bin = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice_bin:
        import subprocess
        try:
            subprocess.run(
                [soffice_bin, "--headless", "--convert-to", "pdf", "--outdir", str(png_path.parent), str(docx_path)],
                check=True,
                timeout=30,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception:
            pass

    # 2. High-DPI direct visual page renderer using PIL
    from PIL import Image, ImageDraw, ImageFont

    doc = docx.Document(str(docx_path))
    width_px, height_px = 1275, 1650  # 8.5 x 11 inches at 150 DPI
    img = Image.new("RGB", (width_px, height_px), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    def _load_font(size: int, bold: bool = False, mono: bool = False):
        candidates = (
            ["consola.ttf", "cour.ttf"]
            if mono
            else (["calibrib.ttf", "arialbd.ttf", "segoeuib.ttf"] if bold else ["calibri.ttf", "arial.ttf", "segoeui.ttf"])
        )
        for c in candidates:
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
        return ImageFont.load_default()

    font_hdr = _load_font(16, bold=False)
    font_title = _load_font(34, bold=True)
    font_h1 = _load_font(24, bold=True)
    font_h2 = _load_font(20, bold=True)
    font_body = _load_font(17, bold=False)
    font_mono = _load_font(15, bold=False, mono=True)

    margin_x = 120
    max_text_w = width_px - 2 * margin_x
    y = 65

    # Running Header
    hdr_text = ""
    if doc.sections and doc.sections[0].header.paragraphs:
        hdr_text = doc.sections[0].header.paragraphs[0].text.strip()
    if hdr_text:
        draw.text((width_px - margin_x - len(hdr_text) * 8, y), hdr_text, fill=(100, 116, 139), font=font_hdr)
    y += 45

    # Walk body elements on Page 1
    for p in doc.paragraphs:
        if y > height_px - 130:
            break
        style_name = p.style.name if p.style else "Normal"
        # Include OMML math text too
        full_p_txt = "".join(t.text or "" for t in p._p.iter() if t.tag in (qn("w:t"), qn("m:t"))).strip()
        if not full_p_txt:
            # Check if horizontal rule
            if p._p.find(f".//{qn('w:pBdr')}") is not None:
                draw.line([(margin_x, y + 6), (width_px - margin_x, y + 6)], fill=(203, 213, 225), width=2)
                y += 20
            continue

        if p == doc.paragraphs[0]:
            fnt = font_title
            color = (15, 23, 42)
            line_h = 42
        elif style_name.startswith("Heading 1"):
            y += 10
            fnt = font_h1
            color = (15, 23, 42)
            line_h = 32
        elif style_name.startswith("Heading"):
            y += 6
            fnt = font_h2
            color = (14, 116, 144)
            line_h = 26
        else:
            fnt = font_body
            color = (30, 41, 59)
            line_h = 23

        indent = 25 if "List" in style_name else 0
        prefix = "• " if "List Bullet" in style_name else ""
        words = (prefix + full_p_txt).split(" ")
        line_acc = ""
        for w in words:
            test_line = f"{line_acc} {w}".strip() if line_acc else w
            if len(test_line) * 9.2 > (max_text_w - indent) and line_acc:
                draw.text((margin_x + indent, y), line_acc, fill=color, font=fnt)
                y += line_h
                line_acc = w
                if y > height_px - 130:
                    break
            else:
                line_acc = test_line
        if line_acc and y <= height_px - 130:
            draw.text((margin_x + indent, y), line_acc, fill=color, font=fnt)
            y += line_h + 6

    # Footer
    draw.line([(margin_x, height_px - 95), (width_px - margin_x, height_px - 95)], fill=(226, 232, 240), width=1)
    draw.text((width_px - margin_x - 95, height_px - 80), "Page 1 of 1", fill=(100, 116, 139), font=font_hdr)

    img.save(str(png_path), format="PNG")
    return png_path
