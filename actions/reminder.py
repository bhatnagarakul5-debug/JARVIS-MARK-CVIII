# actions/reminder.py

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from xml.sax.saxutils import escape as xml_escape


def _parse_natural_query(query: str) -> tuple[str | None, str | None, str]:
    """
    Parses natural reminder strings via `jarvis_rust_core` with Python fallback.
    Returns (date_str, time_str, message).
    """
    try:
        from core.rust_bridge import parse_natural_reminder as _rust_rem, is_rust_active
        if is_rust_active():
            return _rust_rem(query)
    except Exception:
        pass
    q = query.strip()
    now = datetime.now()

    # 1. 'in <N> <m/min/minutes/h/hr/hours> <msg>'
    m_rel = re.match(
        r"^(?:in\s+)?(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours)\s+(.+)$",
        q,
        flags=re.IGNORECASE,
    )
    if m_rel:
        amt = int(m_rel.group(1))
        unit = m_rel.group(2).lower()
        msg = m_rel.group(3).strip()
        delta = timedelta(hours=amt) if unit.startswith("h") else timedelta(minutes=amt)
        dt = now + delta
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"), msg

    # 2. 'YYYY-MM-DD HH:MM <msg>'
    m_full = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})\s+(.+)$", q)
    if m_full:
        return m_full.group(1), m_full.group(2), m_full.group(3).strip()

    # 3. 'HH:MM <msg>'
    m_time = re.match(r"^(\d{1,2}:\d{2})\s+(.+)$", q)
    if m_time:
        t_str = m_time.group(1)
        msg = m_time.group(2).strip()
        try:
            hh, mm = [int(x) for x in t_str.split(":")]
            candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate.strftime("%Y-%m-%d"), candidate.strftime("%H:%M"), msg
        except Exception:
            pass

    # Default: 10 minutes from now if only message given
    if q:
        dt = now + timedelta(minutes=10)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"), q

    return None, None, "Reminder"


def reminder(
    parameters: dict,
    response: str | None = None,
    player=None,
    session_memory=None
) -> str:
    """
    Sets a timed reminder using Windows Task Scheduler (shell=False, XML-escaped, JSON-escaped).

    parameters:
        - date    (str) YYYY-MM-DD
        - time    (str) HH:MM
        - message (str)
        - query   (str, optional) natural query fallback e.g. 'in 15m check oven'
    """
    params = parameters or {}
    date_str = params.get("date")
    time_str = params.get("time")
    message  = params.get("message", "Reminder")
    query    = params.get("query", "")

    if (not date_str or not time_str) and query:
        date_str, time_str, message = _parse_natural_query(query)

    if not date_str or not time_str:
        return "I need both a date and a time (or 'in 10m <message>') to set a reminder."

    try:
        target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        if target_dt <= datetime.now():
            return "That time is already in the past."

        task_name    = f"MARKReminder_{target_dt.strftime('%Y%m%d_%H%M%S')}"
        safe_message = re.sub(r"[\r\n\t]+", " ", str(message)).strip()[:200] or "Reminder"
        json_msg     = json.dumps(safe_message)
        xml_msg      = xml_escape(safe_message)

        python_exe = sys.executable
        if python_exe.lower().endswith("python.exe"):
            pythonw = python_exe[:-10] + "pythonw.exe"
            if os.path.exists(pythonw):
                python_exe = pythonw

        temp_dir      = os.environ.get("TEMP", "C:\\Temp")
        os.makedirs(temp_dir, exist_ok=True)
        notify_script = os.path.join(temp_dir, f"{task_name}.pyw")
        project_root  = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        script_code = f'''import sys, os, time, subprocess
sys.path.insert(0, {json.dumps(project_root)})
MSG = {json_msg}

try:
    import winsound
    for freq in [800, 1000, 1200]:
        winsound.Beep(freq, 200)
        time.sleep(0.1)
except Exception:
    pass

try:
    from win10toast import ToastNotifier
    ToastNotifier().show_toast(
        "J.A.R.V.I.S. Reminder",
        MSG,
        duration=15,
        threaded=False
    )
except Exception:
    try:
        subprocess.run(["msg", "*", "/TIME:30", MSG], shell=False)
    except Exception:
        pass

time.sleep(3)
try:
    os.remove(__file__)
except Exception:
    pass
'''
        with open(notify_script, "w", encoding="utf-8") as f:
            f.write(script_code)

        xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>MARK Reminder: {xml_msg}</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{target_dt.strftime("%Y-%m-%dT%H:%M:%S")}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>{xml_escape(python_exe)}</Command>
      <Arguments>"{xml_escape(notify_script)}"</Arguments>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Principals>
    <Principal>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>'''

        xml_path = os.path.join(temp_dir, f"{task_name}.xml")
        with open(xml_path, "w", encoding="utf-16") as f:
            f.write(xml_content)

        result = subprocess.run(
            ["schtasks", "/Create", "/TN", task_name, "/XML", xml_path, "/F"],
            shell=False,
            capture_output=True,
            text=True,
        )

        try:
            os.remove(xml_path)
        except Exception:
            pass

        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            print(f"[Reminder] ❌ schtasks failed: {err}")
            try:
                os.remove(notify_script)
            except Exception:
                pass
            return "I couldn't schedule the reminder due to a system error."

        if player:
            player.write_log(f"[reminder] set for {date_str} {time_str}: {safe_message}")

        return f"Reminder '{safe_message}' set for {target_dt.strftime('%B %d at %I:%M %p')}."

    except ValueError:
        return "I couldn't understand that date or time format."

    except Exception as e:
        return f"Something went wrong while scheduling the reminder: {str(e)[:80]}"
