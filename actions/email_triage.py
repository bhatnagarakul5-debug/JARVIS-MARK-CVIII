"""
actions/email_triage.py — Universal Email, Outlook, Gmail & Unread Messages Intelligence Engine (Mark 108)
Capabilities:
1. Native Microsoft Outlook Desktop (MAPI COM): Reads unread Outlook emails, all recent Outlook emails,
   and meeting invitations directly from the logged-in Windows Outlook client with zero config needed.
2. Multi-Provider IMAP (Gmail + Outlook/Office365): Reads unread or recent emails, searches by sender/keyword,
   and detects missed meeting links (Teams, Zoom, Google Meet).
3. Live UI Automation / Vision Fallback: Reads unread emails from New Windows Outlook (olk.exe) or Gmail/Outlook Web
   via Windows UI Automation tree + Gemini Vision when MAPI/IMAP are not configured.
4. Cross-App Unread Messages Scanner: Detects unread messages and missed calls across WhatsApp, Discord, Teams, and Telegram.
"""

import re
import json
import sys
import time
import email
import imaplib
from email.header import decode_header
from datetime import datetime
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _get_email_config() -> dict:
    try:
        if API_CONFIG_PATH.exists():
            return json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _clean_text(text: str, limit: int = 320) -> str:
    if not text:
        return ""
    return " ".join(text.split())[:limit]


def _read_outlook_desktop_com(unread_only: bool = True, max_items: int = 8, search_query: str = "") -> list[dict]:
    """
    Reads emails directly from the local Windows Microsoft Outlook application via MAPI COM.
    Requires no password if Outlook is logged in on Windows.
    """
    results = []
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)

        if unread_only:
            items = items.Restrict("[Unread] = True")

        q_low = (search_query or "").lower().strip()
        count = 0
        for item in items:
            if count >= max_items:
                break
            try:
                subj = str(getattr(item, "Subject", "(No Subject)") or "(No Subject)")
                sender = str(getattr(item, "SenderName", "") or getattr(item, "SenderEmailAddress", "Unknown"))
                body = _clean_text(str(getattr(item, "Body", "") or ""), 350)
                rec_time = str(getattr(item, "ReceivedTime", ""))[:19]
                unread_flag = bool(getattr(item, "UnRead", False))

                if q_low and q_low not in subj.lower() and q_low not in sender.lower() and q_low not in body.lower():
                    continue

                results.append({
                    "source": "Outlook Desktop",
                    "from": sender,
                    "subject": subj,
                    "received": rec_time,
                    "unread": unread_flag,
                    "preview": body,
                })
                count += 1
            except Exception:
                continue
    except Exception:
        pass
    return results


