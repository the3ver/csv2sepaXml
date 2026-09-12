@echo off
echo =======================================================
echo  csv2sepaXml - Windows EXE Builder (PyInstaller)
echo =======================================================
echo.

python -m pip install -r requirements.txt pyinstaller
if %ERRORLEVEL% neq 0 (
    echo [FEHLER] Installation der Voraussetzungen fehlgeschlagen.
    pause
    exit /b %ERRORLEVEL%
)

echo Erstelle eigenstaendige csv2sepaXml.exe (v0.3.0)...
python -m PyInstaller --clean --noconfirm --onefile --noupx --name "csv2sepaXml" --version-file "file_version_info.txt" --add-data "schema/pain.008.001.08.xsd;schema" --hidden-import="xmlschema" --hidden-import="elementpath" sepa_generator.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo =======================================================
    echo  [ERFOLG] Die Datei wurde erfolgreich erstellt:
    echo  dist\csv2sepaXml.exe
    echo =======================================================

    echo.
    echo Wende digitale Authenticode-Signatur an...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sign_exe.ps1"

    echo.
    echo Kopiere Begleitdateien nach dist\...
    copy /Y "%~dp0start_app.bat" "%~dp0dist\start_app.bat" >nul
    copy /Y "%~dp0config.example.json" "%~dp0dist\config.example.json" >nul
    copy /Y "%~dp0sample_mitglieder.csv" "%~dp0dist\sample_mitglieder.csv" >nul

    echo Fertig! Der Ordner 'dist' enthaelt jetzt alle noetigen Dateien.
) else (
    echo.
    echo [FEHLER] PyInstaller-Build fehlgeschlagen.
)

pause
