import os
from pathlib import Path

def configure_():
    """
    Configure Google Cloud credentials.
    Works for both local development and Render deployment.
    """
    # Check if already set via environment
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    # Find credentials file relative to this script
    base_path = Path(__file__).resolve().parent
    cred_file = base_path / "gen-lang-client-0230748166-1ccd3a1fddcb.json"

    if cred_file.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_file)
    else:
        print(f"[WARNING] Credentials file not found at: {cred_file}")
