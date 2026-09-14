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
    # jurídico
    "juridic", "legal", "attorney", "advogad", "advocacia", "counsel", "lawyer",
    # trabalhista / relações de trabalho
    "trabalhista", "labor", "labour", "employee relations", "labor relations",
    "employment law", "labor law",
    # RH / departamento pessoal
    "rh", "hr ", "human resources", "recursos humanos", "personnel",
    "departamento pessoal", "people",
    # segurança/saúde ocupacional (relacionado aos assuntos-alvo: insalubridade,
    # periculosidade, ergonomia, doença ocupacional)
    "sst", "ehs", "hse", "safety", "occupational health", "saúde ocupacional",
    "segurança do trabalho", "seguranca do trabalho", "ergonom",
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


def buscar_candidatos_por_dominio(dominio: str, max_paginas: int = 5, por_pagina: int = 100) -> list[str]:
    """Busca, no domínio da empresa, os funcionários com cargo relevante
    (jurídico/RH/trabalhista/SST). Busca sem filtro de título na Apollo (pouco
    confiável entre idiomas) e filtra localmente por palavra-chave, varrendo
    várias páginas pra não perder gente relevante em empresas grandes."""
    candidatos = []
    for pagina in range(1, max_paginas + 1):
        payload = {
            "q_organization_domains_list": [dominio],
            "per_page": por_pagina,
            "page": pagina,
        }
        resp = requests.post(f"{BASE_URL}/mixed_people/api_search", headers=_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pessoas = data.get("people", [])
        candidatos.extend(p["id"] for p in pessoas if cargo_relevante(p.get("title")))
        if len(pessoas) < por_pagina:
            break  # última página
    return candidatos


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


def buscar_contatos_da_empresa(dominio: str, max_paginas: int = 5) -> list[ContatoEncontrado]:
    """Busca e revela TODOS os contatos relevantes de uma empresa (jurídico,
    RH, trabalhista, SST) - quanto mais gente certa encontrada, maior a
    chance de alguém responder."""
    candidatos = buscar_candidatos_por_dominio(dominio, max_paginas=max_paginas)
    contatos = []
    for apollo_id in candidatos:
        contato = revelar_contato(apollo_id)
        if contato:
            contatos.append(contato)
    return contatos
