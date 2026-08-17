import os
import sys
import time

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.rag_engine import query_rag

# Benchmark GİB e-Dönüşüm Evaluation Questions and Expected Truth Asserts
EVAL_DATASET = [
    {
        "id": 1,
        "question": "e-Gider Pusulası UBL standardında hangi XML kök elemanı (root tag) ve ProfileID ile düzenlenir?",
        "expected_keywords": ["CreditNote", "GIDERPUSULASI"],
        "category": "Belge Yapısı"
    },
    {
        "id": 2,
        "question": "e-Gider Pusulası'nda Satış ve İade senaryosu ayrımı hangi UBL elemanı üzerinden yapılır ve hangi kodları alır?",
        "expected_keywords": ["CreditNoteTypeCode", "SATIS", "IADE"],
        "category": "İade ve Satış Tipleri"
    },
    {
        "id": 3,
        "question": "e-Arşiv Fatura şemasına eklenen e-Gider Pusulası elemanları nelerdir?",
        "expected_keywords": ["eGiderPusulasiType", "eGiderPusulasiIptal"],
        "category": "Şema Değişiklikleri"
    },
    {
        "id": 4,
        "question": "e-Gider Pusulası'nda SMS veya operatör onay bilgileri hangi eleman grubu altında tutulur?",
        "expected_keywords": ["operatorUygulamaBilgi"],
        "category": "Doğrulama / İletişim"
    },
    {
        "id": 5,
        "question": "e-Gider Pusulası görsel tasarımında (XSLT) hangi dosya adı kullanılır?",
        "expected_keywords": ["giderPusulasi.xslt"],
        "category": "Tasarım / XSLT"
    },
    {
        "id": 6,
        "question": "e-Gider Pusulası iade senaryosunda eski faturaya atıf hangi eleman ile yapılır?",
        "expected_keywords": ["BillingReference", "InvoiceDocumentReference"],
        "category": "İade Referansı"
    }
]

def run_evaluation():
    print("=" * 60)
    print("🎯 GİB e-Dönüşüm RAG Asistanı Doğruluk & Regresyon Test Seti")
    print("=" * 60)
    
    passed = 0
    total = len(EVAL_DATASET)
    start_time = time.time()
    
    for item in EVAL_DATASET:
        q_id = item["id"]
        q_text = item["question"]
        expected = item["expected_keywords"]
        category = item["category"]
        
        print(f"\n[{q_id}/{total}] Kategori: {category}")
        print(f"❓ Soru: {q_text}")
        print(f"🔍 Beklenen Anahtar Bilgiler: {', '.join(expected)}")
        
        try:
            res = query_rag(q_text)
            answer = res.get("answer", "")
            
            # Check keyword containment (case-insensitive)
            matched = [k for k in expected if k.lower() in answer.lower()]
            match_rate = len(matched) / len(expected)
            
            if match_rate >= 0.66: # At least 2/3 of key terms matched
                print(f"✅ BAŞARILI! (Eşleşen: {matched})")
                passed += 1
            else:
                print(f"❌ KISMİ / BAŞARISIZ! (Eşleşen: {matched}, Eksik: {[k for k in expected if k not in matched]})")
                print(f"   Model Yanıtından Kesit: {answer[:250]}...")
                
        except Exception as e:
            print(f"💥 HATA: {e}")
            
    elapsed = time.time() - start_time
    score = (passed / total) * 100
    
    print("\n" + "=" * 60)
    print(f"📊 TEST RAPORU:")
    print(f"   Toplam Soru: {total}")
    print(f"   Başarılı: {passed}")
    print(f"   Başarısız: {total - passed}")
    print(f"   Doğruluk Skoru: %{score:.1f}")
    print(f"   Toplam Süre: {elapsed:.2f} saniye")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluation()
