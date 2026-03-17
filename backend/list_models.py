import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        if "models" in data:
            print("AVAILABLE EMBEDDING MODELS:")
            for model in data["models"]:
                methods = model.get("supportedGenerationMethods", [])
                if "embedContent" in methods:
                    print("- " + model["name"])
        else:
            print(data)
except Exception as e:
    print("Error:", e)
