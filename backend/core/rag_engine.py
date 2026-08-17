import os
import ssl
import sys
import time
from dotenv import load_dotenv

# Explicitly load backend/.env
env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if not os.path.exists(env_file):
    env_file = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_file)

# SSL certificate verification bypass for corporate proxies / Zscaler
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
ssl._create_default_https_context = ssl._create_unverified_context

def _unverified_default_context(*args, **kwargs):
    ctx = ssl._create_unverified_context(*args, **kwargs)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

ssl.create_default_context = _unverified_default_context

try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

try:
    import httpx
    _orig_httpx_init = httpx.Client.__init__
    def _patched_httpx_init(self, *args, **kwargs):
        kwargs['verify'] = False
        _orig_httpx_init(self, *args, **kwargs)
    httpx.Client.__init__ = _patched_httpx_init

    _orig_httpx_async_init = httpx.AsyncClient.__init__
    def _patched_httpx_async_init(self, *args, **kwargs):
        kwargs['verify'] = False
        _orig_httpx_async_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = _patched_httpx_async_init
except Exception:
    pass

try:
    import aiohttp
    _orig_tcp_init = aiohttp.TCPConnector.__init__
    def _patched_tcp_init(self, *args, **kwargs):
        kwargs['ssl'] = False
        _orig_tcp_init(self, *args, **kwargs)
        self._ssl = False
    aiohttp.TCPConnector.__init__ = _patched_tcp_init
except Exception:
    pass

from langchain_docling import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
import chromadb

load_dotenv()

def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            import sys
            encoding = sys.stdout.encoding or 'utf-8'
            print(msg.encode(encoding, errors='replace').decode(encoding))
        except Exception:
            try:
                print(msg.encode('ascii', errors='replace').decode('ascii'))
            except Exception:
                pass

CHROMA_PATH = "chroma_db_local"

_global_embeddings = None

def get_embeddings():
    global _global_embeddings
    if _global_embeddings is None:
        try:
            _global_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except Exception as e:
            safe_print(f"[RAGEngine] HuggingFace embeddings failed: {e}. Trying GoogleGenerativeAIEmbeddings fallback.")
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                _global_embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
            else:
                raise e
    return _global_embeddings

_global_db = None

def get_db():
    global _global_db
    if _global_db is None:
        chroma_host = os.getenv("CHROMA_SERVER_HOST")
        chroma_port = os.getenv("CHROMA_SERVER_PORT")
        
        if chroma_host:
            port_val = int(chroma_port) if chroma_port else 8000
            safe_print(f"[RAGEngine] Connecting to remote ChromaDB server at {chroma_host}:{port_val}...")
            import chromadb
            client = chromadb.HttpClient(host=chroma_host, port=port_val)
            _global_db = Chroma(
                client=client,
                collection_name="gib_docs",
                embedding_function=get_embeddings()
            )
        else:
            safe_print(f"[RAGEngine] Using local persistent ChromaDB at {CHROMA_PATH}...")
            _global_db = Chroma(
                persist_directory=CHROMA_PATH,
                embedding_function=get_embeddings(),
                collection_name="gib_docs"
            )
    return _global_db

def warmup_rag_engine():
    """Pre-loads HuggingFace embeddings model and ChromaDB client on server startup."""
    try:
        safe_print("[RAGEngine] Warming up HuggingFace embeddings & ChromaDB...")
        get_embeddings()
        get_db()
        safe_print("[RAGEngine] Warmup complete! Vector DB is ready for instant queries.")
    except Exception as e:
        safe_print(f"[RAGEngine] Warmup warning: {e}")


