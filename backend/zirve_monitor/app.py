import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from backend.zirve_monitor import system_proxy
from backend.zirve_monitor.cert_installer import install_mitm_ca_cert

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zirve_monitor_app")

app = FastAPI(title="Zirve Network Inspector")

request_history: List[dict] = []
current_filter = "zirve, entegrator, e_fatura, donusum, e-dönüşüm, edonusum"
current_vpn_bypass = "*vpn*, *forti*, .fortinet.com"
mitmdump_process = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

def is_matching_filter(process_name: str, filter_str: str) -> bool:
    if not filter_str or filter_str == "*":
        return True
    filters = [f.strip().lower() for f in filter_str.split(",") if f.strip()]
    proc = process_name.lower()
    return any(f in proc for f in filters)

def start_mitmdump_process(port=8080):
    global mitmdump_process
    mitmdump_bin = os.path.join(sys.prefix, "Scripts", "mitmdump.exe")
    script_path = os.path.join(os.path.dirname(__file__), "proxy_script.py")
    cmd = [
        mitmdump_bin if os.path.exists(mitmdump_bin) else "mitmdump",
        "-s", script_path,
        "-p", str(port),
        "--listen-host", "127.0.0.1",
        "--set", "block_global=false"
    ]
    try:
        mitmdump_process = subprocess.Popen(cmd)
        logger.info(f"mitmdump process launched (PID: {mitmdump_process.pid}) on port {port}")
    except Exception as e:
        logger.error(f"Failed to start mitmdump process: {e}")

@app.on_event("startup")
async def startup_event():
    install_mitm_ca_cert()
    start_mitmdump_process(8080)
    logger.info("Zirve Inspector Server started at http://localhost:8000")

@app.on_event("shutdown")
async def shutdown_event():
    global mitmdump_process
    system_proxy.disable_system_proxy()
    if mitmdump_process:
        mitmdump_process.terminate()
        logger.info("mitmdump process terminated")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Zirve Inspector Template Not Found</h1>"

@app.get("/proxy.pac")
async def get_pac_script():
    pac_content = """
function FindProxyForURL(url, host) {
    if (shExpMatch(host, "127.0.0.1") || shExpMatch(host, "localhost") || isPlainHostName(host)) {
        return "DIRECT";
    }

    if (dnsDomainIs(host, ".fortinet.com") ||
        dnsDomainIs(host, ".forticlient.com") ||
        shExpMatch(host, "*vpn*") ||
        shExpMatch(host, "*forti*") ||
        shExpMatch(host, "*sslvpn*")) {
        return "DIRECT";
    }

    return "PROXY 127.0.0.1:8080; DIRECT";
}
"""
    return Response(content=pac_content.strip(), media_type="application/x-ns-proxy-autoconfig")

@app.post("/api/internal/flow")
async def receive_internal_flow(request: Request):
    global request_history
    flow_data = await request.json()
    process_name = flow_data.get("processName", "")

    if is_matching_filter(process_name, current_filter):
        request_history.append(flow_data)
        if len(request_history) > 500:
            request_history.pop(0)
        await manager.broadcast({"type": "NEW_REQUEST", "data": flow_data})

    return JSONResponse({"status": "ok"})

@app.get("/api/requests")
async def get_requests():
    return JSONResponse({"requests": request_history, "filter": current_filter, "bypass": current_vpn_bypass})

@app.post("/api/clear")
async def clear_requests():
    global request_history
    request_history.clear()
    await manager.broadcast({"type": "CLEAR"})
    return JSONResponse({"status": "ok"})

@app.get("/api/proxy/status")
async def get_proxy_status():
    enabled, server, bypass = system_proxy.get_system_proxy_status()
    return JSONResponse({"enabled": enabled, "server": server, "bypass": current_vpn_bypass, "filter": current_filter})

@app.post("/api/proxy/toggle")
async def toggle_proxy(request: Request):
    global current_vpn_bypass
    data = await request.json()
    enable = data.get("enable", False)
    custom_bypass = data.get("bypass", "")
    current_vpn_bypass = custom_bypass

    if enable:
        success = system_proxy.enable_system_proxy("127.0.0.1", 8080, custom_bypass=custom_bypass, use_pac=True)
    else:
        success = system_proxy.disable_system_proxy()

    enabled, server, bypass = system_proxy.get_system_proxy_status()
    await manager.broadcast({"type": "PROXY_STATUS_CHANGE", "enabled": enabled, "bypass": custom_bypass})
    return JSONResponse({"success": success, "enabled": enabled, "bypass": custom_bypass})

@app.post("/api/settings/filter")
async def set_filter(request: Request):
    global current_filter
    data = await request.json()
    current_filter = data.get("filter", "zirve").strip().lower()
    await manager.broadcast({"type": "FILTER_CHANGE", "filter": current_filter})
    return JSONResponse({"status": "ok", "filter": current_filter})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        enabled, _, bypass = system_proxy.get_system_proxy_status()
        await websocket.send_json({
            "type": "INIT",
            "requests": request_history,
            "filter": current_filter,
            "proxyEnabled": enabled,
            "bypass": current_vpn_bypass
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
