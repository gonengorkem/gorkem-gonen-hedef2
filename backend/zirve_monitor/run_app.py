import threading
import time
import webbrowser
import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print("Zirve Network Inspector başlatılıyor...")
    print("Tarayıcınız açılıyor: http://localhost:8000")
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.zirve_monitor.app:app", host="127.0.0.1", port=8000, log_level="info")
