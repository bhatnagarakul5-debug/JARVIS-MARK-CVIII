"""

actions/file_generator.py — Universal Multi-Format Document & Technical Documentation Authoring Engine

Empowers JARVIS to generate professional, executive-grade files & architectural documentation:

- Executive Word Documents (.docx) with standalone cover page, metadata table, executive abstract, styled headings, callout boxes, code blocks, zebra-striped tables, and embedded architecture diagrams.

- Interactive HTML Documentation Portals (.html) with responsive Stark/Cyber styling, dark/light theme switcher, real-time live search sidebar, Mermaid diagram rendering, and one-click copyable code snippets.

- Publication-Grade PDF Documents (.pdf) with ReportLab NumberedCanvas (Page X of Y), cover banners, wrapped tables, styled callouts, and embedded diagrams.

- PowerPoint Presentations (.pptx) with 16:9 widescreen layouts, cards, KPI callouts, and speaker notes.

- Excel Spreadsheets (.xlsx, .csv) with headers, automated formulas (SUM, AVERAGE), formatting, and auto-sized columns using OpenPyXL.

- Code & Text Files (.py, .md, .txt, .html, .tex, .json).

- Deep Codebase & Repository Documenter (project_doc): Deeply analyzes manifests, AST symbols, directory topology, and architectures to synthesize complete technical manuals.

"""



import os

import re

import sys

import json

import ast

import html

import tempfile

import subprocess

from pathlib import Path

from datetime import datetime

from typing import Dict, Any, List, Optional, Tuple, Set

from core.ai_client import generate_text_with_retry

from actions.file_controller import set_last_active_document, get_last_active_document



BASE_DIR = Path(__file__).resolve().parent.parent



def _get_output_dir(target_location: str = "desktop") -> Path:

    """Resolves target folder, default to Desktop."""

    loc = (target_location or "desktop").lower().strip()

    if loc in ("desktop", "desk"):

        cand = Path.home() / "OneDrive" / "Desktop"

        if cand.exists(): return cand

        return Path.home() / "Desktop"

    elif loc in ("downloads", "down"):

        cand = Path.home() / "OneDrive" / "Downloads"

        if cand.exists(): return cand

        return Path.home() / "Downloads"

    elif loc in ("documents", "docs"):

        cand = Path.home() / "OneDrive" / "Documents"

        if cand.exists(): return cand

        return Path.home() / "Documents"

    

    p = Path(target_location).expanduser()

    if p.exists() and p.is_dir():

        return p

    return Path.home() / "Desktop"





# ====================================================================

# 0. VISUAL ARCHITECTURE DIAGRAM RENDERER (Matplotlib)

# ====================================================================

def _render_architecture_diagram(

    tiers: Optional[List[Dict[str, Any]]] = None,

    title: str = "System Architecture & Runtime Flow",

    output_path: Optional[Path] = None

) -> Optional[Path]:

    """

    Renders a high-DPI executive system architecture diagram using matplotlib.

    Returns path to the generated image file.

    """

    try:

        import matplotlib

        matplotlib.use("Agg")

        import matplotlib.pyplot as plt

        import matplotlib.patches as patches



        fig, ax = plt.subplots(figsize=(10.5, 4.8), dpi=150)

        fig.patch.set_facecolor("#0F172A")

        ax.set_facecolor("#0F172A")



        # Default multi-tier architecture if none supplied

        diag_tiers = tiers or [

            {

                "name": "1. INGESTION & INTERFACES",

                "items": ["Gemini Live (Voice / Audio)", "HUD Glass Overlay (UI)", "Desktop File Watcher", "Dev Agent / CLI Bridge"],

                "color": "#0E7490", "border": "#22D3EE"

            },

            {

                "name": "2. DISPATCHER & SAFETY",

                "items": ["main.py Runtime Loop", "Safety Shield / Jailbreak", "Integrity Seal (SHA-256)", "Autonomous Self-Healing"],

                "color": "#4338CA", "border": "#818CF8"

            },

            {

                "name": "3. COGNITIVE ENGINES",

                "items": ["Universal File Generator", "Presentation Designer", "Self-Evolution Engine", "Deep Research / RAG"],

                "color": "#0369A1", "border": "#38BDF8"

            },

            {

                "name": "4. STORAGE & SYSTEM BRIDGES",

                "items": ["Filesystem (Word/PDF/HTML)", "SQLite / Knowledge Graph", "OS APIs / Remote Bridge", "OpenVoice VC / Audio Subsystem"],

                "color": "#065F46", "border": "#34D399"

            }

        ]



        n_tiers = len(diag_tiers)

        card_w = 2.25

        card_h = 3.2

        gap = 0.35

        start_x = 0.25

        y = 0.55



        # Title Block

        ax.text(5.25, 4.45, title.upper(), color="#F8FAFC", fontsize=13, fontweight="bold", ha="center")

        ax.text(5.25, 4.12, "J.A.R.V.I.S. Multi-Tier Distributed Architecture & Component Topology", color="#94A3B8", fontsize=9.5, fontstyle="italic", ha="center")



        for idx, tier in enumerate(diag_tiers):

            x = start_x + idx * (card_w + gap)

            rect = patches.FancyBboxPatch(

                (x, y), card_w, card_h,

                boxstyle="round,pad=0.08,rounding_size=0.15",

                facecolor=tier["color"], edgecolor=tier["border"],

                linewidth=1.8, alpha=0.92

            )

            ax.add_patch(rect)



            # Header inside tier

            ax.text(x + card_w / 2.0, y + card_h - 0.35, tier["name"], color="#FFFFFF", fontsize=8.5, fontweight="bold", ha="center")

            ax.plot([x + 0.15, x + card_w - 0.15], [y + card_h - 0.52, y + card_h - 0.52], color=tier["border"], linewidth=1.0)



            # Items inside tier

            item_y = y + card_h - 0.95

            for item in tier.get("items", [])[:4]:

                ax.text(x + 0.15, item_y, f"• {item}", color="#E2E8F0", fontsize=7.2, va="center")

                item_y -= 0.55



            # Flow arrow to next tier

            if idx < n_tiers - 1:

                arrow_x = x + card_w + 0.05

                arrow_y = y + card_h / 2.0

                ax.annotate(

                    "", xy=(arrow_x + gap - 0.1, arrow_y), xytext=(arrow_x, arrow_y),

                    arrowprops=dict(arrowstyle="-|>", color="#38BDF8", lw=2.0, mutation_scale=15)

                )



        ax.set_xlim(0, 10.5)

        ax.set_ylim(0, 4.8)

        ax.axis("off")



        if not output_path:

            tfile = tempfile.NamedTemporaryFile(suffix=".png", delete=False)

            output_path = Path(tfile.name)

            tfile.close()



        plt.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="#0F172A")

        plt.close(fig)

        return output_path

    except Exception as e:

        print("Failed to render architecture diagram:", e)

        return None





# ====================================================================

# 1. ENHANCED WORD DOCUMENT GENERATOR (.docx)

# ====================================================================

def _sections_to_markdown(sections: List[Dict[str, Any]]) -> str:
    """Converts legacy section dicts into clean Markdown for build_docx."""
    blocks: List[str] = []
    for sec in sections or []:
        h = (sec.get("heading") or "").strip()
        lvl = int(sec.get("level", 1) or 1)
        lvl = min(max(lvl, 1), 4)
        if h:
            blocks.append(f"{'#' * lvl} {h}")
        content = (sec.get("content") or "").strip()
        if content:
            blocks.append(content)
        callout = (sec.get("callout") or "").strip()
        if callout:
            blocks.append(f"> {callout}")
        code = (sec.get("code") or "").strip()
        code_lang = (sec.get("code_lang") or "").strip()
        if code:
            blocks.append(f"```{code_lang}\n{code}\n```")
        bullets = sec.get("bullets") or []
        if bullets:
            blocks.append("\n".join(f"- {b}" for b in bullets if str(b).strip()))
        table_data = sec.get("table") or []
        if table_data and isinstance(table_data, list) and len(table_data) > 0:
            t_lines: List[str] = []
            for r_i, row in enumerate(table_data):
                row_cells = [str(c).replace("\n", " ").strip() for c in row]
                t_lines.append("| " + " | ".join(row_cells) + " |")
                if r_i == 0:
                    t_lines.append("| " + " | ".join(["---"] * len(row_cells)) + " |")
            blocks.append("\n".join(t_lines))
    return "\n\n".join(blocks)


def create_word_document(
    filename: str,
    title: str,
    sections: Optional[List[Dict[str, Any]]] = None,
    output_dir: Optional[Path] = None,
    open_after: bool = True,
    subtitle: Optional[str] = None,
    author: str = "Akul Bhatnagar",
    cover_page: bool = False,
    classification: str = "",
    version: str = "1.0.0",
    abstract: Optional[str] = None,
    include_toc: Optional[bool] = None,
    diagram_image: Optional[Path] = None,
    markdown_text: Optional[str] = None,
    short_title: Optional[str] = None,
) -> str:
    """
    Builds a Word (.docx) document using the pure-function AST builder (`actions.docx_builder.build_docx`).
    """
    try:
        from actions.docx_builder import build_docx, acronym_safe_title_case

        if not filename.endswith(".docx"):
            filename += ".docx"

        out_dir = output_dir or _get_output_dir()
        file_path = out_dir / filename

        md_body = markdown_text if (markdown_text and markdown_text.strip()) else _sections_to_markdown(sections or [])
        if abstract and abstract.strip() and abstract.strip() not in md_body:
            md_body = f"> **Abstract:** {abstract.strip()}\n\n" + md_body

        meta = {
            "output_path": file_path,
            "filename": filename,
            "title": title,
            "short_title": short_title,
            "subtitle": subtitle or "",
            "author": author,
            "include_toc": include_toc,
            "diagram_image": diagram_image,
            "include_persona_boilerplate": False,
            "classification": classification,
        }

        built_path = build_docx(md_body, meta)
        set_last_active_document(built_path, title=acronym_safe_title_case(title))

        if open_after:
            try:
                os.startfile(str(built_path))
            except Exception:
                pass

        return f"Successfully generated Executive Word Document: '{built_path.name}' at {built_path.parent}"

    except Exception as e:
        return f"Failed to generate Word document: {e}"


