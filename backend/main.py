from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os
import tempfile
from core.zip_processor import extract_and_filter_zip
from core.diff_engine import run_analysis
from core.scenario_generator import generate_scenarios
from core.schematron_engine import validate_xml_with_schematron
from core.sanitizer_engine import sanitize_ubl_xml
from core.xslt_renderer import render_ubl_to_html
from core.xray_engine import find_xpaths_in_ubl
import base64
from typing import Optional

app = FastAPI(title="GİB Hedef Analizörü API")

# Ensure schematrons directory exists
SCHEMATRONS_DIR = os.path.join(os.path.dirname(__file__), "schematrons")
os.makedirs(SCHEMATRONS_DIR, exist_ok=True)

# Active extraction session paths for on-demand visual diffs
ACTIVE_EXTRACTION_SESSION = {
    "old_dir": None,
    "new_dir": None
}



# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "GİB Hedef Analizörü API Çalışıyor."}

def find_history_content(extraction_dir: str) -> Optional[str]:
    for root, _, files in os.walk(extraction_dir):
        for file in files:
            lf = file.lower()
            if 'history' in lf or 'guncelleme' in lf or 'tarihce' in lf or 'changelog' in lf or 'readme' in lf:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'rb') as f:
                        raw = f.read()
                    try:
                        return raw.decode('utf-8')
                    except UnicodeDecodeError:
                        return raw.decode('windows-1254', errors='replace')
                except Exception as e:
                    print(f"Error reading history file {file_path}: {e}")
    return None

@app.post("/api/analyze")
async def analyze_packages(
    old_package: UploadFile = File(...),
    new_package: UploadFile = File(...)
):
    if not old_package.filename or not new_package.filename or not old_package.filename.endswith('.zip') or not new_package.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Değerlendirme için .zip dosyaları gereklidir.")
    
    # Read files to compute cache key hash
    old_content = await old_package.read()
    new_content = await new_package.read()
    
    import hashlib
    old_hash = hashlib.md5(old_content).hexdigest()
    new_hash = hashlib.md5(new_content).hexdigest()
    cache_key = f"analysis:{old_hash}:{new_hash}"
    
    from core.redis_cache import redis_cache
    cached_response = redis_cache.get(cache_key)
    
    # Save uploaded files temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as old_temp:
        old_temp.write(old_content)
        old_zip_path = old_temp.name
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as new_temp:
        new_temp.write(new_content)
        new_zip_path = new_temp.name
        
    if cached_response:
        try:
            # Extract files so they are available for /api/diff/file on-demand
            old_data = extract_and_filter_zip(old_zip_path)
            new_data = extract_and_filter_zip(new_zip_path)
            ACTIVE_EXTRACTION_SESSION["old_dir"] = old_data["extraction_dir"]
            ACTIVE_EXTRACTION_SESSION["new_dir"] = new_data["extraction_dir"]
            # Clean zip paths
            os.remove(old_zip_path)
            os.remove(new_zip_path)
            print(f"[RedisCache] Analysis cache hit! Returning cached results.")
            return cached_response
        except Exception as ex:
            print(f"[RedisCache] Failed to extract files on cache hit: {ex}. Proceeding without cache.")
            
    try:
        # Extract and filter target files
        old_data = extract_and_filter_zip(old_zip_path)
        new_data = extract_and_filter_zip(new_zip_path)
        
        # Cache active session extraction paths for on-demand diffing
        ACTIVE_EXTRACTION_SESSION["old_dir"] = old_data["extraction_dir"]
        ACTIVE_EXTRACTION_SESSION["new_dir"] = new_data["extraction_dir"]
        
        # Clean raw ZIP files, we only need extracted content now
        os.remove(old_zip_path)
        os.remove(new_zip_path)

        old_files_count = len(old_data["files"])
        new_files_count = len(new_data["files"])

        if old_files_count == 0 and new_files_count == 0:
            raise ValueError("Her iki pakette de XSD/XML (Şema) dosyası bulunamadı. Lütfen Kılavuz (PDF) değil, Şema paketlerini yüklediğinizden emin olun.")
        elif old_files_count == 0:
            raise ValueError(f"Yeni paketten {new_files_count} şema dosyası çıkarıldı ancak Eski Paket'te 0 dosya bulundu! Muhtemelen Eski Paket olarak Kılavuz (PDF) arşivini yüklediniz. Lütfen her iki tarafa da ŞEMA paketlerini yükleyin.")
        elif new_files_count == 0:
            raise ValueError(f"Eski paketten {old_files_count} şema dosyası çıkarıldı ancak Yeni Paket'te 0 dosya bulundu! Muhtemelen Yeni Paket olarak Kılavuz (PDF) arşivini yüklediniz. Lütfen her iki tarafa da ŞEMA paketlerini yükleyin.")
        
        # Run Diff Analysis
        diff_results = run_analysis(old_data, new_data)
        
        # LOGGING FOR DEBUGGING
        with open("debug.log", "w", encoding="utf-8") as f:
            f.write(f"ESKI DOSYALAR: {old_data['files'].keys()}\n")
            f.write(f"YENI DOSYALAR: {new_data['files'].keys()}\n")
            f.write(f"DIFF OVERVIEW:\n")
            for dr in diff_results:
                f.write(f" - {dr['file']} -> {dr['status']} (Fark Sayisi: {len(dr.get('diff', []))})\n")

        # Generate Scenarios based on Diff
        scenario_results = generate_scenarios(diff_results)
        
        # Extract history text (changelog) from the packages
        history_text = find_history_content(new_data["extraction_dir"]) or find_history_content(old_data["extraction_dir"])
        
        response_data = {
            "status": "success",
            "message": "Paketler ayrıştırıldı ve analiz tamamlandı.",
            "data": {
                "old_files_found": len(old_data["files"]),
                "new_files_found": len(new_data["files"]),
                "diff_results": diff_results,
                "scenarios": scenario_results,
                "history": history_text
            }
        }
        
        # Save to Redis Cache (expire in 24 hours)
        redis_cache.set(cache_key, response_data, expire_seconds=86400)
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İşleme sırasında bir hata oluştu: {str(e)}")


