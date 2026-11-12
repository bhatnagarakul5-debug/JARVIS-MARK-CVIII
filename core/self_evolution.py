"""
core/self_evolution.py — Self-Coding & Self-Healing Engine for J.A.R.V.I.S. Mark 108

1. SELF-CODING (acquire_capability):
   - skill     : When JARVIS lacks a capability, he writes a new Python skill module himself.
                 Engines: Antigravity CLI (`agy -p`, headless), then Gemini fallback.
                 Optional 'antigravity_ide' engine dispatches the task to the live Antigravity IDE window.
   - knowledge : Researches a topic and stores it as persistent knowledge (memory/knowledge/*.md),
                 injected into JARVIS's system prompt on every session.
   - character : Designs a new persona/character and registers it with the personality engine.

2. SELF-HEALING (heal_module):
   - When a skill/tool crashes, the traceback is sent to the AI, which patches the faulty module.
   - Safety rails: timestamped backup, AST compile check, public-function preservation,
     truncation guard, protected security modules are never touched, automatic rollback.
"""

import os
import re
import sys
import json
import time
import shutil
import importlib
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
ACTIONS_DIR = BASE_DIR / "actions"
BACKUP_DIR = BASE_DIR / ".backups"
KNOWLEDGE_DIR = BASE_DIR / "memory" / "knowledge"
KNOWLEDGE_INDEX = KNOWLEDGE_DIR / "index.json"
SKILL_REGISTRY = BASE_DIR / "config" / "skill_registry.json"
CUSTOM_PERSONAS = BASE_DIR / "config" / "custom_personas.json"
HEAL_LOG = BASE_DIR / "memory" / "self_heal.log"

# Modules that guard security, credentials, or file-system boundaries are NEVER auto-patched.
HEAL_PROTECTED = {
    "self_edit", "security_shield", "remote_bridge", "anti_shoulder_surfer",
    "file_controller", "security_footage", "send_message", "whatsapp_reader",
    "email_compose", "make_call", "call_manager",
}


# ====================================================================
# Helpers
# ====================================================================

def _log(player, msg: str):
    try:
        if player and hasattr(player, "write_log"):
            player.write_log(msg)
    except Exception:
        pass


def _slug(raw: str, default: str = "item") -> str:
    from core.rust_bridge import slugify_identifier
    return slugify_identifier(raw or "", default_val=default, max_len=48)


def _read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _clean_code(text: str) -> str:
    from core.rust_bridge import strip_markdown_fences
    return strip_markdown_fences(text or "")


def _ai(prompt: str) -> str:
    from core.ai_client import generate_text_with_retry
    return generate_text_with_retry(prompt)


def _public_defs(code: str) -> set:
    from core.rust_bridge import extract_public_defs
    return set(extract_public_defs(code or ""))


def _find_agy() -> Optional[str]:
    cand = shutil.which("agy") or shutil.which("agy.exe")
    if cand:
        return cand
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"
    return str(local) if local.exists() else None


# ====================================================================
# Skill registry (custom self-coded skills)
# ====================================================================

def load_skill_registry() -> Dict[str, Any]:
    return _read_json(SKILL_REGISTRY, {})


def register_skill(name: str, description: str, engine: str):
    reg = load_skill_registry()
    reg[name] = {
        "description": (description or name)[:400],
        "engine": engine,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "path": f"actions/{name}.py",
    }
    _write_json(SKILL_REGISTRY, reg)


def custom_skill_declarations(existing_names: set) -> list:
    """Native Gemini function declarations for every self-coded skill (picked up on each (re)connect)."""
    decls = []
    for name, meta in load_skill_registry().items():
        if name in existing_names or not (ACTIONS_DIR / f"{name}.py").exists():
            continue
        decls.append({
            "name": name,
            "description": f"[Self-coded skill] {meta.get('description', name)}",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query":     {"type": "STRING", "description": "Main input / question / target for the skill"},
                    "args_json": {"type": "STRING", "description": "Optional extra arguments as a JSON object string"},
                },
                "required": [],
            },
        })
    return decls


# ====================================================================
# 1. SELF-CODING: SKILLS
# ====================================================================

