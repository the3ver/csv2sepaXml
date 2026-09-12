@echo off
setlocal

:: Ermittle Verzeichnis dieses Skripts
set "DIR=%~dp0"

:: Suche nach csv2sepaXml.exe (im selben Ordner oder im dist-Ordner)
if exist "%DIR%csv2sepaXml.exe" (
    set "EXE_PATH=%DIR%csv2sepaXml.exe"
) else if exist "%DIR%dist\csv2sepaXml.exe" (
    set "EXE_PATH=%DIR%dist\csv2sepaXml.exe"
) else (
    echo [FEHLER] Die Datei 'csv2sepaXml.exe' wurde nicht gefunden.
    echo Bitte stellen Sie sicher, dass sich dieses Skript im selben Ordner
    echo oder uebergeordnet zum 'dist'-Ordner befindet.
    pause
    exit /b 1
)

:: Entferne Windows 'Mark of the Web' (Zone.Identifier), um SmartScreen-Warnungen zu vermeiden
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%EXE_PATH%' -ErrorAction SilentlyContinue"

:: Starte die Anwendung im Hintergrund / Web-Oberflaeche
start "" "%EXE_PATH%"
exit /b 0
