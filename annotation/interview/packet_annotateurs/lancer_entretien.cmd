@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Annotation interview
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo Python n'est pas trouve. Installez Python 3.8 ou plus recent depuis python.org
  echo en cochant "Add python.exe to PATH", puis relancez ce fichier.
  echo.
  pause
  exit /b 1
)
echo.
set /p ANN=Votre lettre d'annotateur, A B C ou D, puis Entree :
echo.
python -I interview.py --annotator %ANN% --resume
echo.
echo Vous pouvez fermer cette fenetre. Pour reprendre plus tard, relancez ce fichier
echo avec la meme lettre.
echo.
pause
