"""Point d'entrée uvicorn — réexporte l'app FastAPI construite dans app/main.py."""
from app.main import app  # noqa: F401
