import os
import re
import sys

# Try to import pyodbc for SQL Server connectivity
HAS_PYODBC = False
try:
    import pyodbc
    HAS_PYODBC = True
except ImportError:
    pass


def _redact_secrets(text: str) -> str:
    """Bazı ODBC sürücüleri hata mesajına bağlantı dizesini gömebiliyor; loglamadan önce PWD alanını maskele."""
    return re.sub(r"(?i)PWD=[^;]*", "PWD=***", text)

class DBConnector:
    def __init__(self, server=None, database=None, username=None, password=None, trusted=True):
        self.server = server or "localhost\\SQLEXPRESS"
        self.database = database or "zirvegenel"
        self.username = username
        self.password = password
        self.trusted = trusted
        self.connection = None
        self.cursor = None

    def connect(self):
        if not HAS_PYODBC:
            print("[DBConnector] pyodbc not installed. Running in MOCK mode.")
            return False
            
        try:
            if self.trusted:
                conn_str = f"DRIVER={{SQL Server}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;"
            else:
                conn_str = f"DRIVER={{SQL Server}};SERVER={self.server};DATABASE={self.database};UID={self.username};PWD={self.password};"
                
            self.connection = pyodbc.connect(conn_str, timeout=3)
            self.cursor = self.connection.cursor()
            print(f"[DBConnector] Connected to SQL Server database: {self.database}")
            return True
        except Exception as e:
            print(f"[DBConnector] Connection to SQL Server failed: {_redact_secrets(str(e))}. Running in MOCK mode.")
            self.connection = None
            self.cursor = None
            return False

    def execute_query(self, query, params=None):
        """
        Executes an SQL query. Returns list of dicts.
        If connection is mock, returns simulated data.
        """
        if self.connection and self.cursor:
            try:
                if params:
                    self.cursor.execute(query, params)
                else:
                    self.cursor.execute(query)
                    
                columns = [column[0] for column in self.cursor.description]
                results = []
                for row in self.cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return results
            except Exception as e:
                print(f"[DBConnector] Query execution failed: {_redact_secrets(str(e))}")
                return []
        else:
            return self._get_mock_data(query, params)

    def _get_mock_data(self, query, params):
        query_upper = query.upper()
        if "FATURA_ALT" in query_upper or "FATSATIR" in query_upper:
            # Mock Invoice Lines
            return [
                {"SATIRNO": 1, "URUNADI": "A4 KOPYALAMA KAGIDI", "MIKTAR": 10.0, "FIYAT": 120.00, "KDVORAN": 20, "TUTAR": 1200.00, "KDVTEVKIFATKODU": ""},
                {"SATIRNO": 2, "URUNADI": "TUKENMEZ KALEM MAVI", "MIKTAR": 50.0, "FIYAT": 15.50, "KDVORAN": 10, "TUTAR": 775.00, "KDVTEVKIFATKODU": ""}
            ]
        elif "FATURA" in query_upper:
            # Mock Invoice Header
            return [{
                "FATURA_ID": 1001,
                "FATURANO": "GKM2026000000001",
                "TARIH": "2026-07-02",
                "GENELTOPLAM": 2372.50,
                "VERGINO": "1234567890",
                "FIRMAKODU": "GÖRKEM_KOLAY",
                "CARIKODU": "C001",
                "NOT": "Deneme faturasıdır, test amaçlı üretilmiştir."
            }]
        elif "FIRMA" in query_upper or "CARI" in query_upper:
            # Mock Company / Customer Details
            return [{
                "UNVAN": "GÖRKEM KOLAY DANIŞMANLIK LİMİTED ŞİRKETİ",
                "VERGINO": "1234567890",
                "VERGIDAIRESI": "Kordonboyu",
                "ADRES": "Zirve Plaza Kat 4, Ataşehir, İstanbul",
                "TELEFON": "02161234567",
                "EPOSTA": "info@gorkemkolay.com"
            }]
        return []

    def close(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