def _skill_spec(name: str, description: str) -> str:
    return (
        f"Create the file `actions/{name}.py` in this J.A.R.V.I.S. Python project.\n"
        f"Capability required: {description}\n\n"
        "Requirements:\n"
        f"1. Define the entrypoint `def {name}(parameters: dict = None, player=None) -> str:`.\n"
        "2. Read inputs from `params = parameters or {}` (common keys: 'query', plus any task-specific keys).\n"
        "3. Prefer the Python standard library. Any third-party import must be inside try/except with a graceful fallback.\n"
        "4. If AI reasoning is needed, use `from core.ai_client import generate_text_with_retry` (takes a prompt string, returns text).\n"
        "5. Wrap the logic in try/except and ALWAYS return a clear, human-readable result string.\n"
        "6. No destructive actions (deleting files, killing processes, changing system settings) unless the capability explicitly demands it.\n"
        "7. Do not modify any other file in the project."
    )


def _verify_skill_file(name: str) -> Tuple[bool, str]:
    path = ACTIONS_DIR / f"{name}.py"
    if not path.exists():
        return False, "file was not created"
    code = path.read_text(encoding="utf-8", errors="ignore")
    try:
        compile(code, path.name, "exec")
    except SyntaxError as e:
        return False, f"syntax error: {e}"
    if f"def {name}" not in code:
        return False, "entrypoint function missing"
    return True, "ok"


