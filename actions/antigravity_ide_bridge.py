"""
actions/antigravity_ide_bridge.py — Antigravity IDE Action Bridge for JARVIS Mark 108
Enables JARVIS voice chat, text bar, and Telegram commands to inspect Antigravity IDE status,
read artifacts, open folders/files in Antigravity, and dispatch coding prompts directly into Antigravity.
"""

from core.antigravity_bridge import (
    get_antigravity_status,
    dispatch_task_to_ide,
    open_in_antigravity,
    read_antigravity_artifact,
)


def antigravity_ide_control(parameters: dict, player=None) -> str:
    """
    Action handler for Antigravity IDE Bridge.

    parameters:
        action   : status | dispatch | prompt | open | read_artifact | plan
        task     : Instruction or prompt to send to Antigravity IDE
        path     : File or workspace path to open in Antigravity IDE
        artifact : Artifact filename to read from active Antigravity session
        paste    : Bool — if True, focuses Antigravity window and pastes/submits the prompt
    """
    params = parameters or {}
    action = (params.get("action") or "status").lower().strip()
    task = (params.get("task") or params.get("instruction") or params.get("query") or params.get("prompt") or "").strip()
    target_path = (params.get("path") or params.get("file_path") or "").strip()
    artifact = (params.get("artifact") or "").strip()
    paste = bool(params.get("paste", False))

    if action in ("open", "launch", "start"):
        res = open_in_antigravity(target_path or task)
        if player and hasattr(player, "write_log"):
            player.write_log(f"AGY: {res}")
        return res

    if action in ("read", "read_artifact", "artifact") or artifact:
        res = read_antigravity_artifact(artifact or task or "implementation_plan.md")
        if player and hasattr(player, "write_log"):
            player.write_log(f"AGY: Read artifact {artifact or task}")
        return res

    if action in ("status", "plan", "walkthrough", "check") and not task:
        res = get_antigravity_status()
        if player and hasattr(player, "write_log"):
            player.write_log("AGY: Fetched live workspace status.")
        return res

    if action in ("dispatch", "send", "run", "prompt", "type") or task:
        if not task:
            task = action
        res = dispatch_task_to_ide(task, paste_to_window=(paste or action in ("prompt", "type")))
        if player and hasattr(player, "write_log"):
            player.write_log(f"AGY: Dispatched '{task[:38]}'")
        return res

    return get_antigravity_status()
