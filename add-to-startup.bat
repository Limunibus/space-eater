@echo off
echo Creating ClipDedent startup shortcut...

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\ClipDedent.lnk'); $s.TargetPath = 'pythonw'; $s.Arguments = '\"%~dp0clipdedent.pyw\"'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'ClipDedent - Clipboard indentation cleaner'; $s.Save()"

echo.
echo Done! ClipDedent will start automatically on login.
echo Shortcut created in: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
echo.
echo To remove, delete ClipDedent.lnk from the Startup folder.
pause
