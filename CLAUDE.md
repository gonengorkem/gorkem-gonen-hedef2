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
4. **Zip Slip koruması var ama KIRILGAN** (`zip_processor.py`) — `safe_extract_zip()` doğru
   çalışıyor, ANCAK onu çağıran `uncompress_archive_file()` içindeki
   `except (zipfile.BadZipFile, Exception): pass` bloğu, `safe_extract_zip`'in attığı
   Zip Slip `ValueError`'ını da yutup korumasız `tar -xf` fallback'ine düşürüyor.
   **Bu hâlâ düzeltilmedi** — `except` sadece `zipfile.BadZipFile` ile sınırlanmalı.
5. **Global SSL doğrulama bypass'ı env-gated** (`main.py`, `rag_engine.py`) —
   `DISABLE_SSL_VERIFY` env değişkenine bağlı, varsayılan `false`. Prod'da asla `true`
   yapılmamalı; sadece kurumsal proxy arkasında yerel geliştirme için var.
6. **Debug artefaktları kaldırıldı** (`debug.log`, `debug_uploaded.xml`, `debug_files.log`) —
   yeni debug çıktısı eklerken diske kalıcı, sınırsız büyüyen dosya yazma.
7. **Mock veri artık şeffaf** — DB bağlantısı başarısızsa sessizce sahte veri dönülmüyor,
   `is_mock` flag'i veya açık hata veriliyor. Bu deseni koru.

### Hâlâ açık / bilinen eksikler
- **Host binding tutarsız**: `main.py`'nin `if __name__=="__main__"` bloğu varsayılan
  `127.0.0.1`'e düzeltildi, ama `start.bat` hâlâ `--host 0.0.0.0` kullanıyor — asıl
  başlatma yolu bu olduğu için pratikte LAN'a açık kalıyor. Düzeltilmeli.
- **DB adı / connection string injection**: `reconciliation_engine.py`'de `company_code`/`year`
  hâlâ whitelist doğrulamasından geçmeden `db_name` (ODBC DATABASE alanı) içine gömülüyor.
  Veri sorguları parametreli ama bu vektör kapanmadı.
- **İkinci iframe'de `sandbox` eksik**: `App.jsx`'te `xrayResult.html_preview` gösteren iframe
  (X-Ray/Röntgen önizlemesi) `sandbox` attribute'ünden yoksun; sadece KVKK maskeleme
  önizlemesine (`sanResult.html_preview`) eklenmiş.
- **Hiçbir endpoint'te authentication yok.** Bilinçli bir kapsam kararı (tek kişilik iç araç),
  ama `host="0.0.0.0"` ile birleşince risk taşıyor. Eklenirse basit bir API key/header
  kontrolü yeterli olur, büyük bir auth sistemi gerekmez.
- `requirements.txt` versiyon pin'siz.
- CORS `allow_origins=["*"]` (bilinçli, "development" yorumu var).

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

### Bilinen mimari eksikler (öncelik sırasıyla)
1. **Docling import edilmiş ama hiç kullanılmıyor.** PDF okuma hâlâ `PyPDFLoader` (naif metin
   çıkarma) ile yapılıyor. GİB kılavuzları element/kural tablolarıyla dolu; naif metin
   çıkarma bu tabloları karıştırıyor. Docling'i gerçekten devreye almak en yüksek etkili
   iyileştirme. **Dikkat:** Docling'in yerel modellerini indirirken daha önce kurumsal
   proxy/SSL sorunu yaşanmıştı — bu modelleri bir kere, güvenli bir ağdan indirip lokal
   cache'e almayı, ingest sırasında ağa hiç çıkmayacak şekilde ayır. `DISABLE_SSL_VERIFY`'ı
   bu sorunu çözmek için tekrar `true` yapma cazibesine karşı dur.
2. **Konuşma hafızası yok.** `/api/rag/chat` sadece o anki `query`'yi alıyor, önceki
   mesajları backend'e göndermiyor. Takip sorularını ("az önce bahsettiğin...") anlayamıyor.
3. **Sabit karakter chunking (1200 karakter)** başlık/tablo sınırlarını gözetmiyor, bir kural
   tanımını ortadan ikiye bölebiliyor. Docling'e geçince markdown header/tablo bazlı
   chunking'e geçilmeli.

### Yol haritası (üzerinde mutabık kalınan sıralama)
- **Aşama 1 (öncelikli):** Docling entegrasyonu (tablo-korumalı parse) + konuşma hafızası
  (son 3-4 mesajı context'e taşı) + markdown header/tablo bazlı chunking.
- **Aşama 1.5 (Aşama 2'nin gizli önkoşulu):** Versiyonlu, kalıcı paket arşivi. Şu an her
  paket analizi geçici klasörde yapılıp temizleniyor; "v1.15 ile v1.20'yi karşılaştır"
  diye bir araç istenirse, önce karşılaştırılabilecek isimlendirilmiş, kalıcı bir arşiv
  katmanı (mevcut `storage_service`'i genişleterek) kurulmalı.
- **Aşama 2:** Tam ReAct/tool-calling agent yerine, önce **sabit iki adımlı** bir
  "getir → doğrula" akışı (diff + kılavuz aramasını kod içinde sabit sırayla çalıştırıp
  tek sentez prompt'una verme) tercih edilsin — karmaşıklık/gecikme/maliyet daha düşük.
  Basit lookup sorularında mevcut hızlı tek-atış yol korunmalı, her soru ağır bir
  agent döngüsünden geçirilmemeli.
- **Değerlendirme (eval) seti eksik.** Kılavuzlardan 15-20 bilinen doğru cevaplı soru
  hazırlanıp, her RAG değişikliğinden sonra otomatik test edilmeli — "iyileşti mi bozuldu
  mu" sorusu gözlemsel değil, ölçülebilir olmalı. Henüz oluşturulmadı.

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