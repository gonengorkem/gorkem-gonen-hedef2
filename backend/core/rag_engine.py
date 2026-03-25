import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma

load_dotenv()

CHROMA_PATH = "chroma_db"

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

def ingest_document(file_path: str):
    """Loads a PDF document and adds it to the Chroma vector database."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Lütfen projenin backend dizinindeki .env dosyasına GEMINI_API_KEY bilginizi ekleyin.")
        
    loader = PyPDFLoader(file_path)
    pages = loader.load_and_split()
    
    # Bölütleme (Chunking) ayarları: Belgeleri LLM'in anlayacağı kısalıkta dilimlere ayırır.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        length_function=len
    )
    chunks = text_splitter.split_documents(pages)
    
    # Kurallara göre Chroma Vektör Veritabanını oluştur veya yükle
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embeddings())
    
    # Ücretsiz Gemini API limitleri (Dakikada 100 İstek) için chunk'ları yavaş yavaş gönder
    batch_size = 80
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        try:
            db.add_documents(batch)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"API Limitine ulaşıldı. 60 saniye bekleniyor... ({i}/{len(chunks)})")
                time.sleep(60)
                db.add_documents(batch)
            else:
                raise e
                
        if i + batch_size < len(chunks):
            time.sleep(60) # Her 80 chunk grubundan sonra API'nin sıfırlanması için 1 dk bekle
            
    
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
    
    for pdf in pdf_files:
        try:
            loader = PyPDFLoader(pdf)
            pages = loader.load_and_split()
            chunks = text_splitter.split_documents(pages)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"Hata oluşan PDF dosyası atlanıyor: {pdf} - Error: {str(e)}")
            
    if not all_chunks:
         raise ValueError("PDF dosyaları okunurken içeriği sıfır veya hata oluştu.")
         
    # Chroma Vektör Veritabanına topluca ekle
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embeddings())
    
    batch_size = 80
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        try:
            db.add_documents(batch)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"API Limitine ulaşıldı. 60 saniye bekleniyor... ({i}/{len(all_chunks)})")
                time.sleep(60)
                db.add_documents(batch)
            else:
                raise e
                
        if i + batch_size < len(all_chunks):
            time.sleep(60) # Kota sıfırlanması için 1 dk bekle
            
    
    return len(all_chunks)

def query_rag(query_text: str):
    """Queries the Chroma vector database and generates an answer using Gemini."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Lütfen projenin backend dizinindeki .env dosyasına GEMINI_API_KEY bilginizi ekleyin.")
        
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embeddings())
    
    # Vektör veri tabanında en alakalı 4 bölümü (chunk) bul
    results = db.similarity_search_with_relevance_scores(query_text, k=4)
    
    if len(results) == 0:
        context_text = ""
        sources = []
    else:
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        sources = list(set([os.path.basename(doc.metadata.get("source", "Bilinmeyen Kaynak")) for doc, _score in results]))
        
    prompt_template = f"""
    Sen, test uzmanları için geliştirilmiş "GİB Paket Analizörü" uygulaması içinde çalışan uzman bir e-Dönüşüm asistanısın.
    Aşağıdaki resmi GİB/Kılavuz bağlamını (context) kullanarak kullanıcının sorusuna en doğru ve net cevabı ver. 
    Eğer bağlamda cevaba dair bir kural geçmiyorsa, bunu açıkça belirt ancak bir e-Dönüşüm uzmanı olarak bildiğin teknik bilgileri kullanarak (UBL-TR standartları gibi) yardımcı ol. 
    Mümkün olduğunca teknik, net ve doğrudan test edilebilir bilgiler sağla. Yorum katma, kuralı söyle.

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
        
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embeddings())
    
    results = db.similarity_search_with_relevance_scores(query_text, k=4)
    
    if len(results) == 0:
        context_text = ""
    else:
        context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
        
    prompt_template = f"""
    Sen, test uzmanları için geliştirilmiş "GİB Paket Analizörü" uygulaması içinde çalışan uzman bir e-Dönüşüm asistanısın.
    Aşağıdaki resmi GİB/Kılavuz bağlamını (context) kullanarak kullanıcının sorusuna en doğru ve net cevabı ver. 
    Eğer bağlamda cevaba dair bir kural geçmiyorsa, bunu açıkça belirt ancak bir e-Dönüşüm uzmanı olarak bildiğin teknik bilgileri kullanarak (UBL-TR standartları gibi) yardımcı ol. 
    Mümkün olduğunca teknik, net ve doğrudan test edilebilir bilgiler sağla. Yorum katma, kuralı söyle.

    [VERİTABANINDAN ÇEKİLEN İLGİLİ KILAVUZ BİLGİLERİ]:
    {context_text}

    Kullanıcının Sorusu: {query_text}
    """
    
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
    
    async for chunk in model.astream(prompt_template):
        if chunk.content:
            yield chunk.content

