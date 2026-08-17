from lxml import etree
import copy
import base64
import re

def sanitize_ubl_xml(xml_content: bytes) -> bytes:
    """
    Parses a UBL XML bytestream, masks PII (Personally Identifiable Information),
    and returns the sanitized XML bytestream.
    """
    try:
        # Parse without altering original formatting too much, hardened against XXE/Billion Laughs
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            dtd_validation=False,
            load_dtd=False,
            huge_tree=False,
            remove_blank_text=False
        )
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
        
        nodes_to_remove = []
        for elem in root.iter():
            # Extract local name (ignore namespace)
            local_name = etree.QName(elem).localname
            parent = elem.getparent()
            parent_local = etree.QName(parent).localname if parent is not None else ""
            
            # Party Name masking - strictly check parent to avoid corrupting Item/Country/TaxScheme Names
            if local_name == "Name" and elem.text and elem.text.strip():
                if parent_local in ["PartyName", "Person", "Contact", "CorporateRegistrationScheme"]:
                    elem.text = "ANONİM FİRMA A.Ş."
            
            elif local_name in mask_rules and elem.text and elem.text.strip():
                elem.text = mask_rules[local_name]
            
            # Mask free text Notes if they exist
            elif local_name == "Note" and elem.text and elem.text.strip():
                elem.text = "NOT ALANI KVKK KAPSAMINDA MASKELE NMİŞTİR."
            
            # Special handling for VKN/TCKN (CompanyID, IdentificationCode, etc.)
            elif local_name in ["CompanyID", "IdentificationCode", "ID"] and elem.text and elem.text.strip():
                # If it's a PartyTaxScheme/CompanyID or PartyIdentification/ID or Person/NationalityID
                if parent_local in ["PartyTaxScheme", "PartyIdentification", "Person"]:
                    text_len = len(elem.text.strip())
                    if text_len == 11:
                        elem.text = "11111111111"
                    elif text_len == 10:
                        elem.text = "1111111111"
                    else:
                        elem.text = "1111111111" # default mask
            
            # Remove Digital Signatures to anonymize company sign
            elif local_name == "Signature":
                nodes_to_remove.append(elem)
            
            # Clear Embedded Binaries (Logos, attached PDFs) with a 1x1 transparent GIF
            # but preserve the XSLT stylesheet for rendering, masking any embedded images inside it
            elif local_name == "EmbeddedDocumentBinaryObject":
                if elem.text:
                    try:
                        decoded = base64.b64decode(elem.text.strip())
                        if b"<xsl:stylesheet" in decoded or b"<xsl:transform" in decoded:
                            try:
                                xslt_root = etree.fromstring(decoded)
                                b64_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\\n\\r\\t ")
                                for node in xslt_root.iter():
                                    if node.text and len(node.text) > 200:
                                        if not set(node.text) - b64_chars:
                                            node.text = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                                    for attr_name, attr_value in node.attrib.items():
                                        if len(attr_value) > 200 and "base64," in attr_value:
                                            prefix_idx = attr_value.find("base64,") + 7
                                            node.attrib[attr_name] = attr_value[:prefix_idx] + "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                                sanitized_xslt = etree.tostring(xslt_root, encoding='utf-8')
                            except Exception:
                                pattern = b"(data:image/[a-zA-Z0-9+-]+;base64,)[a-zA-Z0-9+/=\\r\\n\\t ]+"
                                replacement = b"\\g<1>R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                                sanitized_xslt = re.sub(pattern, replacement, decoded, flags=re.IGNORECASE)
                            elem.text = base64.b64encode(sanitized_xslt).decode("utf-8")
                        else:
                            elem.text = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                    except Exception:
                        # If base64 decoding fails, clear it anyway
                        elem.text = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
                
        for elem in nodes_to_remove:
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)

        # Convert back to bytes
        # XML declaration is preserved if we write it out. 
        # But etree.tostring doesn't automatically insert <?xml version="1.0" encoding="UTF-8"?> unless specified
        sanitized_xml = etree.tostring(root, encoding='utf-8', xml_declaration=True)
        return sanitized_xml
        
    except Exception as e:
        raise ValueError(f"XML Anonimleştirme sırasında hata oluştu: {str(e)}")
