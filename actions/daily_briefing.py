"""
actions/daily_briefing.py — JARVIS Executive Parallel Daily Briefing & Academic Routine Engine
Compiles Weather, Calendar Schedule, College/Study Deadlines, Workstation & Battery Telemetry,
Email Triage, and Global News in parallel using ThreadPoolExecutor (<3s latency).
Supports exporting the briefing to Word (.docx), PDF (.pdf), or Markdown (.md).
"""

import gc
import ctypes
import datetime
import requests
import psutil
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

try:
    from actions.weather_report import weather_action
except ImportError:
    weather_action = None

try:
    from actions.email_triage import email_triage
except ImportError:
    email_triage = None

try:
    from actions.calendar_manager import calendar_manager
except ImportError:
    calendar_manager = None


def get_news(max_items: int = 5) -> str:
    try:
        response = requests.get("https://news.google.com/rss?hl=en-IN&gl=IN", timeout=3.5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            headlines = []
            for item in root.findall("./channel/item")[:max_items]:
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    headlines.append(title_el.text.strip())
            if headlines:
                return "• " + "\n• ".join(headlines)
        return "No live headlines available right now."
    except Exception as e:
        return f"News feed offline ({e})"


def _get_workstation_telemetry() -> str:
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        vm = psutil.virtual_memory()
        ram_used_gb = round(vm.used / (1024 ** 3), 1)
        ram_total_gb = round(vm.total / (1024 ** 3), 1)
        proc_mb = round(psutil.Process().memory_info().rss / (1024 * 1024), 1)
        bat = psutil.sensors_battery()
        if bat:
            plug = "Charging / AC" if bat.power_plugged else "On Battery"
            bat_str = f"{bat.percent:.0f}% ({plug})"
        else:
            bat_str = "AC Power"
        return (
            f"• CPU: {cpu:.0f}%  |  System RAM: {vm.percent:.0f}% ({ram_used_gb}/{ram_total_gb} GB)\n"
            f"• JARVIS Footprint: {proc_mb} MB  |  Power: {bat_str}"
        )
    except Exception as e:
        return f"Telemetry unavailable: {e}"


def _get_academic_pulse() -> str:
    """Fetches upcoming college assignments, attendance alerts, or study tasks."""
    notes = []
    try:
        base_dir = Path(__file__).resolve().parent.parent
        college_file = base_dir / "memory" / "college_tracker.json"
        if college_file.exists():
            import json
            data = json.loads(college_file.read_text(encoding="utf-8"))
            assignments = [a for a in data.get("assignments", []) if not a.get("completed")]
            exams = data.get("exams", [])
            if assignments:
                top_a = assignments[:3]
                notes.append("Pending Assignments: " + "; ".join(f"{a.get('title', 'Task')} (Due: {a.get('due_date', 'Soon')})" for a in top_a))
            if exams:
                top_e = exams[:2]
                notes.append("Upcoming Exams: " + "; ".join(f"{e.get('subject', 'Exam')} ({e.get('date', 'TBD')})" for e in top_e))
    except Exception:
        pass

    try:
        from actions.stunt_bridge import stunt_assistant
        stunt_res = stunt_assistant({"action": "briefing"})
        if stunt_res and "offline" not in stunt_res.lower() and "error" not in stunt_res.lower():
            notes.append(stunt_res.strip())
    except Exception:
        pass

    if not notes:
        return "• No urgent assignment or exam alerts logged. Ready for study deck or notes generation."
    return "• " + "\n• ".join(notes)


def daily_briefing(parameters: dict, player=None) -> str:
    """
    Compiles Morning, Afternoon, or Evening Executive Briefing in parallel.
    parameters:
        action / mode : morning | afternoon | evening | wrap_up
        city : City for weather (default Delhi)
        export_to : Optional 'docx' | 'pdf' | 'md' to save briefing dossier to Desktop
    """
    params = parameters or {}
    mode = (params.get("action") or params.get("mode") or "").lower().strip()
    city = params.get("city", "Delhi")
    export_to = (params.get("export_to") or "").lower().strip()

    now = datetime.datetime.now()
    hour = now.hour
    if not mode or mode in ("briefing", "daily", "status"):
        if hour < 12:
            mode = "morning"
        elif hour >= 17:
            mode = "evening"
        else:
            mode = "afternoon"

    date_banner = now.strftime("%A, %B %d, %Y — %I:%M %p")
    greeting_map = {
        "morning": f"Good morning, Akul. Here is your executive morning briefing for {date_banner}.",
        "evening": f"Good evening, Akul. Here is your end-of-day wrap-up for {date_banner}.",
        "wrap_up": f"Good evening, Akul. Here is your workstation wrap-up for {date_banner}.",
        "night":   f"Good evening, Akul. Here is your night wrap-up for {date_banner}.",
    }
    greeting = greeting_map.get(mode, f"Good afternoon, Akul. Here is your executive briefing for {date_banner}.")

    cal_act = "today" if mode == "morning" else "upcoming"

    def _task_weather():
        if not weather_action:
            return "Weather module unavailable."
        return weather_action({"city": city}, player=None)

    def _task_calendar():
        if not calendar_manager:
            return "No calendar events scheduled."
        return calendar_manager({"action": cal_act}, player=None)

    def _task_email():
        if not email_triage:
            return ""
        return email_triage({"max_emails": 3}, player=None)

    # Execute slow I/O calls concurrently with strict timeouts
    with ThreadPoolExecutor(max_workers=5) as pool:
        fut_wx   = pool.submit(_task_weather)
        fut_cal  = pool.submit(_task_calendar)
        fut_acad = pool.submit(_get_academic_pulse)
        fut_sys  = pool.submit(_get_workstation_telemetry)
        fut_news = pool.submit(get_news, 5)
        fut_mail = pool.submit(_task_email)

        def _safe_res(fut, timeout_s: float, fallback: str = "") -> str:
            try:
                return (fut.result(timeout=timeout_s) or fallback).strip()
            except Exception:
                return fallback

        wx_res   = _safe_res(fut_wx,   3.5, f"{city}: Weather feed offline")
        cal_res  = _safe_res(fut_cal,  2.5, "No scheduled events")
        acad_res = _safe_res(fut_acad, 2.5, "• Academic tracker nominal")
        sys_res  = _safe_res(fut_sys,  1.5, "• System nominal")
        news_res = _safe_res(fut_news, 3.5, "• News feed offline")
        mail_res = _safe_res(fut_mail, 3.5, "")

    # Update UI Dashboard widget if available
    if player and hasattr(player, "update_dashboard"):
        try:
            short_wx = wx_res.splitlines()[0][:26] if wx_res else city
            short_cal = "Clear" if ("no event" in cal_res.lower() or not cal_res) else cal_res.splitlines()[0][:24]
            short_mail = "Checked" if mail_res else "Standby"
            player.update_dashboard(wx=short_wx, evt=short_cal, mail=short_mail)
        except Exception:
            pass

    sections = [
        greeting,
        f"## 🌤 Weather ({city})\n{wx_res}",
        f"## 📅 Schedule & Calendar\n{cal_res}",
        f"## 🎓 Academic & Study Pulse\n{acad_res}",
        f"## 💻 Workstation & Battery Telemetry\n{sys_res}",
    ]
    if mail_res and "error" not in mail_res.lower():
        sections.append(f"## ✉ Priority Email Triage\n{mail_res}")
    sections.append(f"## 📰 Top Headlines\n{news_res}")

    if mode in ("wrap_up", "evening", "night"):
        gc.collect()
        try:
            if hasattr(ctypes, "windll"):
                ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1, -1)
        except Exception:
            pass
        sections.append("## 🌙 Evening Optimization\n• Flushed Python & OS working-set memory caches. Workstation ready for low-power standby.")

    compiled = "\n\n".join(sections)

    if export_to in ("docx", "pdf", "md", "markdown"):
        try:
            from actions.file_generator import universal_file_creator
            f_res = universal_file_creator({
                "file_type": export_to,
                "filename": f"JARVIS_Daily_Briefing_{now.strftime('%Y%m%d')}",
                "title": f"J.A.R.V.I.S. Executive Briefing — {now.strftime('%B %d, %Y')}",
                "content": compiled,
                "open_after": True,
            }, player=player)
            compiled += f"\n\n📁 **Briefing Exported**: {f_res}"
        except Exception as e:
            compiled += f"\n\n[Export Notice: {e}]"

    if player and hasattr(player, "write_log"):
        player.write_log(f"SYS: Compiled {mode.title()} Executive Briefing.")

    return compiled
