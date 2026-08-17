import winreg
import ctypes
import logging

logger = logging.getLogger("system_proxy")

INTERNET_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_REFRESH = 37

DEFAULT_BYPASS_LIST = (
    "localhost;127.0.0.1;"
    "*vpn*;*forti*;*sslvpn*;*.fortinet.com;*.forticlient.com;"
    "<local>"
)

def refresh_system_proxy():
    try:
        internet_set_option = ctypes.windll.wininet.InternetSetOptionW
        internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
    except Exception as e:
        logger.error(f"Failed to refresh WinINet settings: {e}")

def enable_system_proxy(host="127.0.0.1", port=8080, custom_bypass="", use_pac=True):
    try:
        bypass = DEFAULT_BYPASS_LIST
        if custom_bypass and custom_bypass.strip():
            extra = ";".join([b.strip() for b in custom_bypass.split(",") if b.strip()])
            bypass = f"{extra};{DEFAULT_BYPASS_LIST}"

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, INTERNET_SETTINGS, 0, winreg.KEY_ALL_ACCESS)
        
        # Standard proxy settings
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"{host}:{port}")
        winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, bypass)

        if use_pac:
            # Enable Proxy Auto-Configuration (PAC) Script
            winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, "http://127.0.0.1:8000/proxy.pac")

        winreg.CloseKey(key)
        refresh_system_proxy()
        logger.info(f"System proxy enabled (PAC={use_pac}): {host}:{port} with bypass: {bypass}")
        return True
    except Exception as e:
        logger.error(f"Error enabling system proxy: {e}")
        return False

def disable_system_proxy():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, INTERNET_SETTINGS, 0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        try:
            winreg.DeleteValue(key, "AutoConfigURL")
        except Exception:
            pass
        winreg.CloseKey(key)
        refresh_system_proxy()
        logger.info("System proxy disabled")
        return True
    except Exception as e:
        logger.error(f"Error disabling system proxy: {e}")
        return False

def get_system_proxy_status():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, INTERNET_SETTINGS, 0, winreg.KEY_READ)
        enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
        server, _ = winreg.QueryValueEx(key, "ProxyServer") if enabled else (None, None)
        try:
            bypass, _ = winreg.QueryValueEx(key, "ProxyOverride")
        except Exception:
            bypass = ""
        winreg.CloseKey(key)
        return bool(enabled), server, bypass
    except Exception:
        return False, None, ""
