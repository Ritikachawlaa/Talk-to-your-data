import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
# This script will check which Gemini models are available for your API key.

def check_available_models():
    """
    Connects to the Google AI API and lists all available models
    that support the 'generateContent' method.
    """
    try:
        # Load environment variables from .env file
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            print("ERROR: GEMINI_API_KEY not found in .env file.")
            print("Please ensure your .env file is in the project root and contains your key.")
            return

        genai.configure(api_key=api_key)

        print("Successfully connected to Google AI. Checking for available models...\n")
        print("--- Models available for your API key ---")
        
        found_models = False
        # List all available models
        for model in genai.list_models():
            # Check if the model supports the 'generateContent' method, which our app uses
            if 'generateContent' in model.supported_generation_methods:
                print(model.name)
                found_models = True
        
        if not found_models:
            print("No models supporting 'generateContent' were found for your API key.")
        else:
            print("\n-------------------------------------------")
            print("SUCCESS: Please copy one of the model names above (e.g., 'models/gemini-pro')")
            print("and paste it into the genai.GenerativeModel() line in your views.py file.")

    except Exception as e:
        print(f"An error occurred while trying to connect to the API: {e}")
        print("Please double-check your API key and internet connection.")

if __name__ == "__main__":
    check_available_models()