def _code_skill_with_antigravity_cli(name: str, description: str, player=None, timeout_s: int = 300) -> Tuple[bool, str]:
    agy = _find_agy()
    if not agy:
        return False, "Antigravity CLI not found"
    _log(player, f"SELF-CODE: Antigravity CLI is writing skill '{name}'...")
    prompt = _skill_spec(name, description) + "\nWrite the file now, then reply with a one-line summary."
    try:
        res = subprocess.run(
            [agy, "-p", prompt, "--mode", "accept-edits", "--sandbox",
             "--print-timeout", f"{timeout_s}s"],
            cwd=str(BASE_DIR), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout_s + 30,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        summary = (res.stdout or res.stderr or "").strip()[-400:]
    except subprocess.TimeoutExpired:
        summary = "timed out"
    except Exception as e:
        return False, f"Antigravity CLI error: {e}"
    ok, why = _verify_skill_file(name)
    return ok, (summary if ok else f"Antigravity output unusable ({why}). {summary[:160]}")


def acquire_skill(name: str, description: str, engine: str = "auto", player=None) -> str:
    from core.skills_engine import skills_engine, _PROTECTED_CORE_SKILLS
    name = _slug(name or description[:30], "custom_skill")
    if name in _PROTECTED_CORE_SKILLS:
        name = f"custom_{name}"
    path = ACTIONS_DIR / f"{name}.py"
    engine = (engine or "auto").lower().strip()

    if path.exists() and name in load_skill_registry():
        return f"I already have the '{name}' skill. Run it with self_evolve(action='run_skill', name='{name}')."

    # Live Antigravity IDE: hand the job to the visible IDE agent (asynchronous).
    if engine in ("antigravity_ide", "ide"):
        from core.antigravity_bridge import dispatch_task_to_ide
        register_skill(name, description, "antigravity_ide")
        msg = dispatch_task_to_ide(_skill_spec(name, description), paste_to_window=True)
        return (f"{msg}\nAntigravity IDE is now writing `actions/{name}.py`. Once it's done, say "
                f"'reload skill {name}' and I'll load it.")

    used = None
    detail = ""
    if engine in ("auto", "antigravity", "agy"):
        ok, detail = _code_skill_with_antigravity_cli(name, description, player)
        if ok:
            used = "antigravity_cli"
            skills_engine.reload_skill(name)
        elif engine in ("antigravity", "agy"):
            _log(player, f"SELF-CODE: Antigravity failed ({detail[:80]}); falling back to Gemini.")

    if used is None:
        _log(player, f"SELF-CODE: Gemini is writing skill '{name}'...")
        skills_engine.create_skill(name, description, player=player)
        ok, why = _verify_skill_file(name)
        if not ok:
            return f"Self-coding failed for '{name}': {why}."
        used = "gemini"

    register_skill(name, description, used)
    _log(player, f"SELF-CODE: Skill '{name}' acquired via {used}.")
    return (f"New skill acquired: '{name}' (written by {used.replace('_', ' ')}), saved to actions/{name}.py, "
            f"syntax-verified and hot-loaded. Use it now via self_evolve(action='run_skill', name='{name}', query='...'). "
            f"It becomes a native tool on the next reconnect.")


# ====================================================================
# 1b. SELF-CODING: KNOWLEDGE
# ====================================================================

def acquire_knowledge(topic: str, source_text: str = "", player=None) -> str:
    if not topic:
        return "Please specify what topic I should learn."
    slug = _slug(topic, "topic")
    _log(player, f"SELF-LEARN: Studying '{topic}'...")
    prompt = (
        f"You are building a permanent knowledge file for an AI assistant about: {topic}\n"
        + (f"Use this source material as the primary ground truth:\n{source_text[:12000]}\n\n" if source_text else "")
        + "Write accurate, dense Markdown: a 2-sentence summary first (prefixed 'SUMMARY:'), then key facts, "
          "definitions, numbers, procedures and common pitfalls. Flag anything uncertain. Max ~900 words."
    )
    body = _ai(prompt)
    if body.startswith("Service temporarily busy") or body.startswith("Gemini API key is missing"):
        return f"Couldn't learn '{topic}' right now: {body}"
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    (KNOWLEDGE_DIR / f"{slug}.md").write_text(f"# {topic}\n\n{body}\n", encoding="utf-8")

    m = re.search(r"SUMMARY:\s*(.+?)(?:\n\n|\n#|$)", body, re.DOTALL)
    summary = (m.group(1) if m else body[:300]).strip().replace("\n", " ")[:300]
    idx = _read_json(KNOWLEDGE_INDEX, {})
    idx[slug] = {"title": topic, "summary": summary, "learned": datetime.now().strftime("%Y-%m-%d %H:%M")}
    _write_json(KNOWLEDGE_INDEX, idx)
    return f"Learned '{topic}' and stored it permanently (memory/knowledge/{slug}.md). Summary: {summary}"


def recall_knowledge(topic: str) -> str:
    idx = _read_json(KNOWLEDGE_INDEX, {})
    slug = _slug(topic, "topic")
    if slug not in idx:
        words = set(slug.split("_"))
        scored = sorted(idx.keys(), key=lambda k: -len(words & set(k.split("_"))))
        if scored and words & set(scored[0].split("_")):
            slug = scored[0]
        else:
            return f"I have no stored knowledge on '{topic}'. Ask me to learn it."
    f = KNOWLEDGE_DIR / f"{slug}.md"
    return f.read_text(encoding="utf-8")[:6000] if f.exists() else f"Knowledge file for '{topic}' is missing."


def knowledge_prompt_block(max_items: int = 15) -> str:
    idx = _read_json(KNOWLEDGE_INDEX, {})
    if not idx:
        return ""
    items = sorted(idx.items(), key=lambda kv: kv[1].get("learned", ""), reverse=True)[:max_items]
    lines = ["[SELF-LEARNED KNOWLEDGE — call self_evolve(action='recall_knowledge', name=...) for full detail]"]
    for _, meta in items:
        lines.append(f"- {meta.get('title')}: {meta.get('summary', '')[:220]}")
    return "\n".join(lines) + "\n"


def skills_prompt_block() -> str:
    reg = load_skill_registry()
    if not reg:
        return ""
    lines = ["[SELF-CODED SKILLS — run via self_evolve(action='run_skill', name=..., query=...)]"]
    for name, meta in list(reg.items())[-25:]:
        lines.append(f"- {name}: {meta.get('description', '')[:160]}")
    return "\n".join(lines) + "\n"


# ====================================================================
# 1c. SELF-CODING: CHARACTER / PERSONA
# ====================================================================

def acquire_character(name: str, description: str, activate: bool = True, player=None) -> str:
    key = _slug(name or description[:24], "persona")
    _log(player, f"SELF-CODE: Designing character '{name or key}'...")
    raw = _ai(
        "Design a voice-assistant persona. Return ONLY JSON with keys: "
        "'name' (display name), 'address' (how it addresses the user, 1-2 words), "
        "'description' (120-220 words of behavioural instructions: tone, vocabulary, catchphrases, "
        "what it never does, and 1 example line). Keep it respectful to the user.\n"
        f"Character requested: {name}. Details: {description}"
    )
    try:
        cj = raw.strip()
        if "```" in cj:
            cj = _clean_code(cj)
        data = json.loads(cj[cj.find("{"): cj.rfind("}") + 1])
        assert data.get("description")
    except Exception:
        data = {"name": name or key.title(), "address": "sir",
                "description": f"You are {name}. {description}. Stay fully in character while remaining helpful."}

    personas = _read_json(CUSTOM_PERSONAS, {})
    personas[key] = {"name": data.get("name") or key.title(), "voice": "Charon",
                     "address": data.get("address") or "sir", "description": data["description"]}
    _write_json(CUSTOM_PERSONAS, personas)

    msg = f"Character '{personas[key]['name']}' created (key: {key})."
    if activate:
        from actions.personality_engine import set_personality
        msg += " " + set_personality({"mode": key}, player=player)
        msg += " It takes full effect on the next reconnect."
    return msg


# ====================================================================
# 2. SELF-HEALING
# ====================================================================

def _heal_log(entry: str):
    try:
        HEAL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(HEAL_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {entry}\n")
    except Exception:
        pass


def locate_faulty_module(tb_text: str) -> Optional[str]:
    """Returns the deepest actions/<module>.py stem referenced in a traceback."""
    hits = re.findall(r'File "([^"]+)"', tb_text or "")
    act = str(ACTIONS_DIR.resolve()).lower()
    for fpath in reversed(hits):
        try:
            p = Path(fpath).resolve()
        except Exception:
            continue
        if str(p.parent).lower() == act and p.suffix == ".py":
            return p.stem
    return None


_heal_attempts: Dict[str, float] = {}


def heal_module(module_stem: str, error_text: str, tb_text: str = "", player=None) -> Tuple[bool, str]:
    """AI-patches actions/<module_stem>.py to fix the reported error. Returns (healed, message)."""
    module_stem = _slug(module_stem, "")
    path = ACTIONS_DIR / f"{module_stem}.py"
    if not module_stem or not path.exists():
        return False, f"No module actions/{module_stem}.py to heal."
    if module_stem in HEAL_PROTECTED:
        return False, f"'{module_stem}' is a protected security module; I won't self-patch it."
    last = _heal_attempts.get(module_stem, 0)
    if time.time() - last < 120:
        return False, f"Already attempted to heal '{module_stem}' in the last 2 minutes."
    _heal_attempts[module_stem] = time.time()

    original = path.read_text(encoding="utf-8", errors="ignore")
    if len(original) > 150_000:
        return False, f"'{module_stem}' is too large for safe automatic patching."

    _log(player, f"SELF-HEAL: Diagnosing crash in '{module_stem}'...")
    prompt = (
        f"The Python module `actions/{module_stem}.py` crashed.\n\n"
        f"ERROR: {error_text[:1500]}\n\nTRACEBACK:\n{tb_text[-4000:]}\n\n"
        f"CURRENT FILE:\n```python\n{original}\n```\n\n"
        "Fix the root cause with the smallest possible change. Keep every existing function, signature, "
        "comment and behaviour intact. If the failure is a missing optional dependency, wrap the import in "
        "try/except and return a clear message instead of crashing. "
        "Return the COMPLETE corrected file in a single ```python code block and nothing else."
    )
    patched = _clean_code(_ai(prompt))

    # Safety rails
    if not patched or patched.startswith("Service temporarily busy") or len(patched) < 0.7 * len(original):
        _heal_log(f"{module_stem}: rejected (empty/truncated patch)")
        return False, "Generated patch was empty or truncated; left the module untouched."
    try:
        compile(patched, path.name, "exec")
    except SyntaxError as e:
        _heal_log(f"{module_stem}: rejected (syntax error {e})")
        return False, f"Generated patch had a syntax error ({e}); left the module untouched."
    missing = _public_defs(original) - _public_defs(patched)
    if missing:
        _heal_log(f"{module_stem}: rejected (removed functions {missing})")
        return False, f"Patch removed functions {sorted(missing)}; rejected."
    if patched.strip() == original.strip():
        return False, "AI found no change to make."

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"{module_stem}_{datetime.now():%Y%m%d_%H%M%S}.py.bak"
    shutil.copy2(path, backup)
    path.write_text(patched, encoding="utf-8")

    try:
        mod_name = f"actions.{module_stem}"
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
        else:
            importlib.import_module(mod_name)
    except Exception as e:
        shutil.copy2(backup, path)
        try:
            importlib.reload(sys.modules[f"actions.{module_stem}"])
        except Exception:
            pass
        _heal_log(f"{module_stem}: rolled back (import failed: {e})")
        return False, f"Patched module failed to import ({e}); rolled back."

    _heal_log(f"{module_stem}: healed for error '{error_text[:120]}' (backup {backup.name})")
    _log(player, f"SELF-HEAL: '{module_stem}' patched and reloaded (backup: {backup.name}).")
    return True, f"Self-healed '{module_stem}' (backup saved as .backups/{backup.name})."


def rollback_module(module_stem: str) -> str:
    module_stem = _slug(module_stem, "")
    backups = sorted(BACKUP_DIR.glob(f"{module_stem}_*.py.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        return f"No self-heal backups found for '{module_stem}'."
    shutil.copy2(backups[0], ACTIONS_DIR / f"{module_stem}.py")
    try:
        importlib.reload(sys.modules[f"actions.{module_stem}"])
    except Exception:
        pass
    _heal_log(f"{module_stem}: manual rollback to {backups[0].name}")
    return f"Rolled '{module_stem}' back to {backups[0].name}."


# ====================================================================
# 3. TOOL ENTRYPOINT
# ====================================================================

def self_evolve(parameters: dict, player=None) -> str:
    """
    action: acquire_skill | acquire_knowledge | acquire_character | run_skill | heal | rollback
            | recall_knowledge | list
    name, description, engine (auto|antigravity|antigravity_ide|gemini), query, args_json,
    source_text, error, activate
    """
    p = parameters or {}
    action = (p.get("action") or "list").lower().strip()
    name = (p.get("name") or p.get("skill_name") or p.get("topic") or "").strip()
    desc = (p.get("description") or p.get("prompt") or "").strip()

    try:
        if action in ("acquire_skill", "create_skill", "learn_skill", "code_skill"):
            if not (name or desc):
                return "Tell me what skill I should build (name and/or description)."
            return acquire_skill(name, desc or name, p.get("engine", "auto"), player)

        if action in ("acquire_knowledge", "learn", "learn_topic", "study"):
            return acquire_knowledge(name or desc, p.get("source_text", ""), player)

        if action in ("recall_knowledge", "recall"):
            return recall_knowledge(name or desc)

        if action in ("acquire_character", "create_character", "create_persona", "character"):
            return acquire_character(name, desc or name, str(p.get("activate", True)).lower() != "false", player)

        if action in ("run_skill", "run", "use_skill"):
            from core.skills_engine import skills_engine
            args = {k: v for k, v in p.items() if k not in ("action", "name", "skill_name")}
            return skills_engine.run_skill(name, skill_args=args, player=player)

        if action in ("heal", "repair", "fix"):
            ok, msg = heal_module(name, p.get("error") or desc or "Unknown malfunction reported by user", "", player)
            return msg

        if action == "rollback":
            return rollback_module(name)

        reg = load_skill_registry()
        idx = _read_json(KNOWLEDGE_INDEX, {})
        personas = _read_json(CUSTOM_PERSONAS, {})
        return (f"Self-coded skills ({len(reg)}): {', '.join(reg) or 'none'}\n"
                f"Learned topics ({len(idx)}): {', '.join(v['title'] for v in idx.values()) or 'none'}\n"
                f"Custom characters ({len(personas)}): {', '.join(personas) or 'none'}\n"
                f"Antigravity CLI: {'available' if _find_agy() else 'not found'}")
    except Exception as e:
        traceback.print_exc()
        return f"Self-evolution error: {e}"
