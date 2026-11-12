from __future__ import annotations

import json
import math
import os
import platform
import re
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal, QUrl, QUrlQuery,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont,
    QKeySequence, QLinearGradient, QPainter, QPen, QRadialGradient, QRegion, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR      = _base_dir()
CONFIG_DIR    = BASE_DIR / "config"
API_FILE      = CONFIG_DIR / "api_keys.json"
ORB_CORE_HTML_PATH = CONFIG_DIR / "orb_core.html"
ORB_HTML_PATH = CONFIG_DIR / "orb_hud.html"
_OS           = platform.system()


class C:
    BG        = "#05080f"
    PANEL     = "#080d18"
    PANEL2    = "#0b1322"
    BORDER    = "#16384c"
    BORDER_B  = "#00d4ff"
    BORDER_A  = "#0e2938"
    PRI       = "#00d4ff"
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#071e2b"
    ACC       = "#f59e0b"
    ACC2      = "#fbbf24"
    GREEN     = "#10b981"
    RED       = "#ef4444"
    MUTED_C   = "#f43f5e"
    TEXT      = "#e2e8f0"
    TEXT_DIM  = "#64748b"
    TEXT_MED  = "#94a3b8"
    WHITE     = "#f8fafc"
    DARK      = "#03060b"
    BAR_BG    = "#0f172a"


def _fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024 ** 3:.2f} GB"


class SetupOverlay(QWidget):
    """First-boot API key configuration dialog (only instantiated if config/api_keys.json is missing)."""
    done = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(440, 320)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - 440) // 2, (screen.height() - 320) // 2)

        self.setStyleSheet(f"""
            SetupOverlay {{
                background: {C.BG};
                border: 1px solid {C.BORDER_B};
                border-radius: 4px;
            }}
        """)

        detected = {"darwin": "mac", "windows": "windows"}.get(_OS.lower(), "linux")
        self._sel_os = detected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)

        hdr = QLabel("MARK 108 // INITIALIZATION")
        hdr.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        layout.addWidget(hdr)

        sub = QLabel("Enter API credentials to initialize workstation core.")
        sub.setFont(QFont("Consolas", 8))
        sub.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        layout.addWidget(sub)

        lbl_g = QLabel("GEMINI API KEY")
        lbl_g.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        lbl_g.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        layout.addWidget(lbl_g)

        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza...")
        self._key_input.setFont(QFont("Consolas", 9))
        self._key_input.setFixedHeight(28)
        self._key_input.setStyleSheet(
            f"background: {C.DARK}; color: {C.WHITE}; border: 1px solid {C.BORDER}; padding: 2px 6px;"
        )
        layout.addWidget(self._key_input)

        lbl_o = QLabel("OPENROUTER API KEY")
        lbl_o.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        lbl_o.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        layout.addWidget(lbl_o)

        self._or_input = QLineEdit()
        self._or_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._or_input.setPlaceholderText("sk-or-...")
        self._or_input.setFont(QFont("Consolas", 9))
        self._or_input.setFixedHeight(28)
        self._or_input.setStyleSheet(
            f"background: {C.DARK}; color: {C.WHITE}; border: 1px solid {C.BORDER}; padding: 2px 6px;"
        )
        layout.addWidget(self._or_input)
        layout.addStretch()

        init_btn = QPushButton("INITIALIZE CORE")
        init_btn.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        init_btn.setFixedHeight(32)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(
            f"QPushButton {{ background: {C.PRI_GHO}; color: {C.PRI}; border: 1px solid {C.PRI}; }}"
            f"QPushButton:hover {{ background: {C.PRI}; color: {C.DARK}; }}"
        )
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _submit(self):
        key = self._key_input.text().strip()
        or_key = self._or_input.text().strip() or "local"
        if not key:
            return
        self.done.emit(key, or_key, self._sel_os)
        self.close()


class PrivacyVeilOverlay(QWidget):
    """Full-screen security shield engaged when Anti-Shoulder Surfer detects an onlooker."""
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setStyleSheet("background: rgba(3, 6, 11, 248);")

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setFixedSize(480, 220)
        card.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.RED}; border-radius: 4px;")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t1 = QLabel("SENTRY PRIVACY VEIL // ACTIVE")
        t1.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        t1.setStyleSheet(f"color: {C.RED}; border: none;")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(t1)

        t2 = QLabel("Unrecognized presence detected behind workstation.\nDisplay masked to protect active workspace.")
        t2.setFont(QFont("Consolas", 8))
        t2.setStyleSheet(f"color: {C.TEXT_MED}; border: none;")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(t2)

        btn = QPushButton("DISMISS [ESC]")
        btn.setFixedSize(160, 30)
        btn.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        btn.setStyleSheet(f"color: {C.RED}; background: {C.DARK}; border: 1px solid {C.RED};")
        btn.clicked.connect(self.dismissed.emit)
        c_lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(card)

    def mousePressEvent(self, _):
        self.dismissed.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.dismissed.emit()


