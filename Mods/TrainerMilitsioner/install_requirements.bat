@echo off
echo Installation des modules du Militsioner Trainer...
py -m pip install --upgrade customtkinter pillow
if errorlevel 1 python -m pip install --upgrade customtkinter pillow
echo.
echo Termine. Tu peux fermer cette fenetre.
pause
