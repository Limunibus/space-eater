Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw """ & Replace(WScript.ScriptFullName, "run-background.vbs", "clipdedent.pyw") & """", 0, False
