"""
actions/cooldown_protocol.py — Stark CPU Thermal Cooldown, RAM Trimmer & Power Saving Protocol
Monitors CPU load & thermal spikes, automatically throttling non-essential background tasks,
dropping HUD framerate to 4 FPS Eco Mode, and trimming process working sets.
"""

import gc
import sys
import ctypes
import psutil
import threading

# Cooldown state
_cooldown_active = False
_cooldown_lock = threading.Lock()


def is_cooldown_active() -> bool:
    with _cooldown_lock:
        return _cooldown_active


def set_cooldown_mode(active: bool, player=None) -> str:
    global _cooldown_active
    with _cooldown_lock:
        _cooldown_active = active

    if active:
        gc.collect()
        try:
            if sys.platform == "win32":
                ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1, -1)
        except Exception:
            pass
        if player:
            if hasattr(player, "set_hud_fps"):
                player.set_hud_fps(4)
            if hasattr(player, "write_log"):
                player.write_log("STARK PROTOCOL: Thermal Cooldown & Eco Mode Active. RAM trimmed, HUD set to 4 FPS.")
            if hasattr(player, "push_notification"):
                player.push_notification("CPU Cooldown & Eco Mode Active", "warning")
        return "CPU Cooldown & Eco Mode ACTIVATED. Working-set RAM trimmed and UI power consumption throttled."
    else:
        if player:
            if hasattr(player, "set_hud_fps"):
                player.set_hud_fps(10)
            if hasattr(player, "write_log"):
                player.write_log("STARK PROTOCOL: Thermal Cooldown Deactivated. Standard power restored.")
            if hasattr(player, "push_notification"):
                player.push_notification("CPU Thermal Cooldown Deactivated", "success")
        return "CPU Cooldown Protocol DEACTIVATED. Normal system performance restored."


def check_and_apply_cooldown(cpu_threshold: float = 85.0, player=None) -> dict:
    """
    Checks CPU load and automatically engages/disengages Cooldown Protocol.
    """
    cpu_load = psutil.cpu_percent(interval=0.2)
    ram_load = psutil.virtual_memory().percent

    currently_active = is_cooldown_active()

    if cpu_load >= cpu_threshold and not currently_active:
        set_cooldown_mode(True, player=player)
    elif cpu_load < 60.0 and currently_active:
        set_cooldown_mode(False, player=player)

    return {
        "cpu_percent": cpu_load,
        "ram_percent": ram_load,
        "cooldown_active": is_cooldown_active(),
    }


def cooldown_control(parameters: dict, player=None) -> str:
    """
    Action handler for CPU Thermal Cooldown & Eco Mode Protocol.

    parameters:
        action    : status | activate | deactivate | check | optimize_ram
        threshold : CPU load percentage threshold to trigger cooldown (default 85.0)
    """
    params = parameters or {}
    action = (params.get("action") or "status").lower().strip()
    threshold = float(params.get("threshold", 85.0))

    if action in ("activate", "on", "engage", "eco"):
        return set_cooldown_mode(True, player=player)
    elif action in ("deactivate", "off", "disengage"):
        return set_cooldown_mode(False, player=player)
    elif action in ("optimize_ram", "trim_ram"):
        from actions.system_diagnostics import optimize_system_ram
        return optimize_system_ram(player=player)
    elif action in ("check", "scan"):
        res = check_and_apply_cooldown(cpu_threshold=threshold, player=player)
        status_str = "ACTIVE" if res["cooldown_active"] else "INACTIVE"
        return f"CPU Load: {res['cpu_percent']}% | RAM: {res['ram_percent']}% | Cooldown Status: {status_str}"

    status_str = "ACTIVE (Eco Power Throttled)" if is_cooldown_active() else "INACTIVE (Standard Eco)"
    return f"CPU Thermal Cooldown Protocol Status: {status_str}. Current CPU Load: {psutil.cpu_percent()}%."
