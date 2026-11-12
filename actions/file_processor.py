"""
actions/file_processor.py — JARVIS Universal File Analyzer & Editor Engine (Mark 78)

Supported types & capabilities:
  image   → describe, ocr, analyze, resize, convert, compress
  pdf     → summarize, analyze, extract_text, to_word, edit (converts & edits in Word)
  docx    → summarize, analyze, edit, rewrite, humanize, fix, reformat, append, extract_text
  txt/md  → summarize, analyze, edit, rewrite, humanize, fix, reformat, word_count
  csv     → analyze, filter, sort, convert, stats
  xlsx    → analyze, filter, sort, convert, stats
  json    → validate, format, extract, analyze, to_csv
  code    → explain, review, fix, optimize, run, document, test, edit
  audio   → transcribe, trim, convert, info
  video   → analyze (multimodal keyframes + speech), edit, color_grade, subtitles, merge_clips, trim, extract_audio, extract_frame, compress, transcribe, convert, info
  archive → list, extract
  pptx    → summarize, analyze, edit, add_slide, rewrite, humanize, extract_text, to_pdf
"""

import os
import re
import time
import json
import shutil
import platform
import subprocess
import tempfile
from pathlib import Path

from google import genai
from google.genai import types


def _get_api_key() -> str:
    config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "")
    except Exception:
        return ""


def _gemini_client():
    return genai.Client(api_key=_get_api_key())


def _ai_generate(prompt_or_parts) -> str:
    if isinstance(prompt_or_parts, str):
        try:
            from core.omniroute_client import omniroute_client
            omni_res = omniroute_client.generate_text_fallback(prompt_or_parts)
            if omni_res:
                return omni_res
        except Exception:
            pass

    client = _gemini_client()
    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    for m in models:
        for attempt in range(2):
            try:
                res = client.models.generate_content(model=m, contents=prompt_or_parts)
                if res and res.text:
                    return res.text.strip()
            except Exception as e:
                err_s = str(e)
                if "429" in err_s or "RESOURCE_EXHAUSTED" in err_s:
                    time.sleep(1.2)
                    continue
                break
    return "AI processing encountered a temporary rate limit. Please retry shortly."


