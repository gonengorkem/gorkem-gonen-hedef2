import zipfile
import os
import tempfile
import uuid
import subprocess

TARGET_EXTENSIONS = {'.xsd', '.xslt', '.xml', '.sch'}
ARCHIVE_EXTENSIONS = ('.zip', '.rar')

def safe_extract_zip(zip_ref: zipfile.ZipFile, target_dir: str):
    """
    Zip Slip saldırılarına karşı her dosya yolunu doğrular ve güvenli şekilde çıkarır.
    """
    target_dir_abs = os.path.abspath(target_dir)
    for member in zip_ref.infolist():
        dest_path = os.path.abspath(os.path.join(target_dir_abs, member.filename))
        if not (dest_path == target_dir_abs or dest_path.startswith(target_dir_abs + os.sep)):
            raise ValueError(f"Güvenlik uyarısı: Zip Slip tespit edildi! Geçersiz dosya yolu: {member.filename}")
        zip_ref.extract(member, target_dir_abs)

def uncompress_archive_file(archive_filepath: str, target_dir: str):
    """
    ZIP ve RAR arşivlerini güvenli şekilde extract eder.
    ZIP için standart zipfile kütüphanesini ve Zip Slip denetimini kullanır.
    """
    ext = os.path.splitext(archive_filepath)[1].lower()
    target_dir_abs = os.path.abspath(target_dir)
    
    if ext == '.zip':
        try:
            with zipfile.ZipFile(archive_filepath, 'r') as zip_ref:
                safe_extract_zip(zip_ref, target_dir)
            return
        except zipfile.BadZipFile:
            pass  # Sadece bozuk/non-standard zip ise tar fallback'ine geç
        # Not: ValueError (Zip Slip tespit edildi) burada yutulmaz, işlemi anında keser.
            
    # RAR veya Zip fallback için bsdtar listeleme ve traversal denetimi
    list_res = subprocess.run(["tar", "-tf", archive_filepath], capture_output=True, text=True)
    if list_res.returncode == 0:
        for filename in list_res.stdout.splitlines():
            filename = filename.strip()
            if not filename:
                continue
            dest_path = os.path.abspath(os.path.join(target_dir_abs, filename))
            if not (dest_path == target_dir_abs or dest_path.startswith(target_dir_abs + os.sep)):
                raise ValueError(f"Güvenlik uyarısı: Arşiv içinde Zip Slip / Path Traversal tespit edildi! Dosya: {filename}")

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
    
    try:
        uncompress_archive_file(zip_filepath, extraction_dir)
            
        # Eğer paket içinde başka zip/rar'lar varsa onları da çıkar (GİB paketleri sıklıkla iç içedir)
        extract_nested_zips(extraction_dir)
            
        for root, _, files in os.walk(extraction_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in TARGET_EXTENSIONS:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, extraction_dir).replace('\\', '/')
                    extracted_files[rel_path] = abs_path
            
    except Exception as e:
        raise ValueError(f"Geçersiz veya okunamayan ZIP/RAR arşiv formatı: {zip_filepath} ({str(e)})")
        
    return {
        "extraction_dir": extraction_dir,
        "files": extracted_files
    }

