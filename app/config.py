import os

# All secrets loaded from environment variables
GEM_API_KEY = os.getenv("GEM_API_KEY", "")
GEM_PROJECT_ID = os.getenv("GEM_PROJECT_ID", "gen-lang-client-0230748166")
GEM_LOCATION = os.getenv("GEM_LOCATION", "global")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3-pro-preview")
VISION_API_KEY = os.getenv("VISION_API_KEY", "")

ENDPOINT_NAME = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{GEM_PROJECT_ID}/locations/{GEM_LOCATION}/publishers/google/models/{MODEL_NAME}/"
VERTEX_AI_PROJECT_ID = GEM_PROJECT_ID
