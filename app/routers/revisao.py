from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.db import db_session
from app.templates_engine import templates

router = APIRouter()


@router.get("/revisao")
def fila_revisao(request: Request, responsavel: str | None = None):
    query = """
        SELECT mensagens.*, empresas.razao_social, contatos.nome AS contato_nome
        FROM mensagens
        JOIN empresas ON empresas.id = mensagens.empresa_id
        JOIN contatos ON contatos.id = mensagens.contato_id
        WHERE mensagens.status = 'rascunho_gerado'
    """
    params = []
    if responsavel:
        query += " AND empresas.responsavel = ?"
        params.append(responsavel)
    query += " ORDER BY mensagens.criado_em ASC"

    with db_session() as conn:
        mensagens = conn.execute(query, params).fetchall()

    return templates.TemplateResponse(
        request, "revisao.html", {"mensagens": mensagens, "responsavel_filtro": responsavel}
    )


@router.post("/revisao/{mensagem_id}/aprovar")
def aprovar_mensagem(mensagem_id: int):
    # TODO: integrar com Gmail (criação de rascunho) quando OAuth estiver configurado
    with db_session() as conn:
        conn.execute(
            "UPDATE mensagens SET status = 'aprovada', revisado_em = datetime('now') WHERE id = ?",
            (mensagem_id,),
        )
    return RedirectResponse("/revisao", status_code=303)


@router.post("/revisao/{mensagem_id}/rejeitar")
def rejeitar_mensagem(mensagem_id: int):
    with db_session() as conn:
        conn.execute(
            "UPDATE mensagens SET status = 'rejeitada', revisado_em = datetime('now') WHERE id = ?",
            (mensagem_id,),
        )
    return RedirectResponse("/revisao", status_code=303)


@router.post("/revisao/{mensagem_id}/editar")
def editar_mensagem(mensagem_id: int, conteudo: str = Form(...)):
    with db_session() as conn:
        conn.execute(
            "UPDATE mensagens SET conteudo_gerado = ?, status = 'editada', revisado_em = datetime('now') WHERE id = ?",
            (conteudo, mensagem_id),
        )
    return RedirectResponse("/revisao", status_code=303)
