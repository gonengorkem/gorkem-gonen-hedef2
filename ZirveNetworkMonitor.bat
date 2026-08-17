@echo off
title Zirve Network Inspector
color 0B
echo ========================================================
echo          ZIRVE NETWORK INSPECTOR BASLATILIYOR
echo ========================================================
echo.

cd /d "%~dp0"
set PYTHON_EXE=backend\venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo HATA: Python sanal ortami bulunamadi: %PYTHON_EXE%
    echo Lutfen klasor yapisini kontrol edin.
    pause
    exit /b 1
)

echo [1/2] Sunucu ve Tarayici Baslatiliyor...
echo.
echo Panel Adresi: http://localhost:8000
echo Proxy Portu:  8080
echo.
echo (Kapatmak icin bu pencereyi kapatabilirsiniz)
echo --------------------------------------------------------

"%PYTHON_EXE%" -m backend.zirve_monitor.run_app

pause
