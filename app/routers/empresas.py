from fastapi import APIRouter, Request

from app.db import db_session
from app.templates_engine import templates

router = APIRouter()


@router.get("/empresas")
def listar_empresas(request: Request, status: str | None = None, responsavel: str | None = None):
    query = "SELECT * FROM empresas WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if responsavel:
        query += " AND responsavel = ?"
        params.append(responsavel)
    query += " ORDER BY atualizado_em DESC"

    with db_session() as conn:
        empresas = conn.execute(query, params).fetchall()

    return templates.TemplateResponse(
        "empresas.html",
        {"request": request, "empresas": empresas, "status_filtro": status, "responsavel_filtro": responsavel},
    )


@router.get("/empresas/{empresa_id}")
def detalhe_empresa(request: Request, empresa_id: int):
    with db_session() as conn:
        empresa = conn.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
        processos = conn.execute(
            "SELECT * FROM processos WHERE empresa_id = ? ORDER BY data_distribuicao DESC", (empresa_id,)
        ).fetchall()
        contatos = conn.execute("SELECT * FROM contatos WHERE empresa_id = ?", (empresa_id,)).fetchall()
        mensagens = conn.execute("SELECT * FROM mensagens WHERE empresa_id = ?", (empresa_id,)).fetchall()
        negocio = conn.execute(
            "SELECT * FROM negocios_pipedrive WHERE empresa_id = ?", (empresa_id,)
        ).fetchone()

    return templates.TemplateResponse(
        "empresa_detalhe.html",
        {
            "request": request,
            "empresa": empresa,
            "processos": processos,
            "contatos": contatos,
            "mensagens": mensagens,
            "negocio": negocio,
        },
    )
