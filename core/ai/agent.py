import os
import json
from google.genai import Client
from google.genai import types
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

def get_genai_client():
    """
    Returns a unified Google GenAI Client.
    Automatically switches between Google Cloud Vertex AI (with credit-loaded project ID)
    and Google AI Studio (API Key) based on .env configuration.
    """
    use_vertex = os.getenv("USE_VERTEX_AI", "False").lower() in ("true", "1", "yes")
    
    if use_vertex:
        project_id = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GCP_LOCATION")
        
        if not project_id or not location:
            raise ValueError("GCP_PROJECT_ID and GCP_LOCATION must be set in your .env file to use Vertex AI.")
            
        return Client(
            vertexai=True,
            project=project_id,
            location=location
        )
    else:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        return Client(api_key=api_key)


class GeminiAgent:
    def __init__(self):
        self.client = get_genai_client()
        # Default model to use for reasoning
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def get_embedding(self, text):
        try:
            # Generate Text Embeddings (Supported on both Vertex AI and AI Studio)
            response = self.client.models.embed_content(
                model='text-embedding-004',
                contents=text
            )
            return response.embeddings[0].values
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []

    def extract_skills(self, resume_text):
        prompt = """
        You are an expert Resume Parser. 
        Extract all technical skills, tools, and soft skills from the following resume text.
        Return ONLY a raw JSON list of strings. Do not include markdown formatting.

        Resume Text:
        {text}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt.format(text=resume_text[:10000]),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Error extracting skills: {e}")
            return []