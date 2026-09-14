"""Integração com a API da Apollo (busca de contatos por empresa).

Fluxo em duas chamadas, exigido pela própria Apollo:
1. api_search: busca candidatos por domínio da empresa + cargo (retorna prévia,
   sem e-mail).
2. people/match: revela o contato completo de um candidato (nome, e-mail se
   disponível, LinkedIn). Essa chamada consome crédito da conta Apollo -
   por isso só é feita para os candidatos já filtrados pela busca, não em massa.
"""

from dataclasses import dataclass

import requests

from app.config import APOLLO_API_KEY

BASE_URL = "https://api.apollo.io/api/v1"

# A Apollo normaliza cargos em inglês (ex.: "Attorney" em vez de "Advogado
# Trabalhista"), então em vez de filtrar a busca por título exato (arriscado,
# perde gente com cargo em outro idioma/variação), buscamos todos os
# funcionários do domínio e filtramos aqui por palavra-chave no título,
# cobrindo português e inglês.
PALAVRAS_CHAVE_CARGO = [
    "juridic", "legal", "attorney", "advogad", "advocacia", "counsel",
    "trabalhista", "labor", "labour",
    "rh", "hr ", "human resources", "recursos humanos", "personnel",
    "departamento pessoal", "people",
]


def cargo_relevante(titulo: str | None) -> bool:
    if not titulo:
        return False
    titulo_lower = titulo.lower()
    return any(palavra in titulo_lower for palavra in PALAVRAS_CHAVE_CARGO)


class ApolloNaoConfigurado(Exception):
    pass


@dataclass
class ContatoEncontrado:
    apollo_id: str
    nome: str
    cargo: str | None
    email: str | None
    telefone: str | None
    linkedin_url: str | None


def _headers() -> dict:
    if not APOLLO_API_KEY:
        raise ApolloNaoConfigurado("APOLLO_API_KEY não configurada no .env.")
    return {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "accept": "application/json",
        "x-api-key": APOLLO_API_KEY,
    }


def buscar_candidatos_por_dominio(dominio: str, limite: int = 25) -> list[str]:
    """Busca, no domínio da empresa, os funcionários com cargo relevante
    (jurídico/RH/trabalhista). Busca sem filtro de título na Apollo (pouco
    confiável entre idiomas) e filtra localmente por palavra-chave."""
    payload = {
        "q_organization_domains_list": [dominio],
        "per_page": limite,
    }
    resp = requests.post(f"{BASE_URL}/mixed_people/api_search", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return [p["id"] for p in data.get("people", []) if cargo_relevante(p.get("title"))]


def revelar_contato(apollo_id: str) -> ContatoEncontrado | None:
    """Revela os dados completos de um candidato (consome crédito Apollo)."""
    payload = {"id": apollo_id, "reveal_personal_emails": False}
    resp = requests.post(f"{BASE_URL}/people/match", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    pessoa = resp.json().get("person")
    if not pessoa:
        return None
    telefone = None
    numeros = pessoa.get("phone_numbers") or []
    if numeros:
        telefone = numeros[0].get("sanitized_number") or numeros[0].get("raw_number")
    return ContatoEncontrado(
        apollo_id=pessoa["id"],
        nome=pessoa.get("name") or "",
        cargo=pessoa.get("title"),
        email=pessoa.get("email"),
        telefone=telefone,
        linkedin_url=pessoa.get("linkedin_url"),
    )


def buscar_contatos_da_empresa(dominio: str, limite: int = 25) -> list[ContatoEncontrado]:
    """Busca e revela os contatos de uma empresa, num domínio de e-mail dado."""
    candidatos = buscar_candidatos_por_dominio(dominio, limite=limite)
    contatos = []
    for apollo_id in candidatos:
        contato = revelar_contato(apollo_id)
        if contato:
            contatos.append(contato)
    return contatos