# ====================================================================
# 2. ENHANCED POWERPOINT PRESENTATION (.pptx)
# ====================================================================
def create_presentation(

    filename: str,

    title: str,

    subtitle: str,

    slides_data: List[Dict[str, Any]],

    output_dir: Optional[Path] = None,

    open_after: bool = True

) -> str:

    """

    Creates an executive 16:9 widescreen PowerPoint presentation (.pptx).

    slides_data: list of dicts:

      {

        "title": "Slide Title",

        "type": "bullets" | "comparison" | "kpi",

        "bullets": ["Point 1", "Point 2"],

        "col1_title": "...", "col1_bullets": [...],

        "col2_title": "...", "col2_bullets": [...],

        "kpi_val": "98.5%", "kpi_label": "Accuracy Metric",

        "notes": "Speaker notes"

      }

    """

    try:

        from pptx import Presentation

        from pptx.util import Inches, Pt

        from pptx.dml.color import RGBColor

        from pptx.enum.text import PP_ALIGN



        if not filename.endswith(".pptx"):

            filename += ".pptx"



        out_dir = output_dir or _get_output_dir()

        file_path = out_dir / filename



        prs = Presentation()

        # Set 16:9 widescreen layout

        prs.slide_width = Inches(13.333)

        prs.slide_height = Inches(7.5)



        # Slide 1: Executive Title Slide

        title_slide_layout = prs.slide_layouts[0]

        slide = prs.slides.add_slide(title_slide_layout)

        t_box = slide.shapes.title

        s_box = slide.placeholders[1]



        t_box.text = title

        s_box.text = f"{subtitle}\nAuthored with J.A.R.V.I.S. Mark 78 • {datetime.now().strftime('%B %d, %Y')}"



        # Style Title

        for p in t_box.text_frame.paragraphs:

            p.font.name = "Calibri"

            p.font.size = Pt(40)

            p.font.bold = True

            p.font.color.rgb = RGBColor(14, 116, 144)



        # Content Slides

        bullet_slide_layout = prs.slide_layouts[1]

        for s_info in slides_data:

            s_title = s_info.get("title", "Key Concept")

            s_type = s_info.get("type", "bullets").lower()

            bullets = s_info.get("bullets", [])

            notes_text = s_info.get("notes", "")



            c_slide = prs.slides.add_slide(bullet_slide_layout)

            c_slide.shapes.title.text = s_title

            c_slide.shapes.title.text_frame.paragraphs[0].font.name = "Calibri"

            c_slide.shapes.title.text_frame.paragraphs[0].font.size = Pt(28)

            c_slide.shapes.title.text_frame.paragraphs[0].font.bold = True

            c_slide.shapes.title.text_frame.paragraphs[0].font.color.rgb = RGBColor(15, 23, 42)



            body_shape = c_slide.placeholders[1]

            tf = body_shape.text_frame

            tf.word_wrap = True



            if s_type == "kpi":

                kpi_val = s_info.get("kpi_val", "100%")

                kpi_lbl = s_info.get("kpi_label", "Key Benchmark")

                p1 = tf.paragraphs[0]

                p1.text = kpi_val

                p1.font.size = Pt(56)

                p1.font.bold = True

                p1.font.color.rgb = RGBColor(14, 116, 144)

                p1.alignment = PP_ALIGN.CENTER



                p2 = tf.add_paragraph()

                p2.text = kpi_lbl

                p2.font.size = Pt(20)

                p2.font.italic = True

                p2.alignment = PP_ALIGN.CENTER



                if bullets:

                    tf.add_paragraph().text = ""

                    for b in bullets:

                        bp = tf.add_paragraph()

                        bp.text = f"• {b}"

                        bp.font.size = Pt(16)

            elif s_type == "comparison":

                c1_title = s_info.get("col1_title", "Perspective A")

                c1_pts = s_info.get("col1_bullets", [])

                c2_title = s_info.get("col2_title", "Perspective B")

                c2_pts = s_info.get("col2_bullets", [])



                p_c1 = tf.paragraphs[0]

                p_c1.text = f"▶ {c1_title.upper()}:"

                p_c1.font.bold = True

                p_c1.font.size = Pt(18)

                p_c1.font.color.rgb = RGBColor(14, 116, 144)

                for pt in c1_pts:

                    bp = tf.add_paragraph()

                    bp.text = f"  • {pt}"

                    bp.font.size = Pt(15)



                tf.add_paragraph().text = ""

                p_c2 = tf.add_paragraph()

                p_c2.text = f"▶ {c2_title.upper()}:"

                p_c2.font.bold = True

                p_c2.font.size = Pt(18)

                p_c2.font.color.rgb = RGBColor(79, 70, 229)

                for pt in c2_pts:

                    bp = tf.add_paragraph()

                    bp.text = f"  • {pt}"

                    bp.font.size = Pt(15)

            else:

                for idx, b_text in enumerate(bullets):

                    p = tf.add_paragraph() if idx > 0 else tf.paragraphs[0]

                    p.text = b_text

                    p.level = 0

                    p.font.name = "Calibri"

                    p.font.size = Pt(19)

                    p.font.color.rgb = RGBColor(51, 65, 85)



            if notes_text:

                c_slide.notes_slide.notes_text_frame.text = notes_text



        prs.save(str(file_path))



        set_last_active_document(file_path, title=title)



        if open_after:

            try:

                os.startfile(str(file_path))

            except Exception:

                pass



        return f"Successfully generated 16:9 Presentation: '{file_path.name}' ({len(slides_data) + 1} slides) at {file_path.parent}"



    except Exception as e:

        return f"Failed to generate PowerPoint presentation: {e}"





# ====================================================================

# 3. ENHANCED PDF GENERATOR (ReportLab with NumberedCanvas & Diagram)

# ====================================================================

