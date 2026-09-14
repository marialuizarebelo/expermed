from fastapi import APIRouter, Request

from app.db import db_session
from app.templates_engine import templates

router = APIRouter()


@router.get("/execucoes")
def listar_execucoes(request: Request):
    with db_session() as conn:
        execucoes = conn.execute("SELECT * FROM execucoes ORDER BY iniciado_em DESC").fetchall()

    return templates.TemplateResponse(request, "execucoes.html", {"execucoes": execucoes})


@router.get("/execucoes/{execucao_id}")
def detalhe_execucao(request: Request, execucao_id: int):
    with db_session() as conn:
        execucao = conn.execute("SELECT * FROM execucoes WHERE id = ?", (execucao_id,)).fetchone()
        eventos = conn.execute(
            "SELECT * FROM eventos_log WHERE execucao_id = ? ORDER BY criado_em ASC", (execucao_id,)
        ).fetchall()

    return templates.TemplateResponse(
        request, "execucao_detalhe.html", {"execucao": execucao, "eventos": eventos}
    )


# Rotas de ação (rodar agora / pausar) ficam como placeholders até o
# orquestrador do pipeline (Data Lawyer/Apollo/Pipedrive) ser implementado.
