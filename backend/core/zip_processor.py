import zipfile
import os
import tempfile
import uuid

TARGET_EXTENSIONS = {'.xsd', '.xslt', '.xml', '.sch'}

def extract_nested_zips(extraction_dir: str):
    """
    Kök dizindeki extract edilmiş zip içinde başka .zip'ler varsa onları da çıkarır 
    (İç içe klasör/zip yapısı için).
    """
    found_nested = True
    while found_nested:
        found_nested = False
        for root, _, files in os.walk(extraction_dir):
            for file in files:
                if file.lower().endswith('.zip'):
                    nested_zip_path = os.path.join(root, file)
                    nested_extract_dir = os.path.join(root, file + "_extracted")
                    try:
                        os.makedirs(nested_extract_dir, exist_ok=True)
                        with zipfile.ZipFile(nested_zip_path, 'r') as z:
                            z.extractall(nested_extract_dir)
                        os.remove(nested_zip_path) # Extracted zips can be removed
                        found_nested = True
                        break # break to avoid mutating the os.walk iterator
                    except zipfile.BadZipFile:
                        pass # Silently ignore bad nested zips
            if found_nested:
                break # Restart os.walk since directory structure changed

def extract_and_filter_zip(zip_filepath: str) -> dict:
    """
    Extracts a zip file to a temporary directory and identifies files with target extensions.
    Returns a dict mapping relative paths to their absolute extracted paths.
    """
    extraction_dir = os.path.join(tempfile.gettempdir(), f"gib_processor_{uuid.uuid4().hex}")
    os.makedirs(extraction_dir, exist_ok=True)
    
    extracted_files = {}
    all_files_debug = []
    
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(extraction_dir)
            
        # Eğer paket içinde başka zip'ler varsa onları da çıkar (GİB paketleri sıklıkla iç içedir)
        extract_nested_zips(extraction_dir)
            
        for root, _, files in os.walk(extraction_dir):
            for file in files:
                all_files_debug.append(file)
                ext = os.path.splitext(file)[1].lower()
                if ext in TARGET_EXTENSIONS:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.basename(file)
                    # Sadece isim odaklı son dosya ezilebilir (örn: aynı xsd'den iki adet varsa)
                    # Ancak GİB'de asıl şemalar unique'dir.
                    extracted_files[rel_path] = abs_path
                    
        with open("debug_files.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- YUKLENEN ZIP ISLENDI ---\n")
            f.write(f"Zip Yolu: {zip_filepath}\n")
            f.write(f"Icerisindeki TUM Dosyalar ({len(all_files_debug)} adet): \n")
            for debug_file in all_files_debug:
                f.write(f"  > {debug_file}\n")
            
    except zipfile.BadZipFile:
        raise ValueError(f"Geçersiz ZIP dosyası formatı: {zip_filepath}")
        
    return {
        "extraction_dir": extraction_dir,
        "files": extracted_files
    }
