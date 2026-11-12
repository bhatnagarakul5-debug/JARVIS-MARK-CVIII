# actions/send_message.py
# MARK LVIII — Universal Multi-App Messaging & Calling Engine
# Supports: WhatsApp, Discord (Ctrl+K), Telegram, Microsoft Teams (Ctrl+E),
# Slack (Ctrl+K), Instagram, LinkedIn, Phone Link, and Active Window Chat.
# Uses Zero-Latency URI/Direct Launch + Native UIA (agent_desktop) + Clipboard Paste (Ctrl+V).

import time
import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.04


def _paste_text(text: str):
    """Pastes Unicode/emoji/symbol text instantaneously via clipboard without dropping characters."""
    if not text:
        return
    old_clip = ""
    try:
        old_clip = pyperclip.paste()
    except Exception:
        pass
    try:
        pyperclip.copy(str(text))
        time.sleep(0.06)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.12)
    except Exception:
        pyautogui.write(str(text), interval=0.02)
    finally:
        # Restore previous clipboard after a short delay
        if old_clip:
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass


def _launch_and_focus_app(app_name: str, wait_sec: float = 1.4) -> bool:
    """Focuses an already-open window or launches the app directly via open_app (no blind Win-key typing)."""
    # 1. Try pygetwindow focus first if already running
    try:
        import pygetwindow as gw
        wins = [w for w in gw.getWindowsWithTitle(app_name) if w.title]
        if wins:
            win = wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.35)
            return True
    except Exception:
        pass

    # 2. Try native UIA focus_window
    try:
        from actions.agent_desktop import get_agent_desktop
        res = get_agent_desktop().focus_window(app_name)
        if res.get("ok"):
            time.sleep(0.35)
            return True
    except Exception:
        pass

    # 3. Launch via Direct Path / Protocol URI engine
    try:
        from actions.open_app import open_app
        open_app({"app_name": app_name})
        time.sleep(wait_sec)
        try:
            from actions.agent_desktop import get_agent_desktop
            get_agent_desktop().focus_window(app_name)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[SendMessage] Launch error for {app_name}: {e}")
        return False


