import asyncio
import json
import logging
import time
import uuid
import psutil
from mitmproxy import http

logger = logging.getLogger("zirve_proxy_addon")

class ZirveFilterAddon:
    def __init__(self, callback_func=None, target_process_keyword="zirve"):
        self.callback_func = callback_func
        self.target_process_keyword = target_process_keyword.lower()
        self.process_cache = {}

    def get_process_info(self, client_port):
        if not client_port:
            return None, "Bilinmeyen"
            
        now = time.time()
        if client_port in self.process_cache:
            pid, pname, ts = self.process_cache[client_port]
            if now - ts < 10:
                return pid, pname

        try:
            for conn in psutil.net_connections(kind='tcp'):
                if conn.laddr and conn.laddr.port == client_port:
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            pname = proc.name()
                            self.process_cache[client_port] = (conn.pid, pname, now)
                            return conn.pid, pname
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            return conn.pid, f"PID-{conn.pid}"
        except Exception as e:
            logger.debug(f"Process lookup error: {e}")

        return None, "Sistem / Diğer"

    def is_target_process(self, process_name):
        if not self.target_process_keyword or self.target_process_keyword == "*":
            return True
        return self.target_process_keyword in process_name.lower()

    def request(self, flow: http.HTTPFlow):
        flow.metadata["start_time"] = time.time()

    def response(self, flow: http.HTTPFlow):
        try:
            client_port = flow.client_conn.peername[1] if flow.client_conn and flow.client_conn.peername else None
            pid, process_name = self.get_process_info(client_port)

            # Process filter check
            if not self.is_target_process(process_name):
                return

            start_time = flow.metadata.get("start_time", time.time())
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Request Body
            req_body = ""
            if flow.request.content:
                try:
                    req_body = flow.request.get_text(strict=False)
                except Exception:
                    req_body = f"[Binary Content: {len(flow.request.content)} bytes]"

            # Response Body
            res_body = ""
            if flow.response and flow.response.content:
                try:
                    res_body = flow.response.get_text(strict=False)
                except Exception:
                    res_body = f"[Binary Content: {len(flow.response.content)} bytes]"

            # Format headers
            req_headers = dict(flow.request.headers)
            res_headers = dict(flow.response.headers) if flow.response else {}

            payload = {
                "id": str(uuid.uuid4()),
                "timestamp": time.strftime("%H:%M:%S"),
                "method": flow.request.method,
                "url": flow.request.url,
                "host": flow.request.pretty_host,
                "path": flow.request.path,
                "statusCode": flow.response.status_code if flow.response else 0,
                "durationMs": duration_ms,
                "processName": process_name,
                "pid": pid or "-",
                "requestHeaders": req_headers,
                "requestBody": req_body,
                "responseHeaders": res_headers,
                "responseBody": res_body,
                "responseSize": len(flow.response.content) if flow.response and flow.response.content else 0
            }

            if self.callback_func:
                self.callback_func(payload)

        except Exception as e:
            logger.error(f"Error processing flow: {e}", exc_info=True)