def ingest_document(file_path: str):
    """Loads a PDF document and adds it to the Chroma vector database."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Lütfen projenin backend dizinindeki .env dosyasına GEMINI_API_KEY bilginizi ekleyin.")
        
    from langchain_community.document_loaders import PyPDFLoader
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    
    # Bölütleme (Chunking) ayarları: Belgeleri LLM'in anlayacağı kısalıkta dilimlere ayırır.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        length_function=len
    )
    chunks = text_splitter.split_documents(pages)
    chunks = filter_complex_metadata(chunks)
    
    # Standalone Chroma yerine Local Persistent DB Kullan
    db = get_db()
    
    # Ücretsiz Gemini API limitleri (Dakikada 100 İstek) için chunk'ları yavaş yavaş gönder
    batch_size = 80
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        try:
            db.add_documents(batch)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                safe_print(f"API Limitine ulaşıldı. 60 saniye bekleniyor... ({i}/{len(chunks)})")
                time.sleep(60)
                db.add_documents(batch)
            else:
                raise e
                
        if i + batch_size < len(chunks):
            pass # Sleep removed
            
    
    return len(chunks)

import glob

def ingest_directory(dir_path: str):
    """Loads all PDF documents in a directory and adds them to the Chroma vector database."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Lütfen projenin backend dizinindeki .env dosyasına GEMINI_API_KEY bilginizi ekleyin.")
        
    pdf_files = glob.glob(os.path.join(dir_path, "**", "*.pdf"), recursive=True)
    if not pdf_files:
        raise ValueError("Yüklenen arşiv içerisinde hiçbir PDF (Kılavuz) dosyası bulunamadı.")
        
    all_chunks = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        length_function=len
    )
    
    from langchain_community.document_loaders import PyPDFLoader

    for pdf in pdf_files:
        try:
            safe_print(f"PyPDF ile okunuyor: {pdf}")
            loader = PyPDFLoader(pdf)
            pages = loader.load()
            chunks = text_splitter.split_documents(pages)
            all_chunks.extend(chunks)
        except Exception as e:
            safe_print(f"Hata oluşan PDF dosyası atlanıyor: {pdf} - Error: {str(e)}")
            
    if not all_chunks:
         raise ValueError("PDF dosyaları okunurken içeriği sıfır veya hata oluştu.")
         
    all_chunks = filter_complex_metadata(all_chunks)
         
    # Chroma Persistent Sunucusuna Bağlan
    db = get_db()
    
    batch_size = 80
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        try:
            db.add_documents(batch)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                safe_print(f"API Limitine ulaşıldı. 60 saniye bekleniyor... ({i}/{len(all_chunks)})")
                time.sleep(60)
                db.add_documents(batch)
            else:
                raise e
                
        if i + batch_size < len(all_chunks):
            pass # Sleep removed
            
    
    return len(all_chunks)

def normalize_turkish(text: str) -> str:
    replacements = {
        'ı': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c',
        'ı': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c',
        'I': 'i', 'Ş': 's', 'Ğ': 'g', 'Ü': 'u', 'Ö': 'o', 'Ç': 'c'
    }
    text = text.lower()
    for tr, eng in replacements.items():
        text = text.replace(tr, eng)
    return text

def keyword_search(docs, query_text: str, k: int = 5):
    query_norm = normalize_turkish(query_text)
    stopwords = {"ve", "veya", "ile", "bir", "bu", "da", "de", "icin", "mu", "mudur", "dur", "en", "ise", "altinda"}
    query_words = [w for w in query_norm.replace("-", " ").split() if w not in stopwords and len(w) > 1]
    
    if not query_words:
        return []
        
    scored_docs = []
    for doc in docs:
        content_norm = normalize_turkish(doc.page_content)
        score = 0
        for word in query_words:
            count = content_norm.count(word)
            if count > 0:
                boundary_count = content_norm.count(f" {word} ") + content_norm.count(f"\n{word} ") + content_norm.count(f" {word}\n")
                score += (count * 1.0) + (boundary_count * 2.0)
        if score > 0:
            scored_docs.append((doc, score))
            
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, score in scored_docs[:k]]

def extract_document_version_score(doc) -> tuple:
    """
    Kılavuz dosya adındaki versiyon veya tarih bilgisini çıkararak sıralama anahtarı oluşturur.
    En yüksek versiyon/tarih en üstte yer alır.
    """
    import re
    source = doc.metadata.get("source", "")
    filename = os.path.basename(source).lower()
    
    # 1. v1.18, v.1.18, v1_18, versiyon_1.18 gibi versiyon şablonlarını ara
    version_match = re.search(r'(?:v|version|versiyon|v\.)\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?', filename)
    if version_match:
        major = int(version_match.group(1) or 0)
        minor = int(version_match.group(2) or 0)
        patch = int(version_match.group(3) or 0)
    else:
        # Genel ondalık sayıları ara (örn: kilavuz_1.5.pdf)
        float_match = re.search(r'(\d+)\.(\d+)', filename)
        if float_match:
            major = int(float_match.group(1))
            minor = int(float_match.group(2))
            patch = 0
        else:
            major, minor, patch = 0, 0, 0
            
    # 2. Yıl bilgisini ara (20xx veya 19xx)
    year_match = re.search(r'\b(20\d{2}|19\d{2})\b', filename)
    year = int(year_match.group(1)) if year_match else 0
    
    return (major, minor, patch, year)

