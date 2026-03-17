from lxml import etree
import os
import traceback

def parse_xml_file(filepath: str):
    try:
        # Encoding sorunlarını aşmak için binary okuyup lxml'e vermek daha güvenlidir
        with open(filepath, 'rb') as f:
            content = f.read()
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        return etree.fromstring(content, parser=parser)
    except Exception as e:
        print(f"HATA: {filepath} dosyası parse edilemedi. Sebebi: {e}")
        return None

def extract_elements(tree):
    # Extracts all element names and their attributes from an XML/XSD tree
    elements = {}
    if tree is None:
        return elements
        
    for elem in tree.iter():
        if type(elem) == etree._Comment or type(elem) == etree._ProcessingInstruction:
            continue
            
        # Strip namespace mapping for cleaner target matching
        tag_name = etree.QName(elem.tag).localname if hasattr(elem.tag, 'startswith') else str(elem.tag)
        
        if tag_name not in elements:
            elements[tag_name] = []
            
        tree_path = tree.getroottree().getpath(elem) if hasattr(tree, 'getroottree') else ""
        
        elements[tag_name].append({
            "xpath": tree_path,
            "attributes": dict(elem.attrib) if hasattr(elem, 'attrib') else {},
            "text": elem.text.strip() if hasattr(elem, 'text') and elem.text else None
        })
    return elements

def compare_files(old_filepath: str, new_filepath: str):
    old_tree = parse_xml_file(old_filepath)
    new_tree = parse_xml_file(new_filepath)
    
    old_els = extract_elements(old_tree)
    new_els = extract_elements(new_tree)
    
    diff_report = []
    
    # Check elements in new tree
    for tag_name, new_list in new_els.items():
        if tag_name not in old_els:
            diff_report.append({
                "type": "added",
                "target": tag_name,
                "message": f"'{tag_name}' adlı yeni bir element eklendi.",
                "details": new_list[0]["attributes"] if new_list else {}
            })
            continue
            
        # Simplistic compare for attribute changes on first match (can be deep mapped by xpath)
        old_list = old_els[tag_name]
        for new_item in new_list:
            # find matching old item by xpath
            matched_old = next((x for x in old_list if x["xpath"] == new_item["xpath"]), None)
            if matched_old is None:
                diff_report.append({
                    "type": "added",
                    "target": tag_name,
                    "xpath": new_item["xpath"],
                    "message": f"'{tag_name}' elementi listeye yeni eklendi.",
                })
            else:
                # Compare attributes
                for k, v in new_item["attributes"].items():
                    if k not in matched_old["attributes"]:
                        diff_report.append({
                            "type": "attribute_added",
                            "target": tag_name,
                            "xpath": new_item["xpath"],
                            "message": f"'{tag_name}' elementine '{k}={v}' özelliği eklendi."
                        })
                    elif matched_old["attributes"][k] != v:
                        diff_report.append({
                            "type": "modified",
                            "target": tag_name,
                            "xpath": new_item["xpath"],
                            "message": f"'{tag_name}' elementinin '{k}' özelliği '{matched_old['attributes'][k]}' değerinden '{v}' değerine güncellendi."
                        })
                        
    # Check elements removed from old tree
    for tag_name, old_list in old_els.items():
        if tag_name not in new_els:
            diff_report.append({
                "type": "removed",
                "target": tag_name,
                "message": f"'{tag_name}' adlı element tamamen kaldırıldı."
            })
        else:
            new_list = new_els[tag_name]
            for old_item in old_list:
                matched_new = next((x for x in new_list if x["xpath"] == old_item["xpath"]), None)
                if matched_new is None:
                    diff_report.append({
                        "type": "removed",
                        "target": tag_name,
                        "xpath": old_item["xpath"],
                        "message": f"'{tag_name}' elementinin bir instance'ı kaldırıldı.",
                    })
                    
    return diff_report

def run_analysis(old_data: dict, new_data: dict):
    old_files = old_data["files"]
    new_files = new_data["files"]
    
    all_files = set(old_files.keys()).union(set(new_files.keys()))
    
    results = []
    
    for file_path in all_files:
        if file_path not in old_files:
            results.append({
                "file": file_path,
                "status": "new_file",
                "diff": []
            })
        elif file_path not in new_files:
            results.append({
                "file": file_path,
                "status": "deleted_file",
                "diff": []
            })
        else:
            diff = compare_files(old_files[file_path], new_files[file_path])
            if diff:
                results.append({
                    "file": file_path,
                    "status": "modified",
                    "diff": diff
                })
            else:
                 results.append({
                    "file": file_path,
                    "status": "unchanged",
                    "diff": []
                })
                
    return results
