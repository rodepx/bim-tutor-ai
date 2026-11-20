"""Rutas y configuración. Todo se resuelve relativo a este archivo, no al CWD."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = REPO_ROOT / "data"
CONTRACTS_DIR = REPO_ROOT / "contracts"

# .env de la raíz del repo; las variables ya definidas en el entorno tienen prioridad.
load_dotenv(REPO_ROOT / ".env", override=False)

API_VERSION = "0.1.0"
DEFAULT_DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'profesor_bim.db').as_posix()}"
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def database_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
