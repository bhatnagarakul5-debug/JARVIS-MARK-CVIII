import json
import re
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from google import genai
from google.genai import types

from agent.planner import create_plan, replan
from agent.error_handler import analyze_error, generate_fix, ErrorDecision


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("gemini_api_key", "")


def _get_client() -> genai.Client:
    return genai.Client(api_key=_get_api_key())


def _inject_context(params: dict, tool: str, step_results: dict, goal: str = "") -> dict:
    if not step_results:
        return params

    params = dict(params)

    if tool in ("file_controller", "file_generator") and params.get("action") in ("write", "create_file", None, "create"):
        content = params.get("content", "")
        if not content or len(content) < 50:
            all_results = [
                v for v in step_results.values()
                if v and len(v) > 100 and v not in ("Done.", "Completed.")
            ]
            if all_results:
                combined = "\n\n---\n\n".join(all_results)
                translated = _translate_to_goal_language(combined, goal)
                params["content"] = translated
                print("[Executor] 💉 Injected context into file content")

    return params


def _detect_language(text: str) -> str:
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=(
                "What language is this text written in? "
                "Reply with ONLY the language name in English (e.g. English, Hindi, Spanish).\n\n"
                f"Text: {text[:200]}"
            ),
        )
        return (response.text or "English").strip()
    except Exception:
        return "English"


