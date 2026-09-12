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

echo Erstelle eigenstaendige csv2sepaXml.exe (v0.2.0)...
python -m PyInstaller --clean --noconfirm --onefile --name "csv2sepaXml" --version-file "file_version_info.txt" --add-data "schema/pain.008.001.08.xsd;schema" --hidden-import="xmlschema" --hidden-import="elementpath" sepa_generator.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo =======================================================
    echo  [ERFOLG] Die Datei wurde erfolgreich erstellt:
    echo  dist\csv2sepaXml.exe
    echo =======================================================
) else (
    echo.
    echo [FEHLER] PyInstaller-Build fehlgeschlagen.
)

pause
