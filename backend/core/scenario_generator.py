def generate_scenarios(diff_results: list):
    """
    Takes the structured differences and generates testing scenarios.
    """
    scenarios = []
    
    for file_diff in diff_results:
        filename = file_diff["file"]
        status = file_diff["status"]
        
        if status == "new_file":
            scenarios.append({
                "target": filename,
                "type": "YENİ DOSYA / KURAL SETİ",
                "positive": f"Sistemin {filename} paketini eksiksiz olarak kabul edip işleyebildiği doğrulanmalı.",
                "negative": f"Yeni {filename} kurallarına uymayan bir döküman gönderildiğinde sistemin reddettiği kontrol edilmeli."
            })
            continue
            
        if status == "deleted_file":
            scenarios.append({
                "target": filename,
                "type": "KALDIRILAN DOSYA",
                "positive": f"Eskiden {filename} üzerinden yürüyen kurallara ait validasyonların pasife alındığı (uyarısız geçiş) doğrulanmalı.",
                "negative": "Yok"
            })
            continue
            
        for change in file_diff.get("diff", []):
            ctype = change["type"]
            target = change["target"]
            human_text = change.get("human_readable", "Teknik bir değişiklik yapıldı.")
            
            if ctype == "added":
                scenarios.append({
                    "target": target,
                    "file": filename,
                    "type": "YENİ ALAN (KURAL) EKLENDİ",
                    "positive": f"Sistemin yeni kurala uygun davrandığı doğrulanmalı. (Açıklama: {human_text})",
                    "negative": f"Bu yeni alan/kural ihlal edildiğinde GİB şemasına uygun hata alındığı görülmeli."
                })
            elif ctype == "attribute_added":
                scenarios.append({
                    "target": target,
                    "file": filename,
                    "type": "YENİ ÖZELLİK EKLENDİ",
                    "positive": f"Eklenen özelliğin iş kurallarına uygun doldurulduğunda kabul edildiği doğrulanmalı. (Açıklama: {human_text})",
                    "negative": "Bu yeni özelliğe zıt veya geçersiz bir format gönderildiğinde şematron/şema hatası fırlatıldığı görülmeli."
                })
            elif ctype == "modified":
                scenarios.append({
                    "target": target,
                    "file": filename,
                    "type": "KURAL / ÖZELLİK DEĞİŞTİRİLDİ",
                    "positive": f"Yeni kural setine göre belgenin başarıyla oluşturulduğu doğrulanmalı. (Açıklama: {human_text})",
                    "negative": f"Eski kurala göre veri gönderimi yapıldığında sistemin (GİB standartlarına göre) artık uyarı veya hata üretip üretmediği kontrol edilmeli."
                })
            elif ctype == "removed":
                 scenarios.append({
                    "target": target,
                    "file": filename,
                    "type": "ALAN / KURAL KALDIRILDI",
                    "positive": f"Kaldırılan kurala/alana dair bir veri gönderilmediğinde belgenin yine de başarıyla GİB'e iletilebildiği/validasyonlardan geçtiği kontrol edilmeli. (Açıklama: {human_text})",
                    "negative": f"Artık geçersiz olan veya kaldırılan bir kural/alan belgeye zorla eklenirse sistemin bunu filtreleyip filtrelemediği veya GİB'in reddedip reddetmediği kontrol edilmeli."
                })
                
    return scenarios
