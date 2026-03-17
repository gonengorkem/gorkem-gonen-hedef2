import urllib.request

urls = [
    "https://upload.wikimedia.org/wikipedia/tr/6/69/Gelir_%C4%B0daresi_Ba%C5%9Fkanl%C4%B1%C4%9F%C4%B1_logosu.png",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Gelir_%C4%B0daresi_Ba%C5%9Fkanl%C4%B1%C4%9F%C4%B1_logo.svg/1200px-Gelir_%C4%B0daresi_Ba%C5%9Fkanl%C4%B1%C4%9F%C4%B1_logo.svg.png",
    "https://ivd.gib.gov.tr/assets/img/gib_logo_kucuk.png",
    "https://gib.gov.tr/sites/all/themes/gib/logo.png"
]

success = False
for url in urls:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            if response.status == 200 and 'image' in response.headers.get('Content-Type', ''):
                data = response.read()
                with open('c:/Users/User/.gemini/antigravity/scratch/gorkem-gonen-hedef/frontend/public/gib_logo.png', 'wb') as f:
                    f.write(data)
                print(f"Downloaded from {url}")
                success = True
                break
    except Exception as e:
        print(f"Failed {url}: {e}")

if not success:
    print("ALL FAILED")
