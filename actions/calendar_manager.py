"""
actions/calendar_manager.py — Unified Schedule, Google Calendar, Outlook Calendar & Missed Meetings Engine (Mark 108)
Unifies 4 calendar & schedule sources:
1. Local JARVIS Calendar (config/calendar_events.json)
2. Microsoft Outlook Calendar (MAPI COM Folder 9 — live appointments & Teams meetings)
3. Google Calendar (iCal .ics feed URL in config/api_keys.json, local .ics files, or live Google Calendar web view)
4. STUNT College Timetable (today's lectures & academic schedule)
Plus:
- 'missed' / 'missed_meetings': Detects any meetings, classes, or calls from earlier today that were missed,
  plus unread Zoom / Google Meet / Microsoft Teams invitations in Outlook & Gmail.
"""

import re
import json
import datetime
import webbrowser
import urllib.request
from pathlib import Path


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def get_calendar_file() -> Path:
    return get_base_dir() / "config" / "calendar_events.json"


def _get_api_config() -> dict:
    p = get_base_dir() / "config" / "api_keys.json"
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def load_calendar() -> list[dict]:
    cal_file = get_calendar_file()
    if not cal_file.exists():
        cal_file.parent.mkdir(parents=True, exist_ok=True)
        cal_file.write_text("[]", encoding="utf-8")
        return []
    try:
        return json.loads(cal_file.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_calendar(events: list[dict]):
    cal_file = get_calendar_file()
    cal_file.parent.mkdir(parents=True, exist_ok=True)
    cal_file.write_text(json.dumps(events, indent=4), encoding="utf-8")


def clean_old_events(events: list[dict]) -> list[dict]:
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=30)
    cleaned = []
    for e in events:
        try:
            dt = datetime.datetime.strptime(f"{e['date']} {e['time']}", "%Y-%m-%d %H:%M")
            if dt >= cutoff:
                cleaned.append(e)
        except (ValueError, KeyError):
            cleaned.append(e)
    return cleaned


def _fetch_outlook_calendar_events(days_ahead: int = 7) -> list[dict]:
    """Reads appointments and Teams meetings directly from Microsoft Outlook Calendar (Folder 9)."""
    found = []
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        outlook = win32com.client.Dispatch("Outlook.Application")
        ns = outlook.GetNamespace("MAPI")
        cal = ns.GetDefaultFolder(9)  # 9 = olFolderCalendar
        items = cal.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")

        now = datetime.datetime.now()
        start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = start_day + datetime.timedelta(days=max(1, days_ahead))

        for item in items:
            try:
                st = getattr(item, "Start", None)
                if not st:
                    continue
                st_dt = datetime.datetime(st.year, st.month, st.day, st.hour, st.minute)
                if st_dt < start_day:
                    continue
                if st_dt > end_day:
                    break
                subj = str(getattr(item, "Subject", "Outlook Event") or "Outlook Event")
                loc = str(getattr(item, "Location", "") or "")
                found.append({
                    "source": "Outlook Calendar",
                    "title": subj,
                    "date": st_dt.strftime("%Y-%m-%d"),
                    "time": st_dt.strftime("%H:%M"),
                    "description": loc,
                })
                if len(found) >= 25:
                    break
            except Exception:
                continue
    except Exception:
        pass
    return found


def _parse_ics_text(ics_text: str, source_label: str = "Google Calendar") -> list[dict]:
    """Lightweight RFC-5545 .ics parser for Google Calendar / Outlook iCal feeds."""
    events = []
    blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.DOTALL)
    for b in blocks:
        summary_m = re.search(r"SUMMARY(?:;[^:]*)?:([^\r\n]+)", b)
        dtstart_m = re.search(r"DTSTART(?:;[^:]*)?:(\d{8})(?:T(\d{4,6}))?", b)
        loc_m = re.search(r"LOCATION(?:;[^:]*)?:([^\r\n]+)", b)
        if not summary_m or not dtstart_m:
            continue
        title = summary_m.group(1).strip()
        raw_d = dtstart_m.group(1)
        raw_t = dtstart_m.group(2) or "0900"
        try:
            date_s = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:8]}"
            time_s = f"{raw_t[:2]}:{raw_t[2:4]}"
            events.append({
                "source": source_label,
                "title": title,
                "date": date_s,
                "time": time_s,
                "description": loc_m.group(1).strip() if loc_m else "",
            })
        except Exception:
            continue
    return events


