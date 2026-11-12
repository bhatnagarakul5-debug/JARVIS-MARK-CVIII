import json
import re
import sys
from pathlib import Path
from enum import Enum
from google import genai
from google.genai import types


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


class ErrorDecision(Enum):
    RETRY  = "retry"
    SKIP   = "skip"
    REPLAN = "replan"
    ABORT  = "abort"


ERROR_ANALYST_PROMPT = """You are the error recovery module of J.A.R.V.I.S. Mark 108.

A task step has failed. Analyze the error and decide what to do.

DECISIONS:
- retry   : Transient error (network timeout, temporary file lock, race condition).
- skip    : This step is not critical and the task can succeed without it.
- replan  : The approach was wrong. A different tool or method should be tried.
- abort   : The task is fundamentally impossible or unsafe to continue.

Return ONLY valid JSON:
{
  "decision": "retry|skip|replan|abort",
  "reason": "why it failed",
  "fix_suggestion": "what to try instead (for replan)",
  "max_retries": 1,
  "user_message": "Short message to tell the user (max 15 words)"
}
"""


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("gemini_api_key", "")


def analyze_error(
    step: dict,
    error: str,
    attempt: int = 1,
    max_attempts: int = 2
) -> dict:
    if attempt >= max_attempts:
        print(f"[ErrorHandler] ⚠️ Max attempts reached for step {step.get('step')} — forcing replan")
        return {
            "decision":       ErrorDecision.REPLAN,
            "reason":         f"Failed {attempt} times: {error[:100]}",
            "fix_suggestion": "Try a different approach or tool",
            "max_retries":    0,
            "user_message":   "Trying a different approach, sir.",
        }

    prompt = f"""Failed step:
Tool: {step.get('tool')}
Description: {step.get('description')}
Parameters: {json.dumps(step.get('parameters', {}), indent=2)}
Critical: {step.get('critical', False)}

Error:
{error[:500]}

Attempt number: {attempt}"""

    try:
        client = genai.Client(api_key=_get_api_key())
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=ERROR_ANALYST_PROMPT),
        )
        text = (response.text or "").strip()
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        result = json.loads(text)
        decision_str = result.get("decision", "replan").lower()
        decision_map = {
            "retry":  ErrorDecision.RETRY,
            "skip":   ErrorDecision.SKIP,
            "replan": ErrorDecision.REPLAN,
            "abort":  ErrorDecision.ABORT,
        }
        result["decision"] = decision_map.get(decision_str, ErrorDecision.REPLAN)

        if step.get("critical") and result["decision"] == ErrorDecision.SKIP:
            result["decision"]     = ErrorDecision.REPLAN
            result["user_message"] = "This step is critical — finding alternative approach, sir."

        print(f"[ErrorHandler] Decision: {result['decision'].value} — {result.get('reason', '')}")
        return result

    except Exception as e:
        print(f"[ErrorHandler] ⚠️ Analysis failed: {e} — defaulting to replan")
        return {
            "decision":       ErrorDecision.REPLAN,
            "reason":         str(e),
            "fix_suggestion": "Try alternative approach",
            "max_retries":    1,
            "user_message":   "Encountered an issue, adjusting approach, sir.",
        }


def generate_fix(step: dict, error: str, fix_suggestion: str) -> dict:
    """
    Generates a safe replacement step using existing structured tools (never raw unvalidated code execution).
    """
    desc = step.get("description") or fix_suggestion or "Retry task via search"
    return {
        "step":        step.get("step"),
        "tool":        "web_search",
        "description": f"Fallback search for: {desc}",
        "parameters":  {"query": desc[:200]},
        "depends_on":  step.get("depends_on", []),
        "critical":    step.get("critical", False),
    }
