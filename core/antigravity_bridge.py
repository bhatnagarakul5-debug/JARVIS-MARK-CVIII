"""
core/antigravity_bridge.py — Antigravity IDE & AI Workspace Bridge for J.A.R.V.I.S. Mark 108 (Sovereign Core)
Enables full 2-way telemetry, workspace opening, artifact reading, and live prompt dispatch
between JARVIS and the Antigravity AI pair programmer IDE.
"""

import os
import time
import json
import subprocess
from pathlib import Path

ANTIGRAVITY_ROOT = Path.home() / ".gemini" / "antigravity"
ANTIGRAVITY_BRAIN_ROOT = ANTIGRAVITY_ROOT / "brain"
ANTIGRAVITY_SCRATCH_ROOT = ANTIGRAVITY_ROOT / "scratch"

ANTIGRAVITY_EXE_PATHS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Antigravity" / "Antigravity.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Antigravity" / "bin" / "antigravity.cmd",
]


def get_active_brain_dir() -> Path:
    """Dynamically locates the most recently modified conversation folder in ~/.gemini/antigravity/brain."""
    try:
        if ANTIGRAVITY_BRAIN_ROOT.exists():
            dirs = [d for d in ANTIGRAVITY_BRAIN_ROOT.iterdir() if d.is_dir()]
            if dirs:
                dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
                return dirs[0]
    except Exception:
        pass
    return ANTIGRAVITY_BRAIN_ROOT / "2ac064e2-e6a5-4cd8-b1c5-5245c8e6619e"


def _find_antigravity_exe() -> Path | None:
    for p in ANTIGRAVITY_EXE_PATHS:
        if p.exists():
            return p
    return None


def get_antigravity_status() -> str:
    """Reads live implementation plan, walkthrough, and artifact telemetry from the active Antigravity IDE session."""
    try:
        brain_dir = get_active_brain_dir()
        status_parts = [f"Antigravity IDE Live Bridge (Session `{brain_dir.name[:8]}...`):"]

        if brain_dir.exists():
            artifacts = [
                f.name for f in brain_dir.iterdir()
                if f.is_file() and f.suffix.lower() in (".md", ".html", ".json")
            ]
            if artifacts:
                status_parts.append(f"• Active Artifacts ({len(artifacts)}): {', '.join(artifacts[:8])}")

            plan_file = brain_dir / "implementation_plan.md"
            walkthrough_file = brain_dir / "walkthrough.md"

            if plan_file.exists():
                plan_text = plan_file.read_text(encoding="utf-8", errors="ignore")
                lines = [l.strip() for l in plan_text.splitlines() if l.strip() and not l.startswith("---")]
                first_few = " ".join(lines[:4])
                status_parts.append(f"• Active Plan: {first_few[:240]}...")

            if walkthrough_file.exists():
                wt_text = walkthrough_file.read_text(encoding="utf-8", errors="ignore")
                wt_lines = [l.strip() for l in wt_text.splitlines() if l.strip() and not l.startswith("---")]
                first_wt = " ".join(wt_lines[:4])
                status_parts.append(f"• Recent Walkthrough: {first_wt[:240]}...")

        exe = _find_antigravity_exe()
        if exe:
            status_parts.append(f"• Binary: `{exe.name}` installed and ready.")

        return "\n".join(status_parts)
    except Exception as e:
        return f"Antigravity Bridge status notice: {e}"


def read_antigravity_artifact(artifact_name: str) -> str:
    """Reads the contents of an artifact file from the active Antigravity brain directory."""
    try:
        brain_dir = get_active_brain_dir()
        if not artifact_name.endswith((".md", ".html", ".json", ".txt")):
            for ext in (".md", ".html", ".json"):
                cand = brain_dir / f"{artifact_name}{ext}"
                if cand.exists():
                    artifact_name = cand.name
                    break
        target = (brain_dir / artifact_name).resolve()
        if not str(target).startswith(str(ANTIGRAVITY_ROOT.resolve())):
            return "Access restricted to Antigravity directory."
        if not target.exists():
            return f"Artifact '{artifact_name}' not found in session {brain_dir.name[:8]}."
        text = target.read_text(encoding="utf-8", errors="ignore")
        return text[:3000]
    except Exception as e:
        return f"Error reading Antigravity artifact: {e}"


def open_in_antigravity(target_path: str = "") -> str:
    """Launches Antigravity IDE or opens a specific file/workspace path inside Antigravity."""
    try:
        exe = _find_antigravity_exe()
        if not exe:
            return "Antigravity executable not found in LocalAppData."
        cmd = [str(exe)]
        if target_path:
            p = Path(target_path).expanduser()
            if p.exists():
                cmd.append(str(p.resolve()))
            else:
                cmd.append(target_path)
        creationflags = 0x08000000 if os.name == "nt" else 0
        subprocess.Popen(cmd, creationflags=creationflags, close_fds=True)
        return f"Opened Antigravity IDE{f' with {target_path}' if target_path else ''}."
    except Exception as e:
        return f"Failed to launch Antigravity IDE: {e}"


def dispatch_task_to_ide(instruction: str, paste_to_window: bool = False) -> str:
    """
    Dispatches a task instruction to the active Antigravity IDE workspace queue
    and optionally copies/pastes it into the live Antigravity window.
    """
    try:
        brain_dir = get_active_brain_dir()
        scratch_dir = brain_dir / "scratch"
        scratch_dir.mkdir(parents=True, exist_ok=True)

        queue_file = scratch_dir / "agent_instruction.json"
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sender": "JARVIS Mark 108",
            "instruction": instruction,
        }
        queue_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        try:
            import pyperclip
            pyperclip.copy(instruction)
        except Exception:
            pass

        if paste_to_window:
            try:
                import pygetwindow as gw
                import pyautogui
                wins = [w for w in gw.getAllWindows() if w.title and "antigravity" in w.title.lower()]
                if wins:
                    win = wins[0]
                    if win.isMinimized:
                        win.restore()
                    win.activate()
                    time.sleep(0.35)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.1)
                    pyautogui.press("enter")
                    return f"Dispatched and submitted prompt directly into Antigravity IDE: '{instruction}'"
            except Exception:
                pass

        return f"Dispatched task to Antigravity IDE (and copied to clipboard): '{instruction}'"
    except Exception as e:
        return f"Could not dispatch task to Antigravity IDE: {e}"