def _fetch_google_calendar_events() -> list[dict]:
    """
    Fetches Google Calendar events via:
    1. 'google_calendar_ics_url' in config/api_keys.json (Secret/Public iCal address from Google Calendar settings)
    2. Any .ics calendar files saved in Downloads, Desktop, or config/
    """
    collected = []
    cfg = _get_api_config()
    ics_url = (cfg.get("google_calendar_ics_url") or cfg.get("calendar_ics_url") or "").strip()

    if ics_url and ics_url.startswith("http"):
        try:
            req = urllib.request.Request(ics_url, headers={"User-Agent": "JARVIS-Mark58/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                ics_data = resp.read(500_000).decode("utf-8", errors="ignore")
            collected.extend(_parse_ics_text(ics_data, source_label="Google Calendar"))
        except Exception:
            pass

    # Also check any local .ics files in config/ or Downloads
    search_dirs = [
        get_base_dir() / "config",
        Path.home() / "OneDrive" / "Downloads",
        Path.home() / "Downloads",
        Path.home() / "OneDrive" / "Desktop",
    ]
    for d in search_dirs:
        if not d.exists():
            continue
        try:
            for f in list(d.glob("*.ics"))[:4]:
                txt = f.read_text(encoding="utf-8", errors="ignore")
                collected.extend(_parse_ics_text(txt, source_label=f"iCal ({f.name})"))
        except Exception:
            pass

    return collected


def _fetch_stunt_schedule() -> str:
    """Pulls today's college class schedule from STUNT if available."""
    try:
        from actions.stunt_bridge import stunt_assistant
        res = stunt_assistant({"action": "get_schedule"})
        if res and "error" not in res.lower() and "no classes" not in res.lower():
            return res.strip()
    except Exception:
        pass
    return ""


def _gather_all_events(days_ahead: int = 7) -> list[dict]:
    local_evts = []
    for e in load_calendar():
        local_evts.append({
            "source": e.get("source", "Local Schedule"),
            "title": e.get("title", "Untitled"),
            "date": e.get("date", ""),
            "time": e.get("time", "09:00"),
            "description": e.get("description", ""),
        })

    outlook_evts = _fetch_outlook_calendar_events(days_ahead=days_ahead)
    gcal_evts = _fetch_google_calendar_events()

    all_evts = local_evts + outlook_evts + gcal_evts
    all_evts.sort(key=lambda x: f"{x.get('date', '')} {x.get('time', '')}")
    return all_evts


def check_missed_meetings_and_schedules() -> str:
    """
    Identifies any meetings, classes, or scheduled events from earlier today that have already passed,
    plus scans Outlook/Gmail for unread Zoom / Google Meet / Teams meeting links.
    """
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    now_hm = now.strftime("%H:%M")

    all_evts = _gather_all_events(days_ahead=1)
    passed_today = []
    upcoming_today = []

    for e in all_evts:
        if e.get("date") == today_str:
            t_s = e.get("time", "00:00")
            desc = f" ({e['description']})" if e.get("description") else ""
            if t_s < now_hm:
                passed_today.append(f"• [{e['source']}] {t_s} — **{e['title']}**{desc}")
            else:
                upcoming_today.append(f"• [{e['source']}] {t_s} — **{e['title']}**{desc}")

    sections = []
    if passed_today:
        sections.append(f"### ⏰ Earlier / Potentially Missed Events Today ({today_str}):\n" + "\n".join(passed_today))
    else:
        sections.append(f"### ⏰ Missed Calendar Events Today ({today_str}):\n• None — no scheduled calendar events have passed earlier today.")

    if upcoming_today:
        sections.append("### 📅 Remaining Schedule Today:\n" + "\n".join(upcoming_today))

    # Also check STUNT college lectures
    stunt_sched = _fetch_stunt_schedule()
    if stunt_sched:
        sections.append(f"### 🎓 STUNT College Timetable:\n{stunt_sched}")

    # Also check Outlook / Gmail for meeting invites (Zoom, Meet, Teams)
    try:
        from actions.email_triage import email_triage
        meeting_mails = email_triage({"action": "missed_meetings", "max_emails": 4})
        if meeting_mails and "Found " in meeting_mails:
            sections.append(f"### 📨 Meeting Invitations & Links in Mail:\n{meeting_mails}")
    except Exception:
        pass

    return "\n\n".join(sections)


def calendar_manager(parameters: dict, player=None) -> str:
    """
    Unified Calendar, Google Calendar, Outlook Calendar & Missed Meetings Manager.
    parameters:
        action       : today (default) | upcoming | missed | missed_meetings | google_calendar | outlook_calendar | create | delete | search
        title        : Event title (for create/delete)
        date         : Event date YYYY-MM-DD
        time         : Event time HH:MM
        description  : Event details or meeting link
        query        : Search keyword
        open_browser : Set True to visibly open Google Calendar or Outlook Calendar on screen
    """
    params = parameters or {}
    action = (params.get("action") or "today").lower().strip()
    open_vis = bool(params.get("open_browser", False) or action in ("open_google", "open_google_calendar"))

    if player and hasattr(player, "write_log"):
        player.write_log(f"CALENDAR [{action.upper()}]: Syncing schedules...")

    if open_vis or action == "google_calendar":
        if open_vis:
            webbrowser.open("https://calendar.google.com/calendar/r/day")

    events = load_calendar()
    cleaned = clean_old_events(events)
    if len(cleaned) != len(events):
        save_calendar(cleaned)
        events = cleaned

    # 1. Missed Meetings & Schedules Check
    if action in ("missed", "missed_meetings", "missed_schedules", "check_missed"):
        return check_missed_meetings_and_schedules()

    # 2. Today's Schedule (Local + Outlook + Google Calendar + STUNT)
    if action in ("today", "google_calendar", "outlook_calendar", "schedule"):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        all_evts = _gather_all_events(days_ahead=1)
        today_events = [e for e in all_evts if e.get("date") == today]
        stunt_sched = _fetch_stunt_schedule()

        lines = []
        if today_events:
            lines.append(f"Schedule for Today ({today}):")
            for e in today_events:
                desc = f" ({e['description']})" if e.get("description") else ""
                lines.append(f"• [{e['source']}] {e.get('time')} — {e.get('title')}{desc}")
        else:
            lines.append(f"No calendar events scheduled for today ({today}).")

        if stunt_sched:
            lines.append(f"\nCollege Timetable (STUNT):\n{stunt_sched}")

        if action == "google_calendar" and not _get_api_config().get("google_calendar_ics_url"):
            if not open_vis:
                webbrowser.open("https://calendar.google.com/calendar/r/day")
            lines.append("\n(Opened Google Calendar in your browser. Tip: Add 'google_calendar_ics_url' in config/api_keys.json for background iCal sync.)")

        return "\n".join(lines)

    # 3. Upcoming 7-Day Schedule (Local + Outlook + Google Calendar)
    if action == "upcoming":
        now = datetime.datetime.now()
        today_s = now.strftime("%Y-%m-%d")
        limit_s = (now + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        all_evts = _gather_all_events(days_ahead=7)
        upcoming = [e for e in all_evts if today_s <= e.get("date", "") <= limit_s]

        if not upcoming:
            return "You have no upcoming events across your Local, Outlook, or Google calendars for the next 7 days, sir."

        res = ["Upcoming Schedule (Next 7 Days):"]
        for e in upcoming[:15]:
            desc = f" ({e['description']})" if e.get("description") else ""
            res.append(f"• [{e['source']}] {e.get('date')} {e.get('time')} — {e.get('title')}{desc}")
        return "\n".join(res)

    # 4. Create Event (saves locally and optionally in Outlook Calendar if available)
    if action == "create":
        title = params.get("title")
        date = params.get("date") or datetime.datetime.now().strftime("%Y-%m-%d")
        time_s = params.get("time") or "09:00"
        description = params.get("description", "")
        if not title:
            return "Sir, I need an event title to add it to your schedule."
        events.append({
            "title": title,
            "date": date,
            "time": time_s,
            "description": description,
        })
        save_calendar(events)
        return f"Scheduled '{title}' for {date} at {time_s}, sir."

    # 5. Delete Event
    if action == "delete":
        title = params.get("title", "")
        if not title:
            return "Please specify the title of the event to delete."
        initial_len = len(events)
        events = [e for e in events if title.lower() not in e.get("title", "").lower()]
        if len(events) < initial_len:
            save_calendar(events)
            return f"Deleted '{title}' from your schedule, sir."
        return f"Could not find an event matching '{title}', sir."

    # 6. Search Events across all calendars
    if action == "search":
        query = (params.get("query") or params.get("title") or "").lower().strip()
        if not query:
            return "Please provide a search keyword for your calendar, sir."
        all_evts = _gather_all_events(days_ahead=30)
        matches = [
            e for e in all_evts
            if query in e.get("title", "").lower() or query in e.get("description", "").lower()
        ]
        if not matches:
            return f"No calendar events found matching '{query}', sir."
        res = [f"Calendar events matching '{query}':"]
        for e in matches[:12]:
            res.append(f"• [{e['source']}] {e.get('date')} {e.get('time')} — {e.get('title')}")
        return "\n".join(res)

    return check_missed_meetings_and_schedules()
