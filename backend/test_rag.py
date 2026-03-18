import os
from dotenv import load_dotenv
load_dotenv()

from core.rag_engine import query_rag

try:
    print("Testing query_rag...")
    res = query_rag("Merhaba")
    print("RESULT:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
