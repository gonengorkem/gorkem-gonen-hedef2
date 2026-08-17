import os
import subprocess
import logging

logger = logging.getLogger("cert_installer")

def install_mitm_ca_cert():
    cert_path = os.path.expanduser(r"~\.mitmproxy\mitmproxy-ca-cert.cer")
    if os.path.exists(cert_path):
        try:
            cmd = ["certutil", "-user", "-addstore", "Root", cert_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logger.info(f"Certutil output: {res.stdout}")
            return True
        except Exception as e:
            logger.error(f"Failed to install CA cert: {e}")
    else:
        logger.warning(f"Cert file not found at {cert_path}")
    return False