@app.get("/api/diff/file")
def get_file_diff_endpoint(file_path: str):
    old_dir = ACTIVE_EXTRACTION_SESSION["old_dir"]
    new_dir = ACTIVE_EXTRACTION_SESSION["new_dir"]
    if not old_dir or not new_dir:
        raise HTTPException(status_code=400, detail="Aktif bir analiz oturumu bulunamadı. Lütfen önce paketleri analiz edin.")
    
    file_path_clean = os.path.basename(file_path)
    
    def find_file_recursively(directory: str, filename: str) -> Optional[str]:
        if not directory or not os.path.exists(directory):
            return None
        for root, _, files in os.walk(directory):
            if filename in files:
                return os.path.abspath(os.path.join(root, filename))
        return None

    old_file = find_file_recursively(old_dir, file_path_clean)
    new_file = find_file_recursively(new_dir, file_path_clean)
    
    # Path security check to prevent directory traversal
    if old_file and not old_file.startswith(os.path.abspath(old_dir)):
        raise HTTPException(status_code=403, detail="Geçersiz dosya yolu erişimi (Eski).")
    if new_file and not new_file.startswith(os.path.abspath(new_dir)):
        raise HTTPException(status_code=403, detail="Geçersiz dosya yolu erişimi (Yeni).")
        
    from core.diff_engine import get_file_text_diff
    diff = get_file_text_diff(old_file, new_file)
    return {"file": file_path_clean, "diff": diff}


from core.rag_engine import ingest_document, ingest_directory, query_rag, query_rag_stream

from fastapi import Form
from fastapi.responses import StreamingResponse
import zipfile

