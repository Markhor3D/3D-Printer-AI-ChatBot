import os
import google.generativeai as genai
import dotenv

# Explicitly load .env from the MyGoogleAgent directory
dotenv.load_dotenv(dotenv_path='MyGoogleAgent/.env')

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("Listing available models:")
# Also print the API key being used (masked for security)
api_key_masked = os.getenv("GOOGLE_API_KEY")
if api_key_masked:
    print(f"Using API Key: {api_key_masked[:5]}...{api_key_masked[-5:]}\n")
else:
    print("API Key not found or empty.\n")


for model in genai.list_models():
    print(f"Name: {model.name}")
    print(f"Description: {model.description}")
    print(f"Supported generation methods: {model.supported_generation_methods}\n")