def create_pdf_document(

    filename: str,

    title: str,

    sections: List[Dict[str, Any]],

    output_dir: Optional[Path] = None,

    open_after: bool = True,

    subtitle: Optional[str] = None,

    author: str = "Akul Bhatnagar",

    cover_page: bool = True,

    classification: str = "CONFIDENTIAL // TECHNICAL SPECIFICATION",

    version: str = "1.0.0",

    diagram_image: Optional[Path] = None

) -> str:

    """

    Creates a high-fidelity PDF document with ReportLab, page numbering,

    cover banner, wrapped tables, and embedded diagrams.

    """

    try:

        from reportlab.lib.pagesizes import letter

        from reportlab.lib import colors

        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage

        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        from reportlab.pdfgen import canvas



        if not filename.endswith(".pdf"):

            filename += ".pdf"



        out_dir = output_dir or _get_output_dir()

        file_path = out_dir / filename



        class NumberedCanvas(canvas.Canvas):

            def __init__(self, *args, **kwargs):

                super().__init__(*args, **kwargs)

                self._saved_page_states = []



            def showPage(self):

                self._saved_page_states.append(dict(self.__dict__))

                self._startPage()



            def save(self):

                num_pages = len(self._saved_page_states)

                for state in self._saved_page_states:

                    self.__dict__.update(state)

                    self.draw_header_footer(num_pages)

                    super().showPage()

                super().save()



            def draw_header_footer(self, page_count):

                self.saveState()

                self.setFont("Helvetica", 8)

                self.setFillColor(colors.HexColor("#64748b"))

                # Running Header

                self.drawString(54, 11 * 72 - 36, title[:48])

                self.drawRightString(8.5 * 72 - 54, 11 * 72 - 36, "J.A.R.V.I.S. Technical Intelligence")

                self.setStrokeColor(colors.HexColor("#cbd5e1"))

                self.setLineWidth(0.5)

                self.line(54, 11 * 72 - 40, 8.5 * 72 - 54, 11 * 72 - 40)

                # Footer

                self.drawString(54, 36, f"{classification} • {author}")

                self.drawRightString(8.5 * 72 - 54, 36, f"Page {self._pageNumber} of {page_count}")

                self.restoreState()



        doc = SimpleDocTemplate(

            str(file_path),

            pagesize=letter,

            rightMargin=54, leftMargin=54,

            topMargin=54, bottomMargin=54

        )



        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(

            'DocTitle',

            parent=styles['Heading1'],

            fontName='Helvetica-Bold',

            fontSize=22,

            leading=26,

            textColor=colors.HexColor('#0e7490'),

            spaceAfter=8

        )

        sub_style = ParagraphStyle(

            'DocSub',

            parent=styles['Normal'],

            fontName='Helvetica-Oblique',

            fontSize=10,

            leading=14,

            textColor=colors.HexColor('#64748b'),

            spaceAfter=14

        )

        heading_style = ParagraphStyle(

            'SecHeading',

            parent=styles['Heading2'],

            fontName='Helvetica-Bold',

            fontSize=13,

            leading=17,

            textColor=colors.HexColor('#0f172a'),

            spaceBefore=14,

            spaceAfter=6

        )

        body_style = ParagraphStyle(

            'BodyTextCustom',

            parent=styles['Normal'],

            fontName='Helvetica',

            fontSize=10,

            leading=14.5,

            textColor=colors.HexColor('#334155'),

            spaceAfter=6

        )

        bullet_style = ParagraphStyle(

            'BulletCustom',

            parent=styles['Normal'],

            fontName='Helvetica',

            fontSize=9.5,

            leading=13.5,

            leftIndent=14,

            firstLineIndent=-10,

            textColor=colors.HexColor('#1e293b'),

            spaceAfter=3

        )

        callout_style = ParagraphStyle(

            'CalloutCustom',

            parent=styles['Normal'],

            fontName='Helvetica-Bold',

            fontSize=9.5,

            leading=13.5,

            textColor=colors.HexColor('#0e7490')

        )

        code_style = ParagraphStyle(

            'CodeCustom',

            parent=styles['Normal'],

            fontName='Courier',

            fontSize=8.5,

            leading=11.5,

            textColor=colors.HexColor('#e2e8f0')

        )



        def _rl_fmt(val: str) -> str:

            if not val:

                return ""

            s = str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)

            s = s.replace("\n", "<br/>")

            return s



        story = []



        # 1. Title Block & Cover Banner

        story.append(Paragraph(_rl_fmt(title), title_style))

        sub_label = subtitle or f"Technical Architecture & Executive Specification (v{version}) • Author: {author}"

        story.append(Paragraph(f"{_rl_fmt(sub_label)} &bull; {datetime.now().strftime('%B %d, %Y')}", sub_style))

        story.append(Spacer(1, 8))



        # 2. Embedded Diagram

        if diagram_image and Path(diagram_image).exists():

            try:

                story.append(RLImage(str(diagram_image), width=500, height=225))

                story.append(Spacer(1, 4))

                story.append(Paragraph("<i>Figure 1: High-Level System Architecture & Component Interaction Topology</i>", sub_style))

                story.append(Spacer(1, 10))

            except Exception:

                pass



        # 3. Sections

        for sec in sections:

            h = sec.get("heading")

            if h:

                story.append(Paragraph(_rl_fmt(h), heading_style))



            content = sec.get("content")

            if content:

                for line in str(content).strip().split("\n\n"):

                    if line.strip():

                        story.append(Paragraph(_rl_fmt(line.strip()), body_style))



            callout = sec.get("callout")

            if callout:

                c_tbl = Table([[Paragraph(f"<b>TAKEAWAY / DIRECTIVE:</b> {_rl_fmt(callout)}", callout_style)]], colWidths=[500])

                c_tbl.setStyle(TableStyle([

                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f1f5f9')),

                    ('LINELEFT', (0,0), (0,0), 3, colors.HexColor('#0e7490')),

                    ('TOPPADDING', (0,0), (-1,-1), 6),

                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),

                    ('LEFTPADDING', (0,0), (-1,-1), 8),

                ]))

                story.append(Spacer(1, 4))

                story.append(c_tbl)

                story.append(Spacer(1, 6))



            bullets = sec.get("bullets", [])

            for b in bullets:

                story.append(Paragraph(f"&bull; {_rl_fmt(b)}", bullet_style))



            code_blk = sec.get("code")

            if code_blk:

                code_table = Table([[Paragraph(_rl_fmt(code_blk), code_style)]], colWidths=[500])

                code_table.setStyle(TableStyle([

                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1e293b')),

                    ('TOPPADDING', (0,0), (-1,-1), 6),

                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),

                    ('LEFTPADDING', (0,0), (-1,-1), 8),

                    ('RIGHTPADDING', (0,0), (-1,-1), 8),

                ]))

                story.append(Spacer(1, 4))

                story.append(code_table)

                story.append(Spacer(1, 6))



            tbl_data = sec.get("table")

            if tbl_data and isinstance(tbl_data, list) and len(tbl_data) > 0:

                wrapped_table = []

                for row_idx, r in enumerate(tbl_data):

                    wrapped_row = []

                    for val in r:

                        style_to_use = heading_style if row_idx == 0 else body_style

                        wrapped_row.append(Paragraph(_rl_fmt(str(val)), style_to_use))

                    wrapped_table.append(wrapped_row)



                num_cols = len(tbl_data[0])

                col_w = 500.0 / max(num_cols, 1)

                t = Table(wrapped_table, colWidths=[col_w] * num_cols)

                t.setStyle(TableStyle([

                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),

                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),

                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),

                    ('FONTSIZE', (0,0), (-1,-1), 9),

                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),

                    ('TOPPADDING', (0,0), (-1,-1), 6),

                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),

                ]))

                story.append(Spacer(1, 6))

                story.append(t)

                story.append(Spacer(1, 8))



        doc.build(story, canvasmaker=NumberedCanvas)



        set_last_active_document(file_path, title=title)



        if open_after:

            try:

                os.startfile(str(file_path))

            except Exception:

                pass



        return f"Successfully generated Executive PDF Document: '{file_path.name}' at {file_path.parent}"



    except Exception as e:

        return f"Failed to generate PDF document: {e}"





# ====================================================================

# 4. ENHANCED EXCEL SPREADSHEET GENERATOR (.xlsx)

# ====================================================================

def create_excel_sheet(

    filename: str,

    title: str,

    columns: List[str],

    rows: List[List[Any]],

    output_dir: Optional[Path] = None,

    open_after: bool = True,

    add_summary_row: bool = True

) -> str:

    """

    Creates an Excel spreadsheet (.xlsx) with styles and automated summary formulas.

    """

    try:

        from openpyxl import Workbook

        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        from openpyxl.utils import get_column_letter



        if not filename.endswith(".xlsx"):

            filename += ".xlsx"



        out_dir = output_dir or _get_output_dir()

        file_path = out_dir / filename



        wb = Workbook()

        ws = wb.active

        ws.title = title[:30] if title else "Sheet1"



        # Headers

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

        header_fill = PatternFill(start_color="0E7490", end_color="0E7490", fill_type="solid")

        border_thin = Border(

            left=Side(style='thin', color='CBD5E1'),

            right=Side(style='thin', color='CBD5E1'),

            top=Side(style='thin', color='CBD5E1'),

            bottom=Side(style='thin', color='CBD5E1')

        )



        ws.append(columns)

        for col_idx in range(1, len(columns) + 1):

            cell = ws.cell(row=1, column=col_idx)

            cell.font = header_font

            cell.fill = header_fill

            cell.alignment = Alignment(horizontal="center", vertical="center")



        # Rows

        for r_data in rows:

            ws.append(r_data)



        # Style data cells and format

        for row in ws.iter_rows(min_row=2, max_row=len(rows)+1, min_col=1, max_col=len(columns)):

            for cell in row:

                cell.font = Font(name="Calibri", size=10)

                cell.border = border_thin

                if isinstance(cell.value, (int, float)):

                    cell.alignment = Alignment(horizontal="right")



        # Optional automated summary row for numeric columns

        if add_summary_row and rows:

            summary_row = []

            num_rows = len(rows)

            for c_idx in range(1, len(columns) + 1):

                col_letter = get_column_letter(c_idx)

                sample = rows[0][c_idx - 1] if len(rows[0]) >= c_idx else None

                if c_idx == 1:

                    summary_row.append("Total / Summary")

                elif isinstance(sample, (int, float)):

                    summary_row.append(f"=SUM({col_letter}2:{col_letter}{num_rows+1})")

                else:

                    summary_row.append("")

            ws.append(summary_row)

            sum_row_idx = num_rows + 2

            for c_idx in range(1, len(columns) + 1):

                cell = ws.cell(row=sum_row_idx, column=c_idx)

                cell.font = Font(name="Calibri", size=11, bold=True, color="0F172A")

                cell.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

                cell.border = Border(top=Side(style='thin', color='0F172A'), bottom=Side(style='double', color='0F172A'))



        # Auto-adjust column widths

        for col in ws.columns:

            max_len = max(len(str(cell.value or '')) for cell in col)

            col_letter = get_column_letter(col[0].column)

            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)



        wb.save(str(file_path))



        set_last_active_document(file_path, title=title)



        if open_after:

            try:

                os.startfile(str(file_path))

            except Exception:

                pass



        return f"Successfully generated Excel Spreadsheet: '{file_path.name}' at {file_path.parent}"



    except Exception as e:

        return f"Failed to generate Excel sheet: {e}"





# ====================================================================

# 5. INTERACTIVE HTML DOCUMENTATION PORTAL (.html)

# ====================================================================

