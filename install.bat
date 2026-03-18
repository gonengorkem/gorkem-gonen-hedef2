@echo off
echo ==================================================
echo GORKEM GONEN HEDEF - KURULUM
echo ==================================================
echo.

echo [1/2] Backend (FastAPI) paketleri kuruluyor...
cd backend
py -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..

echo [2/2] Frontend (React+Vite) paketleri kuruluyor...
cd frontend
call npm install
cd ..

echo.
echo Kurulum tamamlandi!
echo Artik start.bat dosyasina tiklayarak projeyi baslatabilirsiniz.
pause
