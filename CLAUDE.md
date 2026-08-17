# Görkem Gönen Hedef — GİB e-Dönüşüm Paket Analizörü

## Proje Amacı

Bu proje, Gelir İdaresi Başkanlığı'nın (GİB) e-Dönüşüm (e-Fatura, e-Arşiv, e-Müstahsil
Makbuzu, e-İrsaliye, e-Serbest Meslek Makbuzu) süreçleri için yayınladığı XML paketlerindeki
şema/şematron değişikliklerini otomatik tespit eden ve test senaryosu üreten bir sistem.

Geliştiren kişi bir **yazılım test uzmanı** (e-dönüşüm projelerinde çalışıyor), proje şirket
içi bireysel hedef kapsamında geliştirildi. Kullanıcı olarak "biz" değil çoğunlukla tek kişi.

## Mimari

- **Backend:** FastAPI (Python), `backend/main.py` giriş noktası, iş mantığı `backend/core/`
  altında modüllere ayrılmış.
- **Frontend:** React + Vite, tek dosya `frontend/src/App.jsx` (2000+ satır, henüz
  component'lara bölünmemiş).
- **Redis:** Analiz sonuçlarını 24 saat cache'liyor (dosya hash'ine göre).
- **ChromaDB:** RAG (kılavuz sohbet) için vektör veritabanı, local persistent ya da uzak sunucu.
- **Gemini API:** RAG cevap üretimi ve history/diff özetleme için.
- **SQL Server (Zirve ERP):** Mutabakat (reconciliation) özelliği canlı bir Zirve veritabanına
  bağlanıp fatura verisini karşılaştırıyor.
