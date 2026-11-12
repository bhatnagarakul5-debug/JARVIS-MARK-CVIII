"""
Windowless Desktop Launcher for J.A.R.V.I.S. Mark LVIII.
Double-clicking this .pyw file launches JARVIS directly via pythonw.exe without ever opening cmd.exe.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(str(BASE_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main import main

if __name__ == "__main__":
    main()
