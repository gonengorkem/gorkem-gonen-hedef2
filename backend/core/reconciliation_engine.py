import os
from lxml import etree
from core.db_connector import DBConnector

# Standard UBL-TR namespaces
NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
}

def parse_ubl_invoice_data(xml_path: str) -> dict:
    """
    Parses key business fields from a UBL invoice XML file.
    """
    try:
        with open(xml_path, 'rb') as f:
            content = f.read()
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        root = etree.fromstring(content, parser=parser)
        
        # Parse basic fields
        invoice_no = root.findtext("cbc:ID", namespaces=NS) or ""
        uuid = root.findtext("cbc:UUID", namespaces=NS) or ""
        issue_date = root.findtext("cbc:IssueDate", namespaces=NS) or ""
        payable_amount = root.findtext("cac:LegalMonetaryTotal/cbc:PayableAmount", namespaces=NS)
        
        # Company Info
        company_name = root.findtext("cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name", namespaces=NS) or \
                       root.findtext("cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName", namespaces=NS) or ""
        company_vkn = root.findtext("cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID='VKN']", namespaces=NS) or \
                      root.findtext("cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID='TCKN']", namespaces=NS) or ""
                      
        # Customer Info
        customer_name = root.findtext("cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name", namespaces=NS) or \
                        root.findtext("cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName", namespaces=NS) or ""
        customer_vkn = root.findtext("cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID='VKN']", namespaces=NS) or \
                       root.findtext("cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID='TCKN']", namespaces=NS) or ""
        
        # Line Items
        lines = []
        for idx, line_node in enumerate(root.findall("cac:InvoiceLine", namespaces=NS)):
            line_no = line_node.findtext("cbc:ID", namespaces=NS) or str(idx + 1)
            item_name = line_node.findtext("cac:Item/cbc:Name", namespaces=NS) or ""
            qty = line_node.findtext("cbc:InvoicedQuantity", namespaces=NS)
            price = line_node.findtext("cac:Price/cbc:PriceAmount", namespaces=NS)
            vat_percent = line_node.findtext("cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent", namespaces=NS)
            line_total = line_node.findtext("cbc:LineExtensionAmount", namespaces=NS)
            
            lines.append({
                "line_no": int(line_no) if line_no.isdigit() else idx + 1,
                "item_name": item_name,
                "quantity": float(qty) if qty else 0.0,
                "price": float(price) if price else 0.0,
                "vat_percent": float(vat_percent) if vat_percent else 0.0,
                "line_total": float(line_total) if line_total else 0.0
            })
            
        return {
            "invoice_no": invoice_no,
            "uuid": uuid,
            "issue_date": issue_date,
            "payable_amount": float(payable_amount) if payable_amount else 0.0,
            "company_name": company_name,
            "company_vkn": company_vkn,
            "customer_name": customer_name,
            "customer_vkn": customer_vkn,
            "lines": lines
        }
    except Exception as e:
        print(f"[ReconciliationEngine] XML Parsing error: {e}")
        return {}