- **zirve_monitor/** — ayrı bir alt-uygulama: mitmproxy tabanlı sistem trafiği izleyici.
  Ana backend'den bağımsız çalışır, sistem proxy'sini ve trust store'u değiştirir.
  Bu, geri kalan sistemle aynı güven seviyesinde olmamalı; yeni özellik eklerken bu alt
  projeyle karıştırma.
- **Deployment:** `install.bat`/`start.bat` ile local (venv + npm dev), ya da
  `podman-compose.yaml` ile konteynerli (Redis + ChromaDB + backend + nginx-frontend).

### Ana modüller (backend/core/)
- `zip_processor.py` — GİB paketlerini (zip/rar, iç içe olabilir) açar, hedef dosyaları filtreler.
- `diff_engine.py` — İki paket arasındaki XSD/XSLT/XML/SCH farkını element/attribute bazında çıkarır.
- `scenario_generator.py` — Diff'lere göre deterministik (LLM'siz) test senaryosu üretir.
- `schematron_engine.py` — XML'i .sch kuralına karşı doğrular.
- `sanitizer_engine.py` — Fatura XML'inden KVKK kapsamındaki kişisel verileri maskeler.
- `xslt_renderer.py` — Faturaya gömülü XSLT'yi çalıştırıp HTML önizleme üretir.
- `xray_engine.py` — Fatura içinde metin/sayı arayıp XPath'ini bulur.
- `reconciliation_engine.py` + `db_connector.py` — SQL Server'daki Zirve verisiyle mutabakat.
- `rag_engine.py` — Kılavuz PDF'lerini ingest edip Gemini ile soru-cevap (RAG).
- `redis_cache.py`, `storage.py` — cache ve S3/local dosya depolama soyutlaması.

## 🔒 Kritik Güvenlik Kuralları — ASLA GERİ ALINMAMALI

Bu proje üzerinde daha önce kapsamlı bir güvenlik denetimi yapıldı ve aşağıdaki açıklar
kapatıldı. Yeni özellik eklerken veya refactor yaparken bunları bozma:

1. **SQL Injection korumalı** (`reconciliation_engine.py`) — tüm SQL sorguları `?` parametreli.
   Yeni bir sorgu eklerken **asla** f-string ile kullanıcı girdisini sorguya gömme.
2. **Path Traversal korumalı** (`main.py`, schematron upload/delete) — `os.path.basename()` +
   `/`,`\` karakteri kontrolü var. Dosya adı alan her yeni endpoint'te aynı deseni kullan.
3. **XSLT Arbitrary File Write kapalı** (`xslt_renderer.py`) — `etree.XSLT(...,
   access_control=etree.XSLTAccessControl.DENY_ALL)` kullanılıyor. Bu satırı **asla kaldırma**;
   kaldırılırsa kullanıcı yüklediği XML içine gömdüğü kötü niyetli XSLT ile sunucuya
   dosya yazabilir (RCE riski). Test edilmiş, PoC ile doğrulanmış bir açıktı.
4. **Zip Slip koruması sağlamlaştırıldı** (`zip_processor.py`) — hem üst seviye
   `uncompress_archive_file()` (`except zipfile.BadZipFile` ile sınırlı, `ValueError`
   Zip Slip istisnası artık yutulmuyor), hem de iç içe arşivleri işleyen
   `extract_nested_zips()` (`except ValueError: raise` ile Zip Slip'i öne geçiriyor,
   sadece bozuk/desteklenmeyen alt-arşivleri sessizce atlıyor). Bu deseni koru: yeni bir
   `except Exception` eklerken Zip Slip `ValueError`'ının içine düşmediğinden emin ol.
5. **Global SSL doğrulama bypass'ı env-gated** (`main.py`, `rag_engine.py`) —
   `DISABLE_SSL_VERIFY` env değişkenine bağlı, varsayılan `false`. Prod'da asla `true`
   yapılmamalı; sadece kurumsal proxy arkasında yerel geliştirme için var. Kod iki dosyada
   birebir kopya (bakım riski — biri güncellenip diğeri unutulabilir, tek yardımcı modüle
   çıkarmak faydalı olur ama acil değil).
6. **Debug artefaktları kaldırıldı** (`debug.log`, `debug_uploaded.xml`, `debug_files.log`) —
   yeni debug çıktısı eklerken diske kalıcı, sınırsız büyüyen dosya yazma.
7. **Mock veri artık şeffaf** — DB bağlantısı başarısızsa sessizce sahte veri dönülmüyor,
   `is_mock` flag'i veya açık hata veriliyor. Bu deseni koru.
8. **XXE koruması tüm XML giriş noktalarında tutarlı** (`diff_engine.py`,
   `schematron_engine.py`, `sanitizer_engine.py`, `xslt_renderer.py`, `xray_engine.py`,
   `reconciliation_engine.py`) — hepsi `resolve_entities=False, no_network=True,
   dtd_validation=False, load_dtd=False, huge_tree=False` ile `etree.XMLParser`
   kullanıyor. Yeni bir yerde ham kullanıcı XML'i parse edilecekse aynı flag setini kopyala;
   `reconciliation_engine.py`'de bu flag'ler eksikti, 2026-08-17'de eklendi.
9. **`/api/rag/ingest` path traversal kapatıldı** (`main.py`) — S3/local storage'a
   kaydedilen kılavuz dosyası artık `os.path.basename(file.filename)` ile sanitize
   ediliyor (önceden ham `file.filename` `guides/` dışına, örn. `backend/` içindeki
   dosyaların üzerine yazılabiliyordu). Dosya adı alan her yeni endpoint'te bu deseni koru.
10. **`.env` dosyası artık ezilmiyor** (`main.py`, `/api/settings/apikey`) — önceden dosya
    `"w"` modda açılıp sadece `GEMINI_API_KEY` satırı yazılıyordu, bu da `DISABLE_SSL_VERIFY`,
    `HOST`, `AWS_*` gibi diğer tüm ayarları her key güncellemesinde siliyordu; ayrıca `key`
    hiç escape edilmeden f-string'e gömülüyordu (satır sonu/`"` içeren bir key ile env
    injection mümkündü). Artık mevcut satırlar korunarak sadece ilgili satır
    güncelleniyor/ekleniyor, `key` içinde `"`/newline varsa istek reddediliyor.

### Hâlâ açık / bilinen eksikler
- **Host binding tutarsız**: `main.py`'nin `if __name__=="__main__"` bloğu ile `start.bat`
  ikisi de artık `127.0.0.1` kullanıyor (2026-08-17 itibarıyla doğrulandı) — daha önceki
  `0.0.0.0` notu güncelliğini yitirmiş, izlemeye devam et ama aktif bir açık değil.
- **DB adı / connection string injection kapatıldı**: `reconciliation_engine.py`'de
  `company_code`/`year` artık regex whitelist (`^[a-zA-Z0-9_\-]+$`, `^\d{4}$`) ile
  doğrulanıyor, sonra `db_name` içine gömülüyor. Önceki not güncelliğini yitirmişti.
- **İkinci iframe'deki `sandbox` eksikliği kapatıldı**: `App.jsx`'te `xrayResult.html_preview`
  iframe'i artık `sandbox="allow-same-origin"` içeriyor. Önceki not güncelliğini yitirmişti.
- **Hiçbir endpoint'te authentication yok.** Bilinçli bir kapsam kararı (tek kişilik iç araç).
  Host binding artık `127.0.0.1`'e düzeltildiği için LAN'a açık olma riski azaldı, ama
  kimliksiz kalmaya devam ediyor — hassas endpoint'ler (DB bağlantısı, dosya silme, `.env`
  yazma) için en azından basit bir API key/header kontrolü düşünülebilir.
- `requirements.txt` artık alt/üst sınır aralıklarıyla pin'li (`>=x,<y` formatı) — tamamen
  pin'siz değil, ama tam sürüm sabitleme (lockfile) yok.
- CORS `allow_origins=["*"]` (bilinçli, "development" yorumu var).
- **SQL bağlantı hatası log sızıntısı kapatıldı** (`db_connector.py`) — `connect()` ve
  `execute_query()` içindeki `except` blokları artık hata mesajını loglamadan önce
  `_redact_secrets()` ile `PWD=...` alanını maskeliyor (bazı ODBC sürücüleri hata mesajına
  bağlantı dizesini gömebiliyordu). Yeni bir DB hata logu eklerken aynı helper'ı kullan.
- **`run_reconciliation` ayrıştırıldı** (`reconciliation_engine.py`) — ~190 satırlık tek
  fonksiyon `_resolve_db_name`, `_fetch_reconciliation_records`, `_audit_header`,
  `_audit_lines` yardımcı fonksiyonlarına bölündü; davranış aynı, sadece test
  edilebilirlik/okunabilirlik için ayrıştırıldı.

## RAG Bölümü (Kılavuz Sohbet) — Amaç ve Durum

**Kullanıcının asıl amacı:** GİB kılavuzlarını (yüzlerce sayfa) tek tek okumak yerine bir
agent'a "öğretip", yeni bir kılavuz yayınlandığında ya da bir şey merak ettiğinde
("XML'e neler eklendi, hangi kural setleri geldi") hızlı, güvenilir, kaynak gösteren
cevap almak.

### Yapılmış olan iyileştirmeler
- Prompt'a hardcoded, eskiyecek mevzuat bilgisi (örn. "KDV oranları Temmuz 2023'te
  güncellendi") **kaldırıldı**. Bir daha böyle statik "güncel gerçek" bilgisi gömme.
- "Asla bilgi yok deme" talimatı kaldırılıp yerine halüsinasyon karşıtı şeffaflık ilkesi
  kondu: context'te yoksa modelin açıkça "bu bilgi kılavuzda yok" diyebilmesi şart.
  Bu davranışı bozacak prompt değişikliği yapma.
- Kaynak/sayfa referansları (`structured_sources`, stream sonu dipnotları) eklendi.
- `extract_metadata_from_path()` — dosya adından versiyon/tip/tarih metadata çıkarıp
  her chunk'a etiketliyor.
- `explain_diff_with_rag()` + `/api/rag/explain-diff` — diff engine'in bulduğu bir XML
  değişikliğini kılavuzdan otomatik açıklatan köprü fonksiyon. Frontend'de kullanılıyor.
- **Aşama 1 tamamlandı (2026-08-17, commit 8609a2e):** Docling entegrasyonu devreye alındı
  (`rag_engine.py`'de `DoclingLoader`/`DocumentConverter` ile tablo-korumalı PDF parse),
  `MarkdownHeaderTextSplitter` ile başlık bazlı bölütleme (1400 karakterlik alt-chunk'larla
  birlikte), `/api/rag/chat` artık `history` parametresi alıp son 4 mesajı prompt'a
  taşıyor (çok turlu diyalog hafızası), ve `backend/tests/eval_rag.py` altında GİB
  kılavuzlarından bilinen-cevaplı bir QA eval seti eklendi. Aşağıdaki "bilinen mimari
  eksikler" listesi bu nedenle güncelliğini yitirmişti — kaldırıldı.
- **Docling sayfa referansı regresyonu düzeltildi (2026-08-17):** Docling entegrasyonu ilk
  haliyle tüm PDF'i `export_to_markdown()` ile TEK bir `Document`'a dönüştürüyordu ve hiç
  `page` metadata'sı set etmiyordu; bu yüzden `query_rag`/`query_rag_stream`/
  `explain_diff_with_rag` içindeki `doc.metadata.get("page", 0) + 1` her zaman "Sayfa 1"
  döndürüyordu — Docling ile parse edilen (yani artık varsayılan/başarılı) her kılavuzda
  kaynak/sayfa atıfları yanlıştı. `load_pdf_with_docling_or_fallback()` artık
  `doc.export_to_markdown(page_no=...)` ile PyPDFLoader'la aynı sözleşmeyi (0 tabanlı
  `page` metadata, sayfa başına bir `Document`) koruyarak sayfa sayfa export ediyor.
  Yeni bir loader/parser eklerken bu sözleşmeyi (her chunk'ta doğru `page` metadata) koru.

### `get_hybrid_context` sıralaması: relevance birincil, versiyon ikincil (2026-08-17)
`get_hybrid_context()` (rag_engine.py) önceden birleştirilmiş (keyword+vektör, alaka
sıralı) listeyi tamamen `extract_document_version_score`'a göre yeniden sıralıyordu — bu,
farklı kılavuz türleri karışık geldiğinde alakasız ama yeni tarihli bir kılavuzun, en
alakalı ama eski tarihli bir parçanın önüne geçmesine yol açabiliyordu. Artık sıralama
`(group_rank, -version_score)` anahtarıyla yapılıyor: `group_rank`, her `doc_title`
grubunun merge sonrası ilk göründüğü sırayı (yani relevance sırasını) sabitliyor;
versiyon/yıl sadece AYNI kılavuzun (aynı `doc_title`) birden fazla versiyonu vektör DB'de
aynı anda mevcutsa o grup içinde en güncelini öne çıkaran bir tie-breaker. Yeni bir
sıralama/skorlama mantığı eklerken relevance sırasını global olarak ezme.

### Yol haritası (üzerinde mutabık kalınan sıralama)
- **Aşama 1: TAMAMLANDI** — Docling entegrasyonu, konuşma hafızası, header/tablo bazlı
  chunking, eval seti (yukarı bakınız).
- **Aşama 1.5 (Aşama 2'nin gizli önkoşulu):** Versiyonlu, kalıcı paket arşivi. Şu an her
  paket analizi geçici klasörde yapılıp temizleniyor; "v1.15 ile v1.20'yi karşılaştır"
  diye bir araç istenirse, önce karşılaştırılabilecek isimlendirilmiş, kalıcı bir arşiv
  katmanı (mevcut `storage_service`'i genişleterek) kurulmalı.
- **Aşama 2:** Tam ReAct/tool-calling agent yerine, önce **sabit iki adımlı** bir
  "getir → doğrula" akışı (diff + kılavuz aramasını kod içinde sabit sırayla çalıştırıp
  tek sentez prompt'una verme) tercih edilsin — karmaşıklık/gecikme/maliyet daha düşük.
  Basit lookup sorularında mevcut hızlı tek-atış yol korunmalı, her soru ağır bir
  agent döngüsünden geçirilmemeli.
- **Değerlendirme (eval) seti eklendi:** `backend/tests/eval_rag.py` — GİB kılavuzlarından
  bilinen doğru cevaplı sorular ve beklenen anahtar kelimeler. Her RAG değişikliğinden sonra
  çalıştırılmalı; henüz CI'a bağlanmadı, manuel çalıştırma gerekiyor.

## Geliştirme Notları

- Python bağımlılıkları `backend/requirements.txt`, sanal ortam `backend/venv`.
- Frontend `frontend/` altında, `npm run dev` ile Vite dev server.
- `.env` dosyası `backend/.env` içinde (gitignore'da, repoya asla commit edilmemeli):
  `GEMINI_API_KEY`, `DISABLE_SSL_VERIFY`, `HOST`, `PORT`, `AWS_*`, `S3_BUCKET_NAME`,
  `CHROMA_SERVER_HOST/PORT`, `REDIS_HOST`.
- Test dosyaları eskiden repoda tek seferlik scratch script olarak duruyordu
  (`list_models.py`, `test_rag.py`, `inspect_zips.py`, `dark_mode_patch.py`,
  `download_logo.py`) — bunlar temizlendi. Yeni tek seferlik/deneme scriptlerini repoya
  commit etme, ya da `scripts/` altında ayrı ve `.gitignore`'da tut.
- Dil: Kullanıcıyla ve UI metinleriyle iletişim Türkçe. Kod içi yorumlar karışık
  (Türkçe/İngilizce), tutarlı olmasa da mevcut dosyanın kendi diline uy.

## Değişiklik Yaparken Genel Prensip

Her yeni endpoint veya özellik eklerken şu soruları sor:
1. Kullanıcı girdisi bir SQL sorgusuna, dosya yoluna veya shell komutuna gömülüyor mu?
   Gömülüyorsa parametreli sorgu / `os.path.basename` + whitelist / `subprocess` argüman
   listesi (shell=False) kullan.
2. Bu endpoint kimliksiz mi? (Şu an hepsi öyle.) Hassas bir işlemse (dosya silme, DB
   bağlantısı, sistem ayarı değiştirme) en azından bunu bilerek yap, mümkünse basit bir
   API key kontrolü ekle.
3. Debug/log çıktısı diske kalıcı ve sınırsız mı yazılıyor? Yazma, ya da rotasyon/limit koy.