def _read_imap_emails(
    provider: str = "auto",
    unread_only: bool = True,
    max_items: int = 8,
    search_query: str = "",
) -> list[dict]:
    """
    Connects to Gmail and/or Outlook IMAP servers using credentials in config/api_keys.json.
    Supports keys:
      - email_address / email_app_password
      - outlook_email / outlook_password
    """
    cfg = _get_email_config()
    accounts = []

    main_user = (cfg.get("email_address") or "").strip()
    main_pass = (cfg.get("email_app_password") or "").strip()
    out_user = (cfg.get("outlook_email") or "").strip()
    out_pass = (cfg.get("outlook_password") or cfg.get("outlook_app_password") or "").strip()

    if provider in ("outlook", "office365"):
        if out_user and out_pass:
            accounts.append(("Outlook IMAP", out_user, out_pass, ["outlook.office365.com", "imap-mail.outlook.com"]))
        elif main_user and main_pass:
            accounts.append(("Outlook/Mail IMAP", main_user, main_pass, ["outlook.office365.com", "imap-mail.outlook.com", "imap.gmail.com"]))
    elif provider == "gmail":
        if main_user and main_pass:
            accounts.append(("Gmail IMAP", main_user, main_pass, ["imap.gmail.com"]))
    else:
        if out_user and out_pass:
            accounts.append(("Outlook IMAP", out_user, out_pass, ["outlook.office365.com", "imap-mail.outlook.com"]))
        if main_user and main_pass:
            hosts = ["outlook.office365.com", "imap-mail.outlook.com"] if any(d in main_user.lower() for d in ("outlook", "hotmail", "live", ".edu")) else ["imap.gmail.com"]
            accounts.append(("Mail IMAP", main_user, main_pass, hosts))

    collected = []
    q_low = (search_query or "").lower().strip()

    for label, user, pwd, hosts in accounts:
        mail = None
        for host in hosts:
            try:
                m = imaplib.IMAP4_SSL(host, 993)
                m.login(user, pwd)
                mail = m
                break
            except Exception:
                continue
        if not mail:
            continue

        try:
            mail.select("INBOX")
            criterion = "UNSEEN" if unread_only else "ALL"
            status, messages = mail.search(None, criterion)
            if status != "OK" or not messages or not messages[0]:
                mail.logout()
                continue

            email_ids = messages[0].split()
            recent_ids = list(reversed(email_ids[-max(max_items * 2, 10):]))

            for e_id in recent_ids:
                if len(collected) >= max_items:
                    break
                status, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        raw_subject = msg.get("Subject", "(No Subject)") or "(No Subject)"
                        subject, enc = decode_header(raw_subject)[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(enc or "utf-8", errors="ignore")

                        raw_from = msg.get("From", "") or ""
                        from_header, enc = decode_header(raw_from)[0]
                        if isinstance(from_header, bytes):
                            from_header = from_header.decode(enc or "utf-8", errors="ignore")

                        date_hdr = msg.get("Date", "")

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try:
                                        body = part.get_payload(decode=True).decode(errors="ignore")
                                        break
                                    except Exception:
                                        pass
                        else:
                            try:
                                body = msg.get_payload(decode=True).decode(errors="ignore")
                            except Exception:
                                pass

                        clean_b = _clean_text(body, 350)
                        if q_low and q_low not in subject.lower() and q_low not in from_header.lower() and q_low not in clean_b.lower():
                            continue

                        collected.append({
                            "source": label,
                            "from": from_header,
                            "subject": subject,
                            "received": date_hdr,
                            "unread": unread_only,
                            "preview": clean_b,
                        })
            mail.logout()
        except Exception:
            try:
                mail.logout()
            except Exception:
                pass

    return collected


def _inspect_live_mail_window(provider: str = "outlook", launch_if_closed: bool = False) -> str:
    """
    Uses Windows UI Automation (agent_desktop) + Vision to read emails directly from an open
    New Windows Outlook (olk.exe) or browser mail tab when COM/IMAP credentials are not set.
    """
    try:
        import pygetwindow as gw
        all_wins = gw.getAllWindows()
        mail_wins = [
            w for w in all_wins
            if w.title and any(k in w.title.lower() for k in ("outlook", "mail", "inbox", "gmail"))
        ]
        if not mail_wins and launch_if_closed:
            from actions.open_app import open_app
            open_app({"app_name": "Outlook" if provider == "outlook" else "Gmail"})
            time.sleep(2.5)
            mail_wins = [
                w for w in gw.getAllWindows()
                if w.title and any(k in w.title.lower() for k in ("outlook", "mail", "inbox", "gmail"))
            ]

        if not mail_wins:
            return ""

        win = mail_wins[0]
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.4)

        from actions.agent_desktop import agent_desktop_control
        snap = agent_desktop_control({"action": "snapshot", "app": win.title})
        if snap and len(snap) > 80:
            return f"Live Mail Window ('{win.title}'):\n{snap[:2200]}"
    except Exception:
        pass
    return ""


def scan_unread_messages_across_apps() -> str:
    """
    Scans open desktop communication apps (WhatsApp, Microsoft Teams, Discord, Telegram, Slack, Outlook)
    for unread message badges in window titles and UI Automation trees.
    """
    unread_reports = []
    try:
        import pygetwindow as gw
        comm_keywords = ("whatsapp", "discord", "telegram", "teams", "slack", "outlook", "gmail", "inbox")
        for w in gw.getAllWindows():
            title = (w.title or "").strip()
            if not title:
                continue
            t_low = title.lower()
            if any(k in t_low for k in comm_keywords):
                badge_m = re.search(r"\((\d+)\)", title)
                if badge_m:
                    count = badge_m.group(1)
                    unread_reports.append(f"• **{title}** — {count} unread notification(s) detected")
                else:
                    unread_reports.append(f"• **{title}** — Window active (no unread badge in title)")
    except Exception:
        pass

    if not unread_reports:
        return "No active messaging windows with unread badges detected right now."
    return "Live Messaging & Mail Window Scan:\n" + "\n".join(unread_reports)


