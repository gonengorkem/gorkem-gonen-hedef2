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

# Optional SSL Certificate Verification Bypass for Corporate Interception Proxies (Zscaler / Fortinet / Corporate CA)
DISABLE_SSL_VERIFY = os.environ.get("DISABLE_SSL_VERIFY", "false").lower() in ("true", "1")

if DISABLE_SSL_VERIFY:
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
    meta_info = extract_metadata_from_path(file_path)
    for p in pages:
        p.metadata.update(meta_info)
        
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
            meta_info = extract_metadata_from_path(pdf)
            for p in pages:
                p.metadata.update(meta_info)
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


def extract_metadata_from_path(file_path: str) -> dict:
    """Extracts semantic document metadata like version, type, and title from filename."""
    filename = os.path.basename(file_path)
    score = extract_document_version_score(filename)
    ver_str = f"v{score[0]}.{score[1]}" if score[0] > 0 else ""
    
    doc_type = "GİB Teknik Kılavuzu"
    fn_lower = filename.lower()
    if "gider" in fn_lower or "pusula" in fn_lower:
        doc_type = "e-Gider Pusulası Kılavuzu"
    elif "arsiv" in fn_lower or "arşiv" in fn_lower:
        doc_type = "e-Arşiv Fatura Kılavuzu"
    elif "fatura" in fn_lower:
        doc_type = "e-Fatura Kılavuzu"
    elif "irsaliye" in fn_lower:
        doc_type = "e-İrsaliye Kılavuzu"
    elif "bilet" in fn_lower:
        doc_type = "e-Bilet Kılavuzu"
    elif "mustahsil" in fn_lower:
        doc_type = "e-Müstahsil Makbuzu Kılavuzu"
        
    return {
        "source": filename,
        "doc_title": os.path.splitext(filename)[0],
        "doc_version": ver_str,
        "doc_type": doc_type,
        "doc_year": score[3] if score[3] > 0 else 2026
    }

