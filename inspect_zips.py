import zipfile
import os
import tempfile
import uuid

def read_txt_from_zip(filepath):
    print(f"\n--- READING TXT FROM {filepath} ---")
    extraction_dir = os.path.join(tempfile.gettempdir(), f"inspect_{uuid.uuid4().hex}")
    os.makedirs(extraction_dir, exist_ok=True)
    
    with zipfile.ZipFile(filepath, 'r') as z:
        z.extractall(extraction_dir)
        
    for root, dirs, files in os.walk(extraction_dir):
        for f in files:
            if f.endswith('.txt'):
                txt_path = os.path.join(root, f)
                print(f"Icerik: {txt_path}")
                try:
                    with open(txt_path, 'r', encoding='utf-8') as text_file:
                        content = text_file.read()
                        print(content[:1000]) # Print first 1000 chars
                except UnicodeDecodeError:
                    with open(txt_path, 'r', encoding='iso-8859-9') as text_file:
                        content = text_file.read()
                        print(content[:1000]) # Print first 1000 chars

read_txt_from_zip(r"C:\yeni.zip")
