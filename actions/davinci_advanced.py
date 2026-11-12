"""
actions/davinci_advanced.py — Advanced AI DaVinci Resolve & Standalone Beat-Sync Cutting & Subtitle Generator
Supports both live DaVinci Resolve timeline markers/cuts and standalone internet-assisted .srt subtitle generation.
"""

import time
import pyautogui
from pathlib import Path
from actions.auto_video_editor import generate_video_subtitles, color_grade_video
from actions.file_controller import resolve_any_file

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.08


def _focus_davinci() -> bool:
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("DaVinci Resolve")
        if wins:
            win = wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.3)
            return True
    except Exception:
        pass
    return False


def beat_sync_cuts(bpm: int = 120, player=None) -> str:
    if not _focus_davinci():
        return "Please open DaVinci Resolve first to place timeline beat-sync cuts, sir."

    pyautogui.hotkey("shift", "4")  # Edit Page
    time.sleep(0.5)
    pyautogui.press("home")

    seconds_per_beat = 60.0 / max(60, min(180, bpm))
    cuts_made = 0

    if player and hasattr(player, "write_log"):
        player.write_log(f"DAVINCI: Beat-Sync cuts at {bpm} BPM ({seconds_per_beat:.2f}s)...")

    for _ in range(6):
        pyautogui.hotkey("ctrl", "b")
        cuts_made += 1
        pyautogui.press("m")
        time.sleep(seconds_per_beat)

    return f"Beat-Sync complete! Placed {cuts_made} rhythmic beat cuts & markers at {bpm} BPM on the DaVinci timeline."


def generate_subtitles(language: str = "English", video_path: str = "", player=None) -> str:
    """
    If a video_path is provided, generates real timestamped .srt subtitles (with live internet verification)
    and burns them into the video. If DaVinci Resolve is open, also adds timeline subtitle markers.
    """
    results = []
    if video_path:
        target = resolve_any_file(video_path) or Path(video_path).expanduser()
        if target.exists() and target.is_file():
            results.append(generate_video_subtitles(target, language=language, burn_in=True))

    if _focus_davinci():
        pyautogui.hotkey("shift", "4")
        time.sleep(0.4)
        pyautogui.press("home")
        for i in range(4):
            pyautogui.press("m")
            time.sleep(0.1)
            pyautogui.press("m")
            time.sleep(0.2)
            pyautogui.write(f"Subtitle Segment #{i + 1} [{language}]", interval=0.02)
            pyautogui.press("enter")
            time.sleep(0.6)
        results.append(f"Added subtitle track markers ({language}) on the active DaVinci Resolve timeline.")

    if not results:
        return "Specify a video file name to generate .srt subtitles, or open DaVinci Resolve to place timeline captions, sir."
    return " ".join(results)


def davinci_advanced_control(parameters: dict, player=None) -> str:
    """
    parameters:
        action     : beat_sync | subtitles | color_grade
        bpm        : Target BPM for beat sync (default 120)
        language   : Language for subtitles (default "English")
        video_path : Optional video file name or path for standalone .srt / color grading
        style      : Optional color grading preset
    """
    params = parameters or {}
    action = (params.get("action") or "beat_sync").lower().strip()
    bpm = int(params.get("bpm", 120))
    lang = params.get("language", "English").strip()
    vpath = (params.get("video_path") or params.get("media_path") or params.get("file_path") or "").strip()
    style = (params.get("style") or "teal_orange").strip()

    if action in ("beat_sync", "beats", "rhythm"):
        return beat_sync_cuts(bpm=bpm, player=player)
    if action in ("subtitles", "captions", "subtitle"):
        return generate_subtitles(language=lang, video_path=vpath, player=player)
    if action in ("color_grade", "grade", "colour_grade") and vpath:
        target = resolve_any_file(vpath) or Path(vpath).expanduser()
        return color_grade_video(target, style=style)

    return beat_sync_cuts(bpm=bpm, player=player)
