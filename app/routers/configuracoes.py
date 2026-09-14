from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.config import ASSUNTOS_INTERESSE, VOLUME_MINIMO_ASSUNTOS_ALVO, VOLUME_MINIMO_TOTAL
from app.db import db_session
from app.templates_engine import templates

router = APIRouter()


@router.get("/configuracoes")
def configuracoes(request: Request):
    with db_session() as conn:
        bloqueios = conn.execute("SELECT * FROM lista_bloqueio ORDER BY adicionado_em DESC").fetchall()

    return templates.TemplateResponse(
        "configuracoes.html",
        {
            "request": request,
            "bloqueios": bloqueios,
            "assuntos_interesse": ASSUNTOS_INTERESSE,
            "volume_minimo_total": VOLUME_MINIMO_TOTAL,
            "volume_minimo_assuntos_alvo": VOLUME_MINIMO_ASSUNTOS_ALVO,
        },
    )


@router.post("/configuracoes/bloqueio/adicionar")
def adicionar_bloqueio(cnpj_ou_razao_social: str = Form(...), motivo: str = Form("")):
    with db_session() as conn:
        conn.execute(
            "INSERT INTO lista_bloqueio (cnpj_ou_razao_social, motivo) VALUES (?, ?)",
            (cnpj_ou_razao_social, motivo),
        )
    return RedirectResponse("/configuracoes", status_code=303)


@router.post("/configuracoes/bloqueio/{bloqueio_id}/remover")
def remover_bloqueio(bloqueio_id: int):
    with db_session() as conn:
        conn.execute("DELETE FROM lista_bloqueio WHERE id = ?", (bloqueio_id,))
    return RedirectResponse("/configuracoes", status_code=303)
