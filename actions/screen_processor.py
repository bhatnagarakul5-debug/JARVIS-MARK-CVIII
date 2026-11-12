"""
actions/screen_processor.py — Instant Camera Snap, Live Screen Observer & Visual Action Engine (Mark 108)
Capabilities:
1. Webcam Snap ('camera'): Captures high-clarity photo when user says 'take a snap' or 'take a picture',
   saves to Pictures/JARVIS_Snaps/, and returns witty, observant human-like commentary.
2. Live Screen Observation ('screen'): Captures the display + active window title when told to 'see the screen',
   'observe the screen', or 'what is on my screen', and analyzes documents, PPTs, videos, or code on screen.
3. Screen Observation + Direct Action (act=True or action intent): When told to 'see the screen and fix/edit/change/type...',
   analyzes the visual screen and automatically acts on it (edits the open Word/PPT/code file, or types/pastes the
   revised content directly into the active window, or clicks the target UI control).
"""

import io
import re
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import mss
import mss.tools

try:
    import PIL.Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

from google import genai
from google.genai import types


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

IMG_MAX_W = 1366
IMG_MAX_H = 900
JPEG_Q = 82


def _get_snaps_dir() -> Path:
    pics = Path.home() / "OneDrive" / "Pictures" / "JARVIS_Snaps"
    if not pics.parent.exists():
        pics = Path.home() / "Pictures" / "JARVIS_Snaps"
    pics.mkdir(parents=True, exist_ok=True)
    return pics


def _get_api_key() -> str:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            keys = json.load(f)
        key = keys.get("gemini_api_key", "")
        if not key:
            raise ValueError("gemini_api_key not found")
        return key
    except Exception as e:
        raise RuntimeError(f"Could not load API key: {e}")


def _get_active_window_title() -> str:
    try:
        import pygetwindow as gw
        win = gw.getActiveWindow()
        if win and win.title:
            return win.title.strip()
    except Exception:
        pass
    return "Desktop"


def _get_camera_index() -> int:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "camera_index" in cfg:
            return int(cfg["camera_index"])
    except Exception:
        pass

    best_index = 0
    for idx in range(4):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            continue
        for _ in range(5):
            cap.read()
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None and frame.mean() > 5:
            best_index = idx
            break

    try:
        cfg = {}
        if API_CONFIG_PATH.exists():
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["camera_index"] = best_index
        with open(API_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        pass

    return best_index


def _to_jpeg(img_bytes: bytes) -> bytes:
    if not _PIL_OK:
        return img_bytes
    img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img.thumbnail([IMG_MAX_W, IMG_MAX_H], PIL.Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_Q, optimize=True)
    return buf.getvalue()


def capture_screenshot(save_to_disk: bool = True) -> tuple[bytes, Path | None]:
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        png_bytes = mss.tools.to_png(shot.rgb, shot.size)
    jpg_bytes = _to_jpeg(png_bytes)
    saved_path = None
    if save_to_disk:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_path = _get_snaps_dir() / f"screen_snap_{ts}.jpg"
        saved_path.write_bytes(jpg_bytes)
    return jpg_bytes, saved_path


def capture_camera_photo(save_to_disk: bool = True) -> tuple[bytes, Path | None]:
    camera_index = _get_camera_index()
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Camera could not be opened (index {camera_index})")

    frame = None
    ret = False
    for _ in range(12):
        ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Could not capture frame from webcam.")

    saved_path = None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if save_to_disk:
        saved_path = _get_snaps_dir() / f"camera_snap_{ts}.jpg"
        cv2.imwrite(str(saved_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])

    if _PIL_OK:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(rgb)
        img.thumbnail([IMG_MAX_W, IMG_MAX_H], PIL.Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_Q, optimize=True)
        return buf.getvalue(), saved_path

    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_Q])
    return buf.tobytes(), saved_path


def _execute_screen_action(action_spec: dict, active_title: str) -> str:
    """Executes an autonomous action derived from observing the screen."""
    act_type = (action_spec.get("action_type") or "none").lower().strip()
    if act_type == "none":
        return ""

    try:
        # 1. Edit open file on disk if filename is known or detected in window title
        if act_type == "edit_file":
            fname = action_spec.get("file_name") or ""
            if not fname and " - " in active_title:
                fname = active_title.split(" - ")[0].strip()
            instr = action_spec.get("edit_instruction") or action_spec.get("text_to_type") or ""
            if fname and instr:
                from actions.file_controller import edit_any_file
                return edit_any_file(path=fname, instruction=instr, open_after=True)

        # 2. Type or paste generated/corrected text directly into the active window on screen
        if act_type in ("type_text", "paste_text", "write"):
            txt = (action_spec.get("text_to_type") or "").strip()
            if txt:
                from core.humanizer import scrub_ai_watermarks
                clean_txt = scrub_ai_watermarks(txt)
                import pyperclip
                import pyautogui
                pyperclip.copy(clean_txt)
                time.sleep(0.15)
                pyautogui.hotkey("ctrl", "v")
                return f"Pasted humanized text ({len(clean_txt.split())} words) directly into '{active_title}'."

        # 3. Click a UI element on screen via UI Automation
        if act_type == "click_element":
            target_el = (action_spec.get("target_element") or "").strip()
            if target_el:
                from actions.agent_desktop import agent_desktop_control
                return agent_desktop_control({"action": "click", "target": target_el})
    except Exception as e:
        return f"Screen action notice: {e}"
    return ""