def _detect_type(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    image_exts = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg", "ico"}
    video_exts = {"mp4", "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v", "3gp"}
    audio_exts = {"mp3", "wav", "ogg", "m4a", "aac", "flac", "wma", "opus"}
    code_exts = {
        "py", "js", "ts", "jsx", "tsx", "html", "css", "java", "c",
        "cpp", "cs", "go", "rs", "rb", "php", "swift", "kt", "sh",
        "bash", "ps1", "lua", "r", "m", "sql", "yaml", "toml",
    }
    archive_exts = {"zip", "rar", "tar", "gz", "7z", "bz2", "xz"}

    if ext in image_exts:
        return "image"
    if ext in video_exts:
        return "video"
    if ext in audio_exts:
        return "audio"
    if ext in code_exts:
        return "code"
    if ext in archive_exts:
        return "archive"
    if ext == "pdf":
        return "pdf"
    if ext in ("docx", "doc"):
        return "docx"
    if ext in ("txt", "md", "rst", "log"):
        return "text"
    if ext in ("csv", "tsv"):
        return "csv"
    if ext in ("xlsx", "xls", "ods"):
        return "excel"
    if ext == "json":
        return "json"
    if ext == "xml":
        return "xml"
    if ext in ("pptx", "ppt"):
        return "pptx"
    return "unknown"


def _file_size_str(path: Path) -> str:
    size = path.stat().st_size
    if size < 1024:
        return f"{size} B"
    if size < 1024**2:
        return f"{size / 1024:.1f} KB"
    if size < 1024**3:
        return f"{size / 1024**2:.1f} MB"
    return f"{size / 1024**3:.1f} GB"


def _output_path(src: Path, suffix: str, new_ext: str = None) -> Path:
    ext = new_ext or src.suffix
    name = f"{src.stem}_{suffix}{ext}"
    return src.parent / name


def _process_image(path: Path, action: str, params: dict, speak=None) -> str:
    try:
        from PIL import Image
    except ImportError:
        return "Pillow is not installed. Run: pip install Pillow"

    action = action or "describe"

    if action in ("describe", "ocr", "analyze", "read", "extract_text"):
        try:
            prompt = {
                "describe":     "Describe this image clearly and make an insightful observation.",
                "ocr":          "Extract all text visible in this image. Return only the text, formatted clearly.",
                "analyze":      "Analyze this image thoroughly: objects, layout, text, colors, and actionable insights.",
                "read":         "Read all text in this image, preserving structure and formatting.",
                "extract_text": "Extract all text from this image.",
            }.get(action, "Describe this image.")

            if params.get("instruction"):
                prompt = params["instruction"]

            img_bytes = path.read_bytes()
            ext = path.suffix.lower().lstrip(".")
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            part_img = types.Part.from_bytes(data=img_bytes, mime_type=mime)
            result = _ai_generate([prompt, part_img])

            if len(result) > 500 and params.get("save", True):
                out = _output_path(path, "analysis", ".txt")
                out.write_text(result, encoding="utf-8")
                return f"{result[:400]}...\n\nFull analysis saved to: {out}"
            return result
        except Exception as e:
            return f"AI image analysis failed: {e}"

    if action == "resize":
        width = int(params.get("width", 0))
        height = int(params.get("height", 0))
        scale = float(params.get("scale", 0))
        try:
            img = Image.open(path)
            w, h = img.size
            if scale:
                new_size = (int(w * scale), int(h * scale))
            elif width and height:
                new_size = (width, height)
            elif width:
                new_size = (width, int(h * width / w))
            elif height:
                new_size = (int(w * height / h), height)
            else:
                return "Please specify width, height, or scale."
            out = _output_path(path, f"resized_{new_size[0]}x{new_size[1]}")
            img.resize(new_size, Image.Resampling.LANCZOS).save(out)
            return f"Resized from {w}x{h} to {new_size[0]}x{new_size[1]}. Saved: {out.name}"
        except Exception as e:
            return f"Resize failed: {e}"

    if action == "convert":
        fmt = params.get("format", "png").lower().strip(".")
        fmt_map = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP", "bmp": "BMP", "tiff": "TIFF"}
        pil_fmt = fmt_map.get(fmt, fmt.upper())
        try:
            img = Image.open(path).convert("RGB") if fmt in ("jpg", "jpeg") else Image.open(path)
            out = _output_path(path, "converted", f".{fmt}")
            img.save(out, pil_fmt)
            return f"Converted to {fmt.upper()}. Saved: {out.name}"
        except Exception as e:
            return f"Convert failed: {e}"

    if action == "compress":
        quality = int(params.get("quality", 70))
        try:
            img = Image.open(path).convert("RGB")
            out = _output_path(path, f"compressed_q{quality}", ".jpg")
            img.save(out, "JPEG", quality=quality, optimize=True)
            return f"Compressed: {_file_size_str(path)} → {_file_size_str(out)}. Saved: {out.name}"
        except Exception as e:
            return f"Compress failed: {e}"

    if action == "info":
        try:
            img = Image.open(path)
            return f"Image info: {img.format}, {img.size[0]}x{img.size[1]}px, mode: {img.mode}, size: {_file_size_str(path)}"
        except Exception as e:
            return f"Info failed: {e}"

    return _process_image(path, "describe", {"instruction": f"{action}: {params}"})


def _process_pdf(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "summarize"
    instruction = params.get("instruction", "")

    def _extract_pdf_text(max_chars=50000) -> str:
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
        except Exception:
            try:
                import PyPDF2
                with open(path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += (page.extract_text() or "") + "\n"
            except Exception:
                return ""
        return text[:max_chars]

    if action in ("edit", "modify", "rewrite", "humanize"):
        # Convert PDF text to an editable humanized Word document and apply the requested edit
        text = _extract_pdf_text()
        if not text.strip():
            return "Could not extract text from PDF to edit."
        from core.humanizer import scrub_ai_watermarks
        prompt = (
            f"Edit and format the following PDF document ('{path.name}') according to this instruction:\n"
            f"INSTRUCTION: {instruction or 'Clean up, humanize, and structure this document clearly.'}\n\n"
            f"SOURCE PDF TEXT:\n{text[:30000]}"
        )
        edited_text = scrub_ai_watermarks(_ai_generate(prompt))
        try:
            from docx import Document
            doc = Document()
            doc.add_heading(path.stem.replace("_", " "), 0)
            for para in edited_text.split("\n\n"):
                if para.strip():
                    doc.add_paragraph(para.strip())
            out = _output_path(path, "edited", ".docx")
            doc.save(out)
            if platform.system() == "Windows":
                os.startfile(str(out))
            return f"Edited PDF content and saved as editable Word document: {out.name} (opened in Word)."
        except Exception as e:
            return f"PDF edit failed: {e}"

    if action in ("summarize", "extract_text", "translate_hint", "analyze", "reformat"):
        text = _extract_pdf_text()
        if not text.strip():
            return "Could not extract text from PDF (may be scanned/image-based)."

        if action == "extract_text":
            out = _output_path(path, "text", ".txt")
            out.write_text(text, encoding="utf-8")
            return f"Text extracted ({len(text)} chars). Saved: {out.name}"

        prompt_map = {
            "summarize":      f"Summarize this PDF document concisely and highlight key takeaways:\n\n{text}",
            "analyze":        f"Analyze this PDF document thoroughly ({instruction}):\n\n{text}",
            "translate_hint": f"What language is this document in and what does it say? Summarize:\n\n{text}",
            "reformat":       f"Reformat this text cleanly with proper structure:\n\n{text}",
        }
        try:
            result = _ai_generate(prompt_map.get(action, f"{instruction or 'Analyze'}:\n\n{text}"))
            if len(result) > 600 and params.get("save", True):
                out = _output_path(path, action, ".txt")
                out.write_text(result, encoding="utf-8")
                return f"{result[:450]}...\n\nFull result saved: {out.name}"
            return result
        except Exception as e:
            return f"AI analysis failed: {e}"

    if action == "info":
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = len(pdf.pages)
            return f"PDF: {pages} pages, size: {_file_size_str(path)}"
        except Exception:
            return f"PDF size: {_file_size_str(path)}"

    if action == "to_word":
        text = _extract_pdf_text()
        if not text:
            return "Could not extract text to convert."
        try:
            from docx import Document
            doc = Document()
            doc.add_heading(path.stem, 0)
            for para in text.split("\n\n"):
                if para.strip():
                    doc.add_paragraph(para.strip())
            out = _output_path(path, "converted", ".docx")
            doc.save(out)
            if platform.system() == "Windows":
                os.startfile(str(out))
            return f"Converted to Word document and opened: {out.name}"
        except Exception as e:
            return f"Conversion failed: {e}"

    return _process_pdf(path, "analyze", {"instruction": f"{action}: {instruction}"})


def _process_text_doc(path: Path, file_type: str, action: str, params: dict, speak=None) -> str:
    action = action or "summarize"
    instruction = params.get("instruction", "")

    if action in ("edit", "modify", "rewrite", "update", "append", "replace"):
        from actions.file_controller import edit_any_file
        return edit_any_file(
            path=str(path),
            instruction=instruction or f"Perform {action} on this document",
            find_text=params.get("find_text", ""),
            replace_text=params.get("replace_text", ""),
            content=params.get("content", ""),
            open_after=True,
        )

    if action == "humanize":
        from core.humanizer import humanizer_tool
        return humanizer_tool({"action": "humanize", "file_path": str(path)})

    def _read_content() -> str:
        if file_type == "docx":
            try:
                from docx import Document
                doc = Document(path)
                paras = [p.text for p in doc.paragraphs if p.text.strip()]
                for tbl in doc.tables:
                    for row in tbl.rows:
                        paras.append(" | ".join(c.text.strip() for c in row.cells))
                return "\n".join(paras)
            except Exception as e:
                return f"Read failed: {e}"
        return path.read_text(encoding="utf-8", errors="ignore")

    content = _read_content()
    if not content.strip():
        return "File appears to be empty."

    if action == "word_count":
        words = len(content.split())
        chars = len(content)
        lines = content.count("\n")
        return f"Word count: {words} words, {chars} characters, {lines} lines."

    if action == "extract_text":
        if file_type != "txt":
            out = _output_path(path, "extracted", ".txt")
            out.write_text(content, encoding="utf-8")
            return f"Text extracted. Saved: {out.name}"
        return content[:2000]

    prompt_map = {
        "summarize":      f"Summarize this document concisely:\n\n{content[:40000]}",
        "analyze":        f"Analyze this document thoroughly ({instruction}):\n\n{content[:40000]}",
        "reformat":       f"Reformat this text with clean structure, proper headings and paragraphs:\n\n{content[:40000]}",
        "fix":            f"Fix grammar, spelling, and style issues in this text while keeping a natural human voice:\n\n{content[:40000]}",
        "translate_hint": f"What language is this and what does it say? Summarize:\n\n{content[:10000]}",
        "to_bullet":      f"Convert this text into a clear bullet-point summary:\n\n{content[:40000]}",
        "custom":         f"{instruction or action}\n\n{content[:40000]}",
    }

    prompt_key = action if action in prompt_map else "custom"
    try:
        result = _ai_generate(prompt_map[prompt_key])
        if action in ("fix", "reformat") and file_type == "docx":
            from actions.file_controller import edit_any_file
            edit_any_file(str(path), content=result, open_after=True)
            return f"Applied {action} directly to '{path.name}' and opened it."
        if len(result) > 600 and params.get("save", True):
            out = _output_path(path, action, ".txt")
            out.write_text(result, encoding="utf-8")
            return f"{result[:420]}...\n\nFull result saved: {out.name}"
        return result
    except Exception as e:
        return f"AI processing failed: {e}"


def _process_data(path: Path, file_type: str, action: str, params: dict, speak=None) -> str:
    try:
        import pandas as pd
    except ImportError:
        return "pandas not installed. Run: pip install pandas openpyxl"

    action = action or "analyze"

    try:
        if file_type == "csv":
            df = pd.read_csv(path, encoding="utf-8", errors="replace")
        else:
            df = pd.read_excel(path)
    except Exception as e:
        return f"Could not read file: {e}"

    if action == "info":
        return (
            f"Rows: {len(df)}, Columns: {len(df.columns)}\n"
            f"Columns: {', '.join(df.columns.astype(str).tolist())}\n"
            f"Size: {_file_size_str(path)}"
        )

    if action == "stats":
        try:
            desc = df.describe(include="all").to_string()
            return f"Statistics:\n{desc[:2000]}"
        except Exception as e:
            return f"Stats failed: {e}"

    if action == "analyze":
        preview = df.head(50).to_string()
        prompt = (
            f"Analyze this dataset. Columns: {list(df.columns)}\n"
            f"Rows: {len(df)}\nPreview:\n{preview}\n\n"
            f"Give sharp insights, patterns, and notable findings."
        )
        return _ai_generate(prompt)

    if action in ("convert", "to_csv", "to_excel", "to_json"):
        fmt = {
            "to_csv": "csv", "to_excel": "xlsx", "to_json": "json",
            "convert": params.get("format", "csv"),
        }.get(action, "csv")
        try:
            if fmt == "csv":
                out = _output_path(path, "converted", ".csv")
                df.to_csv(out, index=False, encoding="utf-8")
            elif fmt == "xlsx":
                out = _output_path(path, "converted", ".xlsx")
                df.to_excel(out, index=False)
            elif fmt == "json":
                out = _output_path(path, "converted", ".json")
                df.to_json(out, orient="records", force_ascii=False, indent=2)
            return f"Converted to {fmt.upper()}. Saved: {out.name}"
        except Exception as e:
            return f"Convert failed: {e}"

    if action == "filter":
        col = params.get("column", "")
        value = params.get("value", "")
        condition = params.get("condition", "equals")
        if not col or col not in df.columns:
            return f"Column '{col}' not found. Available: {', '.join(df.columns.astype(str))}"
        try:
            if condition == "equals":
                filtered = df[df[col] == value]
            elif condition == "contains":
                filtered = df[df[col].astype(str).str.contains(str(value), case=False)]
            elif condition == "gt":
                filtered = df[df[col] > float(value)]
            elif condition == "lt":
                filtered = df[df[col] < float(value)]
            else:
                filtered = df[df[col] == value]
            out = _output_path(path, "filtered", ".csv")
            filtered.to_csv(out, index=False)
            return f"Filtered: {len(filtered)} rows match. Saved: {out.name}"
        except Exception as e:
            return f"Filter failed: {e}"

    if action == "sort":
        col = params.get("column", df.columns[0])
        asc = params.get("ascending", True)
        try:
            sorted_df = df.sort_values(col, ascending=asc)
            out = _output_path(path, "sorted", path.suffix)
            if path.suffix.lower() in (".xlsx", ".xls"):
                sorted_df.to_excel(out, index=False)
            else:
                sorted_df.to_csv(out, index=False)
            return f"Sorted by '{col}'. Saved: {out.name}"
        except Exception as e:
            return f"Sort failed: {e}"

    preview = df.head(30).to_string()
    return _ai_generate(
        f"Task: {params.get('instruction') or action}\nDataset ({len(df)} rows, cols: {list(df.columns)}):\n{preview}"
    )


def _process_json(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "analyze"
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        data = json.loads(content)
    except Exception as e:
        return f"Invalid JSON: {e}"

    if action == "validate":
        return f"Valid JSON. Type: {type(data).__name__}, size: {_file_size_str(path)}"

    if action == "format":
        out = _output_path(path, "formatted", ".json")
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return f"Formatted JSON saved: {out.name}"

    if action in ("analyze", "summarize", "extract"):
        preview = json.dumps(data, indent=2, ensure_ascii=False)[:8000]
        prompt = f"Task: {params.get('instruction') or action} this JSON data:\n{preview}"
        return _ai_generate(prompt)

    if action == "to_csv":
        try:
            import pandas as pd
            if isinstance(data, list):
                df = pd.DataFrame(data)
                out = _output_path(path, "converted", ".csv")
                df.to_csv(out, index=False)
                return f"Converted to CSV. Saved: {out.name}"
            return "JSON must be an array of objects to convert to CSV."
        except ImportError:
            return "pandas not installed."

    return _process_json(path, "analyze", {"instruction": action})


def _process_code(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "explain"
    instruction = params.get("instruction", "")

    if action in ("edit", "modify", "update"):
        from actions.file_controller import edit_any_file
        return edit_any_file(str(path), instruction=instruction or "Improve and fix this code", open_after=False)

    content = path.read_text(encoding="utf-8", errors="ignore")
    ext = path.suffix.lstrip(".")

    if action == "run":
        if ext == "py":
            try:
                result = subprocess.run(
                    ["python", str(path)],
                    capture_output=True, text=True, timeout=30,
                )
                out = result.stdout or result.stderr
                return f"Output:\n{out[:2000]}" if out else "Executed cleanly with no console output."
            except subprocess.TimeoutExpired:
                return "Execution timed out (30s)."
            except Exception as e:
                return f"Run failed: {e}"
        return f"Direct execution not supported for .{ext} files."

    if action == "info":
        lines = content.count("\n")
        words = len(content.split())
        return f"Code file: {lines} lines, {words} words, {_file_size_str(path)}"

    prompt_map = {
        "explain":   f"Explain this {ext} code clearly:\n\n```{ext}\n{content[:30000]}\n```",
        "review":    f"Review this {ext} code for bugs, security issues, and improvements:\n\n```{ext}\n{content[:30000]}\n```",
        "fix":       f"Fix any bugs in this {ext} code and return the corrected version:\n\n```{ext}\n{content[:30000]}\n```",
        "optimize":  f"Optimize this {ext} code for performance and readability:\n\n```{ext}\n{content[:30000]}\n```",
        "document":  f"Add proper documentation/comments to this {ext} code:\n\n```{ext}\n{content[:30000]}\n```",
        "summarize": f"Summarize what this {ext} code does:\n\n```{ext}\n{content[:30000]}\n```",
        "test":      f"Write unit tests for this {ext} code:\n\n```{ext}\n{content[:30000]}\n```",
    }

    prompt = prompt_map.get(action, f"{instruction or action}\n\n```{ext}\n{content[:30000]}\n```")
    result = _ai_generate(prompt)

    if action in ("fix", "optimize", "document") and params.get("save", True):
        out = _output_path(path, action)
        code_match = re.search(r"```(?:\w+)?\n(.*?)```", result, re.DOTALL)
        code_to_save = code_match.group(1) if code_match else result
        out.write_text(code_to_save, encoding="utf-8")
        return f"{result[:400]}...\n\nSaved: {out.name}"
    return result


def _process_audio(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "transcribe"

    if action == "info":
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(path)
            duration = len(audio) / 1000
            mins, secs = divmod(int(duration), 60)
            return f"Audio: {mins}m {secs}s, {audio.channels} ch, {audio.frame_rate}Hz, {_file_size_str(path)}"
        except Exception:
            return f"Audio file: {_file_size_str(path)}"

    if action == "transcribe":
        try:
            content = path.read_bytes()
            mime = {
                "mp3": "audio/mp3", "wav": "audio/wav",
                "ogg": "audio/ogg", "m4a": "audio/mp4",
                "aac": "audio/aac", "flac": "audio/flac",
            }.get(path.suffix.lstrip(".").lower(), "audio/mpeg")
            part_audio = types.Part.from_bytes(data=content, mime_type=mime)
            result = _ai_generate(["Transcribe all speech in this audio file accurately.", part_audio])
            if params.get("save", True):
                out = _output_path(path, "transcript", ".txt")
                out.write_text(result, encoding="utf-8")
                return f"Transcription saved: {out.name}\n\nPreview: {result[:350]}"
            return result
        except Exception as e:
            return f"Transcription failed: {e}"

    if action == "convert":
        fmt = params.get("format", "mp3").lstrip(".")
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(path)
            out = _output_path(path, "converted", f".{fmt}")
            audio.export(out, format=fmt)
            return f"Converted to {fmt.upper()}. Saved: {out.name}"
        except Exception as e:
            return f"Convert failed: {e}"

    if action == "trim":
        start = float(params.get("start", 0))
        end = float(params.get("end", 0))
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(path)
            end_ms = int(end * 1000) if end else len(audio)
            trimmed = audio[int(start * 1000):end_ms]
            out = _output_path(path, f"trim_{int(start)}s_{int(end)}s")
            trimmed.export(out, format=path.suffix.lstrip("."))
            return f"Trimmed audio ({int(start)}s–{int(end)}s). Saved: {out.name}"
        except Exception as e:
            return f"Trim failed: {e}"

    return f"Unknown audio action: '{action}'. Try: transcribe, info, convert, trim"


def _process_video(path: Path, action: str, params: dict, speak=None) -> str:
    action = (action or "analyze").lower().strip()
    instruction = params.get("instruction", "")

    # Route advanced AI video analysis, editing, color grading, clip merging & subtitling to auto_video_editor
    if action in ("analyze", "describe", "edit", "color_grade", "grade", "subtitles", "subtitle", "captions", "merge", "add_clips"):
        from actions.auto_video_editor import auto_edit_video
        return auto_edit_video(
            parameters={
                "action": action,
                "media_path": str(path),
                "style": params.get("style", "") or instruction,
                "reference_path": params.get("reference_path", ""),
                "language": params.get("language", "English"),
                "use_davinci": params.get("use_davinci", False),
            }
        )

    def _ffmpeg_available() -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=3)
            return True
        except Exception:
            return False

    if action == "info":
        try:
            import cv2
            cap = cv2.VideoCapture(str(path))
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                cap.release()
                dur = frames / fps if fps else 0
                mins, secs = divmod(int(dur), 60)
                return f"Video: {mins}m {secs}s ({frames} frames), {w}x{h} @ {fps:.1f} fps, {_file_size_str(path)}"
        except Exception:
            pass
        return f"Video file: {_file_size_str(path)}"

    if action == "extract_audio":
        if not _ffmpeg_available():
            return "ffmpeg not found. Install ffmpeg to extract audio."
        out = _output_path(path, "audio", ".mp3")
        try:
            subprocess.run(
                ["ffmpeg", "-i", str(path), "-q:a", "0", "-map", "a", str(out), "-y"],
                capture_output=True, timeout=300,
            )
            return f"Audio extracted. Saved: {out.name}"
        except Exception as e:
            return f"Extract audio failed: {e}"

    if action == "trim":
        start = params.get("start", "00:00:00")
        end = params.get("end", "")
        if not _ffmpeg_available():
            return "ffmpeg not found."
        out = _output_path(path, "trim", path.suffix)
        try:
            cmd = ["ffmpeg", "-i", str(path), "-ss", str(start)]
            if end:
                cmd += ["-to", str(end)]
            cmd += ["-c", "copy", str(out), "-y"]
            subprocess.run(cmd, capture_output=True, timeout=600)
            return f"Trimmed video saved: {out.name}"
        except Exception as e:
            return f"Trim failed: {e}"

    if action == "extract_frame":
        timestamp = params.get("timestamp", "00:00:01")
        out = _output_path(path, f"frame_{str(timestamp).replace(':', '')}", ".jpg")
        try:
            import cv2
            cap = cv2.VideoCapture(str(path))
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                parts = [float(p) for p in str(timestamp).split(":")]
                secs = parts[-1] + (parts[-2] * 60 if len(parts) > 1 else 0) + (parts[-3] * 3600 if len(parts) > 2 else 0)
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(secs * fps))
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    cv2.imwrite(str(out), frame)
                    return f"Frame extracted at {timestamp}. Saved: {out.name}"
        except Exception as e:
            return f"Extract frame failed: {e}"

    if action == "compress":
        crf = int(params.get("quality", 28))
        if not _ffmpeg_available():
            return "ffmpeg not found."
        out = _output_path(path, f"compressed_crf{crf}", ".mp4")
        try:
            subprocess.run(
                ["ffmpeg", "-i", str(path), "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-c:a", "copy", str(out), "-y"],
                capture_output=True, timeout=1800,
            )
            return f"Compressed: {_file_size_str(path)} → {_file_size_str(out)}. Saved: {out.name}"
        except Exception as e:
            return f"Compress failed: {e}"

    if action == "transcribe":
        from actions.auto_video_editor import generate_video_subtitles
        return generate_video_subtitles(path, language=params.get("language", "English"), burn_in=False)

    if action == "convert":
        fmt = params.get("format", "mp4").lstrip(".")
        if not _ffmpeg_available():
            return "ffmpeg not found."
        out = _output_path(path, "converted", f".{fmt}")
        try:
            subprocess.run(["ffmpeg", "-i", str(path), str(out), "-y"], capture_output=True, timeout=1800)
            return f"Converted to {fmt.upper()}. Saved: {out.name}"
        except Exception as e:
            return f"Convert failed: {e}"

    from actions.auto_video_editor import analyze_video_file
    return analyze_video_file(path, instruction=instruction or action)


def _process_archive(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "list"

    if action == "list":
        try:
            import zipfile
            import tarfile
            ext = path.suffix.lower()
            if ext == ".zip":
                with zipfile.ZipFile(path) as z:
                    names = z.namelist()
            elif ext in (".tar", ".gz", ".bz2", ".xz"):
                with tarfile.open(path) as t:
                    names = t.getnames()
            else:
                return f"Unsupported archive format: {ext}"
            preview = "\n".join(names[:30])
            suffix = f"\n... and {len(names) - 30} more" if len(names) > 30 else ""
            return f"Archive contains {len(names)} files:\n{preview}{suffix}"
        except Exception as e:
            return f"List failed: {e}"

    if action == "extract":
        dest = Path(params.get("destination", str(path.parent / path.stem)))
        dest.mkdir(parents=True, exist_ok=True)
        try:
            shutil.unpack_archive(path, dest)
            return f"Extracted to: {dest}"
        except Exception as e:
            return f"Extract failed: {e}"

    return f"Unknown archive action: '{action}'. Try: list, extract"


def _process_pptx(path: Path, action: str, params: dict, speak=None) -> str:
    action = (action or "summarize").lower().strip()
    instruction = params.get("instruction", "")

    if action in ("edit", "modify", "update", "add_slide", "rewrite"):
        from actions.file_controller import edit_any_file
        return edit_any_file(
            path=str(path),
            instruction=instruction or "Enhance and update this presentation",
            find_text=params.get("find_text", ""),
            replace_text=params.get("replace_text", ""),
            open_after=True,
        )

    if action == "to_pdf":
        from actions.presentation_designer import presentation_designer
        return presentation_designer({"action": "export_pdf", "file_path": str(path)})

    def _read_pptx_text() -> str:
        try:
            from pptx import Presentation
            prs = Presentation(path)
            text = []
            for i, slide in enumerate(prs.slides, 1):
                slide_text = f"\n--- Slide {i} ---\n"
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text += shape.text.strip() + "\n"
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                    if notes:
                        slide_text += f"[Speaker Notes]: {notes}\n"
                text.append(slide_text)
            return "\n".join(text)
        except Exception as e:
            return f"Could not read PPTX: {e}"

    text = _read_pptx_text()
    if action == "extract_text":
        out = _output_path(path, "text", ".txt")
        out.write_text(text, encoding="utf-8")
        return f"Text extracted. Saved: {out.name}"

    prompt = (
        f"{'Summarize' if action == 'summarize' else 'Analyze'} this PowerPoint presentation "
        f"({instruction or 'provide slide-by-slide insights and strengths/improvements'}):\n{text[:30000]}"
    )
    return _ai_generate(prompt)


def file_processor(parameters: dict, player=None, speak=None) -> str:
    params = parameters or {}
    file_path_str = (params.get("file_path") or params.get("path") or params.get("name") or "").strip()
    if not file_path_str and player and getattr(player, "current_file", None):
        file_path_str = player.current_file

    if not file_path_str:
        return "No file path provided. Specify a file name or attach a file on the strip."

    from actions.file_controller import resolve_any_file
    path = resolve_any_file(file_path_str) or Path(file_path_str).expanduser()
    if not path.exists():
        return f"File not found across laptop: {file_path_str}"
    if not path.is_file():
        return f"Path is not a file: {path}"

    file_type = _detect_type(path)
    action = (params.get("action") or "").lower().strip()
    instruction = params.get("instruction", "")
    merged_params = {**params, "instruction": instruction}

    log_msg = f"PROC: {file_type.upper()} // {path.name} ({action or 'auto'})"
    print(f"[FileProcessor] {log_msg}")
    if player and hasattr(player, "write_log"):
        player.write_log(log_msg)

    if file_type == "unknown":
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:10000]
            prompt = (
                f"File: {path.name}\nContent preview:\n{content}\n\n"
                f"Task: {action or instruction or 'Describe what this file contains and what can be done with it.'}"
            )
            return _ai_generate(prompt)
        except Exception as e:
            return f"Unknown file type ({path.suffix}). Could not process: {e}"

    dispatch = {
        "image":   _process_image,
        "pdf":     _process_pdf,
        "docx":    lambda p, a, pm, s: _process_text_doc(p, "docx", a, pm, s),
        "text":    lambda p, a, pm, s: _process_text_doc(p, "text", a, pm, s),
        "csv":     lambda p, a, pm, s: _process_data(p, "csv", a, pm, s),
        "excel":   lambda p, a, pm, s: _process_data(p, "excel", a, pm, s),
        "json":    _process_json,
        "xml":     lambda p, a, pm, s: _process_json(p, a, pm, s),
        "code":    _process_code,
        "audio":   _process_audio,
        "video":   _process_video,
        "archive": _process_archive,
        "pptx":    _process_pptx,
    }

    handler = dispatch.get(file_type)
    if not handler:
        return f"Unsupported file type: {file_type}"

    try:
        result = handler(path, action, merged_params, speak)
        return result or "Done."
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Processing failed: {e}"
