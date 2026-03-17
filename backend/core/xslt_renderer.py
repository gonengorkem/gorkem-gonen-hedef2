from lxml import etree
import base64

def render_ubl_to_html(xml_content: bytes) -> str:
    """
    Takes an XML bytestream, extracts the embedded XSLT,
    applies the XSLT to the XML, and returns the resulting HTML string.
    """
    try:
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(xml_content, parser)
        
        # 1. GİB UBL Formatında XSLT dosyasını bul ("EmbeddedDocumentBinaryObject" içinde)
        xslt_bytes = None
        for elem in root.iter():
            local_name = etree.QName(elem).localname
            if local_name == "EmbeddedDocumentBinaryObject" and elem.text:
                # XSLT dosyası olup olmadığını kontrol edelim
                filename = elem.get("filename", "").lower()
                mime = elem.get("mimeCode", "").lower()
                
                # UBL standartlarına göre XSLT dosyası olabilir
                try:
                    decoded = base64.b64decode(elem.text.strip())
                    if b"<xsl:stylesheet" in decoded or b"<xsl:transform" in decoded:
                        xslt_bytes = decoded
                        break
                except Exception:
                    continue
                    
        if not xslt_bytes:
            raise ValueError("Yüklenen XML dosyası içerisinde render edilebilecek embedded bir XSLT (Tasarım) dosyası bulunamadı.")
            
        # 2. XSLT dosyasını yükle ve dönüştürücüyü oluştur
        xslt_root = etree.fromstring(xslt_bytes)
        transform = etree.XSLT(xslt_root)
        
        # 3. XML'i XSLT kullanarak HTML'e dönüştür
        result_tree = transform(root)
        
        # HTML'i string olarak döndür
        html_str = str(result_tree)
        
        # Eğer <meta charset="..."> eklenmemişse, Türkçe karakter sorununu çözelim
        if "<head>" in html_str.lower() and "charset=" not in html_str.lower():
            html_str = html_str.replace("<head>", "<head><meta charset=\"UTF-8\">", 1)
            
        return html_str
        
    except ValueError as e:
         raise e
    except Exception as e:
         raise ValueError(f"XSLT Render işlemi sırasında hata oluştu: {str(e)}")
