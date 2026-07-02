import os
import time
from dotenv import load_dotenv
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
        _global_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
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
        raise ValueError("Yüklenen ZIP içerisinde hiçbir PDF (Kılavuz) dosyası bulunamadı.")
        
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
            
    return merged[:8]

def query_rag(query_text: str):
    """Queries the Chroma vector database and generates an answer using Gemini."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Lütfen projenin backend dizinindeki .env dosyasına GEMINI_API_KEY bilginizi ekleyin.")
        
    results = get_hybrid_context(query_text)
    
    if len(results) == 0:
        context_text = ""
        sources = []
    else:
        context_text = "\n\n---\n\n".join([doc.page_content for doc in results])
        sources = list(set([os.path.basename(doc.metadata.get("source", "Bilinmeyen Kaynak")) for doc in results]))
        
    prompt_template = f"""
    Sen, test uzmanları için geliştirilmiş "GİB Paket Analizörü" uygulaması içinde çalışan uzman bir e-Dönüşüm asistanısın.
    Aşağıdaki resmi GİB/Kılavuz bağlamını (context) kullanarak kullanıcının sorusuna en doğru ve net cevabı ver. 
    Eğer bağlamda cevaba dair bir kural geçmiyorsa, bunu açıkça belirt ancak bir e-Dönüşüm uzmanı olarak bildiğin teknik bilgileri kullanarak (UBL-TR standartları gibi) yardımcı ol. 
    Mümkün olduğunca teknik, net ve doğrudan test edilebilir bilgiler sağla. Yorum katma, kuralı söyle.

    [GÜNCEL TÜRKİYE MEVZUAT BİLGİLERİ]:
    * Türkiye'deki yasal KDV oranları Temmuz 2023 tarihinde güncellenmiştir.
    * Güncel KDV oranları: %0 (İstisna/Muafiyet), %1, %10 (Eski %8 olanlar %10 yapıldı) ve %20 (Eski %18 olanlar %20 yapıldı) şeklindedir.
    * Eski GİB teknik kılavuzlarında veya XML örneklerinde eski tarihli olmalarından ötürü %8 veya %18 oranları geçebilir. Ancak faturada kullanılabilecek güncel KDV oranlarının %0, %1, %10 ve %20 olduğunu mutlaka vurgulayarak cevap ver.

    [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ BİLGİLERİ]:
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
    if not os.environ.get("GEMINI_API_KEY"):
        yield "Lütfen projenin backend dizinindeki .env dosyasına GEMINI_API_KEY bilginizi ekleyin."
        return
        
    results = get_hybrid_context(query_text)
    
    if len(results) == 0:
        context_text = ""
    else:
        context_text = "\n\n---\n\n".join([doc.page_content for doc in results])
        
    prompt_template = f"""
    Sen, test uzmanları için geliştirilmiş "GİB Paket Analizörü" uygulaması içinde çalışan uzman bir e-Dönüşüm asistanısın.
    Aşağıdaki resmi GİB/Kılavuz bağlamını (context) kullanarak kullanıcının sorusuna en doğru ve net cevabı ver. 
    Eğer bağlamda cevaba dair bir kural geçmiyorsa, bunu açıkça belirt ancak bir e-Dönüşüm uzmanı olarak bildiğin teknik bilgileri kullanarak (UBL-TR standartları gibi) yardımcı ol. 
    Mümkün olduğunca teknik, net ve doğrudan test edilebilir bilgiler sağla. Yorum katma, kuralı söyle.

    [GÜNCEL TÜRKİYE MEVZUAT BİLGİLERİ]:
    * Türkiye'deki yasal KDV oranları Temmuz 2023 tarihinde güncellenmiştir.
    * Güncel KDV oranları: %0 (İstisna/Muafiyet), %1, %10 (Eski %8 olanlar %10 yapıldı) ve %20 (Eski %18 olanlar %20 yapıldı) şeklindedir.
    * Eski GİB teknik kılavuzlarında veya XML örneklerinde eski tarihli olmalarından ötürü %8 veya %18 oranları geçebilir. Ancak faturada kullanılabilecek güncel KDV oranlarının %0, %1, %10 ve %20 olduğunu mutlaka vurgulayarak cevap ver.

    [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ BİLGİLERİ]:
    {context_text}

    Kullanıcının Sorusu: {query_text}
    """

    
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
    
    async for chunk in model.astream(prompt_template):
        if chunk.content:
            yield chunk.content

