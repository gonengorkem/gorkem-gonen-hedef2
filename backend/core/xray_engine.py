from lxml import etree
import base64
import re

def find_xpaths_in_ubl(xml_base64: str, search_text: str) -> list:
    """
    Decodes the base64 XML, searches for the selected text or numeric value,
    and returns a list of matching XPaths and their exact values.
    """
    try:
        xml_bytes = base64.b64decode(xml_base64)
        parser = etree.XMLParser(recover=True, remove_blank_text=False)
        root = etree.fromstring(xml_bytes, parser)
        
        search_text = search_text.strip()
        if not search_text:
            return []
            
        # Determine if search_text is likely a formatted number (e.g., 1.500,00)
        is_numeric = False
        clean_search_float = None
        
        # Strip common currency symbols to handle things like "10.000,00TL"
        currency_symbols = ['TL', 'TRY', '₺', '€', '$', 'EUR', 'USD', '£']
        clean_search_text = search_text.upper()
        for sym in currency_symbols:
            clean_search_text = clean_search_text.replace(sym, "")
        clean_search_text = clean_search_text.strip()
        
        # Simple heuristic for numeric match: Only digits, dots, commas, minus, plus, spaces
        if re.match(r'^[-+\d.,\s]+$', clean_search_text) and any(c.isdigit() for c in clean_search_text):
            try:
                # Convert "1.500,00" or "1,500.00" to a standard float
                # We'll try common Turkish format first: dot for thousands, comma for decimals
                cleaned = clean_search_text.replace(" ", "")
                if "," in cleaned and "." in cleaned:
                    if cleaned.rfind(",") > cleaned.rfind("."):
                        # Turkish: 1.500,00 -> 1500.00
                        cleaned = cleaned.replace(".", "").replace(",", ".")
                    else:
                        # US: 1,500.00 -> 1500.00
                        cleaned = cleaned.replace(",", "")
                elif "," in cleaned:
                    cleaned = cleaned.replace(",", ".")
                
                clean_search_float = float(cleaned)
                is_numeric = True
            except ValueError:
                pass


        results = []
        tree = etree.ElementTree(root)
        
        for elem in root.iter():
            if elem.text:
                text = elem.text.strip()
                if not text:
                    continue
                
                match = False
                
                # If numeric, try to parse XML text as float and compare
                if is_numeric and clean_search_float is not None:
                    try:
                        elem_float = float(text)
                        # We use a small epsilon for floating point comparison just in case
                        if abs(elem_float - clean_search_float) < 0.0001:
                            match = True
                    except ValueError:
                        # Fallback to substring if element is not actually a number
                        if search_text.lower() in text.lower():
                            match = True
                else:
                    # Substring match (case-insensitive)
                    if search_text.lower() in text.lower():
                        match = True
                        
                if match:
                    # Build human-readable XPath using local names
                    parts = []
                    current = elem
                    while current is not None:
                        # Remove namespace for cleaner output
                        parts.insert(0, etree.QName(current).localname)
                        current = current.getparent()
                    
                    xpath_str = "/".join(parts)
                    
                    results.append({
                        "xpath": xpath_str,
                        "value": text,
                        "line": elem.sourceline or 1
                    })
                    
        # Remove exact duplicates
        unique_results = []
        seen = set()
        for r in results:
            identifier = r["xpath"] + r["value"] + str(r["line"])
            if identifier not in seen:
                seen.add(identifier)
                unique_results.append(r)
                
        return unique_results
        
    except Exception as e:
        raise ValueError(f"X-Ray arama hatası: {str(e)}")
