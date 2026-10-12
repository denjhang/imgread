@echo off
chcp 65001 >nul
cd /d "%~dp0"
imgread.cmd test-image.png
pause