def get_hybrid_context(query_text: str):
    from langchain_core.documents import Document
    db = get_db()
    
    # 1. Vektör Benzerlik Araması
    try:
        vector_results = db.similarity_search(query_text, k=5)
    except Exception as e:
        safe_print(f"Vector search failed: {e}")
        vector_results = []
        
    # 2. Anahtar Kelime Araması (Keyword Search)
    try:
        all_data = db._collection.get()
        documents = []
        for idx, doc in enumerate(all_data['documents']):
            metadata = all_data['metadatas'][idx]
            documents.append(Document(page_content=doc, metadata=metadata))
        keyword_results = keyword_search(documents, query_text, k=5)
    except Exception as e:
        safe_print(f"Keyword search failed: {e}")
        keyword_results = []
        
    # 3. İki arama sonucunu birleştirme ve mükerrerleri silme
    seen = set()
    merged = []
    
    # Sırayla bir anahtar kelime sonucu, bir vektör sonucu ekleyelim (özellikle anahtar kelimeleri öne çıkarır)
    for kw_doc, vec_doc in zip(keyword_results, vector_results + [None] * len(keyword_results)):
        if kw_doc:
            snippet = kw_doc.page_content[:150]
            if snippet not in seen:
                seen.add(snippet)
                merged.append(kw_doc)
        if vec_doc:
            snippet = vec_doc.page_content[:150]
            if snippet not in seen:
                seen.add(snippet)
                merged.append(vec_doc)
                
    # Kalanları ekle
    for doc in keyword_results + vector_results:
        if doc:
            snippet = doc.page_content[:150]
            if snippet not in seen:
                seen.add(snippet)
                merged.append(doc)
            
    # En güncel kılavuzları en üstte olacak şekilde kararlı sıralama (stable sort) uygula
    merged.sort(key=extract_document_version_score, reverse=True)
    return merged[:15]


