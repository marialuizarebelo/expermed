import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_PATH = BASE_DIR / "expermed.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

PIPEDRIVE_API_TOKEN = os.getenv("PIPEDRIVE_API_TOKEN", "")
PIPEDRIVE_PIPELINE_ID = os.getenv("PIPEDRIVE_PIPELINE_ID", "")
PIPEDRIVE_STAGE_ID = os.getenv("PIPEDRIVE_STAGE_ID", "")

DATAJUD_API_KEY = os.getenv("DATAJUD_API_KEY", "")

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")

GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")

# Parâmetros de qualificação (seção 3 da especificação)
VOLUME_MINIMO_TOTAL = 200
VOLUME_MINIMO_ASSUNTOS_ALVO = 100
RITMO_MESES = 12  # pendente de confirmação com a Expermed

ASSUNTOS_INTERESSE = [
    "insalubridade",
    "periculosidade",
    "acidente de trabalho",
    "ergonomia",
    "doenca ocupacional",
]