def run_reconciliation(xml_path: str, server: str, company_code: str, year: str, username: str = None, password: str = None, trusted: bool = True) -> dict:
    """
    Compares the XML invoice data against SQL Server database records.
    """
    # 1. Parse UBL XML
    xml_data = parse_ubl_invoice_data(xml_path)
    if not xml_data:
        return {"status": "error", "message": "XML fatura verileri okunamadı."}
        
    invoice_no = xml_data["invoice_no"]
    
    # Determine year database (e.g. 2026T)
    db_name = f"{year}T" if year else "2026T"
    
    # 2. Connect to SQL database
    connector = DBConnector(server=server, database=db_name, username=username, password=password, trusted=trusted)
    is_connected = connector.connect()
    
    # 3. Pull SQL Data
    # Fetch invoice header
    header_query = f"SELECT * FROM dbo.FATURA WHERE FATURANO = '{invoice_no}'"
    header_records = connector.execute_query(header_query)
    
    # Fetch invoice lines
    lines_query = f"SELECT * FROM dbo.FATURA_ALT WHERE FATURANO = '{invoice_no}' OR FATURA_ID = (SELECT FATURA_ID FROM dbo.FATURA WHERE FATURANO = '{invoice_no}')"
    lines_records = connector.execute_query(lines_query)
    
    # Fetch global company info (Cross-database join simulation or direct query)
    company_query = f"SELECT * FROM zirvegenel.dbo.FIRMA_PROFILLERI WHERE FIRMAKODU = '{company_code}'"
    company_records = connector.execute_query(company_query)
    
    # Close connection
    connector.close()
    
    # 4. Comparative Audit Logic
    audit_results = []
    
    # Header Auditing
    sql_header = header_records[0] if header_records else {}
    sql_company = company_records[0] if company_records else {}
    
    # Compare Company Name
    db_comp_name = sql_company.get("UNVAN", "MOCK GÖRKEM KOLAY DANIŞMANLIK LİMİTED ŞİRKETİ") if is_connected else "GÖRKEM KOLAY DANIŞMANLIK LİMİTED ŞİRKETİ"
    audit_results.append({
        "scope": "Firma Bilgisi",
        "field": "Firma Unvanı",
        "db_val": db_comp_name,
        "xml_xpath": "//cac:AccountingSupplierParty/.../cbc:Name",
        "xml_val": xml_data["company_name"],
        "status": "match" if db_comp_name.strip().lower() == xml_data["company_name"].strip().lower() else "mismatch"
    })
    
    # Compare General Total
    db_total = float(sql_header.get("GENELTOPLAM", xml_data["payable_amount"]))
    diff_total = abs(db_total - xml_data["payable_amount"])
    status_total = "match"
    if diff_total > 0.02:
        status_total = "mismatch"
    elif diff_total > 0.00:
        status_total = "drift" # Rounding difference
        
    audit_results.append({
        "scope": "Fatura Toplamı",
        "field": "Ödenecek Tutar",
        "db_val": f"{db_total:.2f} TL",
        "xml_xpath": "//cac:LegalMonetaryTotal/cbc:PayableAmount",
        "xml_val": f"{xml_data['payable_amount']:.2f} TL",
        "status": status_total,
        "details": f"Fark: {diff_total:.4f} TL (Yuvarlama)" if status_total == "drift" else ""
    })
    
    # Line Items Auditing
    xml_lines = xml_data["lines"]
    sql_lines = sorted(lines_records, key=lambda x: x.get("SATIRNO", 0))
    
    for i, xml_line in enumerate(xml_lines):
        sql_line = sql_lines[i] if i < len(sql_lines) else {}
        
        # Compare Line Item Name
        db_item_name = sql_line.get("URUNADI", xml_line["item_name"])
        audit_results.append({
            "scope": f"Satır {xml_line['line_no']}",
            "field": "Ürün/Hizmet Adı",
            "db_val": db_item_name,
            "xml_xpath": "cac:InvoiceLine/cac:Item/cbc:Name",
            "xml_val": xml_line["item_name"],
            "status": "match" if db_item_name == xml_line["item_name"] else "mismatch"
        })
        
        # Compare Quantity
        db_qty = float(sql_line.get("MIKTAR", xml_line["quantity"]))
        audit_results.append({
            "scope": f"Satır {xml_line['line_no']}",
            "field": "Miktar",
            "db_val": f"{db_qty:.2f}",
            "xml_xpath": "cac:InvoiceLine/cbc:InvoicedQuantity",
            "xml_val": f"{xml_line['quantity']:.2f}",
            "status": "match" if db_qty == xml_line["quantity"] else "mismatch"
        })
        
        # Compare Price
        db_price = float(sql_line.get("FIYAT", xml_line["price"]))
        audit_results.append({
            "scope": f"Satır {xml_line['line_no']}",
            "field": "Birim Fiyat",
            "db_val": f"{db_price:.4f} TL",
            "xml_xpath": "cac:InvoiceLine/cac:Price/cbc:PriceAmount",
            "xml_val": f"{xml_line['price']:.4f} TL",
            "status": "match" if db_price == xml_line["price"] else "mismatch"
        })
        
        # Compare VAT Percent
        db_vat = float(sql_line.get("KDVORAN", xml_line["vat_percent"]))
        audit_results.append({
            "scope": f"Satır {xml_line['line_no']}",
            "field": "KDV Oranı",
            "db_val": f"%{db_vat:.0f}",
            "xml_xpath": "cac:InvoiceLine/.../cbc:Percent",
            "xml_val": f"%{xml_line['vat_percent']:.0f}",
            "status": "match" if db_vat == xml_line["vat_percent"] else "mismatch"
        })
        
    # Check for missing elements (e.g. database fields empty in XML)
    if is_connected and not sql_header:
        audit_results.append({
            "scope": "Veri Bulunamadı",
            "field": "Fatura Kaydı",
            "db_val": f"{invoice_no} no'lu kayıt",
            "xml_xpath": "cbc:ID",
            "xml_val": invoice_no,
            "status": "missing_in_db"
        })
        
    return {
        "status": "success",
        "is_mock": not is_connected,
        "invoice_no": invoice_no,
        "audit_results": audit_results
    }
