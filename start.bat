@echo off
echo ==================================================
echo GORKEM GONEN HEDEF - GIB PAKET ANALIZORU BASLATICI
echo ==================================================
echo.

echo [1/2] Backend (FastAPI) Baslatiliyor...
start cmd /k "cd backend && call venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Frontend (React+Vite) Baslatiliyor...
start cmd /k "cd frontend && npm run dev"

echo.
echo Sistem basariyla calistirildi!
echo Birazdan Frontend tarayicida acilacaktir. (Veya http://localhost:5173 adresine gidebilirsiniz.)
echo Backend API http://localhost:8000 adresinde calismaktadir.
pause
