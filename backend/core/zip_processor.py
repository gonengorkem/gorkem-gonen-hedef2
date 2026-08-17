import zipfile
import os
import tempfile
import uuid
import subprocess

TARGET_EXTENSIONS = {'.xsd', '.xslt', '.xml', '.sch'}
ARCHIVE_EXTENSIONS = ('.zip', '.rar')

def uncompress_archive_file(archive_filepath: str, target_dir: str):
    """
    ZIP ve RAR arşivlerini extract eder.
    ZIP için standart zipfile kütüphanesini kullanır, yedek olarak veya .rar için Windows'ta dahili bsdtar (tar) komutunu çalıştırır.
    """
    ext = os.path.splitext(archive_filepath)[1].lower()
    
    if ext == '.zip':
        try:
            with zipfile.ZipFile(archive_filepath, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            return
        except (zipfile.BadZipFile, Exception):
            pass  # Fallback to tar if zipfile fails
            
    # RAR veya Zip fallback için bsdtar kullan
    res = subprocess.run(["tar", "-xf", archive_filepath, "-C", target_dir], capture_output=True)
    if res.returncode != 0:
        err_msg = res.stderr.decode('utf-8', errors='ignore')
        raise ValueError(f"Arşiv dosyası çıkarılamadı ({archive_filepath}): {err_msg or 'Bilinmeyen arşiv hatası'}")

def extract_nested_zips(extraction_dir: str):
    """
    Kök dizindeki extract edilmiş arşiv içinde başka .zip veya .rar'lar varsa onları da çıkarır 
    (İç içe klasör/zip/rar yapısı için).
    """
    found_nested = True
    while found_nested:
        found_nested = False
        for root, _, files in os.walk(extraction_dir):
            for file in files:
                if file.lower().endswith(ARCHIVE_EXTENSIONS):
                    nested_archive_path = os.path.join(root, file)
                    nested_extract_dir = os.path.join(root, file + "_extracted")
                    try:
                        os.makedirs(nested_extract_dir, exist_ok=True)
                        uncompress_archive_file(nested_archive_path, nested_extract_dir)
                        os.remove(nested_archive_path) # Extracted archives can be removed
                        found_nested = True
                        break # break to avoid mutating the os.walk iterator
                    except Exception:
                        pass # Silently ignore bad nested archives
            if found_nested:
                break # Restart os.walk since directory structure changed

def extract_and_filter_zip(zip_filepath: str) -> dict:
    """
    Extracts a zip/rar file to a temporary directory and identifies files with target extensions.
    Returns a dict mapping relative paths to their absolute extracted paths.
    """
    extraction_dir = os.path.join(tempfile.gettempdir(), f"gib_processor_{uuid.uuid4().hex}")
    os.makedirs(extraction_dir, exist_ok=True)
    
    extracted_files = {}
    all_files_debug = []
    
    try:
        uncompress_archive_file(zip_filepath, extraction_dir)
            
        # Eğer paket içinde başka zip/rar'lar varsa onları da çıkar (GİB paketleri sıklıkla iç içedir)
        extract_nested_zips(extraction_dir)
            
        for root, _, files in os.walk(extraction_dir):
            for file in files:
                all_files_debug.append(file)
                ext = os.path.splitext(file)[1].lower()
                if ext in TARGET_EXTENSIONS:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.basename(file)
                    extracted_files[rel_path] = abs_path
                    
        with open("debug_files.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- YUKLENEN ARSIV ISLENDI ---\n")
            f.write(f"Arsiv Yolu: {zip_filepath}\n")
            f.write(f"Icerisindeki TUM Dosyalar ({len(all_files_debug)} adet): \n")
            for debug_file in all_files_debug:
                f.write(f"  > {debug_file}\n")
            
    except Exception as e:
        raise ValueError(f"Geçersiz veya okunamayan ZIP/RAR arşiv formatı: {zip_filepath} ({str(e)})")
        
    return {
        "extraction_dir": extraction_dir,
        "files": extracted_files
    }