def create_html_documentation(

    filename: str,

    title: str,

    subtitle: Optional[str] = None,

    sections: Optional[List[Dict[str, Any]]] = None,

    metadata: Optional[Dict[str, Any]] = None,

    mermaid_diagrams: Optional[List[str]] = None,

    output_dir: Optional[Path] = None,

    open_after: bool = True

) -> str:

    """

    Creates a responsive, interactive, single-page documentation app (.html):

    - Dark & Light mode toggle with CSS variables

    - Sticky sidebar with real-time fuzzy search input filtering headings & content

    - Embedded Mermaid.js library for interactive diagram rendering

    - One-click copy buttons for all code blocks

    - Clean API reference parameter tables, callout banners, and badges

    - Print-to-PDF stylesheet

    """

    try:

        if not filename.endswith(".html"):

            filename += ".html"



        out_dir = output_dir or _get_output_dir()

        file_path = out_dir / filename



        meta = metadata or {}

        author = meta.get("author", "Akul Bhatnagar")

        version = meta.get("version", "1.0.0")

        classification = meta.get("classification", "PRODUCTION // TECHNICAL SPECIFICATION")

        sub_text = subtitle or "Autonomous Software Architecture Manual & Technical Specification"



        secs = sections or [{"heading": "Overview", "content": "Documentation authored by J.A.R.V.I.S."}]

        m_diagrams = mermaid_diagrams or []



        # Build Sidebar Nav Items

        nav_items_html = []

        for idx, s in enumerate(secs):

            h = html.escape(s.get("heading", f"Section {idx+1}"))

            nav_items_html.append(

                f'<a href="#sec-{idx}" class="nav-link" data-title="{h.lower()}">'

                f'<span class="nav-num">{idx+1:02d}</span> {h}'

                f'</a>'

            )

        nav_html_str = "\n".join(nav_items_html)



        # Build Main Content Sections

        content_sections_html = []

        for idx, s in enumerate(secs):

            h_raw = s.get("heading", f"Section {idx+1}")

            h_esc = html.escape(h_raw)

            lvl = s.get("level", 1)



            sec_parts = [

                f'<section id="sec-{idx}" class="doc-section">',

                f'  <div class="section-header">',

                f'    <h{min(lvl+1, 3)} class="section-title">',

                f'      <span class="sec-anchor">#</span> {h_esc}',

                f'    </h{min(lvl+1, 3)}>',

                f'  </div>'

            ]



            # Section text content

            content_txt = s.get("content", "")

            if content_txt:

                for p_raw in str(content_txt).strip().split("\n\n"):

                    if not p_raw.strip():

                        continue

                    p_esc = html.escape(p_raw.strip())

                    p_esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p_esc)

                    p_esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", p_esc)

                    p_esc = p_esc.replace("\n", "<br/>")

                    sec_parts.append(f'  <p class="doc-paragraph">{p_esc}</p>')



            # Mermaid Diagram in section

            m_code = s.get("mermaid")

            if m_code:

                sec_parts.append(

                    f'  <div class="mermaid-container">'

                    f'    <div class="mermaid-label">▶ ARCHITECTURE FLOW DIAGRAM</div>'

                    f'    <div class="mermaid">{html.escape(m_code)}</div>'

                    f'  </div>'

                )



            # Callout Card

            callout = s.get("callout")

            callout_type = s.get("callout_type", "takeaway").lower()

            if callout:

                c_esc = html.escape(callout)

                c_esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", c_esc)

                icon = "⚡"

                callout_cls = "callout-info"

                if "warn" in callout_type:

                    icon, callout_cls = "⚠️", "callout-warn"

                elif "tip" in callout_type or "best" in callout_type:

                    icon, callout_cls = "💡", "callout-tip"

                elif "sec" in callout_type:

                    icon, callout_cls = "🔒", "callout-sec"



                sec_parts.append(

                    f'  <div class="callout-card {callout_cls}">'

                    f'    <span class="callout-icon">{icon}</span>'

                    f'    <div class="callout-body">{c_esc}</div>'

                    f'  </div>'

                )



            # Code Block

            code_str = s.get("code")

            code_lang = s.get("code_lang", "python")

            if code_str:

                sec_parts.append(

                    f'  <div class="code-card">'

                    f'    <div class="code-header">'

                    f'      <span class="code-lang">{html.escape(code_lang.upper())}</span>'

                    f'      <button class="copy-btn" onclick="copyCode(this)">Copy</button>'

                    f'    </div>'

                    f'    <pre><code class="language-{html.escape(code_lang)}">{html.escape(code_str)}</code></pre>'

                    f'  </div>'

                )



            # Bullet List

            bullets = s.get("bullets", [])

            if bullets:

                sec_parts.append('  <ul class="doc-bullets">')

                for b in bullets:

                    b_esc = html.escape(b)

                    b_esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", b_esc)

                    b_esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", b_esc)

                    sec_parts.append(f'    <li>{b_esc}</li>')

                sec_parts.append('  </ul>')



            # Table

            tbl = s.get("table")

            if tbl and isinstance(tbl, list) and len(tbl) > 0:

                sec_parts.append('  <div class="table-wrapper"><table class="doc-table">')

                for r_idx, r in enumerate(tbl):

                    if r_idx == 0:

                        sec_parts.append('    <thead><tr>' + "".join(f'<th>{html.escape(str(c))}</th>' for c in r) + '</tr></thead><tbody>')

                    else:

                        sec_parts.append('    <tr>' + "".join(f'<td>{html.escape(str(c))}</td>' for c in r) + '</tr>')

                sec_parts.append('  </tbody></table></div>')



            sec_parts.append('</section>')

            content_sections_html.append("\n".join(sec_parts))



        main_sections_str = "\n\n".join(content_sections_html)



        # Mermaid diagrams block in header if separate

        extra_mermaid_html = ""

        for m in m_diagrams:

            extra_mermaid_html += (

                f'<div class="mermaid-container">'

                f'  <div class="mermaid-label">▶ SYSTEM ARCHITECTURE & RUNTIME INTERACTION FLOW</div>'

                f'  <div class="mermaid">{html.escape(m)}</div>'

                f'</div>'

            )



        html_template = f'''<!DOCTYPE html>

<html lang="en" data-theme="dark">

<head>

  <meta charset="UTF-8">

  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <title>{html.escape(title)} &bull; J.A.R.V.I.S. Technical Documentation</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">

  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>

  <script>

    mermaid.initialize({{ startOnLoad: true, theme: 'dark', securityLevel: 'loose' }});

  </script>

  <style>

    :root {{

      --bg-base: #0B0F19;

      --bg-surface: #111827;

      --bg-card: #1E293B;

      --border: #334155;

      --accent: #00F0FF;

      --accent-hover: #38BDF8;

      --accent-dim: rgba(0, 240, 255, 0.12);

      --text-main: #F1F5F9;

      --text-muted: #94A3B8;

      --sidebar-w: 290px;

      --code-bg: #030712;

      --transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);

    }}

    [data-theme="light"] {{

      --bg-base: #F8FAFC;

      --bg-surface: #FFFFFF;

      --bg-card: #F1F5F9;

      --border: #CBD5E1;

      --accent: #0284C7;

      --accent-hover: #0369A1;

      --accent-dim: rgba(2, 132, 199, 0.1);

      --text-main: #0F172A;

      --text-muted: #64748B;

      --code-bg: #1E293B;

    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{

      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

      background: var(--bg-base);

      color: var(--text-main);

      display: flex;

      min-height: 100vh;

      line-height: 1.6;

    }}

    .sidebar {{

      width: var(--sidebar-w);

      background: var(--bg-surface);

      border-right: 1px solid var(--border);

      position: fixed;

      top: 0; bottom: 0; left: 0;

      display: flex;

      flex-direction: column;

      z-index: 100;

    }}

    .sidebar-header {{

      padding: 24px 20px 16px;

      border-bottom: 1px solid var(--border);

    }}

    .brand-badge {{

      display: inline-block;

      font-size: 10px;

      font-weight: 800;

      letter-spacing: 1.5px;

      color: var(--accent);

      background: var(--accent-dim);

      padding: 3px 8px;

      border-radius: 4px;

      margin-bottom: 8px;

      border: 1px solid rgba(0, 240, 255, 0.25);

    }}

    .doc-sidebar-title {{

      font-size: 15px;

      font-weight: 700;

      color: var(--text-main);

      white-space: nowrap;

      overflow: hidden;

      text-overflow: ellipsis;

    }}

    .search-box-wrapper {{

      padding: 14px 18px 10px;

    }}

    .search-input {{

      width: 100%;

      background: var(--bg-card);

      border: 1px solid var(--border);

      border-radius: 6px;

      color: var(--text-main);

      padding: 8px 12px;

      font-size: 12.5px;

      outline: none;

      transition: var(--transition);

    }}

    .search-input:focus {{

      border-color: var(--accent);

      box-shadow: 0 0 0 2px var(--accent-dim);

    }}

    .sidebar-nav {{

      flex: 1;

      overflow-y: auto;

      padding: 10px 14px 20px;

    }}

    .nav-link {{

      display: flex;

      align-items: center;

      padding: 8px 10px;

      color: var(--text-muted);

      text-decoration: none;

      font-size: 13px;

      font-weight: 500;

      border-radius: 6px;

      margin-bottom: 3px;

      transition: var(--transition);

    }}

    .nav-link:hover {{

      color: var(--accent);

      background: var(--accent-dim);

    }}

    .nav-num {{

      font-family: 'JetBrains Mono', monospace;

      font-size: 10.5px;

      color: var(--accent);

      opacity: 0.8;

      margin-right: 8px;

    }}

    .sidebar-footer {{

      padding: 14px 18px;

      border-top: 1px solid var(--border);

      font-size: 11px;

      color: var(--text-muted);

      display: flex;

      justify-content: space-between;

      align-items: center;

    }}

    .main-wrapper {{

      margin-left: var(--sidebar-w);

      flex: 1;

      display: flex;

      flex-direction: column;

      min-width: 0;

    }}

    .top-bar {{

      height: 58px;

      background: var(--bg-surface);

      border-bottom: 1px solid var(--border);

      display: flex;

      align-items: center;

      justify-content: space-between;

      padding: 0 36px;

      position: sticky;

      top: 0;

      z-index: 90;

      backdrop-filter: blur(8px);

    }}

    .breadcrumbs {{

      font-size: 13px;

      color: var(--text-muted);

    }}

    .breadcrumbs span {{

      color: var(--accent);

      font-weight: 600;

    }}

    .top-actions {{

      display: flex;

      align-items: center;

      gap: 12px;

    }}

    .btn-action {{

      background: var(--bg-card);

      border: 1px solid var(--border);

      color: var(--text-main);

      padding: 6px 14px;

      border-radius: 6px;

      font-size: 12px;

      font-weight: 600;

      cursor: pointer;

      transition: var(--transition);

    }}

    .btn-action:hover {{

      border-color: var(--accent);

      color: var(--accent);

    }}

    .content-container {{

      max-width: 960px;

      width: 100%;

      margin: 0 auto;

      padding: 36px 36px 80px;

    }}

    .hero-banner {{

      background: var(--bg-surface);

      border: 1px solid var(--border);

      border-radius: 12px;

      padding: 32px;

      margin-bottom: 36px;

      position: relative;

      overflow: hidden;

    }}

    .hero-banner::before {{

      content: '';

      position: absolute;

      top: 0; left: 0; right: 0;

      height: 3px;

      background: linear-gradient(90deg, var(--accent), #38BDF8, #818CF8);

    }}

    .hero-pill {{

      display: inline-block;

      font-size: 10.5px;

      font-weight: 800;

      color: var(--accent);

      background: var(--accent-dim);

      padding: 4px 10px;

      border-radius: 4px;

      margin-bottom: 12px;

      letter-spacing: 1px;

    }}

    .hero-title {{

      font-size: 28px;

      font-weight: 800;

      letter-spacing: -0.5px;

      margin-bottom: 8px;

      color: var(--text-main);

    }}

    .hero-sub {{

      font-size: 14.5px;

      color: var(--text-muted);

      margin-bottom: 20px;

    }}

    .meta-grid {{

      display: grid;

      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));

      gap: 14px;

      padding-top: 18px;

      border-top: 1px solid var(--border);

    }}

    .meta-item {{

      font-size: 12px;

    }}

    .meta-label {{

      color: var(--text-muted);

      font-size: 11px;

      font-weight: 600;

      text-transform: uppercase;

      margin-bottom: 2px;

    }}

    .meta-val {{

      color: var(--text-main);

      font-weight: 600;

    }}

    .doc-section {{

      margin-bottom: 40px;

      padding-top: 24px;

      border-top: 1px solid rgba(255, 255, 255, 0.05);

    }}

    .section-title {{

      font-size: 20px;

      font-weight: 700;

      color: var(--text-main);

      margin-bottom: 14px;

      display: flex;

      align-items: center;

      gap: 8px;

    }}

    .sec-anchor {{

      color: var(--accent);

      opacity: 0.6;

      font-size: 17px;

    }}

    .doc-paragraph {{

      color: var(--text-muted);

      font-size: 14.5px;

      margin-bottom: 14px;

      line-height: 1.7;

    }}

    .doc-paragraph strong {{

      color: var(--text-main);

    }}

    .mermaid-container {{

      background: var(--bg-surface);

      border: 1px solid var(--border);

      border-radius: 8px;

      padding: 24px 16px;

      margin: 18px 0;

      text-align: center;

      overflow-x: auto;

    }}

    .mermaid-label {{

      font-size: 11px;

      font-weight: 800;

      letter-spacing: 1.2px;

      color: var(--accent);

      margin-bottom: 16px;

      text-align: left;

    }}

    .callout-card {{

      display: flex;

      gap: 14px;

      padding: 16px 18px;

      border-radius: 8px;

      margin: 18px 0;

      font-size: 13.5px;

    }}

    .callout-info {{

      background: rgba(14, 116, 144, 0.12);

      border-left: 4px solid #0E7490;

      color: var(--text-main);

    }}

    .callout-warn {{

      background: rgba(217, 119, 6, 0.12);

      border-left: 4px solid #D97706;

      color: var(--text-main);

    }}

    .callout-tip {{

      background: rgba(5, 150, 105, 0.12);

      border-left: 4px solid #059669;

      color: var(--text-main);

    }}

    .callout-sec {{

      background: rgba(79, 70, 229, 0.12);

      border-left: 4px solid #4F46E5;

      color: var(--text-main);

    }}

    .callout-icon {{

      font-size: 18px;

      line-height: 1;

    }}

    .callout-body {{

      flex: 1;

    }}

    .code-card {{

      background: var(--code-bg);

      border: 1px solid var(--border);

      border-radius: 8px;

      margin: 18px 0;

      overflow: hidden;

    }}

    .code-header {{

      background: rgba(255, 255, 255, 0.03);

      padding: 8px 14px;

      display: flex;

      justify-content: space-between;

      align-items: center;

      border-bottom: 1px solid rgba(255, 255, 255, 0.05);

    }}

    .code-lang {{

      font-family: 'JetBrains Mono', monospace;

      font-size: 11px;

      font-weight: 600;

      color: var(--accent);

    }}

    .copy-btn {{

      background: transparent;

      border: 1px solid var(--border);

      color: var(--text-muted);

      padding: 3px 10px;

      border-radius: 4px;

      font-size: 11px;

      cursor: pointer;

      transition: var(--transition);

    }}

    .copy-btn:hover {{

      color: var(--accent);

      border-color: var(--accent);

    }}

    .copy-btn.copied {{

      color: #34D399;

      border-color: #34D399;

    }}

    pre {{

      padding: 16px;

      overflow-x: auto;

      font-family: 'JetBrains Mono', monospace;

      font-size: 12.5px;

      line-height: 1.5;

      color: #E2E8F0;

    }}

    code {{

      font-family: 'JetBrains Mono', monospace;

      font-size: 12.5px;

      background: var(--bg-card);

      padding: 2px 6px;

      border-radius: 4px;

      color: var(--accent);

    }}

    .doc-bullets {{

      margin: 12px 0 16px 20px;

      color: var(--text-muted);

      font-size: 14px;

    }}

    .doc-bullets li {{

      margin-bottom: 6px;

    }}

    .table-wrapper {{

      overflow-x: auto;

      margin: 18px 0;

      border: 1px solid var(--border);

      border-radius: 8px;

    }}

    .doc-table {{

      width: 100%;

      border-collapse: collapse;

      font-size: 13px;

      text-align: left;

    }}

    .doc-table th {{

      background: var(--bg-surface);

      color: var(--text-main);

      padding: 10px 14px;

      font-weight: 700;

      border-bottom: 1px solid var(--border);

    }}

    .doc-table td {{

      padding: 10px 14px;

      border-bottom: 1px solid rgba(255, 255, 255, 0.05);

      color: var(--text-muted);

    }}

    .doc-table tr:last-child td {{ border-bottom: none; }}

    .doc-table tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}



    @media print {{

      .sidebar, .top-bar, .copy-btn {{ display: none !important; }}

      .main-wrapper {{ margin-left: 0 !important; }}

      body {{ background: #fff !important; color: #000 !important; }}

      .hero-banner, .doc-section, .code-card, .table-wrapper {{

        border-color: #ccc !important;

        background: #fff !important;

        color: #000 !important;

      }}

      pre, code {{ color: #000 !important; background: #eee !important; }}

    }}

  </style>

</head>

<body>



  <aside class="sidebar">

    <div class="sidebar-header">

      <span class="brand-badge">J.A.R.V.I.S. TECHNICAL DOCS</span>

      <h2 class="doc-sidebar-title">{html.escape(title)}</h2>

    </div>

    <div class="search-box-wrapper">

      <input type="text" id="docSearch" class="search-input" placeholder="Search documentation... (/)" autocomplete="off">

    </div>

    <nav class="sidebar-nav" id="sidebarNav">

      {nav_html_str}

    </nav>

    <div class="sidebar-footer">

      <span>v{html.escape(version)}</span>

      <span>{datetime.now().strftime('%b %Y')}</span>

    </div>

  </aside>



  <main class="main-wrapper">

    <header class="top-bar">

      <div class="breadcrumbs">Documentation / <span>{html.escape(title[:30])}</span></div>

      <div class="top-actions">

        <button class="btn-action" onclick="toggleTheme()">Theme</button>

        <button class="btn-action" onclick="window.print()">Print / PDF</button>

      </div>

    </header>



    <div class="content-container">

      <div class="hero-banner">

        <span class="hero-pill">{html.escape(classification)}</span>

        <h1 class="hero-title">{html.escape(title)}</h1>

        <p class="hero-sub">{html.escape(sub_text)}</p>

        <div class="meta-grid">

          <div class="meta-item">

            <div class="meta-label">Author / Lead</div>

            <div class="meta-val">{html.escape(author)}</div>

          </div>

          <div class="meta-item">

            <div class="meta-label">System Platform</div>

            <div class="meta-val">J.A.R.V.I.S. Core</div>

          </div>

          <div class="meta-item">

            <div class="meta-label">Specification Version</div>

            <div class="meta-val">v{html.escape(version)}</div>

          </div>

          <div class="meta-item">

            <div class="meta-label">Status</div>

            <div class="meta-val">Verified / Sealed</div>

          </div>

        </div>

      </div>



      {extra_mermaid_html}



      {main_sections_str}

    </div>

  </main>



  <script>

    function copyCode(btn) {{

      const card = btn.closest('.code-card');

      const code = card.querySelector('code').innerText;

      navigator.clipboard.writeText(code).then(() => {{

        btn.innerText = 'Copied!';

        btn.classList.add('copied');

        setTimeout(() => {{

          btn.innerText = 'Copy';

          btn.classList.remove('copied');

        }}, 2000);

      }});

    }}



    function toggleTheme() {{

      const current = document.documentElement.getAttribute('data-theme') || 'dark';

      const target = current === 'dark' ? 'light' : 'dark';

      document.documentElement.setAttribute('data-theme', target);

      localStorage.setItem('jarvis-doc-theme', target);

    }}

    const savedTheme = localStorage.getItem('jarvis-doc-theme');

    if (savedTheme) {{

      document.documentElement.setAttribute('data-theme', savedTheme);

    }}



    const searchInput = document.getElementById('docSearch');

    searchInput.addEventListener('input', (e) => {{

      const q = e.target.value.toLowerCase().trim();

      document.querySelectorAll('#sidebarNav .nav-link').forEach(link => {{

        const title = link.getAttribute('data-title') || '';

        link.style.display = (!q || title.includes(q)) ? 'flex' : 'none';

      }});

      document.querySelectorAll('.doc-section').forEach(sec => {{

        const text = sec.innerText.toLowerCase();

        sec.style.display = (!q || text.includes(q)) ? 'block' : 'none';

      }});

    }});



    window.addEventListener('keydown', (e) => {{

      if (e.key === '/' && document.activeElement !== searchInput) {{

        e.preventDefault();

        searchInput.focus();

      }}

    }});

  </script>

</body>

</html>'''



        file_path.write_text(html_template, encoding="utf-8")



        set_last_active_document(file_path, title=title)



        if open_after:

            try:

                os.startfile(str(file_path))

            except Exception:

                pass



        return f"Successfully generated Interactive HTML Documentation: '{file_path.name}' at {file_path.parent}"



    except Exception as e:

        return f"Failed to generate HTML documentation: {e}"





