import json
import re
import sys
from pathlib import Path
from google import genai
from google.genai import types


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


PLANNER_PROMPT = """You are the planning module of J.A.R.V.I.S. Mark 108 (Sovereign Core).
Your job: break any user goal into a sequence of steps using ONLY the tools listed below.

ABSOLUTE RULES:
- NEVER invent tools not listed below.
- Use web_search or deep_research for information retrieval or research.
- Use file_generator for creating Word (.docx), PDF (.pdf), Excel (.xlsx), or Markdown documents.
- Use presentation_designer or exam_companion for creating PowerPoint (.pptx) presentations or study materials.
- Use agent_desktop or computer_control for UI interactions.
- Max 5 steps. Use the minimum steps needed.

AVAILABLE TOOLS AND THEIR PARAMETERS:

open_app
  app_name: string (required)

web_search
  query: string (required) — clear, focused search query
  mode: "search" or "compare" (optional, default: search)
  items: list of strings (optional, for compare mode)
  aspect: string (optional, for compare mode)

deep_research
  topic: string (required)
  depth: "quick" | "standard" | "deep" (optional)

file_generator
  file_name: string (required, e.g. "Study_Notes.docx" or "Report.pdf")
  title: string (required)
  content: string (optional — auto-generated if omitted)
  topic: string (optional)

presentation_designer
  action: "create" | "from_document" | "edit" (required)
  topic: string (required for create)
  theme: "stark_dark" | "executive_light" | "academic_study" | "emerald_growth" | "royal_velvet" | "crimson_impact" | "minimal_slate" (optional)
  slide_count: int (optional, default: 7)

exam_companion
  action: "cheat_sheet" | "predict_questions" | "flashcards" | "viva" | "create_study_ppt" | "create_study_doc" (required)
  subject: string (required)
  file_path: string (optional)

daily_briefing
  export_to: "docx" | "pdf" | "md" (optional)

system_diagnostics
  action: "full" | "optimize" | "optimize_ram" | "top_processes" | "eco_mode" (optional)

spotify_control
  action: "play" | "pause" | "next" | "previous" | "current" | "volume" (required)
  query: string (optional)

agent_desktop
  action: "snapshot" | "find" | "click" | "type" | "press" | "focus_window" | "launch" | "list_apps" | "list_windows" (required)
  target: string (optional)
  app: string (optional)
  text: string (optional)

browser_control
  action: "go_to" | "search" | "click" | "type" | "scroll" | "get_text" | "press" | "close" (required)
  url: string (for go_to)
  query: string (for search)
  text: string (for click/type)
  direction: "up" | "down" (for scroll)

file_controller
  action: "write" | "create_file" | "read" | "list" | "delete" | "move" | "copy" | "find" | "disk_usage" | "open" (required)
  path: string — use "desktop" for Desktop folder
  name: string — filename
  content: string — file content (for write/create_file)

computer_settings
  action: string (required)
  description: string — natural language description
  value: string (optional)

computer_control
  action: "type" | "click" | "hotkey" | "press" | "scroll" | "screenshot" | "screen_find" | "screen_click" (required)
  text: string (for type)
  x, y: int (for click)
  keys: string (for hotkey, e.g. "ctrl+c")
  key: string (for press)
  direction: "up" | "down" (for scroll)
  description: string (for screen_find/screen_click)

send_message
  receiver: string (required)
  message_text: string (required)
  platform: string (required)

reminder
  date: string YYYY-MM-DD (required)
  time: string HH:MM (required)
  message: string (required)

weather_report
  city: string (required)

code_helper
  action: "write" | "edit" | "run" | "explain" (required)
  description: string (required)
  language: string (optional)
  output_path: string (optional)
  file_path: string (optional)

dev_agent
  description: string (required)
  language: string (optional)

OUTPUT — return ONLY valid JSON, no markdown, no explanation, no code blocks:
{
  "goal": "...",
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "description": "what this step does",
      "parameters": {},
      "critical": true
    }
  ]
}
"""


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("gemini_api_key", "")


def _sanitize_steps(steps: list, goal: str) -> list:
    for step in steps:
        tool = step.get("tool", "")
        if tool in ("generated_code", "cmd_control"):
            desc = step.get("description", goal)
            step["tool"] = "web_search"
            step["parameters"] = {"query": desc[:200]}
    return steps


def create_plan(goal: str, context: str = "") -> dict:
    client = genai.Client(api_key=_get_api_key())

    user_input = f"Goal: {goal}"
    if context:
        user_input += f"\n\nContext: {context}"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=user_input,
            config=types.GenerateContentConfig(system_instruction=PLANNER_PROMPT),
        )
        text = (response.text or "").strip()
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        plan = json.loads(text)

        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Invalid plan structure")

        plan["steps"] = _sanitize_steps(plan["steps"], goal)

        print(f"[Planner] ✅ Plan: {len(plan['steps'])} steps")
        for s in plan["steps"]:
            print(f"  Step {s['step']}: [{s['tool']}] {s['description']}")

        return plan

    except Exception as e:
        print(f"[Planner] ⚠️ Planning failed: {e}")
        return _fallback_plan(goal)


def _fallback_plan(goal: str) -> dict:
    print("[Planner] 🔄 Fallback plan")
    return {
        "goal": goal,
        "steps": [
            {
                "step": 1,
                "tool": "web_search",
                "description": f"Search for: {goal}",
                "parameters": {"query": goal},
                "critical": True,
            }
        ],
    }


def replan(goal: str, completed_steps: list, failed_step: dict, error: str) -> dict:
    client = genai.Client(api_key=_get_api_key())

    completed_summary = "\n".join(
        f"  - Step {s['step']} ({s['tool']}): DONE" for s in completed_steps
    )

    prompt = f"""Goal: {goal}

Already completed:
{completed_summary if completed_summary else '  (none)'}

Failed step: [{failed_step.get('tool')}] {failed_step.get('description')}
Error: {error}

Create a REVISED plan for the remaining work only. Do not repeat completed steps."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=PLANNER_PROMPT),
        )
        text = (response.text or "").strip()
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        plan = json.loads(text)
        plan["steps"] = _sanitize_steps(plan.get("steps", []), goal)
        print(f"[Planner] 🔄 Revised plan: {len(plan['steps'])} steps")
        return plan
    except Exception as e:
        print(f"[Planner] ⚠️ Replan failed: {e}")
        return _fallback_plan(goal)