class JarvisOpeningScreen(QWidget):
    """
    Architectural Stealth Boot Plate (520x200 px).
    Displays operator identity (AKUL) and core readiness for ~1.4s,
    then closes with WA_DeleteOnClose to free 100% of its memory.
    """
    def __init__(self, on_complete=None, parent=None):
        super().__init__(parent)
        self.on_complete = on_complete
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._w, self._h = 520, 200
        self.setFixedSize(self._w, self._h)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.left() + (screen.width() - self._w) // 2,
            screen.top() + (screen.height() - self._h) // 2,
        )

        self._step = 0
        self._max_steps = 24  # 24 * 60ms = ~1.44s total boot card duration
        self._battery_text = "AC POWER // OPTIMAL"
        self._step_interval = 50

        self._seal_ok = True
        try:
            from core.server_security import IntegritySeal
            res = IntegritySeal.verify_integrity()
            self._seal_ok = bool(res.get("is_valid", True))
        except Exception:
            pass

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    @property
    def _current_step(self) -> int:
        return self._step

    def _on_tick(self):
        self._tick()

    def _tick(self):
        self._step += 1
        self.update()
        if self._step >= self._max_steps:
            self._timer.stop()
            self._finish()

    def _finish(self):
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        cb = self.on_complete
        self.on_complete = None
        self.close()
        if callable(cb):
            cb()

    def mousePressEvent(self, _):
        self._finish()

    def keyPressEvent(self, _):
        self._finish()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(4, 4, self._w - 8, self._h - 8)
        p.setBrush(QBrush(QColor("#05080f")))
        p.setPen(QPen(QColor("#16384c"), 1.0))
        p.drawRect(rect)

        # Precision corner ticks (industrial HUD framing)
        p.setPen(QPen(QColor(C.PRI), 1.5))
        L = 12.0
        x0, y0, x1, y1 = rect.left(), rect.top(), rect.right(), rect.bottom()
        for cx, cy, dx, dy in [
            (x0, y0, L, L), (x1, y0, -L, L),
            (x0, y1, L, -L), (x1, y1, -L, -L)
        ]:
            p.drawLine(QPointF(cx, cy), QPointF(cx + dx, cy))
            p.drawLine(QPointF(cx, cy), QPointF(cx, cy + dy))

        # Top hairline header
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.setPen(QColor(C.PRI))
        p.drawText(QRectF(24, 20, 300, 16), Qt.AlignmentFlag.AlignLeft, "J.A.R.V.I.S // MARK 108 SOVEREIGN CORE")
        p.setPen(QColor(C.TEXT_DIM))
        p.drawText(QRectF(self._w - 180, 20, 156, 16), Qt.AlignmentFlag.AlignRight, "REV 108.0 // STEALTH HUD")

        p.setPen(QPen(QColor("#0e2230"), 1.0))
        p.drawLine(QPointF(24, 40), QPointF(self._w - 24, 40))

        # Operator Identity
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.setPen(QColor(C.WHITE))
        p.drawText(QRectF(24, 54, self._w - 48, 28), Qt.AlignmentFlag.AlignLeft, "OPERATOR: AKUL BHATNAGAR")

        p.setFont(QFont("Consolas", 8))
        p.setPen(QColor(C.TEXT_MED))
        p.drawText(
            QRectF(24, 86, self._w - 48, 16),
            Qt.AlignmentFlag.AlignLeft,
            "UIA ACCESSIBILITY ENGINE  •  LIVE WEB SURFER  •  HUMANIZER CORE",
        )

        # Subsystem verification lines
        ratio = min(1.0, self._step / float(self._max_steps))
        p.setFont(QFont("Consolas", 8))
        seal_str = "SHA-256 INTEGRITY SEAL: VERIFIED" if self._seal_ok else "SHA-256 INTEGRITY SEAL: MODIFIED"
        seal_col = C.GREEN if self._seal_ok else C.ACC

        p.setPen(QColor(seal_col if ratio > 0.25 else C.TEXT_DIM))
        p.drawText(QRectF(24, 114, self._w - 48, 16), Qt.AlignmentFlag.AlignLeft, f"[OK] {seal_str}")

        p.setPen(QColor(C.PRI if ratio > 0.55 else C.TEXT_DIM))
        p.drawText(
            QRectF(24, 132, self._w - 48, 16),
            Qt.AlignmentFlag.AlignLeft,
            "[OK] DOCKING LONG NON-OBSTRUCTIVE STEALTH BLADE TO TOP BEZEL",
        )

        # 2px Progress Hairline
        bx, by, bw, bh = 24.0, 164.0, float(self._w - 48), 3.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#0f172a")))
        p.drawRect(QRectF(bx, by, bw, bh))

        fw = bw * ratio
        if fw > 0:
            grad = QLinearGradient(bx, by, bx + fw, by)
            grad.setColorAt(0.0, QColor(C.PRI_DIM))
            grad.setColorAt(1.0, QColor(C.PRI))
            p.setBrush(QBrush(grad))
            p.drawRect(QRectF(bx, by, fw, bh))


class _DummyHud:
    """Lightweight compatibility shim for legacy callers referencing self.hud."""
    def __init__(self):
        self.state = "LISTENING"
        self.speaking = False
        self.muted = False

    def set_fps(self, _fps: int):
        pass

    def trigger_gesture(self, _g: str):
        pass

    def set_emotion(self, _s: str, _c: str = ""):
        pass

    def update(self):
        pass


import ctypes
user32 = ctypes.windll.user32


class NativeOrbCore(QWidget):
    """
    Exact Prototype 3D Raymarched Holographic Shader Orb.
    100% matches the user prototype: 3D living plasma, cobalt-cyan radiance,
    state-reactive color transitions, masked to a pure 86x86 circle with 0 rectangular fillers.
    """
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(86, 86)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMask(QRegion(0, 0, 86, 86, QRegion.RegionType.Ellipse))

        self.state = "LISTENING"
        self.war_mode = False

        self._web = QWebEngineView(self)
        self._web.setFixedSize(86, 86)
        self._web.setStyleSheet("background: transparent;")
        self._web.page().setBackgroundColor(QColor(0, 0, 0, 0))
        # Pass all mouse events directly to parent for native dragging & clicking
        self._web.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._web.setMask(QRegion(0, 0, 86, 86, QRegion.RegionType.Ellipse))

        if ORB_CORE_HTML_PATH.exists():
            self._web.load(QUrl.fromLocalFile(str(ORB_CORE_HTML_PATH.resolve())))
        else:
            self._web.setHtml(ORB_CORE_HTML)

    def set_state(self, st: str):
        self.state = (st or "LISTENING").upper()
        if self.war_mode:
            mode_num = 5.0
        elif self.state in ("THINKING", "PILOTING", "WORKING"):
            mode_num = 2.0
        elif self.state == "SPEAKING":
            mode_num = 3.0
        elif self.state == "MUTED":
            mode_num = 4.0
        else:
            mode_num = 1.0
        try:
            self._web.page().runJavaScript(f"window.setShaderMode && window.setShaderMode({mode_num});")
        except Exception:
            pass

    def set_war_mode(self, w: bool):
        self.war_mode = bool(w)
        mode_num = 5.0 if self.war_mode else 1.0
        try:
            self._web.page().runJavaScript(f"window.setShaderMode && window.setShaderMode({mode_num});")
        except Exception:
            pass

    def trigger_pulse(self):
        try:
            self._web.page().runJavaScript("window.triggerShaderPulse && window.triggerShaderPulse();")
        except Exception:
            pass