# ====================================================================

# 6. DEEP CODEBASE & REPOSITORY DOCUMENTATION ENGINE

# ====================================================================

def document_codebase(

    project_path: Optional[str] = None,

    doc_type: str = "full_manual",

    output_format: str = "docx",

    output_filename: Optional[str] = None,

    target_location: str = "desktop",

    include_diagrams: bool = True,

    open_after: bool = True,

    player=None

) -> str:

    """

    Reads an entire repository/project and generates a comprehensive,

    professional technical documentation manual:

    - Discovers project manifests (requirements.txt, package.json, Cargo.toml, go.mod, etc.)

    - Analyzes directory topology and subsystem roles (Core, Actions, UI, Config)

    - Extracts deep AST symbols (Classes, Functions, Type Annotations, Docstrings, API Routes)

    - Computes Lines of Code (LOC) and language breakdown

    - Generates interactive Mermaid architecture flowcharts

    - Renders visual architecture diagrams embedded in Word (.docx) & PDF (.pdf)

    - Exports to Word (.docx), Interactive HTML (.html), PDF (.pdf), or Markdown (.md)

    """

    p = Path(project_path).resolve() if project_path else BASE_DIR

    if not p.exists() or not p.is_dir():

        return f"Specified project path does not exist: {project_path}"



    project_name = p.name

    if player and hasattr(player, "write_log"):

        player.write_log(f"DOC ENGINE: Analyzing repository '{project_name}' at {p}...")



    # 1. Manifest Discovery

    manifest_info = []

    manifest_files = [

        "requirements.txt", "pyproject.toml", "setup.py", "Pipfile",

        "package.json", "tsconfig.json", "Cargo.toml", "go.mod",

        "Dockerfile", "docker-compose.yml", ".env.example"

    ]

    for mf in manifest_files:

        cand = p / mf

        if cand.exists():

            try:

                snippet = cand.read_text(encoding="utf-8", errors="ignore")[:1200]

                manifest_info.append(f"Manifest: {mf}\n```\n{snippet}\n```")

            except Exception:

                pass



    manifest_summary = "\n\n".join(manifest_info[:4])



    # 2. Directory Topology & File Enumeration

    tree_items: List[str] = []

    ext_counts: Dict[str, int] = {}

    total_loc = 0

    classified_files = {

        "Core Engine": [],

        "Actions & Tools": [],

        "UI & Presentation": [],

        "Config & State": [],

        "Other Modules": []

    }



    ignore_dirs = {".git", "venv", ".venv", "__pycache__", "build", "dist", "node_modules", ".backups", ".cache"}



    for root, dirs, files in os.walk(p):

        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        rel_root = Path(root).relative_to(p)

        for f in files:

            ext = Path(f).suffix.lower()

            if ext in (".py", ".json", ".sql", ".md", ".bat", ".sh", ".js", ".ts", ".html", ".css", ".rs", ".go"):

                full_f = Path(root) / f

                rel_f = str(rel_root / f) if str(rel_root) != "." else f

                tree_items.append(rel_f)

                ext_counts[ext] = ext_counts.get(ext, 0) + 1



                try:

                    if full_f.stat().st_size < 250000:

                        lines_c = sum(1 for _ in open(full_f, "r", encoding="utf-8", errors="ignore"))

                        total_loc += lines_c

                except Exception:

                    pass



                low = rel_f.lower()

                if "core" in low or "main.py" in low or "engine" in low:

                    classified_files["Core Engine"].append(rel_f)

                elif "action" in low or "tool" in low or "controller" in low:

                    classified_files["Actions & Tools"].append(rel_f)

                elif "ui" in low or "hud" in low or "view" in low or "html" in low:

                    classified_files["UI & Presentation"].append(rel_f)

                elif "config" in low or "setting" in low or "model" in low or "data" in low:

                    classified_files["Config & State"].append(rel_f)

                else:

                    classified_files["Other Modules"].append(rel_f)



    # 3. Deep AST / Symbol Extraction on Top Python Modules

    symbol_catalog: List[str] = []

    candidate_py_files = [p / item for item in tree_items if item.endswith(".py") and (p / item).exists()]

    for py_f in candidate_py_files[:30]:

        try:

            rel_name = py_f.relative_to(p)

            code = py_f.read_text(encoding="utf-8", errors="ignore")

            tree = ast.parse(code)

            mod_doc = ast.get_docstring(tree) or ""

            classes_found = []

            funcs_found = []



            for node in tree.body:

                if isinstance(node, ast.ClassDef):

                    c_doc = (ast.get_docstring(node) or "").split("\n")[0][:100]

                    methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]

                    classes_found.append(f"Class {node.name} (Methods: {', '.join(methods[:4])}) — {c_doc}")

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

                    if not node.name.startswith("_") or node.name in ("__init__",):

                        f_doc = (ast.get_docstring(node) or "").split("\n")[0][:80]

                        arg_names = [a.arg for a in node.args.args if a.arg != "self"]

                        funcs_found.append(f"{node.name}({', '.join(arg_names[:4])}) — {f_doc}")



            if classes_found or funcs_found:

                entry = f"Module '{rel_name}':"

                if mod_doc:

                    entry += f" {mod_doc.split('\\n')[0][:120]}"

                if classes_found:

                    entry += "\n  " + "\n  ".join(classes_found[:3])

                if funcs_found:

                    entry += "\n  " + "\n  ".join(funcs_found[:4])

                symbol_catalog.append(entry)

        except Exception:

            pass



    symbols_summary = "\n\n".join(symbol_catalog[:16])



    # 4. Existing Readme

    readme_content = ""

    for r in ["README.md", "README.txt", "readme.md"]:

        if (p / r).exists():

            try:

                readme_content = (p / r).read_text(encoding="utf-8", errors="ignore")[:3500]

                break

            except Exception:

                pass



    files_tree_str = "\n".join(tree_items[:60])

    topology_summary = "\n".join([f"- {k}: {len(v)} files ({', '.join(v[:3])}...)" for k, v in classified_files.items() if v])

    lang_breakdown = ", ".join([f"{k} ({v} files)" for k, v in sorted(ext_counts.items(), key=lambda x: -x[1])[:5]])



    # 5. High-Order Synthesis Prompt

    prompt = (

        f"You are J.A.R.V.I.S., Chief Systems Architect and Principal Technical Writer.\n"

        f"Generate a comprehensive, publication-grade Technical Specification and Architecture Manual for '{project_name}'.\n\n"

        f"PROJECT METADATA:\n"

        f"- Target Root: {p}\n"

        f"- Total Analyzed Files: {len(tree_items)} | Total LOC Estimate: ~{total_loc:,}\n"

        f"- Language & Extension Breakdown: {lang_breakdown}\n\n"

        f"SUBSYSTEM TOPOLOGY:\n{topology_summary}\n\n"

        f"KEY MANIFEST CONTEXT:\n{manifest_summary or 'No standard manifest files found.'}\n\n"

        f"CORE SYMBOLS & FUNCTION SIGNATURES (AST Introspection):\n{symbols_summary or 'Standard modular functions.'}\n\n"

        f"README CONTEXT:\n{readme_content or 'Internal autonomous software repository.'}\n\n"

        "AUTHORING DIRECTIVE:\n"

        "Provide an exhaustive, deeply technical documentation manual with the following structured sections:\n"

        "1. # Executive Architecture Summary & Core Design Philosophy (Design paradigms, high-level objectives, runtime guarantees)\n"

        "2. # System Architecture & Interactive Flowchart (Include a valid Mermaid diagram block: ```mermaid\ngraph TD\n...\n``` illustrating client, dispatcher, engines, and persistence layers)\n"

        "3. # Subsystem Hierarchy & Directory Topology (Detailed breakdown of Core Engine, Actions/Tools, UI, and State stores)\n"

        "4. # Key Classes, API Interfaces & Function Specifications (Deep inspection of primary entrypoints, class contracts, arguments, and return types)\n"

        "5. # Execution Lifecycle & Data Flow Sequence (Step-by-step description of an end-to-end user request pipeline)\n"

        "6. # Configuration, Environment Variables & State Management (Table of required keys, JSON configuration files, and state persistence)\n"

        "7. # Security Posture, Cryptographic Seals & Permissions (Security boundaries, AST verification, input validation, and sandbox enforcement)\n"

        "8. # Developer & DevOps Runbook (Prerequisites, local run commands, test suites, and build instructions)\n"

        "9. # Troubleshooting, Diagnostics & Common Failure Modes (Known recovery routines and diagnostic commands)\n\n"

        "FORMATTING RULES:\n"

        "- Use clean Markdown headings (#, ##)\n"

        "- Use bullet points with **bold terms**\n"

        "- Include at least two `> ` callout boxes (e.g. `> ⚡ ARCHITECTURAL TAKEAWAY:` and `> 🔒 SECURITY DIRECTIVE:`)\n"

        "- Include markdown comparison/configuration tables with pipes (`| Key | Type | Description |`)\n"

        "- Do NOT use lazy filler text."

    )



    doc_text = generate_text_with_retry(prompt)



    out_name = output_filename or f"{project_name}_Technical_Specification"

    out_dir = _get_output_dir(target_location)



    # Parse Markdown into structured sections

    sections = _parse_markdown_to_sections(doc_text)



    # Extract Mermaid diagram if present

    mermaid_diagrams = []

    for s in sections:

        if s.get("mermaid"):

            mermaid_diagrams.append(s["mermaid"])



    # Render Visual Diagram for Word & PDF embedding

    diagram_img_path = None

    if include_diagrams:

        try:

            diagram_img_path = _render_architecture_diagram(

                title=f"{project_name} Architecture & Flowchart"

            )

        except Exception:

            pass



    out_fmt = (output_format or "docx").lower().strip()



    # 1. Word Document (.docx)

    if out_fmt in ("docx", "word", "doc"):

        return create_word_document(

            filename=f"{out_name}.docx",

            title=f"{project_name.upper()} — Technical Specification & Architecture Manual",

            sections=sections,

            output_dir=out_dir,

            open_after=open_after,

            subtitle=f"Complete Software Architecture & System Manual • Total LOC: ~{total_loc:,}",

            author="Akul Bhatnagar",

            cover_page=True,

            classification="PRODUCTION // ARCHITECTURE MANUAL",

            diagram_image=diagram_img_path

        )



    # 2. Interactive HTML Portal (.html)

    elif out_fmt in ("html", "html_doc", "htm", "portal"):

        metadata = {

            "author": "Akul Bhatnagar",

            "version": "1.0.0",

            "classification": "PRODUCTION // TECHNICAL SPECIFICATION",

            "project_path": str(p)

        }

        return create_html_documentation(

            filename=f"{out_name}.html",

            title=f"{project_name.upper()} Architecture Manual",

            subtitle=f"Autonomous Technical Specification & Deep Architecture Manual • {len(tree_items)} Files Analyzed",

            sections=sections,

            metadata=metadata,

            mermaid_diagrams=mermaid_diagrams,

            output_dir=out_dir,

            open_after=open_after

        )



    # 3. Publication-Grade PDF (.pdf)

    elif out_fmt in ("pdf",):

        return create_pdf_document(

            filename=f"{out_name}.pdf",

            title=f"{project_name} Technical Manual",

            sections=sections,

            output_dir=out_dir,

            open_after=open_after,

            subtitle=f"Technical Architecture & System Specification • {datetime.now().strftime('%B %d, %Y')}",

            author="Akul Bhatnagar",

            cover_page=True,

            classification="PRODUCTION // TECHNICAL MANUAL",

            diagram_image=diagram_img_path

        )



    # 4. GitHub-Flavored Markdown (.md)

    else:

        md_file = out_dir / f"{out_name}.md"

        header_badge = (

            f"# {project_name} — Technical Architecture Manual\n\n"

            f"> **Classification**: PRODUCTION // SPECIFICATION  \n"

            f"> **Author**: Akul Bhatnagar  \n"

            f"> **Total Analyzed Files**: {len(tree_items)} (~{total_loc:,} LOC)  \n"

            f"> **Generated**: {datetime.now().strftime('%B %d, %Y')}\n\n"

            f"---\n\n"

        )

        md_file.write_text(header_badge + doc_text, encoding="utf-8")

        set_last_active_document(md_file, title=f"{project_name} Architecture Manual")

        if open_after:

            try:

                os.startfile(str(md_file))

            except Exception:

                pass

        return f"Successfully generated Markdown Documentation: '{md_file.name}' at {md_file.parent}"





