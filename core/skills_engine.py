"""
core/skills_engine.py — J.A.R.V.I.S. Mark 78 (Alpha Core) Dynamic Skills Engine
Dynamically creates, discovers, loads, registers, reloads, and executes action skill modules at runtime.
"""

import os
import re
import sys
import json
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
ACTIONS_DIR = BASE_DIR / "actions"

_PROTECTED_CORE_SKILLS = {
    "agent_desktop", "anti_shoulder_surfer", "antigravity_coder", "antigravity_ide_bridge",
    "archive_intel", "audio_device_manager", "auto_video_editor", "browser_control",
    "calendar_manager", "call_manager", "camera_system", "clipboard_manager", "code_helper",
    "college_hub", "computer_control", "computer_settings", "cooldown_protocol",
    "daily_briefing", "davinci_advanced", "davinci_control", "desktop", "dev_agent",
    "document_chat", "email_compose", "email_triage", "exam_companion", "file_controller",
    "file_generator", "file_processor", "file_watcher", "flight_finder", "focus_mode",
    "game_updater", "ghost_protocol", "make_call", "news_intel", "open_app",
    "personality_engine", "presentation_designer", "project_autopilot", "reminder",
    "remote_bridge", "research_assistant", "scheduler", "screen_processor", "search_memory",
    "security_footage", "security_shield", "self_edit", "send_message", "smart_reply",
    "spotify_control", "stunt_bridge", "system_diagnostics", "system_monitor",
    "tab_manager", "voice_macros", "war_mode", "weather_report", "web_search",
    "whatsapp_connector", "whatsapp_reader", "youtube_video",
}


