"""
actions/exam_companion.py — Academic Exam Companion, Tutor, Study PPT & Document Studio for JARVIS Mark 108
Provides high-level academic intelligence:
- Document reading, analysis, and syllabus breakdown (PDF, DOCX, PPTX, Images/OCR, Test papers).
- One-command Study PowerPoint (.pptx) generation from any topic or uploaded lecture PDF/DOCX.
- One-command Study Guide / Revision Document (.docx / .pdf) with Markdown tables, callouts & formulas.
- Multi-mode concept explanations: Feynman technique, in-depth mathematical rigor, or rapid cram.
- Interactive Socratic Drill, Viva Voce prep, mock tests, and flashcards with instant evaluation.
- Step-by-step problem solver for derivations, numericals, and past paper questions.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from core.ai_client import generate_text_with_retry, get_api_key as _get_api_key


def _extract_document_text(file_path: str) -> tuple[str, str]:
    """Extracts text from PDF, DOCX, PPTX, TXT, or Image (via Gemini 2.5 Flash Vision)."""
    p = Path(file_path).expanduser()
    if not p.exists():
        for base in [
            Path.home() / "OneDrive" / "Desktop",
            Path.home() / "Desktop",
            Path.home() / "OneDrive" / "Downloads",
            Path.home() / "Downloads",
            Path.home() / "OneDrive" / "Documents",
            Path.home() / "Documents",
        ]:
            cand = base / file_path
            if cand.exists():
                p = cand
                break

    if not p.exists():
        return "", f"File not found: '{file_path}'"

    ext = p.suffix.lower()
    text = ""

    # 1. PDF
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            for idx, page in enumerate(reader.pages[:40]):
                t = page.extract_text()
                if t:
                    text += f"\n--- Page {idx+1} ---\n" + t
            return text.strip(), ""
        except Exception as e:
            return "", f"PDF extraction error: {e}"

    # 2. Word (.docx)
    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(str(p))
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    row_txt = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_txt:
                        text += row_txt + "\n"
            return text.strip(), ""
        except Exception as e:
            return "", f"DOCX extraction error: {e}"

    # 3. PowerPoint (.pptx)
    elif ext in (".pptx", ".ppt"):
        try:
            from pptx import Presentation
            prs = Presentation(str(p))
            for idx, slide in enumerate(prs.slides):
                text += f"\n--- Slide {idx+1} ---\n"
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            if paragraph.text.strip():
                                text += paragraph.text + "\n"
            return text.strip(), ""
        except Exception as e:
            return "", f"PPTX extraction error: {e}"

    # 4. Text / Markdown / Code
    elif ext in (".txt", ".md", ".csv", ".json", ".py"):
        try:
            return p.read_text(encoding="utf-8", errors="ignore"), ""
        except Exception as e:
            return "", f"Text file read error: {e}"

    # 5. Image (Diagram, Whiteboard, Handwritten test) via Gemini 2.5 Flash Vision
    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        api_key = _get_api_key()
        if not api_key:
            return "", "Gemini API key missing for image document processing."
        try:
            client = genai.Client(api_key=api_key)
            img_bytes = p.read_bytes()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type=mime),
                    "Carefully transcribe all text, formulas, diagrams, questions, and notes from this academic document/image."
                ]
            )
            return res.text.strip() if res and res.text else "", ""
        except Exception as e:
            return "", f"Image vision OCR error: {e}"

    return "", f"Unsupported file extension: {ext}"


def exam_companion(parameters: dict, player=None) -> str:
    """
    JARVIS Academic Exam Companion, Study Deck & Document Intelligence Engine.
    parameters:
      action:
        - 'create_study_ppt' | 'make_ppt' | 'study_ppt' | 'presentation' | 'slides'
        - 'create_study_doc' | 'make_doc' | 'study_guide' | 'notes'
        - 'create_cheat_sheet' | 'cheat_sheet' | 'formula_sheet'
        - 'predict_questions' | 'exam_questions'
        - 'quiz_me' | 'flashcards' | 'viva'
        - 'explain' | 'analyze_document' | 'solve_question' | 'study_plan'
      topic / subject: Subject or topic name
      file_path: Optional path to uploaded document (auto-detects UI dropped file if omitted)
      mode: 'feynman' | 'deep' | 'cram' | 'mcq' | 'step_by_step'
      export_to: 'none' | 'docx' | 'pdf' | 'pptx'
      slide_count: int (default 8 for study PPTs)
      theme: Presentation theme (default 'academic_study' or 'stark_dark')
    """
    params = parameters or {}
    action = (params.get("action") or "explain").lower().strip()
    topic = (params.get("topic") or params.get("subject") or params.get("query") or "").strip()
    file_path = (params.get("file_path") or "").strip()
    if not file_path and player and getattr(player, "current_file", None):
        file_path = player.current_file

    mode = (params.get("mode") or "feynman").lower().strip()
    export_to = (params.get("export_to") or "none").lower().strip()
    slide_count = int(params.get("slide_count") or 8)
    theme = params.get("theme") or "academic_study"

    # ------------------------------------------------------------------
    # 0A. DEDICATED STUDY POWERPOINT DECK GENERATOR
    # ------------------------------------------------------------------
    if action in ("create_study_ppt", "make_ppt", "study_ppt", "presentation", "slides"):
        from actions.presentation_designer import presentation_designer
        if file_path and Path(file_path).expanduser().exists():
            return presentation_designer({
                "action": "from_document",
                "file_path": file_path,
                "topic": topic or Path(file_path).stem.replace("_", " ").title(),
                "theme": theme,
                "slide_count": slide_count,
                "audience": "University Exam & Lecture Review",
                "open_after": True,
            }, player=player)
        else:
            target_topic = topic or "Academic Lecture & Exam Revision"
            return presentation_designer({
                "action": "create",
                "topic": f"{target_topic} — Comprehensive Academic Study & Exam Review Deck",
                "theme": theme,
                "slide_count": slide_count,
                "audience": "University Students & Exam Preparation",
                "open_after": True,
            }, player=player)

    api_key = _get_api_key()
    if not api_key:
        return "Sir, Gemini API Key is required for the Exam Companion engine."

    doc_text = ""
    doc_note = ""
    if file_path:
        if player and hasattr(player, "write_log"):
            player.write_log(f"EXAM ENGINE: Extracting academic document '{Path(file_path).name}'...")
        doc_text, err = _extract_document_text(file_path)
        if err:
            doc_note = f"\n[Document Notice: {err}]"

    client = genai.Client(api_key=api_key)

    # ------------------------------------------------------------------
    # 0B. DEDICATED STUDY GUIDE / REVISION DOCUMENT (.DOCX / .PDF)
    # ------------------------------------------------------------------
    if action in ("create_study_doc", "make_doc", "study_guide", "notes", "create_notes"):
        target_subject = topic or (Path(file_path).stem.replace("_", " ") if file_path else "Academic Course")
        prompt = (
            f"You are J.A.R.V.I.S., preparing a comprehensive, executive-grade University Study Guide & Revision Document on: {target_subject}.\n"
            "Structure the document using clean Markdown with these exact sections:\n"
            "# Executive Overview & Learning Objectives\n"
            "# Core Concepts & Theoretical Foundations\n"
            "(Use bullet points and `> KEY FORMULA:` or `> IMPORTANT:` callout blocks for critical definitions)\n"
            "# Key Concepts Comparison Table\n"
            "(Include a Markdown pipe table `| Concept | Definition / Formula | Exam Application |`)\n"
            "# Step-by-Step Worked Examples\n"
            "# Top 5 High-Probability Exam Questions & Model Answers\n"
            "# Common Exam Pitfalls & Rapid Revision Checklist\n"
        )
        if doc_text:
            prompt += f"\nBase your study guide directly on this source material:\n```\n{doc_text[:15000]}\n```"

        output = generate_text_with_retry(prompt, client=client)
        from actions.file_generator import universal_file_creator
        clean_t = re.sub(r"[^a-zA-Z0-9_-]", "_", target_subject)[:28]
        fmt = export_to if export_to in ("pdf", "docx", "md") else "docx"
        f_res = universal_file_creator({
            "file_type": fmt,
            "filename": f"{clean_t}_Study_Guide",
            "title": f"Academic Study Guide: {target_subject.title()}",
            "subtitle": "J.A.R.V.I.S. Mark 108 Academic & Exam Intelligence Division",
            "content": output,
            "open_after": True,
        }, player=player)
        return f"{output}\n\n📁 **Study Guide Generated & Opened**: {f_res}{doc_note}"

    # 1. EXPLAIN TOPIC / CONCEPT
    if action in ("explain", "explain_topic", "tutor", "teach"):
        style_prompt = {
            "feynman": "Explain using the Feynman Technique: crystal-clear, relatable real-world analogies, zero unnecessary jargon, intuitive mental models, followed by high-yield key takeaways.",
            "deep": "Provide deep academic and mathematical rigor: state formal definitions, core equations, derivations, assumptions, boundary conditions, and edge cases.",
            "cram": "Provide an ultra-condensed Exam Cram breakdown: 5-bullet summary, essential formulas, high-probability exam questions, and common mistakes students lose marks on."
        }.get(mode, "Explain clearly with structure, intuitive examples, and key takeaways.")

        prompt = (
            f"You are J.A.R.V.I.S., Akul's academic mentor and exam companion.\n"
            f"Topic to explain: {topic or 'the uploaded document'}\n"
            f"Style: {style_prompt}\n"
        )
        if doc_text:
            prompt += f"\nContext from uploaded lecture/textbook ({len(doc_text)} chars):\n```\n{doc_text[:12000]}\n```\n"

        prompt += "\nFormat with markdown headers, bold terms, and bullet points. Be concise, engaging, and direct."
        output = generate_text_with_retry(prompt, client=client)

        if export_to in ("docx", "pdf", "pptx"):
            from actions.file_generator import universal_file_creator
            clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", topic or "Exam_Revision")[:25]
            f_res = universal_file_creator({
                "file_type": export_to,
                "filename": f"{clean_name}_Study_Notes",
                "title": f"Study Guide: {topic.title() if topic else 'Academic Revision'}",
                "content": output,
                "open_after": True,
            }, player=player)
            output += f"\n\n📁 **Exported**: {f_res}"

        return output + doc_note

    # 2. ANALYZE DOCUMENT / SYLLABUS
    elif action in ("analyze_document", "analyze", "breakdown", "summarize_doc"):
        if not doc_text:
            return f"Please provide or drop a document (PDF, Word, PPTX, or Image notes) to analyze, sir.{doc_note}"

        prompt = (
            "You are J.A.R.V.I.S., Akul's academic exam wingman.\n"
            "Analyze the following college lecture/textbook document:\n"
            "# Executive Summary\n"
            "# Core Concepts, Definitions & Formulas\n"
            "# Summary Comparison Table\n"
            "(Include a Markdown pipe table summarizing the key topics/formulas)\n"
            "# Top 5 High-Probability Exam Questions\n"
            "# Common Pitfalls & Exam Traps\n\n"
            f"Document Content:\n```\n{doc_text[:15000]}\n```"
        )
        output = generate_text_with_retry(prompt, client=client)

        if export_to in ("docx", "pdf", "pptx"):
            from actions.file_generator import universal_file_creator
            f_name = Path(file_path).stem if file_path else "Document_Analysis"
            f_res = universal_file_creator({
                "file_type": export_to,
                "filename": f"{f_name}_Exam_Analysis",
                "title": f"Exam Breakdown: {f_name.replace('_', ' ').title()}",
                "content": output,
                "open_after": True,
            }, player=player)
            output += f"\n\n📁 **Exported**: {f_res}"

        return output

    # 3. PREDICT QUESTIONS / VIVA / QUIZ ME / FLASHCARDS
    elif action in ("quiz_me", "quiz", "mock_test", "flashcards", "predict_questions", "exam_questions", "viva"):
        if action in ("predict_questions", "exam_questions"):
            prompt = (
                f"You are J.A.R.V.I.S., analyzing exam patterns for: {topic or 'the uploaded syllabus/notes'}.\n"
                "Predict the Top 10 highest-probability exam questions divided into:\n"
                "# Section A: Conceptual & Short-Answer Questions (5 Marks)\n"
                "# Section B: Analytical, Derivation & Problem-Solving Questions (10 Marks)\n"
                "# Section C: Model Marking Scheme & Key Points Examiners Look For"
            )
        elif action == "viva":
            prompt = (
                f"You are J.A.R.V.I.S., conducting a rigorous Viva Voce / Oral Exam preparation drill on: {topic or 'the uploaded material'}.\n"
                "Provide 8 sharp Viva questions ranging from foundational to tricky edge-cases, each followed by a crisp, confident 2-3 sentence model answer."
            )
        else:
            prompt = (
                f"You are J.A.R.V.I.S., running a high-yield exam drill session for Akul on: {topic or 'the uploaded material'}.\n"
                "Generate 5 sharp, realistic college exam questions (3 Multiple Choice with options A/B/C/D, 2 Short Analytical).\n"
                "Include the Answer Key with concise explanations at the end under a '--- ANSWER KEY ---' divider."
            )
        if doc_text:
            prompt += f"\nSource Material:\n```\n{doc_text[:12000]}\n```"

        output = generate_text_with_retry(prompt, client=client)
        if export_to in ("docx", "pdf", "pptx"):
            from actions.file_generator import universal_file_creator
            clean_t = re.sub(r"[^a-zA-Z0-9_-]", "_", topic or action)[:24]
            f_res = universal_file_creator({
                "file_type": export_to,
                "filename": f"{clean_t}_{action}",
                "title": f"Academic Drill ({action.replace('_', ' ').title()}): {topic or 'Course Material'}",
                "content": output,
                "open_after": True,
            }, player=player)
            output += f"\n\n📁 **Exported**: {f_res}"
        return output

    # 4. SOLVE QUESTION / DERIVATION
    elif action in ("solve_question", "solve", "math", "derivation"):
        prompt = (
            f"You are J.A.R.V.I.S., assisting Akul with solving an exam question.\n"
            f"Problem Statement: {topic}\n"
        )
        if doc_text:
            prompt += f"\nContext/Reference Material:\n```\n{doc_text[:10000]}\n```"
        prompt += (
            "\nProvide:\n"
            "1. Given variables and what needs to be solved\n"
            "2. Relevant governing formulas and principles\n"
            "3. Step-by-step rigorous solution and intermediate calculations\n"
            "4. Final Boxed Answer with appropriate units\n"
            "5. Sanity check: Why this answer makes intuitive sense."
        )
        return generate_text_with_retry(prompt, client=client)

    # 5. STUDY PLAN / REVISION SCHEDULE
    elif action in ("study_plan", "revision_schedule", "plan"):
        days = params.get("days", 7)
        prompt = (
            f"You are J.A.R.V.I.S., creating an optimized, realistic {days}-day exam revision schedule for Akul.\n"
            f"Subject/Scope: {topic or 'Upcoming College Finals'}\n"
            "Include a structured Markdown table (`| Day | Morning Block | Afternoon Practice | Evening Active Recall |`) "
            "plus high-yield study tips."
        )
        output = generate_text_with_retry(prompt, client=client)

        if export_to in ("docx", "xlsx", "pdf"):
            from actions.file_generator import universal_file_creator
            f_res = universal_file_creator({
                "file_type": export_to,
                "filename": "Exam_Revision_Schedule",
                "title": f"{days}-Day Revision Roadmap: {topic or 'Finals'}",
                "content": output,
                "open_after": True,
            }, player=player)
            output += f"\n\n📁 **Schedule Exported**: {f_res}"

        return output

    # 6. CRAM SHEET EXPORT
    elif action in ("create_cheat_sheet", "cheat_sheet", "cram_sheet", "formula_sheet"):
        prompt = (
            f"You are J.A.R.V.I.S. Create a master high-yield Exam Formula & Cheat Sheet for: {topic or 'College Course'}.\n"
            "Organize strictly using Markdown sections:\n"
            "# Must-Know Definitions\n"
            "# Core Formulas & Variables Table\n"
            "(Include a Markdown pipe table `| Formula / Law | Equation | Variables & Units |`)\n"
            "# Key Theorems & Decision Rules\n"
            "# Top 3 Common Exam Mistakes to Avoid"
        )
        if doc_text:
            prompt += f"\nSource Material:\n```\n{doc_text[:14000]}\n```"

        output = generate_text_with_retry(prompt, client=client)

        from actions.file_generator import universal_file_creator
        clean_t = re.sub(r"[^a-zA-Z0-9_-]", "_", topic or "Subject")[:20]
        fmt = export_to if export_to in ("pdf", "docx", "pptx") else "pdf"
        f_res = universal_file_creator({
            "file_type": fmt,
            "filename": f"{clean_t}_Master_Cheat_Sheet",
            "title": f"Master Cheat Sheet: {topic.title() if topic else 'Course Revision'}",
            "content": output,
            "open_after": True,
        }, player=player)

        return f"{output}\n\n📁 **Cheat Sheet Created & Opened**: {f_res}"

    return (
        f"Unknown exam_companion action: '{action}'. Available: "
        "create_study_ppt, create_study_doc, create_cheat_sheet, predict_questions, "
        "quiz_me, flashcards, viva, explain, analyze_document, solve_question, study_plan"
    )
