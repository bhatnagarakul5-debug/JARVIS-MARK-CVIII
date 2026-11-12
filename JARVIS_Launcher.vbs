Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = strDir

If fso.FileExists(strDir & "\venv\Scripts\pythonw.exe") Then
    WshShell.Run """" & strDir & "\venv\Scripts\pythonw.exe"" """ & strDir & "\main.py""", 0, False
Else
    WshShell.Run "pythonw.exe """ & strDir & "\main.py""", 0, False
End If

Set WshShell = Nothing
Set fso = Nothing