def _sanitize_skill_name(raw_name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", (raw_name or "").strip().lower().replace(".py", ""))
    clean = re.sub(r"_+", "_", clean).strip("_")
    if not clean or clean[0].isdigit():
        clean = f"custom_{clean or 'skill'}"
    return clean


def _clean_generated_code(text: str) -> str:
    text = (text or "").strip()
    if "```" in text:
        m = re.search(r"```[a-zA-Z0-9_+-]*\r?\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    text = re.sub(r"^```[a-zA-Z0-9_+-]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```$", "", text)
    return text.strip()


class SkillsEngine:
    """Singleton manager for dynamic action skill creation, discovery, registration, reloading, and execution."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.loaded_skills = {}
            cls._instance.discover_skills()
        return cls._instance

    def discover_skills(self, inspect_functions: bool = False) -> dict:
        """
        Discovers all valid python action modules in actions/ directory.
        Defaults to lightweight metadata scanning (0 RAM/CPU import overhead at startup).
        Full module import only happens on reload_skill, create_skill, run_skill, or when inspect_functions=True.
        """
        if not ACTIONS_DIR.exists():
            return self.loaded_skills

        sys_path = str(ACTIONS_DIR)
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)

        for file_path in ACTIONS_DIR.glob("*.py"):
            if file_path.name.startswith("_") or file_path.name == "setup.py":
                continue
            stem = file_path.stem
            if not inspect_functions and stem in self.loaded_skills:
                continue
            if not inspect_functions:
                self.loaded_skills[stem] = {
                    "module": None,
                    "functions": [stem],
                    "path": str(file_path)
                }
                continue
            module_name = f"actions.{stem}"
            try:
                mod = importlib.import_module(module_name)
                funcs = [name for name, obj in inspect.getmembers(mod, inspect.isfunction) if not name.startswith("_")]
                self.loaded_skills[stem] = {
                    "module": mod,
                    "functions": funcs,
                    "path": str(file_path)
                }
            except Exception as e:
                print(f"[SkillsEngine] Warning loading {module_name}: {e}")

        return self.loaded_skills

    def reload_skill(self, skill_name: str) -> str:
        """Reloads a specific skill module dynamically at runtime."""
        skill_name = _sanitize_skill_name(skill_name)
        module_key = f"actions.{skill_name}"
        if skill_name in self.loaded_skills and self.loaded_skills[skill_name].get("module") is not None:
            try:
                mod = self.loaded_skills[skill_name]["module"]
                reloaded = importlib.reload(mod)
                funcs = [name for name, obj in inspect.getmembers(reloaded, inspect.isfunction) if not name.startswith("_")]
                self.loaded_skills[skill_name] = {
                    "module": reloaded,
                    "functions": funcs,
                    "path": self.loaded_skills[skill_name]["path"]
                }
                return f"Mark 78 Apex Engine: Skill '{skill_name}' successfully reloaded at runtime ({len(funcs)} exported functions)."
            except Exception as e:
                return f"Failed to reload skill '{skill_name}': {e}"
        else:
            try:
                mod = importlib.import_module(module_key)
                mod = importlib.reload(mod)
                funcs = [name for name, obj in inspect.getmembers(mod, inspect.isfunction) if not name.startswith("_")]
                self.loaded_skills[skill_name] = {
                    "module": mod,
                    "functions": funcs,
                    "path": str(ACTIONS_DIR / f"{skill_name}.py")
                }
                return f"Mark 78 Apex Engine: Skill '{skill_name}' dynamically loaded ({len(funcs)} functions: {', '.join(funcs[:5])})!"
            except Exception as e:
                return f"Skill '{skill_name}' not found or invalid: {e}"

    def create_skill(self, skill_name: str, description: str, custom_code: str = "", player=None) -> str:
        """
        Autonomously authors, AST-verifies, saves, and hot-loads a new Python action skill in actions/<skill_name>.py.
        """
        clean_name = _sanitize_skill_name(skill_name or description[:30])
        if clean_name in _PROTECTED_CORE_SKILLS:
            clean_name = f"custom_{clean_name}"

        target_path = ACTIONS_DIR / f"{clean_name}.py"
        if player and hasattr(player, "write_log"):
            player.write_log(f"SKILLS ENGINE: Synthesizing new skill '{clean_name}'...")

        code_to_write = (custom_code or "").strip()
        if not code_to_write:
            try:
                from core.ai_client import generate_text_with_retry
                prompt = f"""You are the J.A.R.V.I.S. Mark 78 Skill Architect.
Write a complete, self-contained, production-ready Python action skill module for `actions/{clean_name}.py`.

Skill Name: `{clean_name}`
Task / Capability Description: {description}

CRITICAL REQUIREMENTS:
1. Output ONLY valid Python code (no markdown fences, no commentary).
2. Must define a main entrypoint function with this exact signature:
   `def {clean_name}(parameters: dict = None, player=None) -> str:`
3. Inside `{clean_name}(parameters, player)`:
   - Safely parse `params = parameters or {{}}`
   - Implement the requested capability using Python standard library (`os`, `sys`, `json`, `urllib.request`, `datetime`, `pathlib`, `subprocess`, `psutil`, etc.) or `core.ai_client.generate_text_with_retry` if AI reasoning is needed.
   - Wrap logic in `try...except Exception as e:` and return a clear, informative `str` summary of the result.
4. Do NOT use external packages that might not be installed without a try/except fallback.
"""
                raw = generate_text_with_retry(prompt)
                code_to_write = _clean_generated_code(raw)
            except Exception:
                code_to_write = ""

        # Verify syntax and entrypoint; fall back to deterministic template if AI output is invalid
        valid_syntax = False
        if code_to_write and f"def {clean_name}" in code_to_write:
            try:
                compile(code_to_write, f"{clean_name}.py", "exec")
                valid_syntax = True
            except SyntaxError:
                valid_syntax = False

        if not valid_syntax:
            safe_desc = (description or clean_name).replace('"""', "'''")
            code_to_write = f'''"""
actions/{clean_name}.py — Custom J.A.R.V.I.S. Mark 78 Skill Module
Capability: {safe_desc}
"""

from datetime import datetime
from typing import Dict, Any
from core.ai_client import generate_text_with_retry


def {clean_name}(parameters: Dict[str, Any] = None, player=None) -> str:
    """
    Dynamic skill entrypoint for: {safe_desc}
    """
    params = parameters or {{}}
    query = params.get("query") or params.get("input") or params.get("topic") or "{safe_desc}"
    if player and hasattr(player, "write_log"):
        player.write_log(f"SKILL [{clean_name}]: Executing...")
    try:
        prompt = (
            f"You are executing the J.A.R.V.I.S. skill '{clean_name}' ({{'{safe_desc}'}}).\\n"
            f"Input parameters: {{params}}\\n"
            f"Query/Task: {{query}}\\n"
            "Provide a concise, accurate, directly actionable result."
        )
        res = generate_text_with_retry(prompt)
        return f"[{clean_name}] {{res}}"
    except Exception as e:
        return f"[{clean_name}] Execution error: {{e}}"
'''

        ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
        target_path.write_text(code_to_write, encoding="utf-8")

        load_msg = self.reload_skill(clean_name)
        if player and hasattr(player, "write_log"):
            player.write_log(f"SKILLS ENGINE: Skill '{clean_name}' created & hot-loaded.")

        return (
            f"Skill '{clean_name}' created, syntax-verified, and hot-loaded at `{target_path}`.\n"
            f"Status: {load_msg}\n"
            f"You can invoke it anytime via `mark_58_control(action='run_skill', skill_name='{clean_name}')`."
        )

    def run_skill(self, skill_name: str, skill_args: Optional[dict] = None, player=None) -> str:
        """Dynamically executes a skill module in actions/<skill_name>.py at runtime."""
        clean_name = _sanitize_skill_name(skill_name)
        target_path = ACTIONS_DIR / f"{clean_name}.py"
        if not target_path.exists():
            return f"Skill '{clean_name}' does not exist in `actions/`. Use `action='create_skill'` to create it first."

        if clean_name not in self.loaded_skills or self.loaded_skills[clean_name].get("module") is None:
            self.reload_skill(clean_name)

        entry = self.loaded_skills.get(clean_name, {})
        mod = entry.get("module")
        if mod is None:
            return f"Skill '{clean_name}' could not be imported."

        fn = getattr(mod, clean_name, None)
        if not callable(fn):
            # Fallback to first public function defined in the module
            for fname in entry.get("functions", []):
                cand = getattr(mod, fname, None)
                if callable(cand):
                    fn = cand
                    break

        if not callable(fn):
            return f"Skill '{clean_name}' has no callable entrypoint function."

        try:
            sig = inspect.signature(fn)
            kwargs = {}
            if "parameters" in sig.parameters:
                kwargs["parameters"] = skill_args or {}
            if "player" in sig.parameters:
                kwargs["player"] = player
            if kwargs:
                res = fn(**kwargs)
            elif len(sig.parameters) >= 1:
                res = fn(skill_args or {})
            else:
                res = fn()
            return str(res)
        except Exception as e:
            return f"Error running skill '{clean_name}': {e}"

    def list_skills(self) -> str:
        """Lists all active loaded skills and their exported functions."""
        self.discover_skills()
        lines = [f"=== J.A.R.V.I.S. Mark 78 Active Skill Modules ({len(self.loaded_skills)}) ==="]
        for name, data in sorted(self.loaded_skills.items()):
            fn_count = len(data['functions'])
            tag = "[CORE]" if name in _PROTECTED_CORE_SKILLS else "[CUSTOM]"
            lines.append(f"• {name.ljust(24)} {tag} ({fn_count} fn)")
        return "\n".join(lines)


skills_engine = SkillsEngine()


def mark_58_skills_control(parameters: dict, player=None) -> str:
    """Action handler for Mark 78 Alpha Core Dynamic Skills Control."""
    params = parameters or {}
    action = (params.get("action") or "list").lower().strip()
    skill_name = (params.get("skill_name") or params.get("name") or "").strip()
    description = (params.get("description") or params.get("prompt") or params.get("task") or "").strip()
    custom_code = (params.get("code") or "").strip()
    skill_args = params.get("skill_args") or params.get("args") or {}
    if isinstance(skill_args, str):
        try:
            skill_args = json.loads(skill_args)
        except Exception:
            skill_args = {"query": skill_args}

    if action in ("create", "create_skill", "make", "make_skill", "new_skill", "build_skill"):
        if not skill_name and not description:
            return "Please provide a 'skill_name' and 'description' to create a new skill."
        return skills_engine.create_skill(skill_name or description[:25], description or skill_name, custom_code=custom_code, player=player)

    if action in ("run", "run_skill", "execute", "execute_skill", "invoke"):
        if not skill_name:
            return "Please specify 'skill_name' to execute."
        return skills_engine.run_skill(skill_name, skill_args=skill_args, player=player)

    if action in ("reload", "reload_skills", "refresh", "load"):
        if not skill_name:
            return skills_engine.list_skills()
        return skills_engine.reload_skill(skill_name)

    return skills_engine.list_skills()


# Backward compatibility aliases
mark_41_skills_control = mark_58_skills_control
mark_45_skills_control = mark_58_skills_control
