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
            
            if ctype == "added":
                scenarios.append({
                    "target": target,
                    "file": filename,
                    "type": "YENİ ALAN (KURAL) EKLENDİ",
                    "positive": f"'{target}' alanının uygun formata göre doldurulup gönderilebildiği doğrulanmalı.",
                    "negative": f"'{target}' alanı eksik, formatı hatalı veya sınırları dışındaysa sistemin kabul etmemesi kontrol edilmeli."
                })
            elif ctype == "attribute_added":
                message = change.get("message", "")
                scenarios.append({
                    "target": target,
                    "file": filename,
                    "type": "YENİ ÖZELLİK (ATTRIBUTE) EKLENDİ",
                    "positive": f"'{target}' alanının eklenen yeni özelliğe ({message.replace(f'{target} elementine ', '')}) uygun olarak doldurulup geçebildiği doğrulanmalı.",
                    "negative": "Eklenen bu özelliğe zıt/uyumsuz bir değer gönderildiğinde şematron/şema hatası fırlatıldığı görülmeli."
                })
            elif ctype == "modified":
                message = change.get("message", "")
                scenarios.append({
                    "target": target,
                    "file": filename,
                    "type": "KURAL / ÖZELLİK DEĞİŞTİRİLDİ",
                    "positive": f"Yeni kural setine göre ('{target}' alanı için güncellenmiş değer vb.) belgenin hatasız geçişi doğrulanmalı.",
                    "negative": f"Eski kurala göre veri gönderimi yapıldığında sistemin (GİB standartlarına göre) artık hata üretip üretmediği kontrol edilmeli."
                })
            elif ctype == "removed":
                 scenarios.append({
                    "target": target,
                    "file": filename,
                    "type": "ALAN / KURAL KALDIRILDI",
                    "positive": f"'{target}' alanı gönderilmediğinde belgenin yine de başarıyla GİB'e iletilebildiği/validasyonlardan geçtiği kontrol edilmeli.",
                    "negative": f"Artık geçersiz olan '{target}' alanı belgeye eklenirse sistemin kabul edip etmediği, ediyorsa da zararsız aktarıp aktarmadığı kontrol edilmeli."
                })
                
    return scenarios