# ====================================================================

# 7. ENHANCED MARKDOWN-TO-STRUCTURED-SECTIONS PARSER

# ====================================================================

def _parse_markdown_to_sections(md_text: str) -> List[Dict[str, Any]]:

    """

    Parses Markdown text into rich structured sections for Word (.docx),

    HTML (.html), and PDF (.pdf):

    - Headings (#, ##, ###)

    - Bullet points (-, *, •)

    - Multi-variant callouts (> Takeaway, > Warning, > Tip, > Security)

    - Fenced code blocks (```lang ... ```) with language tracking

    - Mermaid diagrams (```mermaid ... ```)

    - Pipe tables (| col1 | col2 |) with header detection

    """

    if not md_text or not md_text.strip():

        return [{"heading": "Executive Summary", "content": "Document generated by J.A.R.V.I.S. Mark 78."}]



    sections: List[Dict[str, Any]] = []

    cur: Dict[str, Any] = {

        "heading": "Overview",

        "level": 1,

        "content": "",

        "bullets": [],

        "table": [],

        "callout": "",

        "callout_type": "takeaway",

        "code": "",

        "code_lang": "",

        "mermaid": ""

    }

    in_code = False

    in_mermaid = False

    code_lang = ""

    code_lines: List[str] = []

    table_rows: List[List[str]] = []



    def _flush_cur():

        nonlocal cur, table_rows

        if table_rows:

            cur["table"] = table_rows

            table_rows = []

        if (

            cur["content"].strip()

            or cur["bullets"]

            or cur["table"]

            or cur["callout"]

            or cur["code"]

            or cur["mermaid"]

        ):

            sections.append(cur)



    for raw_line in md_text.splitlines():

        line = raw_line.rstrip()

        stripped = line.strip()



        # Fenced code block toggle

        if stripped.startswith("```"):

            if in_code:

                full_code = "\n".join(code_lines).strip()

                if in_mermaid or code_lang == "mermaid":

                    cur["mermaid"] = full_code

                else:

                    cur["code"] = (cur.get("code", "") + "\n" + full_code).strip()

                    cur["code_lang"] = code_lang

                code_lines = []

                in_code = False

                in_mermaid = False

                code_lang = ""

            else:

                in_code = True

                code_lang = stripped[3:].strip().lower()

                in_mermaid = (code_lang == "mermaid")

            continue



        if in_code:

            code_lines.append(line)

            continue



        # Markdown pipe table row

        if stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 2:

            cells = [c.strip() for c in stripped.strip("|").split("|")]

            if all(re.match(r"^:?-{2,}:?$", c) for c in cells if c):

                continue

            table_rows.append(cells)

            continue

        elif table_rows:

            cur["table"] = table_rows

            table_rows = []



        # Heading

        if stripped.startswith("#"):

            hashes = len(stripped) - len(stripped.lstrip("#"))

            h_text = stripped.lstrip("#").strip()

            if h_text:

                _flush_cur()

                cur = {

                    "heading": h_text,

                    "level": 1 if hashes <= 2 else 2,

                    "content": "",

                    "bullets": [],

                    "table": [],

                    "callout": "",

                    "callout_type": "takeaway",

                    "code": "",

                    "code_lang": "",

                    "mermaid": ""

                }

                continue



        # Callout (> ...)

        if stripped.startswith(">"):

            c_txt = stripped.lstrip(">").strip()

            if c_txt:

                low_c = c_txt.lower()

                if "warn" in low_c:

                    cur["callout_type"] = "warning"

                elif "tip" in low_c or "best" in low_c:

                    cur["callout_type"] = "tip"

                elif "sec" in low_c:

                    cur["callout_type"] = "security"

                else:

                    cur["callout_type"] = "takeaway"



                cur["callout"] = (cur["callout"] + " " + c_txt).strip() if cur["callout"] else c_txt

            continue



        # Bullet point

        if stripped.startswith(("- ", "* ", "• ")):

            cur["bullets"].append(stripped[2:].strip())

            continue



        # Regular paragraph line

        if stripped:

            cur["content"] += stripped + "\n"



    _flush_cur()

    return sections or [{"heading": "Overview", "content": md_text.strip()}]





