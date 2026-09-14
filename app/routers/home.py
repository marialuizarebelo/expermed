from fastapi import APIRouter, Request

from app.db import db_session
from app.templates_engine import templates

router = APIRouter()


@router.get("/")
def home(request: Request):
    with db_session() as conn:
        total_empresas = conn.execute("SELECT COUNT(*) c FROM empresas").fetchone()["c"]
        qualificadas = conn.execute(
            "SELECT COUNT(*) c FROM empresas WHERE status = 'qualificada'"
        ).fetchone()["c"]
        mensagens_geradas = conn.execute("SELECT COUNT(*) c FROM mensagens").fetchone()["c"]
        por_etapa = conn.execute(
            "SELECT etapa_atual, COUNT(*) c FROM negocios_pipedrive GROUP BY etapa_atual"
        ).fetchall()

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "total_empresas": total_empresas,
            "qualificadas": qualificadas,
            "mensagens_geradas": mensagens_geradas,
            "por_etapa": por_etapa,
        },
    )