def _translate_to_goal_language(content: str, goal: str) -> str:
    if not goal:
        return content
    try:
        target_lang = _detect_language(goal)
        if target_lang.lower() == "english":
            return content
        client = _get_client()
        prompt = (
            f"You are a professional translator. Translate the following text into {target_lang}.\n"
            f"- Keep all facts, numbers, and formatting intact.\n"
            f"- Output ONLY the translated text.\n\n"
            f"Text:\n{content[:4000]}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return (response.text or content).strip()
    except Exception as e:
        print(f"[Executor] ⚠️ Translation failed: {e}")
        return content


def _call_tool(tool: str, parameters: dict, speak: Callable | None) -> str:
    if tool == "open_app":
        from actions.open_app import open_app
        return open_app(parameters=parameters, player=None) or "Done."

    elif tool == "web_search":
        from actions.web_search import web_search
        return web_search(parameters=parameters, player=None) or "Done."

    elif tool == "game_updater":
        from actions.game_updater import game_updater
        return game_updater(parameters=parameters, player=None, speak=speak) or "Done."

    elif tool == "browser_control":
        from actions.browser_control import browser_control
        return browser_control(parameters=parameters, player=None) or "Done."

    elif tool == "file_controller":
        from actions.file_controller import file_controller
        return file_controller(parameters=parameters, player=None) or "Done."

    elif tool == "file_generator":
        from actions.file_generator import universal_file_creator
        return universal_file_creator(parameters=parameters, player=None) or "Done."

    elif tool == "presentation_designer":
        from actions.presentation_designer import presentation_designer
        return presentation_designer(parameters=parameters, player=None) or "Done."

    elif tool == "exam_companion":
        from actions.exam_companion import exam_companion
        return exam_companion(parameters=parameters, player=None) or "Done."

    elif tool == "deep_research":
        from actions.deep_research import deep_research
        return deep_research(parameters=parameters, player=None) or "Done."

    elif tool == "daily_briefing":
        from actions.daily_briefing import daily_briefing
        return daily_briefing(parameters=parameters, player=None) or "Done."

    elif tool in ("system_diagnostics", "system_optimizer"):
        from actions.system_diagnostics import run_system_diagnostics
        return run_system_diagnostics(parameters=parameters, player=None) or "Done."

    elif tool == "spotify_control":
        from actions.spotify_control import spotify_control
        return spotify_control(parameters=parameters, player=None) or "Done."

    elif tool == "agent_desktop":
        from actions.agent_desktop import agent_desktop_control
        return agent_desktop_control(parameters=parameters, player=None) or "Done."

    elif tool == "code_helper":
        from actions.code_helper import code_helper
        return code_helper(parameters=parameters, player=None, speak=speak) or "Done."

    elif tool == "dev_agent":
        from actions.dev_agent import dev_agent
        return dev_agent(parameters=parameters, player=None, speak=speak) or "Done."

    elif tool == "screen_process":
        from actions.screen_processor import screen_process
        screen_process(parameters=parameters, player=None)
        return "Screen captured and analyzed."

    elif tool == "send_message":
        from actions.send_message import send_message
        return send_message(parameters=parameters, player=None) or "Done."

    elif tool == "reminder":
        from actions.reminder import reminder
        return reminder(parameters=parameters, player=None) or "Done."

    elif tool == "youtube_video":
        from actions.youtube_video import youtube_video
        return youtube_video(parameters=parameters, player=None) or "Done."

    elif tool == "weather_report":
        from actions.weather_report import weather_action
        return weather_action(parameters=parameters, player=None) or "Done."

    elif tool == "computer_settings":
        from actions.computer_settings import computer_settings
        return computer_settings(parameters=parameters, player=None) or "Done."

    elif tool == "desktop_control":
        from actions.desktop import desktop_control
        return desktop_control(parameters=parameters, player=None) or "Done."

    elif tool == "computer_control":
        from actions.computer_control import computer_control
        return computer_control(parameters=parameters, player=None) or "Done."

    elif tool == "flight_finder":
        from actions.flight_finder import flight_finder
        return flight_finder(parameters=parameters, player=None, speak=speak) or "Done."

    elif tool == "self_evolve":
        from core.self_evolution import self_evolve
        return self_evolve(parameters=parameters, player=None) or "Done."

    else:
        # Mark 108 Sovereign Core: Check dynamic/self-coded skills first, then auto-synthesize if missing
        from core.skills_engine import skills_engine
        from core.sovereign_core import SovereignSkillSynthesizer

        skills_engine.discover_skills()
        if tool in skills_engine.loaded_skills:
            return skills_engine.run_skill(tool, skill_args=parameters, player=None) or "Done."

        desc = parameters.get("description") or parameters.get("query") or f"Execute capability for {tool}"
        synth_res = SovereignSkillSynthesizer.synthesize_missing_capability(
            skill_name=tool,
            description=str(desc),
            engine="auto",
            player=None,
        )
        if synth_res.get("status") == "VERIFIED":
            return skills_engine.run_skill(synth_res["skill_name"], skill_args=parameters, player=None) or "Done."
        raise ValueError(f"Unsupported or unknown tool '{tool}' (auto-synthesis status: {synth_res.get('status')}).")


class AgentExecutor:

    MAX_REPLAN_ATTEMPTS = 2

    def execute(
        self,
        goal:        str,
        speak:       Callable | None        = None,
        cancel_flag: threading.Event | None = None,
    ) -> str:
        print(f"\n[Executor] 🎯 Goal: {goal}")
        try:
            from core.sovereign_core import SovereignDeliberationCouncil, SovereignEquilibriumDaemon
            delib = SovereignDeliberationCouncil.deliberate(goal)
            telem = SovereignEquilibriumDaemon.sample_telemetry()
            print(f"[SovereignCore] Council Consensus: {delib['consensus_approved']} (Conf: {delib['aggregate_confidence']}) | Regime: {telem['operating_regime']}")
        except Exception:
            pass

        replan_attempts = 0
        completed_steps = []
        step_results    = {}
        plan            = create_plan(goal)

        while True:
            steps = plan.get("steps", [])

            if not steps:
                msg = "I couldn't create a valid plan for this task, sir."
                if speak:
                    speak(msg)
                return msg

            success      = True
            failed_step  = None
            failed_error = ""

            for step in steps:
                if cancel_flag and cancel_flag.is_set():
                    if speak:
                        speak("Task cancelled, sir.")
                    return "Task cancelled."

                step_num = step.get("step", "?")
                tool     = step.get("tool", "web_search")
                desc     = step.get("description", "")
                params   = step.get("parameters", {})

                params = _inject_context(params, tool, step_results, goal=goal)

                print(f"\n[Executor] ▶️ Step {step_num}: [{tool}] {desc}")

                attempt = 1
                step_ok = False

                while attempt <= 3:
                    if cancel_flag and cancel_flag.is_set():
                        break
                    try:
                        result = _call_tool(tool, params, speak)
                        step_results[step_num] = result
                        completed_steps.append(step)
                        print(f"[Executor] ✅ Step {step_num} done: {str(result)[:100]}")
                        step_ok = True
                        break

                    except Exception as e:
                        import traceback as _tb
                        error_msg = str(e)
                        tb_str = _tb.format_exc()
                        print(f"[Executor] ❌ Step {step_num} attempt {attempt} failed: {error_msg}")
                        if attempt == 1:
                            try:
                                from core.sovereign_core import SovereignSelfHealer
                                heal_res = SovereignSelfHealer.diagnose_and_heal("", error_msg, tb_text=tb_str)
                                if heal_res.get("healed"):
                                    print(f"[SovereignCore] Self-healed module '{heal_res.get('module')}' — retrying step {step_num}")
                                    attempt += 1
                                    continue
                            except Exception:
                                pass

                        recovery = analyze_error(step, error_msg, attempt=attempt)
                        decision = recovery["decision"]
                        user_msg = recovery.get("user_message", "")

                        if speak and user_msg:
                            speak(user_msg)

                        if decision == ErrorDecision.RETRY:
                            attempt += 1
                            time.sleep(2)
                            continue

                        elif decision == ErrorDecision.SKIP:
                            print(f"[Executor] ⏭️ Skipping step {step_num}")
                            completed_steps.append(step)
                            step_ok = True
                            break

                        elif decision == ErrorDecision.ABORT:
                            msg = f"Task aborted, sir. {recovery.get('reason', '')}"
                            if speak:
                                speak(msg)
                            return msg

                        else:
                            fix_suggestion = recovery.get("fix_suggestion", "")
                            if fix_suggestion:
                                try:
                                    fixed_step = generate_fix(step, error_msg, fix_suggestion)
                                    if speak:
                                        speak("Trying an alternative approach, sir.")
                                    res = _call_tool(
                                        fixed_step["tool"],
                                        fixed_step["parameters"],
                                        speak,
                                    )
                                    step_results[step_num] = res
                                    completed_steps.append(step)
                                    step_ok = True
                                    break
                                except Exception as fix_err:
                                    print(f"[Executor] ⚠️ Fix failed: {fix_err}")

                            failed_step  = step
                            failed_error = error_msg
                            success      = False
                            break

                if not step_ok and not failed_step:
                    failed_step  = step
                    failed_error = "Max retries exceeded"
                    success      = False

                if not success:
                    break

            if success:
                return self._summarize(goal, completed_steps, speak)

            if replan_attempts >= self.MAX_REPLAN_ATTEMPTS:
                msg = f"Task failed after {replan_attempts} replan attempts, sir."
                if speak:
                    speak(msg)
                return msg

            if speak:
                speak("Adjusting my approach, sir.")

            replan_attempts += 1
            plan = replan(goal, completed_steps, failed_step, failed_error)

    def _summarize(self, goal: str, completed_steps: list, speak: Callable | None) -> str:
        fallback = f"All done, sir. Completed {len(completed_steps)} steps for: {goal[:60]}."
        try:
            client    = _get_client()
            steps_str = "\n".join(f"- {s.get('description', '')}" for s in completed_steps)
            prompt    = (
                f'User goal: "{goal}"\n'
                f"Completed steps:\n{steps_str}\n\n"
                "Write a single natural sentence summarizing what was accomplished. "
                "Address the user as 'sir'. Be direct and positive."
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            summary = (response.text or fallback).strip()
            if speak:
                speak(summary)
            return summary
        except Exception:
            if speak:
                speak(fallback)
            return fallback