# ====================================================================

# 8. UNIVERSAL DISPATCHER

# ====================================================================

def universal_file_creator(parameters: dict, player=None) -> str:

    """

    Main tool handler for creating any file requested by the user.

    Automatically intercepts edit requests and graph additions to modify existing documents in-place.

    parameters:

      file_type: 'docx' | 'pptx' | 'pdf' | 'xlsx' | 'html_doc' | 'code' | 'markdown' | 'project_doc'

      filename / file_name: e.g. 'Project_Blueprint.docx'

      title: Title of document or presentation

      content: Raw text or structured body (auto-generated via AI if omitted!)

      topic: Topic for AI synthesis when content is empty

      doc_type: 'full_manual' | 'architecture' | 'api_reference' | 'user_guide' | 'technical_spec' | 'executive_brief' | 'readme'

      format: Output format for project_doc ('docx', 'html', 'pdf', 'md')

      sections: Optional list of sections

      slides: Optional list of slide data for presentations

      columns: Optional list of column names for Excel

      rows: Optional list of row lists for Excel

      target_location: 'desktop' | 'downloads' | 'documents'

      project_path: Optional path for documenting a codebase

      include_diagrams: True to render visual architecture diagrams

      cover_page: True to generate executive standalone cover page

      open_after: True to auto-open file

    """

    params = parameters or {}

    action = (params.get("action") or "").lower().strip()

    fname = (params.get("filename") or params.get("file_name") or params.get("name") or "Document").strip()

    from actions.docx_builder import acronym_safe_title_case
    title = acronym_safe_title_case((params.get("title") or params.get("topic") or Path(fname).stem.replace("_", " ")).strip())

    content = (params.get("content") or "").strip()

    instruction = (params.get("instruction") or "").strip()

    open_after = params.get("open_after", True)

    low_title = title.lower()

    low_inst = (instruction or content).lower()

    low_fname = fname.lower()



    # Intercept edits and graph additions so we never recreate an existing document

    is_graph_req = (

        action in ("add_graph", "insert_graph", "add_chart", "insert_chart")

        or any(k in low_title or k in low_inst for k in ("add graph", "insert graph", "add chart", "insert chart", "put graph", "put chart"))

    )

    is_edit_req = (

        action in ("edit", "modify", "update", "replace")

        or low_title.startswith(("edit ", "update ", "modify ", "change ", "replace "))

        or low_fname.startswith(("edit ", "update ", "modify "))

    )



    if is_graph_req:

        from actions.file_controller import fetch_and_insert_graph

        target_doc = None if fname in ("Document", "Document.docx", "") else fname

        g_q = params.get("graph_query") or params.get("query") or params.get("topic") or title

        for remove_word in ("add graph of", "insert graph of", "add chart of", "insert chart of", "add graph", "insert graph", "add chart", "insert chart", "graph of", "chart of", "put graph", "put chart"):

            g_q = re.sub(re.escape(remove_word), "", g_q, flags=re.IGNORECASE).strip()

        return fetch_and_insert_graph(

            document_path=target_doc,

            graph_query=g_q or "market performance chart",

            caption=params.get("caption") or g_q,

            open_after=bool(open_after)

        )



    if is_edit_req:

        from actions.file_controller import edit_any_file

        target_doc = None if fname in ("Document", "Document.docx", "") else fname

        inst = instruction or content or title

        return edit_any_file(

            path=target_doc or "",

            instruction=inst,

            find_text=params.get("find_text", ""),

            replace_text=params.get("replace_text", ""),

            content=content if not (content and title == content) else "",

            open_after=bool(open_after)

        )



    # Route all new document generation through Universal Document Intelligence & QA Orchestrator

    try:

        from core.document_qa.orchestrator import UniversalDocumentOrchestrator

        from core.document_qa.config import get_qa_config

        qa_cfg = get_qa_config()

        if qa_cfg.get("enabled", True):

            orchestrator = UniversalDocumentOrchestrator()

            return orchestrator.orchestrate_generation(parameters=params, player=player)

    except Exception as e:

        if player and hasattr(player, "write_log"):

            player.write_log(f"DOCUMENT QA // Fallback to direct generator: {e}")



    inferred_ext = Path(fname).suffix.lower().lstrip(".")

    ftype = (params.get("file_type") or inferred_ext or "docx").lower().strip()

    loc = params.get("target_location") or "desktop"

    cover_page = params.get("cover_page", True)

    include_diagrams = params.get("include_diagrams", True)

    doc_type = (params.get("doc_type") or "technical_spec").lower().strip()

    out_dir = _get_output_dir(loc)



    if player and hasattr(player, "write_log"):

        player.write_log(f"FILE GEN: Generating {ftype.upper()} file '{fname}' in {loc}...")



    # 1. Project / Codebase Documenter

    if ftype in ("project_doc", "codebase_doc", "doc_code"):

        proj_p = params.get("project_path") or str(BASE_DIR)

        doc_fmt = params.get("format") or params.get("output_format") or "docx"

        return document_codebase(

            project_path=proj_p,

            doc_type=doc_type,

            output_format=doc_fmt,

            output_filename=fname,

            target_location=loc,

            include_diagrams=include_diagrams,

            open_after=open_after,

            player=player

        )



    # 2. Interactive HTML Documentation Portal

    if ftype in ("html_doc", "htmldoc", "html_documentation") or (ftype in ("html", "htm") and (params.get("doc_type") or "doc" in fname.lower() or "architecture" in fname.lower())):

        if not content and not params.get("sections"):

            synth_prompt = (

                f"You are J.A.R.V.I.S., Chief Systems Architect. Author a modern, interactive technical specification and architecture manual for '{title}'.\n"

                f"Document Type: {doc_type}. Context: {content or title}\n"

                "Include clean Markdown headings (#, ##), bullet points, at least one > callout box, at least one code snippet, a table, and a ```mermaid\ngraph TD\n...\n``` block."

            )

            content = generate_text_with_retry(synth_prompt)



        parsed_secs = params.get("sections") or _parse_markdown_to_sections(content)

        metadata = {

            "author": "Akul Bhatnagar",

            "version": "1.0.0",

            "classification": "PRODUCTION // TECHNICAL SPECIFICATION",

            "project_path": str(BASE_DIR)

        }

        return create_html_documentation(

            filename=fname,

            title=title,

            subtitle=params.get("subtitle") or f"Autonomous Technical Specification & Architecture Portal ({doc_type.replace('_', ' ').title()})",

            sections=parsed_secs,

            metadata=metadata,

            output_dir=out_dir,

            open_after=open_after

        )



    # Auto-synthesize rich content if none was supplied for docx, pdf, or md

    if not content and not params.get("sections") and ftype in ("docx", "word", "doc", "pdf", "md", "markdown"):

        if doc_type == "api_reference":

            genre_rules = "Provide detailed API Endpoints, HTTP methods, parameter tables (Name, Type, Required, Description), request/response JSON schemas, and error code tables."

        elif doc_type == "architecture":

            genre_rules = "Provide System Topology, Component Interactions, Mermaid flow diagram, Data Flow Lifecycle, State Schema, and Security Boundaries."

        elif doc_type == "user_guide":

            genre_rules = "Provide Prerequisites, Quickstart Walkthrough, Step-by-Step Instructions, Common Pitfalls, and Troubleshooting FAQ."

        else:

            genre_rules = "Provide Executive Architecture Summary, Component Breakdown, Key Functions, Configuration Schema, and Security Best Practices."



        synth_prompt = (

            f"You are J.A.R.V.I.S., Chief Software Architect. Write a thorough, authentic human-written technical document on: '{title}'.\n"

            f"Document Genre: {doc_type}. Specific Focus: {genre_rules}\n"

            "CRITICAL ANTI-AI-DETECTOR MANDATE: Vary sentence lengths dramatically. NEVER use AI cliché words like delve, tapestry, testament, underscore, pivotal, crucial, multifaceted, realm, moreover, furthermore, or in conclusion.\n"

            "Use clean Markdown formatting with:\n"

            "- `#` section headings\n"

            "- Bullet points (`- `) with **bold key terms**\n"

            "- At least one `> ` callout box for the core takeaway or formula\n"

            "- A Markdown comparison/summary pipe table (`| Category | Key Detail | Impact / Application |`)\n"

        )

        content = generate_text_with_retry(synth_prompt)



    # Run built-in Humanizer & AI-Detector check on raw content

    human_badge = ""

    if content and ftype in ("docx", "word", "doc", "pdf", "md", "markdown", "txt"):

        try:

            from core.humanizer import scrub_ai_watermarks, detect_ai_patterns, humanize_text

            content = scrub_ai_watermarks(content)

            rep = detect_ai_patterns(content)

            if rep["human_score"] < 88:

                content, rep = humanize_text(content, use_llm=True, player=player)

            human_badge = f" [Human Detector: {rep['human_score']}% Human — {rep['verdict']}]"

            if player and hasattr(player, "write_log"):

                player.write_log(f"HUMAN DETECTOR // {rep['human_score']}% HUMAN ({rep['verdict']})")

        except Exception:

            pass



    # 3. Word Document

    if ftype in ("docx", "word", "doc"):

        secs = params.get("sections") or _parse_markdown_to_sections(content)

        try:

            from core.humanizer import humanize_document_sections

            secs, rep = humanize_document_sections(secs, use_llm=False)

            if not human_badge:

                human_badge = f" [Human Detector: {rep['human_score']}% Human]"

        except Exception:

            pass



        diag_img = None

        if include_diagrams:

            try:

                diag_img = _render_architecture_diagram(title=f"{title} Architecture Flow")

            except Exception:

                pass



        res = create_word_document(
            filename=fname,
            title=title,
            sections=secs,
            output_dir=out_dir,
            open_after=open_after,
            subtitle=params.get("subtitle"),
            cover_page=cover_page,
            diagram_image=diag_img,
            markdown_text=content,
            short_title=params.get("short_title")
        )

        return res + human_badge



    # 4. PowerPoint Presentation

    elif ftype in ("pptx", "powerpoint", "presentation", "slides"):

        try:

            from actions.presentation_designer import create_intriguing_presentation

            theme = params.get("theme", "stark_dark")

            slides_data = params.get("slides")

            res = create_intriguing_presentation(

                topic=title,

                theme=theme,

                target_location=loc,

                open_after=open_after,

                source_content=content,

                custom_slides=slides_data,

                filename=fname

            )

            if res.get("status") == "success":

                return f"Executive 16:9 Presentation generated successfully: {res.get('file_path')} [Theme: {res.get('theme_name')}, Slides: {res.get('slide_count')}]"

        except Exception:

            pass



        slides_data = params.get("slides")

        if not slides_data:

            parsed_secs = _parse_markdown_to_sections(content)

            slides_data = [

                {

                    "title": s.get("heading", "Key Concept"),

                    "bullets": s.get("bullets") or [line for line in s.get("content", "").splitlines() if line.strip()][:5],

                }

                for s in parsed_secs

            ]

        sub = params.get("subtitle") or "Prepared by J.A.R.V.I.S. Mark 78"

        return create_presentation(fname, title, sub, slides_data, output_dir=out_dir, open_after=open_after)



    # 5. PDF Document

    elif ftype in ("pdf",):

        secs = params.get("sections") or _parse_markdown_to_sections(content)

        try:

            from core.humanizer import humanize_document_sections

            secs, rep = humanize_document_sections(secs, use_llm=False)

            if not human_badge:

                human_badge = f" [Human Detector: {rep['human_score']}% Human]"

        except Exception:

            pass



        diag_img = None

        if include_diagrams:

            try:

                diag_img = _render_architecture_diagram(title=f"{title} Architecture Flow")

            except Exception:

                pass



        return create_pdf_document(

            filename=fname,

            title=title,

            sections=secs,

            output_dir=out_dir,

            open_after=open_after,

            subtitle=params.get("subtitle"),

            cover_page=cover_page,

            diagram_image=diag_img

        ) + human_badge



    # 6. Excel Spreadsheet

    elif ftype in ("xlsx", "excel", "spreadsheet", "csv"):

        cols = params.get("columns")

        rows = params.get("rows")

        if not rows and content:

            parsed_secs = _parse_markdown_to_sections(content)

            for s in parsed_secs:

                if s.get("table") and len(s["table"]) >= 2:

                    cols = s["table"][0]

                    rows = []

                    for r in s["table"][1:]:

                        parsed_row = []

                        for cell_val in r:

                            c_clean = str(cell_val).replace(",", "").replace("$", "").replace("%", "").strip()

                            try:

                                parsed_row.append(float(c_clean) if "." in c_clean else int(c_clean))

                            except ValueError:

                                parsed_row.append(cell_val)

                        rows.append(parsed_row)

                    break

        if not rows:

            try:

                xl_prompt = (

                    f"Generate a realistic, structured dataset for an Excel spreadsheet titled '{title}'.\n"

                    f"Context: {content or title}\n"

                    "Return ONLY valid JSON with keys 'columns' (list of 4-6 strings) and 'rows' (list of 6-10 lists, including at least one numeric column for automatic SUM formulas)."

                )

                raw_xl = generate_text_with_retry(xl_prompt)

                clean_xl = raw_xl.strip()

                if "```json" in clean_xl:

                    clean_xl = clean_xl.split("```json", 1)[1].split("```", 1)[0].strip()

                elif "```" in clean_xl:

                    clean_xl = clean_xl.split("```", 1)[1].split("```", 1)[0].strip()

                xl_data = json.loads(clean_xl)

                cols = xl_data.get("columns") or cols

                rows = xl_data.get("rows") or rows

            except Exception:

                pass

        cols = cols or ["Item", "Category", "Metric", "Notes"]

        rows = rows or [["Sample 1", "General", 100, "Verified"]]

        return create_excel_sheet(fname, title, cols, rows, output_dir=out_dir, open_after=open_after)



    # 7. Plain Code or Markdown File

    else:

        ext = ftype if ftype.startswith(".") else f".{ftype}"

        if not fname.endswith(ext):

            fname += ext

        target_file = out_dir / fname

        target_file.write_text(content, encoding="utf-8")

        set_last_active_document(target_file, title=title)

        if open_after:

            try:

                os.startfile(str(target_file))

            except Exception:

                pass

        return f"Successfully generated file: '{target_file.name}' at {target_file.parent}"

