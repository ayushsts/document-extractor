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

    # Priority 1: Render secret file location
    render_secret = Path("/etc/secrets/gcp-credentials.json")
    if render_secret.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(render_secret)
        print("[CONFIG] Using Render secret file")
        return

    # Priority 2: Local development file
    base_path = Path(__file__).resolve().parent
    cred_file = base_path / "gen-lang-client-0230748166-1ccd3a1fddcb.json"

    if cred_file.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_file)
        print("[CONFIG] Using local credentials file")
    else:
        print(f"[WARNING] Credentials file not found!")
