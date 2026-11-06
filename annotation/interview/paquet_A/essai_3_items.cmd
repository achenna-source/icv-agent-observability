@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Essai : trois items
if exist essai\responses_ESSAI.jsonl del essai\responses_ESSAI.jsonl
echo.
echo   ESSAI. Trois trajectoires, les memes questions que la ronde reelle.
echo   Rien de ce que vous repondez ici ne compte dans l etude.
echo.
python -I interview.py --annotator ESSAI --sample essai\sample_essai.jsonl --out essai\responses_ESSAI.jsonl --resume
echo.
pause
