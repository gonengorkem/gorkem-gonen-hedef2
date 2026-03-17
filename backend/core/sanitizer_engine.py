from lxml import etree
import copy

def sanitize_ubl_xml(xml_content: bytes) -> bytes:
    """
    Parses a UBL XML bytestream, masks PII (Personally Identifiable Information),
    and returns the sanitized XML bytestream.
    """
    try:
        # Parse without altering original formatting too much
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(xml_content, parser)
        
        # We will loop through all elements and check their local-name
        # Masking mappings based on element local name
        mask_rules = {
            "Name": "ANONİM FİRMA A.Ş.",
            "FirstName": "ANONİM",
            "FamilyName": "KİŞİ",
            "RegistrationName": "ANONİM BİLİŞİM TEST A.Ş.",
            "BuildingName": "TEST BİNASI",
            "CitySubdivisionName": "TEST İLÇESİ",
            "CityName": "TEST ŞEHRİ",
            "StreetName": "TEST SOKAĞI",
            "Room": "1",
            "BuildingNumber": "10",
            "Telephone": "05555555555",
            "Telefax": "05555555555",
            "ElectronicMail": "test@test.com",
        }
        
        for elem in root.iter():
            # Extract local name (ignore namespace)
            local_name = etree.QName(elem).localname
            
            if local_name in mask_rules and elem.text and elem.text.strip():
                elem.text = mask_rules[local_name]
            
            # Special handling for VKN/TCKN (CompanyID, IdentificationCode, etc.)
            elif local_name in ["CompanyID", "IdentificationCode", "ID"] and elem.text and elem.text.strip():
                # Check if parent is PartyIdentification or similar to avoid messing up generic IDs (like Invoice/ID)
                parent_local = etree.QName(elem.getparent()).localname if elem.getparent() is not None else ""
                
                # If it's a PartyTaxScheme/CompanyID or PartyIdentification/ID or Person/NationalityID
                if parent_local in ["PartyTaxScheme", "PartyIdentification", "Person"]:
                    text_len = len(elem.text.strip())
                    if text_len == 11:
                        elem.text = "11111111111"
                    elif text_len == 10:
                        elem.text = "1111111111"
                    else:
                        elem.text = "1111111111" # default mask
                
        # Convert back to bytes
        # XML declaration is preserved if we write it out. 
        # But etree.tostring doesn't automatically insert <?xml version="1.0" encoding="UTF-8"?> unless specified
        sanitized_xml = etree.tostring(root, encoding='utf-8', xml_declaration=True)
        return sanitized_xml
        
    except Exception as e:
        raise ValueError(f"XML Anonimleştirme sırasında hata oluştu: {str(e)}")