def query_rag(query_text: str):
    """Queries the Chroma vector database and generates a high-trust grounded answer using Gemini."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Lütfen projenin backend dizinindeki .env dosyasına GEMINI_API_KEY bilginizi ekleyin.")
        
    results = get_hybrid_context(query_text)
    
    if len(results) == 0:
        context_text = ""
        sources = []
        structured_sources = []
    else:
        context_parts = []
        structured_sources = []
        seen_src = set()
        for doc in results:
            src_name = os.path.basename(doc.metadata.get("source", "Bilinmeyen Kaynak"))
            page_num = doc.metadata.get("page", 0) + 1
            doc_type = doc.metadata.get("doc_type", "GİB Kılavuzu")
            part_content = f"[Kaynak: {src_name} ({doc_type}), Sayfa: {page_num}]\n{doc.page_content}"
            context_parts.append(part_content)
            
            src_key = f"{src_name}_{page_num}"
            if src_key not in seen_src:
                seen_src.add(src_key)
                structured_sources.append({
                    "title": src_name,
                    "page": page_num,
                    "type": doc_type,
                    "snippet": doc.page_content[:180].strip()
                })
                
        context_text = "\n\n---\n\n".join(context_parts)
        sources = list(set([os.path.basename(doc.metadata.get("source", "Bilinmeyen Kaynak")) for doc in results]))
        
    prompt_template = f"""
    Sen, Gelir İdaresi Başkanlığı (GİB) e-Dönüşüm standartları, UBL-TR XML şemaları ve entegrasyon kuralları konusunda uzmanlaşmış **Kıdemli Mevzuat ve Sistem Analistisin**.

    GÖREVİN:
    Yazılım geliştiricilerin ve iş analistlerinin yüzlerce sayfalık GİB teknik kılavuzlarını okumasına gerek kalmadan; e-Gider Pusulası, e-Arşiv Fatura, e-Fatura, XML şema değişiklikleri ve entegrasyon kurallarına dair sorularını **en yüksek doğruluk ve güvenilirlikle** yanıtlamaktır.

    TEMEL İLKELER & GÜVENİLİRLİK KURALLARI:
    1. **Kesin Doğruluk (Ground Truth):** Yanıtını öncelikle aşağıdaki [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ BİLGİLERİ] içeriğindeki resmi metinlere dayandır. Bilgileri verirken ilgili kılavuz adına ve sayfa/madde numarasına açıkça atıfta bulun.
    2. **Şeffaf Ayrım (Halüsinasyon Yasağı):** Sorulan kural veya detay sağlanan kılavuz parçalarında yer almıyorsa, kesinlikle uydurma kural veya tahmin üretme. *"Bu detay sistemde yüklü olan kılavuz sayfalarında açıkça yer almamaktadır; genel UBL 2.1 standardına göre..."* şeklinde şeffaf bir ayrım belirt.
    3. **Yapılandırılmış Format:** Analistlerin hızla test senaryosu ve iş kuralı çıkarabilmesi için cevabını net başlıklar, maddeler ve teknik XML/XPath örnekleri ile sun.

    [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ VE ŞEMA BİLGİLERİ]:
    {context_text}

    Kullanıcının Sorusu: {query_text}
    """
    
    # Gemini 2.5 Flash modelini kullanarak cevap üret
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
    response = model.invoke(prompt_template)
    
    return {
        "answer": response.content,
        "sources": sources,
        "structured_sources": structured_sources
    }



async def query_rag_stream(query_text: str):
    """Queries the Chroma vector database and generates a streaming answer using Gemini with footnotes."""
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
        
    citations = []
    if len(results) == 0:
        context_text = ""
    else:
        context_parts = []
        seen = set()
        for doc in results:
            src_name = os.path.basename(doc.metadata.get("source", "Bilinmeyen Kaynak"))
            page_num = doc.metadata.get("page", 0) + 1
            doc_type = doc.metadata.get("doc_type", "GİB Kılavuzu")
            part_content = f"[Kaynak: {src_name} ({doc_type}), Sayfa: {page_num}]\n{doc.page_content}"
            context_parts.append(part_content)
            
            key = f"{src_name}_{page_num}"
            if key not in seen and len(citations) < 4:
                seen.add(key)
                citations.append(f"📄 **{src_name}** — Sayfa {page_num}")
                
        context_text = "\n\n---\n\n".join(context_parts)
        
    prompt_template = f"""
    Sen, Gelir İdaresi Başkanlığı (GİB) e-Dönüşüm standartları, UBL-TR XML şemaları ve entegrasyon kuralları konusunda uzmanlaşmış **Kıdemli Mevzuat ve Sistem Analistisin**.

    GÖREVİN:
    Yazılım geliştiricilerin ve iş analistlerinin yüzlerce sayfalık GİB teknik kılavuzlarını okumasına gerek kalmadan; e-Gider Pusulası, e-Arşiv Fatura, e-Fatura, XML şema değişiklikleri ve entegrasyon kurallarına dair sorularını **en yüksek doğruluk ve güvenilirlikle** yanıtlamaktır.

    TEMEL İLKELER & GÜVENİLİRLİK KURALLARI:
    1. **Kesin Doğruluk (Ground Truth):** Yanıtını öncelikle aşağıdaki [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ BİLGİLERİ] içeriğindeki resmi metinlere dayandır.
    2. **Şeffaf Ayrım (Halüsinasyon Yasağı):** Sorulan kural veya detay sağlanan kılavuz parçalarında yer almıyorsa, kesinlikle uydurma kural veya tahmin üretme. *"Bu detay sistemde yüklü olan kılavuz sayfalarında açıkça yer almamaktadır..."* şeklinde şeffaf bir ayrım belirt.
    3. **Yapılandırılmış Format:** Analistlerin hızla test senaryosu ve iş kuralı çıkarabilmesi için cevabını net başlıklar, maddeler ve teknik XML/XPath örnekleri ile sun.

    [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ VE ŞEMA BİLGİLERİ]:
    {context_text}

    Kullanıcının Sorusu: {query_text}
    """

    try:
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key=api_key)
        async for chunk in model.astream(prompt_template):
            if chunk.content:
                yield chunk.content
                
        # Akış sonunda doğrulanabilir kaynak dipnotları ekle
        if citations:
            yield "\n\n---\n**📚 Referans Kılavuz Sayfaları:**\n" + "\n".join([f"* {c}" for c in citations])
    except Exception as e:
        safe_print(f"[RAGStreamError] Exception during stream generation: {e}")
        import traceback
        traceback.print_exc()
        yield f"\n\n⚠️ Yanıt üretilirken bir hata oluştu: {str(e)}"


def explain_diff_with_rag(element_name: str, diff_type: str = "added", file_name: str = "") -> dict:
    """
    Takes a schema diff element (e.g. 'eGiderPusulasiType' or 'operatorUygulamaBilgi'),
    searches the ingested PDF guides for its legislative rationale and usage scenario,
    and returns a concise 2-3 sentence explanation with citations.
    """
    if not os.environ.get("GEMINI_API_KEY"):
        return {
            "explanation": "Kılavuz açıklaması için Gemini API anahtarı tanımlanmalıdır.",
            "citations": []
        }
        
    query = f"{element_name} {file_name} ne işe yarar hangi senaryoda kullanılır kılavuz açıklaması zorunluluk"
    try:
        results = get_hybrid_context(query)
    except Exception:
        results = []
        
    if not results:
        return {
            "explanation": f"'{element_name}' elemanı için sistemde kayıtlı kılavuzlarda doğrudan bir açıklama paragrafı bulunamadı.",
            "citations": []
        }
        
    context_parts = []
    citations = []
    seen = set()
    for doc in results[:6]:
        src_name = os.path.basename(doc.metadata.get("source", "Kılavuz"))
        page_num = doc.metadata.get("page", 0) + 1
        key = f"{src_name}_{page_num}"
        if key not in seen and len(citations) < 3:
            seen.add(key)
            citations.append({"title": src_name, "page": page_num})
        context_parts.append(f"[{src_name} - Sayfa {page_num}]:\n{doc.page_content}")
        
    context_text = "\n\n".join(context_parts)
    prompt = f"""
    Sen bir Kıdemli e-Dönüşüm Sistem Analistisin.
    GİB teknik kılavuzlarından alınan aşağıdaki metinlere dayanarak, XML şemasında tespit edilen '{element_name}' ({diff_type}) elemanının:
    1. Mevzuattaki amacını (Neden eklendi/kullanılıyor?),
    2. Hangi iş senaryosunda (Örn: İade, Kargo bilgisi, SMS/Operatör doğrulama vb.) zorunlu veya seçimli olduğunu
    en fazla 2-3 vurucu ve net cümle ile özetle.
    
    [KILAVUZ METİNLERİ]:
    {context_text}
    """
    try:
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
        resp = model.invoke(prompt)
        return {
            "explanation": resp.content.strip(),
            "citations": citations
        }
    except Exception as e:
        return {
            "explanation": f"Açıklama üretilemedi: {str(e)}",
            "citations": citations
        }


