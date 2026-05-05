import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print(f"Checking models for API Key: {api_key[:10]}...")
try:
    for m in genai.list_models():
        if 'embedContent' in m.supported_generation_methods:
            print(f"Found embedding model: {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