class HolographicOrbWindow(QMainWindow):
    """
    Solid Shape Holographic Orb & Extended Sleek Taskbar for J.A.R.V.I.S. Mark LVIII.
    - True Solid Shapes: Circle orb + capsule taskbar with ZERO rectangular fillers.
    - Native Hardware Dragging: Direct Win32 WM_NCLBUTTONDOWN on orb move with 0 latency.
    - Full-Feature Extended Taskbar: 840px wide sleek capsule with model switcher, long prompt,
      file badge, snap, mic, halt, blade switch, retract, and close.
    - Constant Visibility: Always on top over secondary wallpapers and Wallpaper Engine.
    """
    _log_sig          = pyqtSignal(str)
    _state_sig        = pyqtSignal(str)
    _notif_sig        = pyqtSignal(str, str)
    _cam_frame_sig    = pyqtSignal(object)
    _model_sig        = pyqtSignal(str)
    _emotion_sig      = pyqtSignal(str, str)
    _gesture_sig      = pyqtSignal(str)
    _fps_throttle_sig = pyqtSignal(int)
    _privacy_veil_sig = pyqtSignal(bool, str)

    def __init__(self, face_path: str = ""):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S // SOLID HOLOGRAPHIC ORB")
        self.setAcceptDrops(True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.on_text_command = None
        self.on_model_switch = None
        self.on_switch_mode  = None
        self._muted          = False
        self._current_file: str | None = None
        self._state          = "LISTENING"
        self._war_mode       = False
        self._dragging       = False
        self._press_pt       = QPoint()
        self.hud             = _DummyHud()

        # Center horizontally at top of screen
        screen = QApplication.primaryScreen().availableGeometry()
        self._normal_pos = QPoint(max(20, (screen.width() - 950) // 2), screen.top() + 15)
        self.move(self._normal_pos)

        central = QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)

        self._root_lay = QHBoxLayout(central)
        self._root_lay.setContentsMargins(0, 0, 0, 0)
        self._root_lay.setSpacing(10)

        # 1. Pure Circular Solid Orb (86x86 px)
        self._orb = NativeOrbCore()
        self._root_lay.addWidget(self._orb)

        # 2. Sleek, Long Frosted-Glass Taskbar Capsule (840px wide, 36px height)
        self._taskbar = QFrame()
        self._taskbar.setFixedHeight(36)
        self._taskbar.setStyleSheet("""
            QFrame {
                background: rgba(5, 9, 16, 225);
                border: 1px solid rgba(0, 225, 255, 48);
                border-radius: 18px;
            }
        """)
        t_lay = QHBoxLayout(self._taskbar)
        t_lay.setContentsMargins(12, 2, 10, 2)
        t_lay.setSpacing(7)

        # Operator Badge
        self._id_lbl = QLabel("AKUL // LVIII")
        self._id_lbl.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._id_lbl.setStyleSheet("color: #00e1ff; border: none; background: transparent;")
        t_lay.addWidget(self._id_lbl)

        # Status LED + Label
        self._status_dot = QFrame()
        self._status_dot.setFixedSize(5, 5)
        self._status_dot.setStyleSheet("background: #00e1ff; border-radius: 2px; border: none;")
        t_lay.addWidget(self._status_dot)

        self._state_lbl = QLabel("ONLINE")
        self._state_lbl.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._state_lbl.setStyleSheet("color: #7395b8; border: none; background: transparent;")
        t_lay.addWidget(self._state_lbl)

        sep1 = QLabel("|")
        sep1.setFont(QFont("Consolas", 8))
        sep1.setStyleSheet("color: rgba(255, 255, 255, 30); border: none; background: transparent;")
        t_lay.addWidget(sep1)

        # File Badge
        self._file_badge = QLabel("")
        self._file_badge.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._file_badge.setStyleSheet("color: #10b981; border: none; background: transparent;")
        self._file_badge.setVisible(False)
        t_lay.addWidget(self._file_badge)

        # Spacious Long Command Input (280px+ width)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Command, message apps, research, or ask J.A.R.V.I.S... [Enter]")
        self._input.setFont(QFont("Consolas", 8))
        self._input.setMinimumWidth(280)
        self._input.setStyleSheet("""
            QLineEdit {
                background: rgba(0, 0, 0, 95);
                color: #eaf6ff;
                border: 1px solid rgba(0, 225, 255, 35);
                border-radius: 12px;
                padding: 3px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #00e1ff;
            }
        """)
        self._input.returnPressed.connect(self._send)
        t_lay.addWidget(self._input, 1)

        # Model Brain Selector Buttons
        self._btn_models = {}
        for label, m_key in [("2.5-F", "gemini-2.5-flash-native-audio-latest"), ("2.5-P", "gemini-2.5-pro"), ("OMNI", "omniroute")]:
            mb = self._make_micro_btn(label, f"Switch Brain to {m_key}", lambda _, k=m_key: self._on_model_click(k))
            t_lay.addWidget(mb)
            self._btn_models[m_key] = mb

        sep2 = QLabel("|")
        sep2.setFont(QFont("Consolas", 8))
        sep2.setStyleSheet("color: rgba(255, 255, 255, 30); border: none; background: transparent;")
        t_lay.addWidget(sep2)

        # Action Buttons
        self._btn_file = self._make_micro_btn("+FILE", "Upload / Attach File", self._browse_file)
        self._btn_snap = self._make_micro_btn("SNAP",  "Camera/Screen Snapshot", self._trigger_snap)
        self._btn_mic  = self._make_micro_btn("MIC",   "Toggle Microphone [F4]", self._toggle_mute)
        self._btn_halt = self._make_micro_btn("HALT",  "Emergency Stop Speech/Task", self._emergency_halt, accent="#ef4444")
        self._btn_blade = self._make_micro_btn("BLADE", "Switch to Tactical Stealth Blade", self._switch_to_blade)
        self._btn_ret  = self._make_micro_btn("<",     "Retract to Solid Circle Orb", self._toggle_taskbar)
        self._btn_ret.setFixedWidth(18)
        self._btn_close = self._make_micro_btn("X",    "Close J.A.R.V.I.S.", self._close_jarvis, accent="#ef4444")
        self._btn_close.setFixedWidth(18)

        for btn in (self._btn_file, self._btn_snap, self._btn_mic, self._btn_halt, self._btn_blade, self._btn_ret, self._btn_close):
            t_lay.addWidget(btn)

        self._root_lay.addWidget(self._taskbar)

        # Hook mouse press/move on Orb for Native Hardware Drag & Click
        self._orb.mousePressEvent = self._on_orb_mouse_press
        self._orb.mouseMoveEvent = self._on_orb_mouse_move
        self._orb.mouseReleaseEvent = self._on_orb_mouse_release

        # Allow dragging the window from the taskbar capsule or operator badge
        self._taskbar.mousePressEvent = self._on_taskbar_mouse_press
        self._id_lbl.mousePressEvent = self._on_taskbar_mouse_press

        # Signals
        self._log_sig.connect(self._append_log)
        self._state_sig.connect(self._apply_state)
        self._notif_sig.connect(self._on_notification)
        self._emotion_sig.connect(self._apply_emotion)
        self._privacy_veil_sig.connect(self._on_set_privacy_veil)

        self._privacy_veil: PrivacyVeilOverlay | None = None
        self._overlay: SetupOverlay | None = None

        self._ready = self._check_config()
        self.ready_event = threading.Event()
        if self._ready:
            self.ready_event.set()
        else:
            self._show_setup()

        # Topmost enforcement timer
        self.force_topmost()
        self._top_timer = QTimer(self)
        self._top_timer.timeout.connect(self.force_topmost)
        self._top_timer.start(1500)

        # Shortcuts
        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_cmd = QShortcut(QKeySequence("Ctrl+Space"), self)
        sc_cmd.activated.connect(self._toggle_taskbar)
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self._on_escape)

        self.adjustSize()

    def _make_micro_btn(self, text: str, tooltip: str, slot, accent: str = "") -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(22)
        btn.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        fg = accent if accent else "#7395b8"
        bdr = accent if accent else "rgba(255, 255, 255, 25)"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 8);
                color: {fg};
                border: 1px solid {bdr};
                border-radius: 6px;
                padding: 0px 6px;
            }}
            QPushButton:hover {{
                color: #ffffff;
                border: 1px solid {accent or '#00e1ff'};
                background: rgba(0, 225, 255, 30);
            }}
        """)
        btn.clicked.connect(slot)
        return btn

    def force_topmost(self):
        try:
            hwnd = int(self.winId())
            user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0010 | 0x0040)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self.force_topmost()

    def _on_orb_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._press_pt = event.globalPosition().toPoint()
            self._orb.trigger_pulse()

    def _on_orb_mouse_move(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            dist = (event.globalPosition().toPoint() - self._press_pt).manhattanLength()
            if dist > 4:
                self._dragging = True
                user32.ReleaseCapture()
                user32.SendMessageW(int(self.winId()), 0xA1, 2, 0)  # Native Windows hardware drag

    def _on_orb_mouse_release(self, event):
        if not self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._toggle_taskbar()

    def _toggle_taskbar(self):
        visible = not self._taskbar.isVisible()
        self._taskbar.setVisible(visible)
        if visible:
            self._input.setFocus()
        self.adjustSize()

    def _on_escape(self):
        if self._taskbar.isVisible():
            self._taskbar.setVisible(False)
            self.adjustSize()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File for J.A.R.V.I.S", str(Path.home()), "All Files (*.*)")
        if path:
            self._on_file_selected(path)

    def _on_file_selected(self, path: str):
        self._current_file = path
        p = Path(path)
        short_name = p.name if len(p.name) <= 20 else p.name[:17] + "..."
        self._file_badge.setText(f"[{short_name}]")
        self._file_badge.setVisible(True)
        if not self._taskbar.isVisible():
            self._taskbar.setVisible(True)
        self._input.setFocus()
        self.adjustSize()

    def clear_file(self):
        self._current_file = None
        self._file_badge.setText("")
        self._file_badge.setVisible(False)
        self.adjustSize()

    def _trigger_snap(self):
        self._send_text_cmd("take a picture and comment on what you see")

    def _emergency_halt(self):
        self._orb.trigger_pulse()
        self._send_text_cmd("halt")

    def _send(self):
        txt = self._input.text().strip()
        self._input.clear()
        if not txt and not self._current_file:
            return
        if not txt and self._current_file:
            txt = f"Analyze the attached file: {self._current_file}"
        elif self._current_file:
            txt = f"[ACTIVE_FILE={self._current_file}] {txt}"
        self._orb.trigger_pulse()
        self._send_text_cmd(txt)

    def _send_text_cmd(self, text: str):
        if callable(self.on_text_command):
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

    @property
    def orb_core(self):
        return self._orb

    @property
    def taskbar_widget(self):
        return self._taskbar

    def _on_taskbar_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            user32.ReleaseCapture()
            user32.SendMessageW(int(self.winId()), 0xA1, 2, 0)

    def set_model(self, model_key: str):
        self._on_model_click(model_key)

    def _on_model_click(self, model_key: str):
        for k, btn in self._btn_models.items():
            if k == model_key:
                btn.setStyleSheet("color: #00e1ff; border: 1px solid #00e1ff; background: rgba(0, 225, 255, 45); font-weight: bold; border-radius: 6px; padding: 0px 6px;")
            else:
                btn.setStyleSheet("color: #7395b8; border: 1px solid rgba(0, 225, 255, 30); background: transparent; border-radius: 6px; padding: 0px 6px;")
        if callable(self.on_model_switch):
            try:
                self.on_model_switch(model_key)
            except Exception:
                pass

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        if self._muted:
            self._btn_mic.setText("MUTE")
            self._apply_state("MUTED")
        else:
            self._btn_mic.setText("MIC")
            self._apply_state("LISTENING")

    def _apply_state(self, state: str):
        st = (state or "LISTENING").upper()
        self._state = st
        self.hud.state = st
        self.hud.speaking = (st == "SPEAKING")
        self._orb.set_state(st)
        if st == "SPEAKING":
            self._state_lbl.setText("SPEAK")
            self._state_lbl.setStyleSheet("color: #10b981; border: none; background: transparent;")
            self._status_dot.setStyleSheet("background: #10b981; border-radius: 2px; border: none;")
        elif st in ("THINKING", "PILOTING", "WORKING"):
            self._state_lbl.setText("EXEC")
            self._state_lbl.setStyleSheet("color: #f59e0b; border: none; background: transparent;")
            self._status_dot.setStyleSheet("background: #f59e0b; border-radius: 2px; border: none;")
        elif st == "MUTED":
            self._state_lbl.setText("MUTED")
            self._state_lbl.setStyleSheet("color: #f43f5e; border: none; background: transparent;")
            self._status_dot.setStyleSheet("background: #f43f5e; border-radius: 2px; border: none;")
        else:
            self._state_lbl.setText("ONLINE")
            self._state_lbl.setStyleSheet("color: #00e1ff; border: none; background: transparent;")
            self._status_dot.setStyleSheet("background: #00e1ff; border-radius: 2px; border: none;")

    def _append_log(self, text: str):
        pass

    def _on_notification(self, msg: str, level: str):
        self._orb.trigger_pulse()

    def _apply_emotion(self, state: str, color_hex: str = ""):
        self._orb.trigger_pulse()

    def set_emotion(self, state: str, color_hex: str = ""):
        self._emotion_sig.emit(state, color_hex)

    def trigger_gesture(self, gesture: str):
        pass

    def set_hud_fps(self, fps: int):
        pass

    def _switch_to_blade(self):
        if callable(self.on_switch_mode):
            self.on_switch_mode("blade")

    def _close_jarvis(self):
        QApplication.instance().quit()

    def set_war_theme(self, enabled: bool):
        self._war_mode = bool(enabled)
        self._orb.set_war_mode(enabled)
        mode_val = "WAR" if enabled else ("MUTED" if self._muted else "LISTENING")
        self._apply_state(mode_val)

    def update_dashboard(self, wx: str = None, evt: str = None, mail: str = None, **kwargs):
        pass

    def set_privacy_veil(self, enabled: bool, reason: str = ""):
        self._privacy_veil_sig.emit(enabled, reason)

    def _dismiss_privacy_veil(self):
        self._on_set_privacy_veil(False)
        try:
            from actions.anti_shoulder_surfer import get_anti_shoulder_surfer
            get_anti_shoulder_surfer().dismiss_veil()
        except Exception:
            pass

    def _on_set_privacy_veil(self, enabled: bool, reason: str = ""):
        if enabled:
            if not self._privacy_veil:
                self._privacy_veil = PrivacyVeilOverlay()
                self._privacy_veil.dismissed.connect(self._dismiss_privacy_veil)
            self._privacy_veil.show()
            self._privacy_veil.raise_()
        else:
            if self._privacy_veil and self._privacy_veil.isVisible():
                self._privacy_veil.hide()

    def _check_config(self) -> bool:
        if not API_FILE.exists():
            return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key"))
        except Exception:
            return False

    def _show_setup(self):
        self._overlay = SetupOverlay()
        self._overlay.done.connect(self._on_setup_done)
        self._overlay.show()

    def _on_setup_done(self, key: str, or_key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({
                "gemini_api_key":     key,
                "openrouter_api_key": or_key,
                "os_system":          os_name,
            }, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        self.ready_event.set()
        self._overlay = None
        self._apply_state("LISTENING")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local and os.path.exists(local):
                self._on_file_selected(local)
                break

    def closeEvent(self, event):
        try:
            from actions.camera_system import camera_mgr
            if camera_mgr.is_active:
                camera_mgr.stop()
            from actions.anti_shoulder_surfer import get_anti_shoulder_surfer
            if get_anti_shoulder_surfer().is_active():
                get_anti_shoulder_surfer().stop_sentry()
        except Exception:
            pass
        super().closeEvent(event)


class MainWindow(QMainWindow):
    """
    Long Non-Obstructive Tactical Stealth Blade (680x28 px docked in the upper-right titlebar dead-zone).
    - Zero continuous timers when idle (0% CPU / 0% iGPU).
    - Never blocks browser tabs, code editors, or app canvases.
    - Auto-dims to 0.72 opacity when idle; snaps to 0.97 on hover or active command.
    - Collapses to a 68x22 px Edge Micro-Tag ('M-LVIII') when '_' is clicked.
    """
    _log_sig          = pyqtSignal(str)
    _state_sig        = pyqtSignal(str)
    _notif_sig        = pyqtSignal(str, str)
    _cam_frame_sig    = pyqtSignal(object)
    _model_sig        = pyqtSignal(str)
    _emotion_sig      = pyqtSignal(str, str)
    _gesture_sig      = pyqtSignal(str)
    _fps_throttle_sig = pyqtSignal(int)
    _privacy_veil_sig = pyqtSignal(bool, str)

    _BAR_W  = 700
    _BAR_H  = 28
    _MINI_W = 68
    _MINI_H = 22

    def __init__(self, face_path: str = ""):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S // MARK LVIII")
        self.setAcceptDrops(True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.75)

        self.on_text_command = None
        self.on_model_switch = None
        self.on_switch_mode  = None
        self._muted          = False
        self._current_file: str | None = None
        self._state          = "LISTENING"
        self._war_mode       = False
        self._collapsed_edge = False
        self._drag_offset    = QPoint()
        self.hud             = _DummyHud()

        # Position in top-right bezel dead-zone (left of window min/max/close buttons)
        screen = QApplication.primaryScreen().availableGeometry()
        self._normal_pos = QPoint(
            max(screen.left() + 20, screen.right() - self._BAR_W - 155),
            screen.top() + 3,
        )
        self.move(self._normal_pos)

        central = QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)

        self._root_lay = QVBoxLayout(central)
        self._root_lay.setContentsMargins(0, 0, 0, 0)
        self._root_lay.setSpacing(3)

        # 1. Collapsed Edge Micro-Tag (68x22 px, hidden unless user clicks '_')
        self._edge_btn = QPushButton("M-LVIII")
        self._edge_btn.setFixedSize(self._MINI_W, self._MINI_H)
        self._edge_btn.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._edge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edge_btn.setToolTip("Expand J.A.R.V.I.S Stealth Blade")
        self._edge_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(5, 8, 15, 238);
                color: {C.PRI};
                border: 1px solid {C.BORDER};
                border-radius: 2px;
                padding: 0px 4px;
            }}
            QPushButton:hover {{
                border: 1px solid {C.PRI};
                background: rgba(8, 18, 30, 250);
            }}
        """)
        self._edge_btn.clicked.connect(self._toggle_edge_collapse)
        self._edge_btn.setVisible(False)
        self._root_lay.addWidget(self._edge_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # 2. Main 680x28 px Tactical Stealth Blade (Original Sharp Industrial Strip, Made Long)
        self._blade = QFrame()
        self._blade.setFixedSize(self._BAR_W, self._BAR_H)
        self._root_lay.addWidget(self._blade)

        b_lay = QHBoxLayout(self._blade)
        b_lay.setContentsMargins(10, 0, 6, 0)
        b_lay.setSpacing(6)

        self._led = QFrame()
        self._led.setFixedSize(6, 6)
        self._led.setStyleSheet(f"background: {C.PRI}; border: none; border-radius: 1px;")
        b_lay.addWidget(self._led)

        self._id_lbl = QLabel("AKUL // LVIII")
        self._id_lbl.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._id_lbl.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        b_lay.addWidget(self._id_lbl)

        self._state_lbl = QLabel("LISTEN")
        self._state_lbl.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._state_lbl.setStyleSheet(f"color: {C.GREEN}; border: none; background: transparent;")
        b_lay.addWidget(self._state_lbl)

        sep = QLabel("|")
        sep.setFont(QFont("Consolas", 8))
        sep.setStyleSheet(f"color: {C.BORDER}; border: none; background: transparent;")
        b_lay.addWidget(sep)

        self._ticker_lbl = QLabel("READY // ONLINE")
        self._ticker_lbl.setFont(QFont("Consolas", 8))
        self._ticker_lbl.setStyleSheet(f"color: {C.TEXT}; border: none; background: transparent;")
        self._ticker_lbl.setMinimumWidth(240)
        b_lay.addWidget(self._ticker_lbl, 1)

        # Precision Micro-Buttons (No emojis, crisp 1px borders)
        self._btn_cmd  = self._make_micro_btn("CMD",  "Command Input [Ctrl+Space]", self._toggle_cmd_row)
        self._btn_file = self._make_micro_btn("FILE", "Upload / Attach File", self._browse_file)
        self._btn_snap = self._make_micro_btn("SNAP", "Take Camera/Screen Snap & Comment", self._trigger_snap)
        self._btn_mic  = self._make_micro_btn("MIC",  "Toggle Microphone [F4]", self._toggle_mute)
        self._btn_log  = self._make_micro_btn("LOG",  "Toggle Telemetry Drawer", self._toggle_log_drawer)
        self._btn_halt = self._make_micro_btn("HALT", "Stop Active Automation / Speech", self._emergency_halt, accent=C.RED)
        self._btn_orb  = self._make_micro_btn("ORB",  "Switch to Holographic Orb Mode", self._switch_to_orb)
        self._btn_min   = self._make_micro_btn("_",    "Minimize / Tuck to 68px Edge Tag", self._toggle_edge_collapse)
        self._btn_min.setFixedWidth(18)
        self._btn_close = self._make_micro_btn("X",    "Close J.A.R.V.I.S", self._close_jarvis, accent=C.RED)
        self._btn_close.setFixedWidth(18)

        for btn in (self._btn_cmd, self._btn_file, self._btn_snap, self._btn_mic, self._btn_log, self._btn_halt, self._btn_orb, self._btn_min, self._btn_close):
            b_lay.addWidget(btn)

        # 3. Collapsible 1-Line Command Input Row (680x28 px, with FILE upload button + text command input)
        self._cmd_panel = QFrame()
        self._cmd_panel.setFixedWidth(self._BAR_W)
        self._cmd_panel.setFixedHeight(30)
        self._cmd_panel.setVisible(False)
        self._cmd_panel.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 8, 15, 248);
                border: 1px solid {C.PRI};
                border-radius: 2px;
            }}
        """)
        c_lay = QHBoxLayout(self._cmd_panel)
        c_lay.setContentsMargins(8, 2, 6, 2)
        c_lay.setSpacing(6)

        prompt_tag = QLabel(">")
        prompt_tag.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        prompt_tag.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        c_lay.addWidget(prompt_tag)

        self._file_badge = QLabel("")
        self._file_badge.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._file_badge.setStyleSheet(f"color: {C.GREEN}; border: none; background: transparent;")
        self._file_badge.setVisible(False)
        c_lay.addWidget(self._file_badge)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type command, message, web research, or file task... [Enter to run, Esc to close]")
        self._input.setFont(QFont("Consolas", 8))
        self._input.setStyleSheet(
            f"QLineEdit {{ background: transparent; color: {C.WHITE}; border: none; padding: 1px 2px; }}"
        )
        self._input.returnPressed.connect(self._send)
        c_lay.addWidget(self._input, 1)

        up_in_panel = self._make_micro_btn("+FILE", "Upload File", self._browse_file)
        c_lay.addWidget(up_in_panel)

        self._clear_file_btn = self._make_micro_btn("CLR", "Detach File", self.clear_file)
        self._clear_file_btn.setVisible(False)
        c_lay.addWidget(self._clear_file_btn)

        run_btn = self._make_micro_btn("EXEC", "Execute Command [Enter]", self._send, accent=C.PRI)
        c_lay.addWidget(run_btn)
        self._root_lay.addWidget(self._cmd_panel)

        # 4. Collapsible Telemetry & Log Drawer (680px wide, hidden by default; 0 timer cost when hidden)
        self._drawer = QFrame()
        self._drawer.setFixedWidth(self._BAR_W)
        self._drawer.setVisible(False)
        self._drawer.setStyleSheet(f"""
            QFrame {{
                background: rgba(5, 8, 15, 246);
                border: 1px solid {C.BORDER};
                border-radius: 2px;
            }}
        """)
        d_lay = QVBoxLayout(self._drawer)
        d_lay.setContentsMargins(8, 6, 8, 6)
        d_lay.setSpacing(4)

        top_strip = QHBoxLayout()
        top_strip.setSpacing(8)
        self._sys_stat_lbl = QLabel("CPU --%  |  RAM --%  |  BAT --%")
        self._sys_stat_lbl.setFont(QFont("Consolas", 7))
        self._sys_stat_lbl.setStyleSheet(f"color: {C.TEXT_MED}; border: none; background: transparent;")
        top_strip.addWidget(self._sys_stat_lbl)
        top_strip.addStretch()

        self._btn_models = {}
        for label, m_key in [
            ("2.5-F", "gemini-2.5-flash-native-audio-latest"),
            ("2.5-P", "gemini-2.5-pro"),
            ("OMNI",  "omniroute"),
        ]:
            mb = self._make_micro_btn(label, f"Switch Brain to {m_key}", lambda _, k=m_key: self._on_model_click(k))
            top_strip.addWidget(mb)
            self._btn_models[m_key] = mb
        d_lay.addLayout(top_strip)

        self._dash_strip = QLabel("WX: --  |  CAL: --  |  MAIL: --")
        self._dash_strip.setFont(QFont("Consolas", 7))
        self._dash_strip.setStyleSheet(f"color: {C.TEXT_DIM}; border: none; background: transparent;")
        d_lay.addWidget(self._dash_strip)

        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setFixedHeight(115)
        self._log_box.document().setMaximumBlockCount(200)
        self._log_box.setFont(QFont("Consolas", 8))
        self._log_box.setStyleSheet(f"""
            QTextEdit {{
                background: {C.DARK};
                color: {C.TEXT};
                border: 1px solid {C.BORDER_A};
                padding: 4px;
            }}
        """)
        d_lay.addWidget(self._log_box)
        self._root_lay.addWidget(self._drawer)

        self._apply_blade_style(C.BORDER)

        # Signals
        self._log_sig.connect(self._append_log)
        self._state_sig.connect(self._apply_state)
        self._notif_sig.connect(self._on_notification)
        self._emotion_sig.connect(self._apply_emotion)
        self._privacy_veil_sig.connect(self._on_set_privacy_veil)

        self._privacy_veil: PrivacyVeilOverlay | None = None
        self._overlay: SetupOverlay | None = None

        self._ready = self._check_config()
        self.ready_event = threading.Event()
        if self._ready:
            self.ready_event.set()
        else:
            self._show_setup()

        # Shortcuts
        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_cmd = QShortcut(QKeySequence("Ctrl+Space"), self)
        sc_cmd.activated.connect(self._toggle_cmd_row)
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self._on_escape)

        self.adjustSize()

    def _make_micro_btn(self, text: str, tooltip: str, slot, accent: str = "") -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(18)
        btn.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        fg = accent if accent else C.TEXT_MED
        bdr = accent if accent else C.BORDER
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL};
                color: {fg};
                border: 1px solid {bdr};
                border-radius: 2px;
                padding: 0px 5px;
            }}
            QPushButton:hover {{
                color: {C.WHITE};
                border: 1px solid {accent or C.PRI};
                background: {C.PRI_GHO};
            }}
        """)
        btn.clicked.connect(slot)
        return btn

    def _apply_blade_style(self, border_hex: str):
        bg = "#140306" if self._war_mode else "rgba(5, 8, 15, 244)"
        bdr = C.RED if self._war_mode else border_hex
        self._blade.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {bdr};
                border-radius: 2px;
            }}
        """)

    def enterEvent(self, event):
        self.setWindowOpacity(0.97)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._cmd_panel.isVisible() and not self._drawer.isVisible():
            self.setWindowOpacity(0.75)
        super().leaveEvent(event)

    def _toggle_edge_collapse(self):
        self._collapsed_edge = not self._collapsed_edge
        screen = QApplication.primaryScreen().availableGeometry()
        if self._collapsed_edge:
            self._cmd_panel.setVisible(False)
            self._drawer.setVisible(False)
            self._blade.setVisible(False)
            self._edge_btn.setVisible(True)
            self.adjustSize()
            self.move(screen.right() - self._MINI_W - 140, screen.top() + 3)
            self.setWindowOpacity(0.68)
        else:
            self._edge_btn.setVisible(False)
            self._blade.setVisible(True)
            self.adjustSize()
            self.move(self._normal_pos)
            self.setWindowOpacity(0.92)

    def _toggle_cmd_row(self):
        vis = not self._cmd_panel.isVisible()
        self._cmd_panel.setVisible(vis)
        self.adjustSize()
        if vis:
            self.setWindowOpacity(0.98)
            self.activateWindow()
            self._input.setFocus()
        else:
            self.setWindowOpacity(0.75)

    def _toggle_log_drawer(self):
        vis = not self._drawer.isVisible()
        if vis:
            self._refresh_drawer_telemetry()
        self._drawer.setVisible(vis)
        self.adjustSize()
        self.setWindowOpacity(0.96 if vis else 0.75)

    def _refresh_drawer_telemetry(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            bat = psutil.sensors_battery()
            bat_str = f"{bat.percent:.0f}%" if bat else "AC"
            self._sys_stat_lbl.setText(f"CPU {cpu:.0f}%  |  RAM {mem:.0f}%  |  PWR {bat_str}")
        except Exception:
            pass

    def _on_escape(self):
        if self._privacy_veil and self._privacy_veil.isVisible():
            self._dismiss_privacy_veil()
            return
        if self._cmd_panel.isVisible() or self._drawer.isVisible():
            self._cmd_panel.setVisible(False)
            self._drawer.setVisible(False)
            self.adjustSize()
            self.setWindowOpacity(0.75)

    def _emergency_halt(self):
        if not self._muted:
            self._toggle_mute()
        self._apply_state("IDLE")
        self._ticker_lbl.setText("HALTED // CONTROLS RELEASED")
        self._led.setStyleSheet(f"background: {C.RED}; border: none;")

    def _close_jarvis(self):
        try:
            if self._privacy_veil:
                self._privacy_veil.close()
        except Exception:
            pass
        try:
            self.close()
            QApplication.quit()
        finally:
            os._exit(0)

    def _trigger_snap(self):
        self._ticker_lbl.setText("SNAP // CAPTURING & ANALYZING...")
        self._send_text_cmd("take a picture and comment on what you see")

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File for J.A.R.V.I.S", str(Path.home()), "All Files (*.*)"
        )
        if path:
            self._on_file_selected(path)

    def clear_file(self):
        self._current_file = None
        self._file_badge.setText("")
        self._file_badge.setVisible(False)
        self._clear_file_btn.setVisible(False)
        self._btn_file.setText("FILE")
        self._btn_file.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 2px; padding: 0px 5px;
            }}
            QPushButton:hover {{
                color: {C.WHITE}; border: 1px solid {C.PRI}; background: {C.PRI_GHO};
            }}
        """)
        self._ticker_lbl.setText("FILE CLEARED // READY")

    def _on_file_selected(self, path: str):
        self._current_file = path
        p = Path(path)
        try:
            size = _fmt_size(p.stat().st_size)
        except Exception:
            size = ""
        short_name = p.name if len(p.name) <= 28 else p.name[:25] + "..."
        self._ticker_lbl.setText(f"FILE // {short_name}")
        self._file_badge.setText(f"[{short_name}]")
        self._file_badge.setVisible(True)
        self._clear_file_btn.setVisible(True)
        self._btn_file.setText("FILE*")
        self._btn_file.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO}; color: {C.GREEN};
                border: 1px solid {C.GREEN}; border-radius: 2px; padding: 0px 5px;
            }}
        """)
        # Automatically open the command row so user can immediately type a command for the file
        if not self._cmd_panel.isVisible():
            self._cmd_panel.setVisible(True)
            self.adjustSize()
        self.setWindowOpacity(0.98)
        self.activateWindow()
        self._input.setPlaceholderText(f"File '{short_name}' attached — type command & press Enter...")
        self._input.setFocus()

        self._append_log(f"FILE: {p.name} ({size}) attached")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._ticker_lbl.setText("DROP FILE TO ATTACH")
            self._apply_blade_style(C.GREEN)

    def dropEvent(self, event: QDropEvent):
        self._apply_blade_style(C.BORDER)
        urls = event.mimeData().urls()
        if urls:
            local = urls[0].toLocalFile()
            if local:
                self._on_file_selected(local)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            if not self._collapsed_edge:
                self._normal_pos = new_pos

    def _send(self):
        txt = self._input.text().strip()
        self._input.clear()
        self._cmd_panel.setVisible(False)
        self.adjustSize()
        self.setWindowOpacity(0.75)
        if not txt and not self._current_file:
            return
        if not txt and self._current_file:
            txt = f"Analyze the attached file: {self._current_file}"
        elif self._current_file:
            txt = f"[ACTIVE_FILE={self._current_file}] {txt}"
        self._append_log(f"CMD > {txt}")
        self._ticker_lbl.setText(f"EXEC // {txt[:48].upper()}")
        if callable(self.on_text_command):
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _send_text_cmd(self, text: str):
        self._append_log(f"CMD > {text}")
        if callable(self.on_text_command):
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

    def _on_model_click(self, model_key: str):
        self._append_log(f"SYS: Switched AI Brain Model to '{model_key}'.")
        if callable(self.on_model_switch):
            try:
                self.on_model_switch(model_key)
            except Exception as e:
                self._append_log(f"ERR: Model switch failed: {e}")

    def _switch_to_orb(self):
        if callable(getattr(self, "on_switch_mode", None)):
            self.on_switch_mode("orb")

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        if self._muted:
            self._btn_mic.setText("MUTE")
            self._btn_mic.setStyleSheet(
                f"QPushButton {{ background: #1f060c; color: {C.MUTED_C}; border: 1px solid {C.MUTED_C}; border-radius: 2px; padding: 0px 5px; }}"
            )
            self._apply_state("MUTED")
        else:
            self._btn_mic.setText("MIC")
            self._btn_mic.setStyleSheet(
                f"QPushButton {{ background: {C.PANEL}; color: {C.GREEN}; border: 1px solid {C.GREEN}; border-radius: 2px; padding: 0px 5px; }}"
            )
            self._apply_state("LISTENING")

    def _apply_state(self, state: str):
        st = (state or "LISTENING").upper()
        self._state = st
        self.hud.state = st
        self.hud.speaking = (st == "SPEAKING")

        if st == "SPEAKING":
            self._state_lbl.setText("SPEAK")
            self._state_lbl.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
            self._led.setStyleSheet(f"background: {C.PRI}; border: none;")
            self._apply_blade_style(C.PRI)
        elif st in ("THINKING", "PILOTING", "WORKING"):
            self._state_lbl.setText("EXEC")
            self._state_lbl.setStyleSheet(f"color: {C.ACC}; border: none; background: transparent;")
            self._led.setStyleSheet(f"background: {C.ACC}; border: none;")
            self._apply_blade_style(C.ACC)
        elif st == "MUTED":
            self._state_lbl.setText("MUTED")
            self._state_lbl.setStyleSheet(f"color: {C.MUTED_C}; border: none; background: transparent;")
            self._led.setStyleSheet(f"background: {C.MUTED_C}; border: none;")
            self._apply_blade_style(C.BORDER)
        elif st == "LOCKED":
            self._state_lbl.setText("LOCKED")
            self._state_lbl.setStyleSheet(f"color: {C.RED}; border: none; background: transparent;")
            self._led.setStyleSheet(f"background: {C.RED}; border: none;")
            self._apply_blade_style(C.RED)
        else:
            self._state_lbl.setText("LISTEN")
            self._state_lbl.setStyleSheet(f"color: {C.GREEN}; border: none; background: transparent;")
            self._led.setStyleSheet(f"background: {C.GREEN}; border: none;")
            self._apply_blade_style(C.BORDER)

    def _append_log(self, text: str):
        clean = (text or "").strip().replace("\n", " ")
        if not clean:
            return
        ts = time.strftime("%H:%M:%S")
        self._log_box.append(f"[{ts}] {clean}")

        # Update single-line stealth ticker with longer 56-char non-emoji readout
        short = re.sub(r"[^\x20-\x7E]", "", clean).strip()
        if len(short) > 56:
            short = short[:53] + "..."
        if short:
            self._ticker_lbl.setText(short.upper())

    def _on_notification(self, msg: str, level: str):
        clean = re.sub(r"[^\x20-\x7E]", "", (msg or "")).strip()
        if clean:
            self._ticker_lbl.setText(clean[:56].upper())
        self._append_log(f"[{level.upper()}] {msg}")

    def _apply_emotion(self, state: str, color_hex: str):
        if color_hex:
            self._led.setStyleSheet(f"background: {color_hex}; border: none;")

    def write_log(self, text: str):
        self._log_sig.emit(text)

    def push_notification(self, msg: str, level: str = "info"):
        self._notif_sig.emit(msg, level)

    def update_dashboard(self, wx: str = None, evt: str = None, mail: str = None, **kwargs):
        wx_val   = wx or kwargs.get("weather") or "--"
        evt_val  = evt or kwargs.get("cal") or kwargs.get("focus") or "--"
        mail_val = mail or kwargs.get("mail") or "--"
        self._dash_strip.setText(f"WX: {str(wx_val)[:22]}  |  CAL: {str(evt_val)[:22]}  |  MAIL: {str(mail_val)[:20]}")

    def set_emotion(self, state: str, color_hex: str = ""):
        self._emotion_sig.emit(state, color_hex)

    def trigger_gesture(self, gesture: str):
        pass

    def set_hud_fps(self, fps: int):
        pass

    def set_war_theme(self, enabled: bool):
        self._war_mode = bool(enabled)
        self._apply_blade_style(C.RED if enabled else C.BORDER)
        self._ticker_lbl.setText("WAR PROTOCOL // ACTIVE" if enabled else "STANDBY // RESTORED")

    def set_privacy_veil(self, enabled: bool, reason: str = ""):
        self._privacy_veil_sig.emit(enabled, reason)

    def _dismiss_privacy_veil(self):
        self._on_set_privacy_veil(False)
        try:
            from actions.anti_shoulder_surfer import get_anti_shoulder_surfer
            get_anti_shoulder_surfer().dismiss_veil()
        except Exception:
            pass

    def _on_set_privacy_veil(self, enabled: bool, reason: str = ""):
        if enabled:
            if not self._privacy_veil:
                self._privacy_veil = PrivacyVeilOverlay()
                self._privacy_veil.dismissed.connect(self._dismiss_privacy_veil)
            self._privacy_veil.show()
            self._privacy_veil.raise_()
        else:
            if self._privacy_veil and self._privacy_veil.isVisible():
                self._privacy_veil.hide()

    def _check_config(self) -> bool:
        if not API_FILE.exists():
            return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key"))
        except Exception:
            return False

    def _show_setup(self):
        self._overlay = SetupOverlay()
        self._overlay.done.connect(self._on_setup_done)
        self._overlay.show()

    def _on_setup_done(self, key: str, or_key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({
                "gemini_api_key":    key,
                "openrouter_api_key": or_key,
                "os_system":         os_name,
            }, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        self.ready_event.set()
        self._overlay = None
        self._apply_state("LISTENING")

    def closeEvent(self, event):
        try:
            from actions.camera_system import camera_mgr
            if camera_mgr.is_active:
                camera_mgr.stop()
            from actions.anti_shoulder_surfer import get_anti_shoulder_surfer
            if get_anti_shoulder_surfer().is_active():
                get_anti_shoulder_surfer().stop_sentry()
        except Exception:
            pass
        super().closeEvent(event)


class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app

    def mainloop(self):
        self._app.exec()

    def protocol(self, *_):
        pass


class JarvisUI:
    def __init__(self, face_path: str = "", size=None, show_splash: bool = True):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._face_path = face_path
        self._ui_mode = self._get_saved_ui_mode()

        if self._ui_mode == "blade":
            self._win = MainWindow(face_path)
        else:
            self._win = HolographicOrbWindow(face_path)

        self._win.on_switch_mode = self.switch_ui_mode
        self.root = _RootShim(self._app)

        if show_splash:
            self._splash = JarvisOpeningScreen(on_complete=self._win.show)
            self._splash.show()
        else:
            self._win.show()

    def _get_saved_ui_mode(self) -> str:
        if API_FILE.exists():
            try:
                d = json.loads(API_FILE.read_text(encoding="utf-8"))
                return str(d.get("ui_mode", "orb")).lower()
            except Exception:
                pass
        return "orb"

    def switch_ui_mode(self, new_mode: str):
        target = "blade" if new_mode.lower() == "blade" else "orb"
        if target == self._ui_mode:
            return

        old_cb_cmd = self._win.on_text_command
        old_cb_model = self._win.on_model_switch
        old_file = self._win._current_file
        old_state = self._win._state
        old_muted = self._win._muted
        old_war = getattr(self._win, "_war_mode", False)

        self._win.hide()

        if target == "blade":
            self._win = MainWindow(self._face_path)
        else:
            self._win = HolographicOrbWindow(self._face_path)

        self._win.on_switch_mode = self.switch_ui_mode
        self._win.on_text_command = old_cb_cmd
        self._win.on_model_switch = old_cb_model
        if old_file:
            self._win._on_file_selected(old_file)
        self._win._apply_state(old_state)
        if old_muted:
            self._win._muted = True
            self._win._apply_state("MUTED")
        if old_war:
            self._win.set_war_theme(True)

        self._ui_mode = target
        if API_FILE.exists():
            try:
                d = json.loads(API_FILE.read_text(encoding="utf-8"))
                d["ui_mode"] = target
                API_FILE.write_text(json.dumps(d, indent=4), encoding="utf-8")
            except Exception:
                pass

        self._win.show()

    @property
    def ui_mode(self) -> str:
        return self._ui_mode

    @property
    def orb_window(self):
        return self._win if isinstance(self._win, HolographicOrbWindow) else None

    @property
    def blade_window(self):
        return self._win if isinstance(self._win, MainWindow) else None

    def toggle_ui_mode(self):
        next_mode = "blade" if self._ui_mode == "orb" else "orb"
        self.switch_ui_mode(next_mode)

    def append_transcript(self, text: str, role: str = ""):
        prefix = f"[{role.upper()}]: " if role else ""
        self.write_log(f"{prefix}{text}")

    def set_war_theme(self, enabled: bool):
        self._win.set_war_theme(enabled)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._current_file

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    @property
    def on_model_switch(self):
        return self._win.on_model_switch

    @on_model_switch.setter
    def on_model_switch(self, cb):
        self._win.on_model_switch = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def set_emotion(self, state: str, color_hex: str = ""):
        self._win._emotion_sig.emit(state, color_hex)

    def trigger_gesture(self, gesture: str):
        self._win.trigger_gesture(gesture)

    def set_hud_fps(self, fps: int):
        self._win.set_hud_fps(fps)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def push_notification(self, msg: str, level: str = "info"):
        self._win.push_notification(msg, level)

    def update_dashboard(self, wx: str = None, evt: str = None, mail: str = None, **kwargs):
        self._win.update_dashboard(wx, evt, mail, **kwargs)

    def wait_for_api_key(self):
        if hasattr(self._win, "ready_event"):
            self._win.ready_event.wait()
        else:
            while not self._win._ready:
                time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def set_privacy_veil(self, enabled: bool, reason: str = ""):
        self._win.set_privacy_veil(enabled, reason)

    def dismiss_privacy_veil(self):
        self._win._dismiss_privacy_veil()
