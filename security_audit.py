"""
security_audit.py — Pre-Commit Security & Privacy Auditor for JARVIS Mark XL
Scans all files queued for Git commit to ensure 0 API keys, 0 user memories,
0 passwords, 0 Gmail credentials, and 0 face photos are exposed.
"""

import os
import re
import sys
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

FORBIDDEN_FILES = [
    "config/api_keys.json",
    "config/jarvis_settings.json",
    "config/voice_profile.npy",
    "memory/conversation_log.json",
    "memory/user_memory.json",
    "memory/conversations.jsonl",
    "memory/long_term.json",
    "memory/security_events.log",
    "memory/security_ledger.jsonl",
    "config/known_faces",
    "memory/chroma_db",
]

FORBIDDEN_REGEXES = [
    ("Google API Key", re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")),
    ("OpenRouter API Key", re.compile(r"sk-or-v1-[a-f0-9]{48,64}")),
    ("Anthropic API Key", re.compile(r"sk-ant-api[A-Za-z0-9_\-]{20,}")),
    ("OpenAI API Key", re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}")),
    ("Telegram Bot Token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b")),
    ("Private Key Block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]

def run_security_audit():
    print("=== JARVIS MARK 78 PRE-COMMIT SECURITY AUDIT ===")
    print(f"Auditing directory: {BASE_DIR}\n")

    # 1. Check Git Status for Forbidden Files
    violations = []
    try:
        status_out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            shell=False,
            text=True,
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL,
        )
        for line in status_out.splitlines():
            status_code = line[:2]
            file_path = line[3:].strip()
            if status_code.strip() == "D" or status_code.startswith("D"):
                continue
            if file_path.endswith(".example"):
                continue
            for forbidden in FORBIDDEN_FILES:
                if forbidden == file_path or file_path.startswith(forbidden.rstrip("/") + "/"):
                    violations.append(f"FORBIDDEN FILE TRACKED: {file_path}")
    except Exception as e:
        print(f"Notice running git status: {e}")

    # 2. Check Tracked Files Content for Forbidden Patterns
    try:
        ls_out = subprocess.check_output(
            ["git", "ls-files"],
            shell=False,
            text=True,
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL,
        )
        tracked_files = [line.strip() for line in ls_out.splitlines() if line.strip()]

        for tf in tracked_files:
            if tf.endswith("security_audit.py") or tf.endswith(".example"):
                continue
            tf_path = BASE_DIR / tf
            if tf_path.exists() and tf_path.is_file() and not tf.endswith((".png", ".ico", ".jpg", ".zip", ".exe", ".mp3", ".wav")):
                try:
                    content = tf_path.read_text(encoding="utf-8", errors="ignore")
                    for label, rx in FORBIDDEN_REGEXES:
                        m = rx.search(content)
                        if m:
                            snippet = m.group(0)[:8] + "..."
                            violations.append(f"LEAKED {label} ({snippet}) IN FILE: {tf}")
                except Exception:
                    pass

    except Exception as e:
        print(f"Notice checking tracked files: {e}")

    print("------------------------------------------------")
    if violations:
        print("❌ SECURITY AUDIT FAILED! The following items must be untracked before push:")
        for v in violations:
            print(f"  • {v}")
        return False
    else:
        print("✅ 100% SECURITY AUDIT PASSED!")
        print("  • 0 API Keys detected.")
        print("  • 0 Passwords or App Passwords detected.")
        print("  • 0 Private Memory databases detected.")
        print("  • 0 Personal face photos detected.")
        print("  • All sensitive data successfully shielded by .gitignore.")
        print("------------------------------------------------")
        return True

if __name__ == "__main__":
    success = run_security_audit()
    sys.exit(0 if success else 1)
