import os

# Import the app without a built frontend (FastAPI skips that check in development).
os.environ.setdefault("FASTAPI_ENV", "development")