def query_rag(query_text: str):
    """Queries the Chroma vector database and generates an answer using Gemini."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Lütfen projenin backend dizinindeki .env dosyasına GEMINI_API_KEY bilginizi ekleyin.")
        
    results = get_hybrid_context(query_text)
    
    if len(results) == 0:
        context_text = ""
        sources = []
    else:
        context_parts = []
        for doc in results:
            src_name = os.path.basename(doc.metadata.get("source", "Bilinmeyen Kaynak"))
            page_num = doc.metadata.get("page", 0) + 1
            part_content = f"[Kaynak: {src_name}, Sayfa: {page_num}]\n{doc.page_content}"
            context_parts.append(part_content)
        context_text = "\n\n---\n\n".join(context_parts)
        sources = list(set([os.path.basename(doc.metadata.get("source", "Bilinmeyen Kaynak")) for doc in results]))
        
    prompt_template = f"""
    Sen, GİB (Gelir İdaresi Başkanlığı) e-Dönüşüm standartları, UBL-TR XML şemaları ve teknik kılavuzlar konusunda uzmanlaşmış **Kıdemli e-Dönüşüm Yazılım ve Entegrasyon Analistisin**.

    GÖREVİN:
    Kullanıcının e-Gider Pusulası, e-Fatura, e-Arşiv Fatura, paket değişiklikleri veya entegrasyon kurallarına dair sorularını zengin, detaylı, profesyonelce kategorize edilmiş ve teknik maddeler içeren kapsamlı bir analiz raporu şeklinde yanıtlamaktır.

    ÖNEMLİ TALİMATLAR:
    1. Kullanıcı paket analizini veya eski belgelere göre nelerin değiştiğini sorduğunda; hem veritabanından çekilen kılavuz metinlerini hem de bir e-Dönüşüm uzmanı olarak bildiğin teknik standartları (UBL 2.1 CreditNote, `ProfileID = GIDERPUSULASI`, `CreditNoteTypeCode` (`SATIS` / `IADE`), `eArsiv.xsd` şemasına eklenen `eGiderPusulasiType` ve `eGiderPusulasiIptal` elemanları, İade senaryoları (`EARSIV_FATURA`, `BELGESIZ`, `SATIS_FISI`), SMS/Operatör doğrulama `operatorUygulamaBilgi`, Kargo bilgileri `kargoBilgi` ve `giderPusulasi.xslt` görsel tasarımı) birleştirerek tam teşekküllü bir analist raporu hazırla.
    2. Kesinlikle "bağlamda bilgi bulunmamaktadır" veya çekimser/kısa yanıtlar verme. Bilgileri kategorize ederek (Belge Yapısı, Şema Değişiklikleri, İade Senaryoları, Raporlama vb.) açıkla.
    3. Markdown başlıkları, tablolar ve emojiler kullanarak okumayı kolaylaştır.

    [GÜNCEL TÜRKİYE MEVZUAT BİLGİLERİ]:
    * Türkiye'deki yasal KDV oranları Temmuz 2023 tarihinde güncellenmiştir.
    * Güncel KDV oranları: %0 (İstisna/Muafiyet), %1, %10 (Eski %8 olanlar %10 yapıldı) ve %20 (Eski %18 olanlar %20 yapıldı) şeklindedir.

    [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ VE ŞEMA BİLGİLERİ]:
    {context_text}

    Kullanıcının Sorusu: {query_text}
    """
    
    # Gemini 2.5 Flash modelini kullanarak cevap üret
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
    response = model.invoke(prompt_template)
    
    return {
        "answer": response.content,
        "sources": sources
    }



async def query_rag_stream(query_text: str):
    """Queries the Chroma vector database and generates a streaming answer using Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        yield "⚠️ Asistanı kullanabilmek için lütfen API Key alanından Gemini API Key bilginizi tanımlayınız."
        return
        
    try:
        import asyncio
        results = await asyncio.to_thread(get_hybrid_context, query_text)
        results = results or []
    except Exception as e:
        safe_print(f"[RAGStream] Hybrid search error: {e}")
        results = []
        
    if len(results) == 0:
        context_text = ""
    else:
        context_parts = []
        for doc in results:
            src_name = os.path.basename(doc.metadata.get("source", "Bilinmeyen Kaynak"))
            page_num = doc.metadata.get("page", 0) + 1
            part_content = f"[Kaynak: {src_name}, Sayfa: {page_num}]\n{doc.page_content}"
            context_parts.append(part_content)
        context_text = "\n\n---\n\n".join(context_parts)
        
    prompt_template = f"""
    Sen, GİB (Gelir İdaresi Başkanlığı) e-Dönüşüm standartları, UBL-TR XML şemaları ve teknik kılavuzlar konusunda uzmanlaşmış **Kıdemli e-Dönüşüm Yazılım ve Entegrasyon Analistisin**.

    GÖREVİN:
    Kullanıcının e-Gider Pusulası, e-Fatura, e-Arşiv Fatura, paket değişiklikleri veya entegrasyon kurallarına dair sorularını zengin, detaylı, profesyonelce kategorize edilmiş ve teknik maddeler içeren kapsamlı bir analiz raporu şeklinde yanıtlamaktır.

    ÖNEMLİ TALİMATLAR:
    1. Kullanıcı paket analizini veya eski belgelere göre nelerin değiştiğini sorduğunda; hem veritabanından çekilen kılavuz metinlerini hem de bir e-Dönüşüm uzmanı olarak bildiğin teknik standartları (UBL 2.1 CreditNote, `ProfileID = GIDERPUSULASI`, `CreditNoteTypeCode` (`SATIS` / `IADE`), `eArsiv.xsd` şemasına eklenen `eGiderPusulasiType` ve `eGiderPusulasiIptal` elemanları, İade senaryoları (`EARSIV_FATURA`, `BELGESIZ`, `SATIS_FISI`), SMS/Operatör doğrulama `operatorUygulamaBilgi`, Kargo bilgileri `kargoBilgi` ve `giderPusulasi.xslt` görsel tasarımı) birleştirerek tam teşekküllü bir analist raporu hazırla.
    2. Kesinlikle "bağlamda bilgi bulunmamaktadır" veya çekimser/kısa yanıtlar verme. Bilgileri kategorize ederek (Belge Yapısı, Şema Değişiklikleri, İade Senaryoları, Raporlama vb.) açıkla.
    3. Markdown başlıkları, tablolar ve emojiler kullanarak okumayı kolaylaştır.

    [GÜNCEL TÜRKİYE MEVZUAT BİLGİLERİ]:
    * Türkiye'deki yasal KDV oranları Temmuz 2023 tarihinde güncellenmiştir.
    * Güncel KDV oranları: %0 (İstisna/Muafiyet), %1, %10 (Eski %8 olanlar %10 yapıldı) ve %20 (Eski %18 olanlar %20 yapıldı) şeklindedir.

    [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ VE ŞEMA BİLGİLERİ]:
    {context_text}

    Kullanıcının Sorusu: {query_text}
    """

    try:
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key=api_key)
        async for chunk in model.astream(prompt_template):
            if chunk.content:
                yield chunk.content
    except Exception as e:
        safe_print(f"[RAGStreamError] Exception during stream generation: {e}")
        import traceback
        traceback.print_exc()
        yield f"\n\n⚠️ Yanıt üretilirken bir hata oluştu: {str(e)}"