def _send_whatsapp(receiver: str, message: str, player=None) -> str:
    """
    Sends a WhatsApp message via Windows WhatsApp Desktop (MSIX).
    Uses instant URI launch + Ctrl+F search + clipboard paste + UIA verification.
    """
    try:
        if not _launch_and_focus_app("WhatsApp", wait_sec=1.8):
            return "Could not open WhatsApp Desktop."

        time.sleep(0.4)
        # 1. Focus Search Bar (Ctrl+F in WhatsApp Desktop)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.25)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        time.sleep(0.1)

        # 2. Paste contact name and select first result
        _paste_text(receiver)
        time.sleep(0.75)
        pyautogui.press("down")
        time.sleep(0.15)
        pyautogui.press("enter")
        time.sleep(0.55)

        # 3. Try UIA focus on message input box if available, then paste & send
        try:
            from actions.agent_desktop import get_agent_desktop
            ad = get_agent_desktop()
            f_res = ad.find("Type a message", app="WhatsApp")
            if f_res.get("ok"):
                matches = f_res.get("data", {}).get("matches", [])
                if matches:
                    ref = matches[0].get("ref_id") or matches[0].get("ref")
                    if ref:
                        ad.click(ref)
                        time.sleep(0.15)
        except Exception:
            pass

        _paste_text(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return f"Sent message to {receiver} on WhatsApp."
    except Exception as e:
        return f"WhatsApp messaging error: {e}"


def _send_discord(receiver: str, message: str, player=None) -> str:
    """
    Sends a Discord DM or channel message via Discord Desktop.
    Uses Discord's native Quick Switcher (Ctrl+K) -> Paste receiver -> Enter -> Paste message -> Enter.
    """
    try:
        if not _launch_and_focus_app("Discord", wait_sec=2.0):
            return "Could not open Discord."

        time.sleep(0.45)
        # Clear any open modal, then open Discord Quick Switcher (Ctrl+K)
        pyautogui.press("escape")
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.35)

        _paste_text(receiver)
        time.sleep(0.65)
        pyautogui.press("enter")
        time.sleep(0.65)

        _paste_text(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return f"Sent message to {receiver} on Discord."
    except Exception as e:
        return f"Discord messaging error: {e}"


def _send_telegram(receiver: str, message: str, player=None) -> str:
    """Sends a Telegram message via Telegram Desktop."""
    try:
        if not _launch_and_focus_app("Telegram", wait_sec=1.6):
            return "Could not open Telegram Desktop."

        time.sleep(0.4)
        pyautogui.press("escape")
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.25)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")

        _paste_text(receiver)
        time.sleep(0.75)
        pyautogui.press("down")
        time.sleep(0.15)
        pyautogui.press("enter")
        time.sleep(0.5)

        _paste_text(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return f"Sent message to {receiver} on Telegram."
    except Exception as e:
        return f"Telegram messaging error: {e}"


def _send_teams(receiver: str, message: str) -> str:
    """Sends a message via Microsoft Teams (Ctrl+E search bar)."""
    try:
        if not _launch_and_focus_app("Microsoft Teams", wait_sec=2.2):
            return "Could not open Microsoft Teams."

        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "e")
        time.sleep(0.35)
        _paste_text(receiver)
        time.sleep(0.8)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.7)

        _paste_text(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return f"Sent message to {receiver} on Microsoft Teams."
    except Exception as e:
        return f"Teams messaging error: {e}"


def _send_slack(receiver: str, message: str) -> str:
    """Sends a message via Slack Quick Switcher (Ctrl+K)."""
    try:
        if not _launch_and_focus_app("Slack", wait_sec=1.8):
            return "Could not open Slack."

        time.sleep(0.4)
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.35)
        _paste_text(receiver)
        time.sleep(0.65)
        pyautogui.press("enter")
        time.sleep(0.6)

        _paste_text(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return f"Sent message to {receiver} on Slack."
    except Exception as e:
        return f"Slack messaging error: {e}"


def _send_instagram(receiver: str, message: str) -> str:
    """Sends an Instagram DM via browser."""
    try:
        import webbrowser
        webbrowser.open("https://www.instagram.com/direct/new/")
        time.sleep(3.2)
        _paste_text(receiver)
        time.sleep(1.2)
        pyautogui.press("down")
        time.sleep(0.25)
        pyautogui.press("enter")
        time.sleep(0.4)
        for _ in range(3):
            pyautogui.press("tab")
            time.sleep(0.08)
        pyautogui.press("enter")
        time.sleep(1.2)
        _paste_text(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return f"Sent Instagram DM to {receiver}."
    except Exception as e:
        return f"Instagram error: {e}"


def _send_active_window(message: str, target_field: str = "") -> str:
    """Types and sends text directly into the currently active chat/application window without losing focus."""
    try:
        if target_field:
            try:
                from actions.agent_desktop import get_agent_desktop
                ad = get_agent_desktop()
                f_res = ad.find(target_field)
                if f_res.get("ok"):
                    matches = f_res.get("data", {}).get("matches", [])
                    if matches:
                        ref = matches[0].get("ref_id") or matches[0].get("ref")
                        if ref:
                            ad.click(ref)
                            time.sleep(0.12)
            except Exception:
                pass
        _paste_text(message)
        time.sleep(0.12)
        pyautogui.press("enter")
        return f"Sent text into active window: '{message[:40]}'"
    except Exception as e:
        return f"Active window text error: {e}"


def _send_generic(platform_name: str, receiver: str, message: str) -> str:
    """
    Universal fallback for any other messaging app (LinkedIn, Signal, Messenger, etc.).
    Uses open_app + UIA search/input detection + clipboard paste.
    """
    try:
        if not _launch_and_focus_app(platform_name, wait_sec=1.8):
            return f"Could not open {platform_name}."

        time.sleep(0.5)
        if receiver:
            # Try UIA find on contact name first
            clicked_contact = False
            try:
                from actions.agent_desktop import get_agent_desktop
                ad = get_agent_desktop()
                f_res = ad.find(receiver, app=platform_name)
                if f_res.get("ok"):
                    matches = f_res.get("data", {}).get("matches", [])
                    if matches:
                        ref = matches[0].get("ref_id") or matches[0].get("ref")
                        if ref and ad.click(ref).get("ok"):
                            clicked_contact = True
                            time.sleep(0.45)
            except Exception:
                pass

            if not clicked_contact:
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                _paste_text(receiver)
                time.sleep(0.75)
                pyautogui.press("down")
                time.sleep(0.15)
                pyautogui.press("enter")
                time.sleep(0.55)

        _paste_text(message)
        time.sleep(0.15)
        pyautogui.press("enter")
        return f"Sent message to {receiver or 'active chat'} via {platform_name}."
    except Exception as e:
        return f"{platform_name} messaging error: {e}"


def unlock_whatsapp_locked_chats(passcode: str = "", contact: str = "", message: str = "") -> str:
    """
    Accesses WhatsApp Locked Chats using user passcode,
    unlocks the vault, and optionally opens a contact and sends a reply.
    """
    try:
        from actions.whatsapp_reader import unlock_locked_chats
        ok = unlock_locked_chats(passcode=passcode)
        if not ok:
            return "Could not focus or unlock WhatsApp Locked Chats."

        if contact:
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.25)
            pyautogui.hotkey("ctrl", "a")
            _paste_text(contact)
            time.sleep(0.7)
            pyautogui.press("down")
            time.sleep(0.15)
            pyautogui.press("enter")
            time.sleep(0.5)
            if message:
                _paste_text(message)
                time.sleep(0.15)
                pyautogui.press("enter")
                return f"Unlocked Locked Chats, opened '{contact}', and sent message."
            return f"Unlocked Locked Chats and opened '{contact}'."

        return "WhatsApp Locked Chats vault unlocked."
    except Exception as e:
        return f"Failed to unlock Locked Chats: {e}"


def send_message(parameters: dict, player=None) -> str:
    """
    Universal messaging handler across all desktop & web messaging apps.
    parameters:
        receiver     : Contact, username, or channel name to message (optional if platform='active')
        message_text : The message content to send
        platform     : whatsapp | discord | telegram | teams | slack | instagram | linkedin | active
        is_locked    : bool (if True, unlocks WhatsApp locked chats using user passcode)
        passcode     : str (passcode for locked chats)
    """
    params       = parameters or {}
    receiver     = (params.get("receiver") or params.get("contact") or params.get("to") or "").strip()
    message_text = (params.get("message_text") or params.get("message") or params.get("text") or "").strip()
    platform_str = (params.get("platform") or params.get("app") or "whatsapp").strip().lower()
    is_locked    = bool(params.get("is_locked", False) or "locked" in platform_str or "locked" in receiver.lower())
    passcode     = params.get("passcode", "")

    if is_locked:
        if player:
            player.write_log("MSG // UNLOCKING WHATSAPP VAULT")
        return unlock_whatsapp_locked_chats(passcode=passcode, contact=receiver, message=message_text)

    if not message_text:
        return "Please specify what message text to send, sir."

    if platform_str in ("active", "current", "here", "screen") or not receiver:
        if player:
            player.write_log("MSG // SENDING IN ACTIVE WINDOW")
        return _send_active_window(message_text, target_field=receiver)

    if player:
        player.write_log(f"MSG // {platform_str.upper()} -> {receiver.upper()}")

    if any(k in platform_str for k in ("whatsapp", "wp", "wapp")):
        result = _send_whatsapp(receiver, message_text, player=player)
    elif any(k in platform_str for k in ("discord", "dc")):
        result = _send_discord(receiver, message_text, player=player)
    elif any(k in platform_str for k in ("telegram", "tg")):
        result = _send_telegram(receiver, message_text, player=player)
    elif "team" in platform_str:
        result = _send_teams(receiver, message_text)
    elif "slack" in platform_str:
        result = _send_slack(receiver, message_text)
    elif any(k in platform_str for k in ("instagram", "ig", "insta")):
        result = _send_instagram(receiver, message_text)
    else:
        result = _send_generic(platform_str, receiver, message_text)

    if player:
        player.write_log(f"MSG // {result}")
    return result


def _call_whatsapp(contact: str, call_type: str = "audio") -> str:
    """Makes a WhatsApp audio/video call via Windows WhatsApp Desktop."""
    try:
        if not _launch_and_focus_app("WhatsApp", wait_sec=1.8):
            return "Could not open WhatsApp."
        time.sleep(0.5)

        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        _paste_text(contact)
        time.sleep(0.8)
        pyautogui.press("down")
        time.sleep(0.15)
        pyautogui.press("enter")
        time.sleep(0.7)

        # Try UIA button click first ('Audio call' / 'Video call' / 'Voice call')
        target_btn = "Video call" if call_type == "video" else "Audio call"
        clicked = False
        try:
            from actions.agent_desktop import get_agent_desktop
            ad = get_agent_desktop()
            for btn_lbl in ([target_btn, "Voice call", "Call"] if call_type != "video" else ["Video call"]):
                f_res = ad.find(btn_lbl, app="WhatsApp")
                if f_res.get("ok"):
                    matches = f_res.get("data", {}).get("matches", [])
                    if matches:
                        ref = matches[0].get("ref_id") or matches[0].get("ref")
                        if ref and ad.click(ref).get("ok"):
                            clicked = True
                            break
        except Exception:
            pass

        if not clicked:
            if call_type == "video":
                pyautogui.hotkey("ctrl", "shift", "v")
            else:
                pyautogui.hotkey("ctrl", "shift", "c")

        return f"{call_type.title()} call started to {contact} via WhatsApp."
    except Exception as e:
        return f"WhatsApp call error: {e}"


def _call_phone_link(contact: str) -> str:
    """Makes a phone call via the Phone Link (ms-phone:) Windows app."""
    try:
        if not _launch_and_focus_app("Phone Link", wait_sec=2.2):
            return "Could not open Phone Link."
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)
        _paste_text(contact)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(0.4)
        pyautogui.press("enter")
        return f"Call started to {contact} via Phone Link."
    except Exception as e:
        return f"Phone Link call error: {e}"


def make_call(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None
) -> str:
    params    = parameters or {}
    contact   = (params.get("contact") or params.get("receiver") or "").strip()
    platform  = (params.get("platform") or "whatsapp").strip().lower()
    call_type = (params.get("call_type") or "audio").strip().lower()

    if not contact:
        return "Please specify who to call, sir."

    if player:
        player.write_log(f"CALL // {platform.upper()} -> {contact.upper()}")

    if "phone" in platform or "link" in platform:
        result = _call_phone_link(contact)
    else:
        result = _call_whatsapp(contact, call_type)

    if player:
        player.write_log(f"CALL // {result}")
    return result
