"""Integração com a API do Pipedrive.

Por enquanto, só leitura: puxar organizações/negócios do funil "Outbound
Trabalhista" pra dentro do nosso banco local. Escrita de volta (mover
etapa, criar nota de histórico, criar campos customizados) fica pra depois,
quando a leitura estiver validada.
"""

from dataclasses import dataclass

import requests

from app.config import PIPEDRIVE_API_TOKEN

BASE_URL = "https://api.pipedrive.com/v1"

PIPELINE_OUTBOUND_TRABALHISTA_ID = 1
CAMPO_CNPJ_ORGANIZACAO = "45359471510083f3cb56e03244103cca5a8f16f2"


class PipedriveNaoConfigurado(Exception):
    pass


@dataclass
class EmpresaPipedrive:
    deal_id: int
    org_id: int | None
    nome: str
    stage_id: int
    cnpj: str | None
    site: str | None


def _get(path: str, params: dict | None = None) -> dict:
    if not PIPEDRIVE_API_TOKEN:
        raise PipedriveNaoConfigurado("PIPEDRIVE_API_TOKEN não configurado no .env.")
    p = {"api_token": PIPEDRIVE_API_TOKEN}
    if params:
        p.update(params)
    resp = requests.get(f"{BASE_URL}{path}", params=p, timeout=30)
    resp.raise_for_status()
    return resp.json()


def listar_negocios_outbound_trabalhista() -> list[EmpresaPipedrive]:
    """Lista todos os negócios ativos do funil Outbound Trabalhista, com CNPJ
    e site da organização vinculada. Só leitura - não grava nada."""
    empresas = []
    start = 0
    while True:
        data = _get("/deals", {"start": start, "limit": 100, "status": "all_not_deleted"})
        deals = data.get("data") or []
        for d in deals:
            if d.get("pipeline_id") != PIPELINE_OUTBOUND_TRABALHISTA_ID:
                continue
            org = d.get("org_id") or {}
            org_id = org.get("value")
            org_detalhe = _get(f"/organizations/{org_id}")["data"] if org_id else {}
            empresas.append(
                EmpresaPipedrive(
                    deal_id=d["id"],
                    org_id=org_id,
                    nome=org.get("name") or d.get("title") or "",
                    stage_id=d["stage_id"],
                    cnpj=org_detalhe.get(CAMPO_CNPJ_ORGANIZACAO),
                    site=org_detalhe.get("website"),
                )
            )
        pagination = data.get("additional_data", {}).get("pagination", {})
        if not pagination.get("more_items_in_collection") or not deals:
            break
        start += 100
    return empresas
