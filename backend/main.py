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

app = FastAPI(title="GİB Hedef Analizörü API")

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
    if not old_package.filename.endswith('.zip') or not new_package.filename.endswith('.zip'):
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

from core.rag_engine import ingest_document, ingest_directory, query_rag
from fastapi import Form
import zipfile

@app.post("/api/rag/ingest")
async def api_rag_ingest(file: UploadFile = File(...)):
    filename = file.filename.lower()
    if not (filename.endswith(".pdf") or filename.endswith(".zip")):
        raise HTTPException(status_code=400, detail="Lütfen sadece Kılavuz (PDF) veya Kılavuzları içeren bir ZIP arşivi yükleyiniz.")
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
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

@app.post("/api/validate/schematron")
async def api_validate_schematron(
    xml_file: UploadFile = File(...),
    sch_file: UploadFile = File(...)
):
    if not xml_file.filename.endswith('.xml') or not sch_file.filename.endswith('.sch'):
        raise HTTPException(status_code=400, detail="Bir .xml ve bir .sch uzantılı dosya yüklenmelidir.")
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as xml_temp:
        shutil.copyfileobj(xml_file.file, xml_temp)
        xml_path = xml_temp.name
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sch") as sch_temp:
        shutil.copyfileobj(sch_file.file, sch_temp)
        sch_path = sch_temp.name
        
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
        if os.path.exists(sch_path):
            os.remove(sch_path)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