def email_triage(parameters: dict, player=None) -> str:
    """
    Universal Email, Outlook & Unread Message Triage Handler.
    parameters:
        action       : read_unread (default) | read_all | outlook | unread_outlook | gmail | search | missed_meetings | unread_messages
        provider     : auto | outlook | gmail
        query        : Optional keyword/sender filter
        max_emails   : Max emails to fetch (default 6)
        open_client  : Set True to visibly open Outlook/Gmail if no background session is found
    """
    params = parameters or {}
    action = (params.get("action") or "read_unread").lower().strip()
    provider = (params.get("provider") or "auto").lower().strip()
    query = (params.get("query") or "").strip()
    max_emails = int(params.get("max_emails", 6))
    open_client = bool(params.get("open_client", False))

    if "outlook" in action:
        provider = "outlook"
    elif "gmail" in action:
        provider = "gmail"

    unread_only = action not in ("read_all", "all", "recent", "search", "outlook_all")
    if action == "missed_meetings":
        unread_only = False
        if not query:
            query = "meeting"

    if player and hasattr(player, "write_log"):
        player.write_log(f"MAIL [{provider.upper()}/{action.upper()}]: Scanning inbox...")

    # 1. If specifically asking for cross-app unread messages (WhatsApp, Discord, Teams, Telegram + Mail)
    if action in ("unread_messages", "messages", "check_messages"):
        msg_scan = scan_unread_messages_across_apps()
        mail_items = _read_outlook_desktop_com(unread_only=True, max_items=4) or _read_imap_emails(provider="auto", unread_only=True, max_items=4)
        if mail_items:
            lines = [f"• [{m['source']}] From: {m['from']} | Subject: {m['subject']}" for m in mail_items]
            return f"{msg_scan}\n\nUnread Emails ({len(mail_items)}):\n" + "\n".join(lines)
        return msg_scan

    # 2. Try Native Outlook Desktop COM first (when provider is auto or outlook)
    emails = []
    if provider in ("auto", "outlook"):
        emails.extend(_read_outlook_desktop_com(unread_only=unread_only, max_items=max_emails, search_query=query))

    # 3. Also query IMAP (Gmail / Office365) if configured
    if len(emails) < max_emails:
        imap_items = _read_imap_emails(
            provider=provider,
            unread_only=unread_only,
            max_items=max_emails - len(emails),
            search_query=query,
        )
        emails.extend(imap_items)

    # 4. If missed_meetings requested, also scan for Zoom / Google Meet / Teams keywords
    if action == "missed_meetings" and not emails:
        for kw in ("zoom", "meet.google", "teams", "invite", "calendar"):
            emails.extend(_read_outlook_desktop_com(unread_only=False, max_items=3, search_query=kw))
            emails.extend(_read_imap_emails(provider=provider, unread_only=False, max_items=3, search_query=kw))
            if emails:
                break

    if emails:
        formatted = []
        for idx, e in enumerate(emails[:max_emails], 1):
            status_tag = "UNREAD" if e.get("unread") else "READ"
            formatted.append(
                f"{idx}. [{e['source']} — {status_tag}] From: {e['from']}\n"
                f"   Subject: {e['subject']} ({e.get('received', '')})\n"
                f"   Preview: {e['preview']}"
            )
        header = f"Found {len(emails)} {'unread ' if unread_only else ''}{provider.title() if provider != 'auto' else ''} email(s):\n\n"
        return header + "\n\n".join(formatted)

    # 5. Live Window UI Automation fallback (if New Windows Outlook or Web Mail is open)
    live_snap = _inspect_live_mail_window(provider=provider if provider != "auto" else "outlook", launch_if_closed=open_client)
    if live_snap:
        return live_snap

    msg_scan = scan_unread_messages_across_apps()
    return (
        f"No {'unread ' if unread_only else ''}emails found via local Outlook MAPI or IMAP "
        f"(add 'email_address'/'email_app_password' or 'outlook_email'/'outlook_password' in config/api_keys.json, "
        f"or open Outlook/Gmail on screen for live visual reading).\n\n{msg_scan}"
    )
