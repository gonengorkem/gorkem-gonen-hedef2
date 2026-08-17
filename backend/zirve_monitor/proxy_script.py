import base64
import io
import json
import logging
import re
import time
import uuid
import zipfile
import xml.dom.minidom
import psutil
import requests
from mitmproxy import http

logger = logging.getLogger("zirve_proxy_script")

API_ENDPOINT = "http://127.0.0.1:8000/api/internal/flow"
PROCESS_CACHE = {}

def prettify_xml(xml_string):
    try:
        # Remove empty lines / text nodes for clean formatting
        dom = xml.dom.minidom.parseString(xml_string.strip())
        return dom.toprettyxml(indent="  ")
    except Exception:
        return xml_string

def auto_extract_ubl_xml(body_text):
    if not body_text:
        return None
    
    # Search for Base64 ZIP patterns starting with UEsDB inside binaryData or SOAP body
    matches = re.findall(r'(UEsDB[A-Za-z0-9+/=\s]{40,})', body_text)
    for b64_str in matches:
        clean_b64 = re.sub(r'\s+', '', b64_str)
        try:
            raw_bytes = base64.b64decode(clean_b64)
            if raw_bytes.startswith(b'PK\x03\x04'):
                with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                    for fname in zf.namelist():
                        if fname.lower().endswith('.xml'):
                            xml_bytes = zf.read(fname)
                            xml_str = xml_bytes.decode('utf-8', errors='ignore')
                            return {
                                "filename": fname,
                                "xmlContent": prettify_xml(xml_str)
                            }
        except Exception:
            continue
    return None

def get_process_info(client_port):
    if not client_port:
        return None, "Bilinmeyen"
        
    now = time.time()
    if client_port in PROCESS_CACHE:
        pid, pname, ts = PROCESS_CACHE[client_port]
        if now - ts < 10:
            return pid, pname

    try:
        for conn in psutil.net_connections(kind='tcp'):
            if conn.laddr and conn.laddr.port == client_port:
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        pname = proc.name()
                        PROCESS_CACHE[client_port] = (conn.pid, pname, now)
                        return conn.pid, pname
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return conn.pid, f"PID-{conn.pid}"
    except Exception:
        pass

    return None, "Sistem / Diğer"

def request(flow: http.HTTPFlow):
    flow.metadata["start_time"] = time.time()

def response(flow: http.HTTPFlow):
    try:
        client_port = flow.client_conn.peername[1] if flow.client_conn and flow.client_conn.peername else None
        pid, process_name = get_process_info(client_port)

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

        req_headers = dict(flow.request.headers)
        res_headers = dict(flow.response.headers) if flow.response else {}

        # Auto extract UBL e-Invoice XML if binaryData contains zip
        extracted_info = auto_extract_ubl_xml(req_body) or auto_extract_ubl_xml(res_body)

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
            "responseSize": len(flow.response.content) if flow.response and flow.response.content else 0,
            "hasInvoiceXml": bool(extracted_info),
            "invoiceFilename": extracted_info["filename"] if extracted_info else None,
            "invoiceXml": extracted_info["xmlContent"] if extracted_info else None
        }

        # Post to FastAPI internal endpoint
        try:
            requests.post(API_ENDPOINT, json=payload, timeout=2)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error processing flow: {e}")
