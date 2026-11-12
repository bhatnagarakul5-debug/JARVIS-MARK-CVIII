@echo off
cd /d "%~dp0"

:: Launch JARVIS completely windowless via pythonw.exe so CMD never stays on screen
if exist "venv\Scripts\pythonw.exe" (
    start "" /B "venv\Scripts\pythonw.exe" "%~dp0main.py"
    exit /b 0
)

where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" /B pythonw "%~dp0main.py"
    exit /b 0
)

where pyw >nul 2>&1
if %errorlevel% equ 0 (
    start "" /B pyw -3 "%~dp0main.py"
    exit /b 0
)

if exist "venv\Scripts\python.exe" (
    start "" /B "venv\Scripts\python.exe" "%~dp0main.py"
    exit /b 0
)

start "" /B python "%~dp0main.py"
exit /b 0
