@echo off
chcp 65001 >nul
setlocal
echo ============================================
echo   imgread installer - zero-config image reading
echo ============================================
set ROOT=%~dp0
cd /d "%ROOT%"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Install Python 3.10+ first.
    pause & exit /b 1
)

echo [1/4] Creating venv...
python -m venv venv
if errorlevel 1 (echo [ERROR] venv failed & pause & exit /b 1)

echo [2/4] Installing dependencies (first run downloads ~200MB)...
call venv\Scripts\python.exe -m pip install -q --upgrade pip
call venv\Scripts\python.exe -m pip install -q -r requirements.txt
if errorlevel 1 (echo [ERROR] pip install failed & pause & exit /b 1)

echo [3/4] Writing commands...
> imgread.cmd  echo @echo off
>> imgread.cmd echo "%%~dp0venv\Scripts\python.exe" "%%~dp0imgread.py" %%*
> imgvlm.cmd  echo @echo off
>> imgvlm.cmd echo "%%~dp0venv\Scripts\python.exe" "%%~dp0imgvlm.py" %%*

echo [4/4] Adding to PATH (takes effect in NEW terminals)...
for %%i in ("%ROOT%.") do set DIRNAME=%%~nxi
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); if($p -notlike '*%ROOT%*'){[Environment]::SetEnvironmentVariable('Path', $p+';%ROOT%','User')}"

echo.
echo DONE. Open a NEW terminal and test:
echo   imgread your-image.png
echo   imgvlm your-image.png "what is this?"
pause