@app.post("/api/rag/ingest")
async def api_rag_ingest(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı okunamadı.")
    filename = file.filename.lower()
    if not (filename.endswith(".pdf") or filename.endswith(".zip")):
        raise HTTPException(status_code=400, detail="Lütfen sadece Kılavuz (PDF) veya Kılavuzları içeren bir ZIP arşivi yükleyiniz.")
        
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content) # type: ignore
        tmp_path = tmp.name
        
    try:
        # Backup the uploaded guide (PDF/ZIP) to S3 standard storage or local fallback
        from core.storage import storage_service
        storage_service.save_file(content, os.path.join("guides", file.filename))
        
        if filename.endswith(".zip"):
            extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            chunk_count = ingest_directory(extract_dir)
            shutil.rmtree(extract_dir, ignore_errors=True)
            
            # Invalidate RAG chat cache
            from core.redis_cache import redis_cache
            redis_cache.clear_prefix("rag:chat:")
            
            return {"status": "success", "message": f"ZIP içindeki PDF'ler başarıyla tarandı ve {chunk_count} parça GİB kuralı veritabanına eğitildi!"}
        else:
            chunk_count = ingest_document(tmp_path)
            
            # Invalidate RAG chat cache
            from core.redis_cache import redis_cache
            redis_cache.clear_prefix("rag:chat:")
            
            return {"status": "success", "message": f"{chunk_count} parça GİB kuralı başarıyla Vektör Veritabanına işlendi!"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/api/rag/chat")
async def api_rag_chat(query: str = Form(...)):
    try:
        from core.redis_cache import redis_cache
        cache_key = f"rag:chat:{query.strip()}"
        cached_res = redis_cache.get(cache_key)
        if cached_res:
            print(f"[RedisCache] RAG Chat cache hit! Returning cached answer.")
            return {"status": "success", "data": cached_res}
            
        res = query_rag(query)
        # Cache RAG answer for 12 hours
        redis_cache.set(cache_key, res, expire_seconds=43200)
        return {"status": "success", "data": res}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/chat/stream")
async def api_rag_chat_stream(query: str = Form(...)):
    try:
        return StreamingResponse(query_rag_stream(query), media_type="text/plain") # type: ignore
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/apikey")
async def api_save_key(key: str = Form(...)):
    import os
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    try:
        # Save to .env file permanently
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f'GEMINI_API_KEY="{key}"\n')
            
        # Apply to running process immediately
        os.environ["GEMINI_API_KEY"] = key
        
        return {"status": "success", "message": "API Key sisteme başarıyla tanımlandı! Uygulamayı yeniden başlatmanıza gerek kalmadan asistanı kullanabilirsiniz."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Key kaydedilirken hata oluştu: {str(e)}")

@app.get("/api/settings/apikey/status")
async def api_get_key_status():
    import os
    has_key = bool(os.environ.get("GEMINI_API_KEY"))
    return {"hasKey": has_key}

@app.get("/api/schematron/list")
async def api_list_schematrons():
    """Returns a list of saved schematron files."""
    try:
        from core.storage import storage_service
        files = storage_service.list_files("schematrons")
        files = [f for f in files if f.endswith('.sch')]
        return {"status": "success", "data": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schematron/upload")
async def api_upload_schematron(file: UploadFile = File(...)):
    """Saves a schematron file to the server/S3 for future use."""
    if not file.filename or not file.filename.endswith('.sch'):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir .sch dosyası yükleyiniz.")
        
    try:
        content = await file.read()
        from core.storage import storage_service
        dest_path = os.path.join(SCHEMATRONS_DIR, file.filename)
        storage_service.save_file(content, dest_path)
        return {"status": "success", "message": f"{file.filename} başarıyla kaydedildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kayıt işlemi başarısız: {str(e)}")

@app.delete("/api/schematron/{filename}")
async def api_delete_schematron(filename: str):
    """Deletes a saved schematron file from local/S3."""
    from core.storage import storage_service
    dest_path = os.path.join(SCHEMATRONS_DIR, filename)
    success = storage_service.delete_file(dest_path)
    if success:
        return {"status": "success", "message": f"{filename} silindi."}
    raise HTTPException(status_code=404, detail="Dosya bulunamadı.")

@app.post("/api/validate/schematron")
async def api_validate_schematron(
    xml_file: UploadFile = File(...),
    sch_file: Optional[UploadFile] = File(None),
    sch_filename: Optional[str] = Form(None)
):
    if not xml_file.filename or not xml_file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Doğrulanacak dosya .xml olmalıdır.")
        
    if not sch_file and not sch_filename:
        raise HTTPException(status_code=400, detail="Lütfen bir .sch (Şematron) dosyası yükleyin veya kayıtlı kurallardan birini seçin.")
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as xml_temp:
        shutil.copyfileobj(xml_file.file, xml_temp)
        xml_path = xml_temp.name
        
    sch_path = None
    is_temp_sch = False
    
    if sch_file and sch_file.filename:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sch") as sch_temp:
            shutil.copyfileobj(sch_file.file, sch_temp)
            sch_path = sch_temp.name
            is_temp_sch = True
    elif sch_filename:
        sch_path = os.path.join(SCHEMATRONS_DIR, sch_filename)
        # S3 sync: download if not present locally
        from core.storage import storage_service
        if not os.path.exists(sch_path):
            s3_content = storage_service.load_file(os.path.join("schematrons", sch_filename))
            if s3_content:
                os.makedirs(SCHEMATRONS_DIR, exist_ok=True)
                with open(sch_path, "wb") as f:
                    f.write(s3_content)
            else:
                os.remove(xml_path)
                raise HTTPException(status_code=404, detail="Seçilen şematron dosyası sunucuda veya S3 depolamasında bulunamadı.")
            
    try:
        results = validate_xml_with_schematron(xml_path, sch_path)
        return {
            "status": "success" if results["is_valid"] else "error",
            "message": "Geçerli" if results["is_valid"] else "Hatalar Bulundu",
            "data": results
        }
    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(xml_path):
            os.remove(xml_path)
        if is_temp_sch and sch_path and os.path.exists(sch_path):
            os.remove(sch_path)

@app.post("/api/sanitize/xml")
async def api_sanitize_xml(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir .xml dosyası yükleyin.")
        
    try:
        content = await file.read()
        with open("debug_uploaded.xml", "wb") as dbg:
            dbg.write(content)
        sanitized_content = sanitize_ubl_xml(content)
        
        # Try rendering to HTML (it may fail if XSLT is not embedded, we don't block XML generation though)
        html_preview = ""
        try:
            html_preview = render_ubl_to_html(sanitized_content)
        except Exception as e:
            html_preview = f"<div style='padding:20px;color:red;font-family:sans-serif;'><h3>Önizleme Oluşturulamadı</h3><p>{str(e)}</p></div>"
            
        # Return base64 XML and HTML via JSON
        xml_b64 = base64.b64encode(sanitized_content).decode("utf-8")
        
        return {
             "status": "success",
             "message": "Fatura kişisel verilerden temizlendi ve başarıyla dışa aktarıldı.",
             "data": {
                 "xml_base64": xml_b64,
                 "html_preview": html_preview,
                 "filename": f"KVKK_Maskeli_{file.filename}"
             }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anonimleştirme işlemi sırasında beklenmedik hata oluştu: {str(e)}")

@app.post("/api/render")
async def api_render_xml(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir .xml dosyası yükleyin.")
        
    try:
        content = await file.read()
        html_preview = render_ubl_to_html(content)
        xml_b64 = base64.b64encode(content).decode("utf-8")
        
        return {
             "status": "success",
             "message": "Fatura görseli başarıyla oluşturuldu.",
             "data": {
                 "xml_base64": xml_b64,
                 "html_preview": html_preview,
                 "filename": file.filename
             }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fatura görselleştirilemedi: {str(e)}")

@app.post("/api/xray")
async def api_xray(xml_base64: str = Form(...), search_text: str = Form(...)):
    try:
        results = find_xpaths_in_ubl(xml_base64, search_text)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reconcile/companies")
def api_get_reconcile_companies(
    server: str = Form(...),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    trusted: bool = Form(True)
):
    from core.db_connector import DBConnector
    connector = DBConnector(server=server, database="master", username=username, password=password, trusted=trusted)
    is_connected = connector.connect()
    
    if not is_connected:
        return ["KOLAY_GÖRKEM", "MİKRO_GÖRKEM", "MİKRO_TEST", "ZED-10185"]
        
    try:
        query = "SELECT name FROM sys.databases"
        records = connector.execute_query(query)
        companies = []
        for r in records:
            name = r.get("name", "")
            if name.endswith("_GENEL") and name.upper() not in ["ZIRVEGENEL", "MİKRO_GENEL"]:
                comp_code = name[:-6]
                companies.append(comp_code)
        return sorted(list(set(companies)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Firmalar listelenirken hata oluştu: {str(e)}")
    finally:
        connector.close()

@app.post("/api/reconcile/years")
def api_get_reconcile_years(
    server: str = Form(...),
    company_code: str = Form(...),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    trusted: bool = Form(True)
):
    import re
    from core.db_connector import DBConnector
    connector = DBConnector(server=server, database="master", username=username, password=password, trusted=trusted)
    is_connected = connector.connect()
    
    if not is_connected:
        return ["2026", "2025"]
        
    try:
        query = "SELECT name FROM sys.databases"
        records = connector.execute_query(query)
        years = []
        pattern = re.compile(rf"^{re.escape(company_code)}_(\d{{4}})T$", re.IGNORECASE)
        for r in records:
            name = r.get("name", "")
            match = pattern.match(name)
            if match:
                years.append(match.group(1))
        return sorted(list(set(years)), reverse=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yıllar listelenirken hata oluştu: {str(e)}")
    finally:
        connector.close()

@app.post("/api/reconcile")
async def api_reconcile_invoice(
    file: UploadFile = File(...),
    server: str = Form(...),
    company_code: str = Form(...),
    year: str = Form(...),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    trusted: bool = Form(True)
):
    if not file.filename or not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir UBL XML dosyası yükleyiniz.")
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
        
    try:
        from core.reconciliation_engine import run_reconciliation
        res = run_reconciliation(
            xml_path=tmp_path,
            server=server,
            company_code=company_code,
            year=year,
            username=username,
            password=password,
            trusted=trusted
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mutabakat testi sırasında hata oluştu: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

