# actions/open_app.py
# MARK LVIII — Universal Zero-Latency Laptop App Launcher & Lifecycle Hook
# Directly hooked into Akul's Dell 15 (C: & D: drives, MSIX Store Apps, Registry Store & Start Menu)

import os
import time
import shutil
import platform
import subprocess
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

# ==============================================================================
# 1. EXACT DIRECT EXECUTABLE PATHS DISCOVERED ON AKUL'S LAPTOP (C: & D: DRIVES)
# ==============================================================================
_DIRECT_LAPTOP_PATHS = {
    # Academic & Custom Platforms
    "stunt": [
        r"C:\Users\Akul\OneDrive\Desktop\STUNT\STUNT.exe",
        r"C:\Users\Akul\OneDrive\Desktop\Developer Work\STUNT\STUNT.exe",
        r"C:\Users\Akul\Desktop\STUNT\dist\STUNT.exe",
        r"C:\Users\Akul\OneDrive\Desktop\STUNT.exe",
    ],
    # Creative & Design Suite
    "davinci":         [r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"],
    "davinci resolve": [r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"],
    "resolve":         [r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"],
    "canva":           [r"C:\Users\Akul\AppData\Local\Programs\Canva\Canva.exe"],
    "musehub":         [r"C:\Program Files\MuseHub\current\MuseHub.exe"],
    "audacity":        [r"C:\Program Files\MuseHub\current\MuseHub.exe"],
    "wallpaper engine": [
        r"D:\STEAM\steamapps\common\wallpaper_engine\wallpaperui.exe",
        r"D:\STEAM\steamapps\common\wallpaper_engine\bin\wallpaperui.exe",
        r"D:\STEAM\steamapps\common\wallpaper_engine\launcher.exe",
    ],

    # Coding, AI & Developer Tools
    "antigravity": [
        r"C:\Users\Akul\AppData\Local\Programs\antigravity\Antigravity.exe",
        r"C:\Users\Akul\AppData\Local\Programs\Antigravity IDE\Antigravity IDE.exe",
    ],
    "antigravity ide": [
        r"C:\Users\Akul\AppData\Local\Programs\Antigravity IDE\Antigravity IDE.exe",
        r"C:\Users\Akul\AppData\Local\Programs\antigravity\Antigravity.exe",
    ],
    "vscode":             [r"C:\Users\Akul\AppData\Local\Programs\Microsoft VS Code\Code.exe"],
    "visual studio code": [r"C:\Users\Akul\AppData\Local\Programs\Microsoft VS Code\Code.exe"],
    "code":               [r"C:\Users\Akul\AppData\Local\Programs\Microsoft VS Code\Code.exe"],
    "android studio":     [r"C:\Program Files\Android\Android Studio\bin\studio64.exe"],
    "git bash":           [r"C:\Program Files\Git\git-bash.exe"],
    "nodejs":             [r"C:\Program Files\nodejs\node.exe"],

    # Browsers
    "chrome":        [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
    "google chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
    "brave":         [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"],
    "brave browser": [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"],
    "edge":          [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
    "microsoft edge":[r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
    "opera":         [r"C:\Users\Akul\AppData\Local\Programs\Opera GX\opera.exe"],
    "opera gx":      [r"C:\Users\Akul\AppData\Local\Programs\Opera GX\opera.exe"],
    "tor":           [r"C:\Users\Akul\OneDrive\Desktop\TOR\Tor Browser\Browser\firefox.exe"],
    "tor browser":   [r"C:\Users\Akul\OneDrive\Desktop\TOR\Tor Browser\Browser\firefox.exe"],

    # Microsoft Office 2024 Suite
    "word":               [r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
    "microsoft word":     [r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
    "excel":              [r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
    "microsoft excel":    [r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
    "powerpoint":         [r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"],
    "microsoft powerpoint":[r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"],
    "onenote":            [r"C:\Program Files\Microsoft Office\root\Office16\ONENOTE.EXE"],
    "onedrive":           [r"C:\Users\Akul\AppData\Local\Microsoft\OneDrive\OneDrive.exe"],

    # Communication & Conferencing
    "discord":       [r"C:\Users\Akul\AppData\Local\Discord\Discord.exe"],
    "zoom":          [r"C:\Users\Akul\AppData\Roaming\Zoom\bin\Zoom.exe"],
    "zoom meetings": [r"C:\Users\Akul\AppData\Roaming\Zoom\bin\Zoom.exe"],

    # Gaming & Launchers (C: & D: Drives)
    "steam":                   [r"D:\STEAM\steam.exe"],
    "ea":                      [r"C:\Program Files\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe"],
    "ea app":                  [r"C:\Program Files\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe"],
    "ea desktop":              [r"C:\Program Files\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe"],
    "fc 26":                   [r"D:\EA SPORTS FC 26\FC26.exe"],
    "fc26":                    [r"D:\EA SPORTS FC 26\FC26.exe"],
    "fifa":                    [r"D:\EA SPORTS FC 26\FC26.exe"],
    "ea sports fc 26":         [r"D:\EA SPORTS FC 26\FC26.exe"],
    "rockstar":                [r"C:\Program Files\Rockstar Games\Launcher\Launcher.exe"],
    "rockstar games launcher": [r"C:\Program Files\Rockstar Games\Launcher\Launcher.exe"],
    "red dead redemption":     [r"D:\XboxGames\Red Dead Redemption (PC)\Content\Redistributables\Rockstar-Games-Launcher.exe"],
    "rdr":                     [r"D:\XboxGames\Red Dead Redemption (PC)\Content\Redistributables\Rockstar-Games-Launcher.exe"],
    "lunar":                   [r"C:\Users\Akul\AppData\Local\Programs\Lunar Client\Lunar Client.exe"],
    "lunar client":            [r"C:\Users\Akul\AppData\Local\Programs\Lunar Client\Lunar Client.exe"],
    "modrinth":                [r"C:\Users\Akul\AppData\Local\Modrinth App\Modrinth App.exe"],
    "modrinth app":            [r"C:\Users\Akul\AppData\Local\Modrinth App\Modrinth App.exe"],
    "tlauncher":               [r"C:\Users\Akul\AppData\Roaming\.minecraft\TLauncher.exe"],
    "minecraft":               [
        r"D:\XboxGames\Minecraft Launcher\Content\gamelaunchhelper.exe",
        r"D:\XboxGames\Minecraft- Java Edition\Content\gamelaunchhelper.exe",
        r"C:\Users\Akul\AppData\Local\Programs\Lunar Client\Lunar Client.exe",
    ],
    "call of duty": [
        r"D:\XboxGames\Call of Duty- Modern Warfare 2\Content\gamelaunchhelper.exe",
        r"D:\XboxGames\Call of Duty\Content\gamelaunchhelper.exe",
    ],
    "cod": [
        r"D:\XboxGames\Call of Duty- Modern Warfare 2\Content\gamelaunchhelper.exe",
        r"D:\XboxGames\Call of Duty\Content\gamelaunchhelper.exe",
    ],
    "modern warfare 2": [r"D:\XboxGames\Call of Duty- Modern Warfare 2\Content\gamelaunchhelper.exe"],
    "mw2":              [r"D:\XboxGames\Call of Duty- Modern Warfare 2\Content\gamelaunchhelper.exe"],
    "flight simulator": [r"D:\XboxGames\Microsoft Flight Simulator 2024\Content\flightsimulator2024.exe"],
    "msfs":             [r"D:\XboxGames\Microsoft Flight Simulator 2024\Content\flightsimulator2024.exe"],
    "no man's sky":     [r"D:\XboxGames\No Man's Sky\Content\Binaries\NMS.exe"],
    "nms":              [r"D:\XboxGames\No Man's Sky\Content\Binaries\NMS.exe"],
    "asphalt":          [r"D:\XboxGames\Asphalt Legends\Content\gamelaunchhelper.exe"],
    "asphalt legends":  [r"D:\XboxGames\Asphalt Legends\Content\gamelaunchhelper.exe"],
    "fall again":       [r"D:\STEAM\steamapps\common\Fall Again\FallAgain\Binaries\Win64\FallAgain-Win64-Shipping.exe"],
    "meccha chameleon": [r"D:\STEAM\steamapps\common\MECCHA CHAMELEON\Chameleon\Binaries\Win64\PenguinHotel-Win64-Shipping.exe"],

    # Utilities & Hardware Suites
    "logi options":     [r"C:\Program Files\LogiOptionsPlus\logioptionsplus.exe"],
    "logi options+":    [r"C:\Program Files\LogiOptionsPlus\logioptionsplus.exe"],
    "dell optimizer":   [r"C:\Program Files\Dell\DellOptimizer\Console\DellOptimizer.ThickClient.exe"],
}

# ==============================================================================
# 2. INSTANT WINDOWS URI SCHEMES & MSIX APP USER MODEL IDS (0.05s LAUNCH)
# ==============================================================================
_WINDOWS_URI_AND_AUMID = {
    "whatsapp":         "whatsapp:",
    "spotify":          "spotify:",
    "telegram":         "tg:",
    "phone link":       "ms-phone:",
    "your phone":       "ms-phone:",
    "outlook":          "ms-outlook:",
    "mail":             "ms-outlook:",
    "teams":            "msteams:",
    "microsoft teams":  "msteams:",
    "todo":             "ms-todo:",
    "to do":            "ms-todo:",
    "microsoft to do":  "ms-todo:",
    "settings":         "ms-settings:",
    "snipping tool":    "ms-screenclip:",
    "calculator":       "calculator:",
    "calc":             "calculator:",
    "camera":           "microsoft.windows.camera:",
    "photos":           "ms-photos:",
    "clock":            "ms-clock:",
    "store":            "ms-windows-store:",
    "microsoft store":  "ms-windows-store:",
    "xbox":             "xbox:",
    "claude":           r"shell:AppsFolder\AnthropicPBC.Claude_fnn82j28hfe8t!Claude",
    "clipchamp":        r"shell:AppsFolder\Clipchamp.Clipchamp_yxz26nhyzhsrt!App",
    "linkedin":         r"shell:AppsFolder\7EE7776C.LinkedInforWindows_w1wdnht996qgy!App",
    "prime video":      r"shell:AppsFolder\AmazonVideo.PrimeVideo_pwbj9vvecjh7j!App",
    "lively":           r"shell:AppsFolder\12030rocksdanister.LivelyWallpaper_97hta09mmv6hy!App",
    "lively wallpaper": r"shell:AppsFolder\12030rocksdanister.LivelyWallpaper_97hta09mmv6hy!App",
    "sticky notes":     r"shell:AppsFolder\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe!App",
    "copilot":          r"shell:AppsFolder\Microsoft.MicrosoftOfficeHub_8wekyb3d8bbwe!Microsoft.MicrosoftOfficeHub",
    "terminal":         "wt.exe",
    "windows terminal": "wt.exe",
    "cmd":              "cmd.exe",
    "powershell":       "powershell.exe",
    "notepad":          "notepad.exe",
    "paint":            "mspaint.exe",
    "task manager":     "taskmgr.exe",
    "explorer":         "explorer.exe",
    "file explorer":    "explorer.exe",
    "control panel":    "control.exe",
    "this pc":          "shell:MyComputerFolder",
    "downloads":        "shell:Downloads",
    "recycle bin":      "shell:RecycleBinFolder",
}

# Process-name mapping for closing / focusing apps
_PROCESS_NAMES = {
    "stunt": "STUNT.exe",
    "davinci": "Resolve.exe",
    "davinci resolve": "Resolve.exe",
    "canva": "Canva.exe",
    "vscode": "Code.exe",
    "visual studio code": "Code.exe",
    "antigravity": "Antigravity.exe",
    "chrome": "chrome.exe",
    "brave": "brave.exe",
    "edge": "msedge.exe",
    "opera": "opera.exe",
    "opera gx": "opera.exe",
    "discord": "Discord.exe",
    "spotify": "Spotify.exe",
    "whatsapp": "WhatsApp.Root.exe",
    "telegram": "Telegram.exe",
    "claude": "claude.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "onenote": "ONENOTE.EXE",
    "outlook": "olk.exe",
    "steam": "steam.exe",
    "wallpaper engine": "wallpaperui.exe",
    "lunar client": "Lunar Client.exe",
    "modrinth": "Modrinth App.exe",
    "tlauncher": "TLauncher.exe",
    "zoom": "Zoom.exe",
}

_DYNAMIC_CACHE: dict[str, str] = {}


def _scan_dynamic_apps() -> dict[str, str]:
    """
    Lazily indexes Start Menu .lnk shortcuts and Registry AppCompatFlags/MuiCache
    so even newly installed applications launch directly without blind keyboard typing.
    """
    if _DYNAMIC_CACHE:
        return _DYNAMIC_CACHE

    # 1. Start Menu .lnk files
    start_dirs = [
        Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
        Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs",
        Path.home() / "Desktop",
        Path.home() / "OneDrive" / "Desktop",
    ]
    for d in start_dirs:
        if d.exists():
            try:
                for lnk in d.rglob("*.lnk"):
                    stem = lnk.stem.lower().strip()
                    if stem and "uninstall" not in stem:
                        _DYNAMIC_CACHE[stem] = str(lnk)
            except Exception:
                pass

    # 2. Windows Registry AppCompatFlags Store (exact .exe paths used on this machine)
    if platform.system() == "Windows":
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
                i = 0
                while True:
                    try:
                        val_name, _, _ = winreg.EnumValue(k, i)
                        i += 1
                        if val_name.lower().endswith(".exe") and Path(val_name).exists():
                            stem = Path(val_name).stem.lower()
                            if stem not in ("setup", "uninstall", "unins000", "update"):
                                _DYNAMIC_CACHE.setdefault(stem, val_name)
                    except OSError:
                        break
        except Exception:
            pass

    return _DYNAMIC_CACHE


def _try_registry_launch(app_name: str) -> bool:
    """Try to find and launch an app via Windows Registry App Paths."""
    try:
        import winreg
        clean = app_name.lower().replace(".exe", "")
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key = winreg.OpenKey(
                    root,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\\" + clean + ".exe",
                )
                path = winreg.QueryValue(key, None)
                if path and Path(path.strip('"')).exists():
                    subprocess.Popen(
                        [path.strip('"')],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _launch_windows(raw_name: str) -> tuple[bool, str]:
    key = raw_name.lower().strip()

    # 1. Exact Direct Laptop Path Match (or substring match)
    candidates = _DIRECT_LAPTOP_PATHS.get(key)
    if not candidates:
        for k, paths in _DIRECT_LAPTOP_PATHS.items():
            if k == key or (len(key) >= 4 and (key in k or k in key)):
                candidates = paths
                break

    if candidates:
        for exe_path in candidates:
            p = Path(exe_path)
            if p.exists():
                subprocess.Popen(
                    [str(p)],
                    cwd=str(p.parent),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, f"Direct path ({p.name})"

    # 2. Instant Windows Protocol URI or MSIX AppUserModelId
    uri_target = _WINDOWS_URI_AND_AUMID.get(key)
    if not uri_target:
        for k, u in _WINDOWS_URI_AND_AUMID.items():
            if k == key or (len(key) >= 4 and (key in k or k in key)):
                uri_target = u
                break

    if uri_target:
        try:
            if uri_target.endswith(":") or uri_target.startswith("ms-") or uri_target.startswith("microsoft."):
                os.startfile(uri_target)
                return True, f"Protocol URI ({uri_target})"
            elif uri_target.startswith("shell:"):
                subprocess.Popen(
                    ["explorer.exe", uri_target],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, f"Shell AppFolder ({uri_target})"
            else:
                subprocess.Popen(
                    [uri_target],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, f"System binary ({uri_target})"
        except Exception:
            pass

    # 3. Windows Registry App Paths
    if _try_registry_launch(key):
        return True, "Registry App Paths"

    # 4. System PATH lookup (shutil.which)
    which_bin = shutil.which(key) or shutil.which(key.replace(" ", ""))
    if which_bin:
        try:
            subprocess.Popen([which_bin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"System PATH ({Path(which_bin).name})"
        except Exception:
            pass

    # 5. Dynamic Start Menu .lnk & Registry AppCompat Store
    dyn = _scan_dynamic_apps()
    matched_target = dyn.get(key)
    if not matched_target:
        for k, target_path in dyn.items():
            if key in k or k in key:
                matched_target = target_path
                break

    if matched_target and Path(matched_target).exists():
        try:
            if matched_target.lower().endswith(".lnk"):
                os.startfile(matched_target)
            else:
                subprocess.Popen(
                    [matched_target],
                    cwd=str(Path(matched_target).parent),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return True, f"Discovered shortcut ({Path(matched_target).name})"
        except Exception:
            pass

    return False, "Not found in direct paths, URI schemes, or Start Menu"


def _close_windows_app(app_name: str) -> str:
    key = app_name.lower().strip()
    proc_target = _PROCESS_NAMES.get(key, f"{key.replace(' ', '')}.exe").lower()
    closed = []
    if _PSUTIL:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info["name"] or "").lower()
                if pname == proc_target or key in pname:
                    proc.terminate()
                    closed.append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    if closed:
        return f"Closed {', '.join(sorted(set(closed)))}, sir."
    return f"No running process matching '{app_name}' was found."


def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    app_name = (params.get("app_name") or params.get("name") or params.get("target") or "").strip()
    action = (params.get("action") or "open").lower().strip()

    if action in ("list", "installed", "list_apps"):
        known = sorted(set(list(_DIRECT_LAPTOP_PATHS.keys()) + list(_WINDOWS_URI_AND_AUMID.keys())))
        return f"JARVIS has {len(known)} pre-mapped laptop applications & games ready for instant launch: " + ", ".join(known[:40])

    if not app_name:
        return "Please specify which application to open, sir."

    if action in ("close", "quit", "kill", "exit"):
        if player:
            player.write_log(f"APP // CLOSE {app_name.upper()}")
        return _close_windows_app(app_name)

    if action in ("focus", "switch", "bring_to_front"):
        try:
            from actions.agent_desktop import agent_desktop_control
            return agent_desktop_control({"action": "focus_window", "app": app_name}, player=player)
        except Exception as e:
            return f"Could not focus {app_name}: {e}"

    if player:
        player.write_log(f"APP // LAUNCH {app_name.upper()}")

    if platform.system() == "Windows":
        ok, method = _launch_windows(app_name)
        if ok:
            return f"Launched {app_name} ({method}), sir."
        return f"Could not locate '{app_name}' on your laptop. Say 'list installed apps' to see all mapped applications."

    return f"Unsupported OS for direct launch: {platform.system()}"
