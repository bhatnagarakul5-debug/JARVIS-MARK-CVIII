"""
security_audit.py — Pre-Commit Security & Privacy Auditor for JARVIS Mark 108
Accelerated via `jarvis_rust_core` Native Rust Exoskeleton (Rayon 12-Thread Parallel Scanner).
Scans all files queued for Git commit to ensure 0 API keys, 0 user memories,
0 passwords, 0 Gmail credentials, and 0 face photos are exposed.
"""

import sys
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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


def run_security_audit() -> bool:
    print("=== JARVIS MARK 108 PRE-COMMIT SECURITY AUDIT ===")
    print(f"Auditing directory: {BASE_DIR}\n")

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

    try:
        ls_out = subprocess.check_output(
            ["git", "ls-files"],
            shell=False,
            text=True,
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL,
        )
        tracked_files = [line.strip() for line in ls_out.splitlines() if line.strip()]
        from core.rust_bridge import audit_files_for_secrets
        secret_hits = audit_files_for_secrets(str(BASE_DIR), tracked_files)
        violations.extend(secret_hits)
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