def analyze_image_with_commentary(
    image_bytes: bytes,
    user_prompt: str,
    source_type: str = "camera",
    saved_path: Path | None = None,
    act_on_screen: bool = False,
) -> str:
    """
    Uses Gemini 2.5 Flash Vision to inspect the captured picture/screen, deliver sharp, witty,
    natural commentary, and optionally execute direct edits/actions on what is visible on screen.
    """
    client = genai.Client(api_key=_get_api_key())
    active_title = _get_active_window_title() if source_type == "screen" else "Webcam"

    p_low = (user_prompt or "").lower()
    wants_action = act_on_screen or (
        source_type == "screen"
        and any(
            kw in p_low
            for kw in (
                "fix", "edit", "rewrite", "change", "type", "write", "solve",
                "answer", "fill", "click", "update", "add to", "act on",
            )
        )
    )

    if wants_action:
        prompt = (
            f"You are JARVIS observing Akul's live laptop screen.\n"
            f"Active Window Title: '{active_title}'\n"
            f"User Command: {user_prompt}\n\n"
            "Analyze the screen and return a JSON object with:\n"
            "{\n"
            '  "commentary": "2-sentence sharp, natural spoken summary of what you see and what change you are making",\n'
            '  "action_type": "paste_text" | "edit_file" | "click_element" | "none",\n'
            '  "text_to_type": "If user wants you to write/fix/solve/reply on screen, put the complete humanized text/solution here",\n'
            '  "file_name": "If editing an open file visible in the titlebar, put its filename here",\n'
            '  "edit_instruction": "Instruction for modifying the file",\n'
            '  "target_element": "Button or UI control name if clicking"\n'
            "}"
        )
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt,
            ],
        )
        raw = (resp.text or "").strip() if resp else ""
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                spec = json.loads(m.group(0))
                comment = spec.get("commentary", "Observed your screen and executed the update, sir.")
                act_res = _execute_screen_action(spec, active_title)
                if act_res:
                    return f"{comment} [{act_res}]"
                return comment
            except Exception:
                pass

    prompt = (
        f"You are JARVIS, Akul's sharp, witty, perceptive AI partner.\n"
        f"Source captured: {source_type.upper()} "
        f"({'Webcam photo of Akul/surroundings' if source_type == 'camera' else f'Live laptop screen — Active window: {active_title}'}).\n"
        f"User's request: {user_prompt or 'Look at this and give me your observation.'}\n\n"
        f"Instructions:\n"
        f"1. Observe the exact visual details (if webcam: expression, posture, objects, lighting; if screen: open document, slides, video timeline, code, or data).\n"
        f"2. Speak naturally with dry British wit, warmth, and crisp clarity — no robotic lists or clichés.\n"
        f"3. Keep it to 2–3 sentences unless the user asked for a deep breakdown."
    )

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt,
        ],
    )
    comment = (resp.text or "").strip() if resp else "Captured and analyzed, sir."
    if saved_path:
        return f"{comment} (Saved to {saved_path.name})"
    return comment


def screen_process(
    parameters: dict,
    response: str | None = None,
    player=None,
    session_memory=None,
    live_session=None,
    live_loop=None,
) -> str:
    params = parameters or {}
    user_text = (
        params.get("text")
        or params.get("user_text")
        or params.get("prompt")
        or "Observe this and tell me what you see"
    ).strip()
    raw_angle = (params.get("angle") or "").lower().strip()
    act_flag = bool(params.get("act", False) or params.get("act_on_screen", False))

    t_low = user_text.lower()
    camera_keywords = (
        "picture", "photo", "selfie", "camera", "webcam",
        "look at me", "holding", "wearing", "my face", "take a snap",
    )
    screen_keywords = (
        "screen", "screenshot", "window", "display", "monitor",
        "desktop", "code", "document", "slide", "ppt", "video",
    )

    if raw_angle == "camera":
        use_camera = True
    elif raw_angle == "screen" and not any(k in t_low for k in ("picture", "photo", "selfie", "camera", "webcam", "look at me")):
        if "take a snap" in t_low and not any(sk in t_low for sk in screen_keywords):
            use_camera = True
        else:
            use_camera = False
    elif any(k in t_low for k in camera_keywords) and not any(sk in t_low for sk in screen_keywords):
        use_camera = True
    else:
        use_camera = False

    if player and hasattr(player, "write_log"):
        player.write_log(f"VISION // {'CAMERA SNAP' if use_camera else 'SCREEN OBSERVATION'}...")

    saved_path = None
    source_used = "camera" if use_camera else "screen"
    try:
        if use_camera:
            try:
                image_bytes, saved_path = capture_camera_photo(save_to_disk=True)
            except Exception as cam_err:
                print(f"[Vision] Camera unavailable ({cam_err}), falling back to screen capture.")
                image_bytes, saved_path = capture_screenshot(save_to_disk=True)
                source_used = "screen"
        else:
            image_bytes, saved_path = capture_screenshot(save_to_disk=True)
    except Exception as e:
        err_msg = f"Could not capture visual feed, sir: {e}"
        if player and hasattr(player, "write_log"):
            player.write_log(f"ERR: {err_msg}")
        return err_msg

    # Stream frame into active Gemini Live session so JARVIS maintains continuous visual memory
    if live_session is not None and live_loop is not None:
        try:
            import asyncio
            asyncio.run_coroutine_threadsafe(
                live_session.send_realtime_input(
                    media={"data": image_bytes, "mime_type": "image/jpeg"}
                ),
                live_loop,
            )
        except Exception:
            pass

    try:
        commentary = analyze_image_with_commentary(
            image_bytes=image_bytes,
            user_prompt=user_text,
            source_type=source_used,
            saved_path=saved_path,
            act_on_screen=act_flag,
        )
        if player and hasattr(player, "write_log"):
            player.write_log(f"VISION // {commentary[:90]}")
        return commentary
    except Exception as e:
        if saved_path:
            return f"Captured to {saved_path}, sir, though analysis encountered an error: {e}"
        return f"Visual analysis error: {e}"


def warmup_session(player=None):
    pass
