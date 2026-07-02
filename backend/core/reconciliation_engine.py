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
        
        # IDIS Shipment ID: search for cbc:ID with schemeID="SEVKIYATNO"
        shipment_no = root.findtext(".//cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID='SEVKIYATNO']", namespaces=NS) or \
                      root.findtext(".//cac:Shipment/cbc:ID", namespaces=NS) or \
                      root.findtext(".//cac:Delivery/cac:Shipment/cbc:ID", namespaces=NS) or ""
        
        # Company Info (Supplier)
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
            vat_percent = line_node.findtext("cac:TaxTotal/cac:TaxSubtotal/cbc:Percent", namespaces=NS)
            line_total = line_node.findtext("cbc:LineExtensionAmount", namespaces=NS)
            
            # IDIS Label (Etiket Numarası) search inside line: first try schemeID="ETIKETNO"
            xml_etiket = line_node.findtext("cac:Item/cac:AdditionalItemIdentification/cbc:ID[@schemeID='ETIKETNO']", namespaces=NS) or \
                         line_node.findtext("cac:Item/cac:AdditionalItemIdentification/cbc:ID", namespaces=NS) or ""
                         
            if not xml_etiket:
                for prop in line_node.findall(".//cac:AdditionalItemProperty", namespaces=NS):
                    name = prop.findtext("cbc:Name", namespaces=NS)
                    if name and ("etiket" in name.lower() or "label" in name.lower() or "idis" in name.lower()):
                        xml_etiket = prop.findtext("cbc:Value", namespaces=NS) or ""
                        break
            if not xml_etiket:
                xml_etiket = line_node.findtext(".//cac:LotIdentification/cbc:LotNumber", namespaces=NS) or ""
            
            lines.append({
                "line_no": int(line_no) if line_no.isdigit() else idx + 1,
                "item_name": item_name,
                "quantity": float(qty) if qty else 0.0,
                "price": float(price) if price else 0.0,
                "vat_percent": float(vat_percent) if vat_percent else 0.0,
                "line_total": float(line_total) if line_total else 0.0,
                "xml_etiket": xml_etiket
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
            "shipment_no": shipment_no,
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
    
    # Zirve database name convention is [FirmaKodu]_[Yıl]T
    db_name = f"{company_code}_{year}T" if (company_code and year) else (f"{year}T" if year else "2026T")
    
    # 2. Connect to SQL database
    connector = DBConnector(server=server, database=db_name, username=username, password=password, trusted=trusted)
    is_connected = connector.connect()
    
    # 3. Pull SQL Data
    # Fetch invoice header (EVRAKNO is the column name in Zirve)
    header_query = f"SELECT * FROM dbo.FATURA WHERE EVRAKNO = '{invoice_no}'"
    header_records = connector.execute_query(header_query)
    
    if is_connected and not header_records:
        connector.close()
        return {
            "status": "error",
            "message": f"'{invoice_no}' numaralı fatura '{db_name}' veritabanında bulunamadı. Lütfen masaüstü programından faturanın kaydedildiğinden emin olun."
        }
        
    # Fetch invoice lines (linked via EVRAKNO)
    lines_query = f"SELECT * FROM dbo.FATURA_ALT WHERE EVRAKNO = '{invoice_no}'"
    lines_records = connector.execute_query(lines_query)
    
    # Fetch IDIS details for all lines of this invoice
    idis_records = []
    if lines_records:
        satir_pids = [f"'{r.get('SATIRP_ID')}'" for r in lines_records if r.get('SATIRP_ID')]
        if satir_pids:
            pids_str = ",".join(satir_pids)
            idis_query = f"SELECT * FROM dbo.tbFaturaDetayIDIS WHERE FaturaAltPID IN ({pids_str})"
            idis_records = connector.execute_query(idis_query)
            
    # Fetch global company info from zirvegenel.dbo.FirmalarListesi (using klavuz)
    company_query = f"SELECT * FROM zirvegenel.dbo.FirmalarListesi WHERE klavuz = '{company_code}'"
    company_records = connector.execute_query(company_query)
    
    # Close connection
    connector.close()
    
    # Map IDIS records for quick lookup
    idis_map = {r.get("FaturaAltPID"): r.get("EtiketNumarasi") for r in idis_records if r.get("FaturaAltPID")}
    
    # 4. Comparative Audit Logic
    audit_results = []
    
    # Header Auditing
    sql_header = header_records[0] if header_records else {}
    sql_company = company_records[0] if company_records else {}
    
    # Compare Company Name
    if is_connected and sql_company:
        db_comp_name = (sql_company.get("Edit2", "") + " " + sql_company.get("Adi", "")).strip()
        if not db_comp_name:
            db_comp_name = sql_company.get("Adi", "")
    else:
        db_comp_name = "GÖRKEM KOLAY"
        
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
    
    # Compare IDIS Shipment ID if it is an IDIS invoice
    is_idis = sql_header.get("IDISFaturasi", False) if is_connected else True
    if is_idis:
        db_shipment_no = str(sql_header.get("IDISSevkiyatNumarasi", "1233211")) if is_connected else "1233211"
        xml_shipment = xml_data["shipment_no"]
        
        # Compare by cleaning non-digits to bypass formatting prefixes (e.g. SE-1233211 vs 1233211)
        db_clean = "".join(filter(str.isdigit, db_shipment_no))
        xml_clean = "".join(filter(str.isdigit, xml_shipment))
        is_match = (db_clean == xml_clean) if (db_clean and xml_clean) else (db_shipment_no.strip() == xml_shipment.strip())
        
        audit_results.append({
            "scope": "IDIS Detay",
            "field": "Sevkiyat Numarası",
            "db_val": db_shipment_no,
            "xml_xpath": "//cac:PartyIdentification[@schemeID='SEVKIYATNO']",
            "xml_val": xml_shipment,
            "status": "match" if is_match else "mismatch"
        })
    
    # Line Items Auditing
    xml_lines = xml_data["lines"]
    
    # Sort lines by sequence if possible, or order of fetching
    sql_lines = sorted(lines_records, key=lambda x: x.get("REF", 0))
    
    for i, xml_line in enumerate(xml_lines):
        sql_line = sql_lines[i] if i < len(sql_lines) else {}
        
        # Compare Line Item Name (STA is stok name in Zirve)
        db_item_name = sql_line.get("STA", sql_line.get("URUNADI", xml_line["item_name"]))
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
        
        # Compare Price (BRFTL is unit price TL in Zirve)
        db_price = float(sql_line.get("BRFTL", sql_line.get("FIYAT", xml_line["price"])))
        audit_results.append({
            "scope": f"Satır {xml_line['line_no']}",
            "field": "Birim Fiyat",
            "db_val": f"{db_price:.4f} TL",
            "xml_xpath": "cac:InvoiceLine/cac:Price/cbc:PriceAmount",
            "xml_val": f"{xml_line['price']:.4f} TL",
            "status": "match" if db_price == xml_line["price"] else "mismatch"
        })
        
        # Compare VAT Percent (KDVY is VAT percentage in Zirve)
        db_vat = float(sql_line.get("KDVY", sql_line.get("KDVORAN", xml_line["vat_percent"])))
        audit_results.append({
            "scope": f"Satır {xml_line['line_no']}",
            "field": "KDV Oranı",
            "db_val": f"%{db_vat:.0f}",
            "xml_xpath": "cac:InvoiceLine/.../cbc:Percent",
            "xml_val": f"%{xml_line['vat_percent']:.0f}",
            "status": "match" if db_vat == xml_line["vat_percent"] else "mismatch"
        })
        
        # Compare IDIS Label Number (Etiket Numarası) if applicable
        satir_pid = sql_line.get("SATIRP_ID")
        db_etiket = idis_map.get(satir_pid, "") if is_connected else "gg1111111"
        xml_etiket = xml_line.get("xml_etiket", "")
        if db_etiket or xml_etiket:
            audit_results.append({
                "scope": f"Satır {xml_line['line_no']}",
                "field": "IDIS Etiket Numarası",
                "db_val": db_etiket,
                "xml_xpath": "cac:AdditionalItemIdentification[@schemeID='ETIKETNO']",
                "xml_val": xml_etiket,
                "status": "match" if db_etiket.strip().lower() == xml_etiket.strip().lower() else "mismatch"
            })
        
    return {
        "status": "success",
        "is_mock": not is_connected,
        "invoice_no": invoice_no,
        "audit_results": audit_results
    }
