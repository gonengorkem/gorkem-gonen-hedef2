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
import base64
from typing import Optional

app = FastAPI(title="GİB Hedef Analizörü API")

# Ensure schematrons directory exists
SCHEMATRONS_DIR = os.path.join(os.path.dirname(__file__), "schematrons")
os.makedirs(SCHEMATRONS_DIR, exist_ok=True)


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

@app.post("/api/analyze")
async def analyze_packages(
    old_package: UploadFile = File(...),
    new_package: UploadFile = File(...)
):
    if not old_package.filename or not new_package.filename or not old_package.filename.endswith('.zip') or not new_package.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Değerlendirme için .zip dosyaları gereklidir.")
    
    # Save uploaded files temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as old_temp:
        shutil.copyfileobj(old_package.file, old_temp)
        old_zip_path = old_temp.name
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as new_temp:
        shutil.copyfileobj(new_package.file, new_temp)
        new_zip_path = new_temp.name
        
    try:
        # Extract and filter target files
        old_data = extract_and_filter_zip(old_zip_path)
        new_data = extract_and_filter_zip(new_zip_path)
        
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
        
        return {
            "status": "success",
            "message": "Paketler ayrıştırıldı ve analiz tamamlandı.",
            "data": {
                "old_files_found": len(old_data["files"]),
                "new_files_found": len(new_data["files"]),
                "diff_results": diff_results,
                "scenarios": scenario_results
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İşleme sırasında bir hata oluştu: {str(e)}")

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
        if filename.endswith(".zip"):
            extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            chunk_count = ingest_directory(extract_dir)
            shutil.rmtree(extract_dir, ignore_errors=True)
            return {"status": "success", "message": f"ZIP içindeki PDF'ler başarıyla tarandı ve {chunk_count} parça GİB kuralı veritabanına eğitildi!"}
        else:
            chunk_count = ingest_document(tmp_path)
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
        res = query_rag(query)
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
        files = [f for f in os.listdir(SCHEMATRONS_DIR) if f.endswith('.sch')]
        return {"status": "success", "data": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schematron/upload")
async def api_upload_schematron(file: UploadFile = File(...)):
    """Saves a schematron file to the server for future use."""
    if not file.filename or not file.filename.endswith('.sch'):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir .sch dosyası yükleyiniz.")
        
    file_path = os.path.join(SCHEMATRONS_DIR, file.filename)
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return {"status": "success", "message": f"{file.filename} başarıyla kaydedildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kayıt işlemi başarısız: {str(e)}")

@app.delete("/api/schematron/{filename}")
async def api_delete_schematron(filename: str):
    """Deletes a saved schematron file."""
    file_path = os.path.join(SCHEMATRONS_DIR, filename)
    if os.path.exists(file_path) and file_path.startswith(SCHEMATRONS_DIR):
        os.remove(file_path)
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
        if not os.path.exists(sch_path):
            os.remove(xml_path)
            raise HTTPException(status_code=404, detail="Seçilen şematron dosyası sunucuda bulunamadı.")
            
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
