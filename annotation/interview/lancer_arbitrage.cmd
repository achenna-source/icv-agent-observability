@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Arbitrage des items en litige
echo.
echo   ARBITRAGE. Vous voyez les etiquettes sans savoir qui les a produites.
echo   Choisissez parmi celles que les lecteurs ont ecrites, ou u si le codebook
echo   ne tranche pas. Commandes : une etiquette, u, steps, ?, skip, save.
echo.
python -I adjudicate.py --adjudicator AC
echo.
pause
