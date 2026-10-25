@echo off
cd /d "%~dp0"
echo Installation des outils de construction...
py -m pip install --upgrade pyinstaller customtkinter pillow
if errorlevel 1 python -m pip install --upgrade pyinstaller customtkinter pillow
echo.
echo Construction des deux versions...
py build_release.py --exe
if errorlevel 1 python build_release.py --exe
echo.
echo Termine. Les zips sont dans le dossier release.
pause
