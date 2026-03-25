from lxml import etree
from lxml.isoschematron import Schematron

def validate_xml_with_schematron(xml_file_path, sch_file_path):
    """
    Validates an XML file against a Schematron (.sch) ruleset.
    Returns a dictionary with validation status and SVRL error reports.
    """
    try:
        # Parse SCH and initialize Schematron validator
        sch_doc = etree.parse(sch_file_path)
        schematron = Schematron(sch_doc, store_report=True)
        
        # Parse XML
        xml_doc = etree.parse(xml_file_path)
        
        # Validate
        is_valid = schematron.validate(xml_doc)
        
        results = {
            "is_valid": is_valid,
            "errors": [],
            "warnings": [] # Schematron warnings aren't directly distinct natively without role="warning" but we can try parsing roles if needed
        }
        
        if not is_valid:
            # SVRL XML output
            report = schematron.validation_report
            
            # Namespace for SVRL
            ns = {"svrl": "http://purl.oclc.org/dsdl/svrl"}
            
            # Find all failed assertions
            failed_asserts = report.findall(".//svrl:failed-assert", namespaces=ns) if report is not None else []
            
            for f_assert in failed_asserts:
                text_elem = f_assert.find("svrl:text", namespaces=ns)
                error_msg = text_elem.text.strip() if text_elem is not None and text_elem.text is not None else "Bilinmeyen Hata"
                location = f_assert.get("location", "Bilinmeyen Konum")
                test_rule = f_assert.get("test", "")
                
                # Attempt to extract the actual XML node text that failed using the location XPath
                actual_value = "Değer okunamadı"
                try:
                    if location != "Bilinmeyen Konum":
                        nodes = xml_doc.xpath(location)
                        if nodes:
                            elem = nodes[0]
                            if hasattr(elem, 'text') and elem.text is not None and elem.text.strip():
                                actual_value = elem.text.strip()
                            else:
                                # If the node has no text (e.g., missing child elements), return its tag name nicely
                                tag_name = etree.QName(elem).localname
                                actual_value = f"<{tag_name}> (İçeriği boş veya alt elemanı eksik)"
                except Exception:
                    pass
                
                results["errors"].append({
                    "message": error_msg,
                    "location": location,
                    "test": test_rule,
                    "value": actual_value
                })
        
        return results
        
    except etree.XMLSyntaxError as e:
        return {
            "is_valid": False,
            "errors": [{"message": f"XML/SCH Format Hatası: {str(e)}", "location": "N/A", "test": "N/A"}],
            "warnings": []
        }
    except Exception as e:
        return {
            "is_valid": False,
            "errors": [{"message": f"Validasyon motorunda hata: {str(e)}", "location": "N/A", "test": "N/A"}],
            "warnings": []
        }
