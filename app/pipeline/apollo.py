"""Integração com a API da Apollo (busca de contatos por empresa).

Fluxo:
1. resolver_dominio_por_nome: acha o domínio da empresa pelo nome (a maioria
   das empresas no Pipedrive não tem site cadastrado).
2. api_search: busca todos os funcionários do domínio (sem filtro de título -
   a Apollo normaliza cargo em inglês, então filtramos por palavra-chave
   localmente pra não perder gente por causa de tradução/variação).
3. people/match: revela o contato completo de um candidato (nome, e-mail se
   disponível, telefone). Consome crédito Apollo - só é chamado pros
   candidatos já filtrados e priorizados, no máximo MAX_CONTATOS_POR_EMPRESA.

Prioridade: jurídico/advogado trabalhista em primeiro lugar, depois RH/SST -
no máximo 5 contatos por empresa (mandar pra gente demais na mesma empresa
parece spam e não é o padrão usado hoje pelo time comercial).
"""

from dataclasses import dataclass

import requests

from app.config import APOLLO_API_KEY

BASE_URL = "https://api.apollo.io/api/v1"

MAX_CONTATOS_POR_EMPRESA = 5

# Prioridade 1 (mais relevante): jurídico e advogado trabalhista - é o que o
# time comercial busca primeiro na prática.
PALAVRAS_PRIORIDADE_1 = [
    "juridic", "legal", "attorney", "advogad", "advocacia", "counsel", "lawyer",
    "trabalhista", "labor relations", "employee relations", "employment law", "labor law",
]

# Prioridade 2: RH / departamento pessoal / segurança e saúde ocupacional
# (relacionado aos assuntos-alvo: insalubridade, periculosidade, ergonomia).
PALAVRAS_PRIORIDADE_2 = [
    "rh", "hr ", "human resources", "recursos humanos", "personnel", "departamento pessoal", "people",
    "sst", "ehs", "hse", "safety", "occupational health", "saúde ocupacional",
    "segurança do trabalho", "seguranca do trabalho", "ergonom",
]


def prioridade_cargo(titulo: str | None) -> int | None:
    """Retorna 1 (jurídico/trabalhista), 2 (RH/SST) ou None (não relevante)."""
    if not titulo:
        return None
    titulo_lower = titulo.lower()
    if any(p in titulo_lower for p in PALAVRAS_PRIORIDADE_1):
        return 1
    if any(p in titulo_lower for p in PALAVRAS_PRIORIDADE_2):
        return 2
    return None


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


# Sufixos de razão social que atrapalham o match por nome na Apollo (o nome
# comercial cadastrado lá raramente inclui "LTDA", "S.A." etc).
_SUFIXOS_RAZAO_SOCIAL = [
    " LTDA", " S.A.", " S/A", " SA", " EIRELI", " EPP", " ME",
    " INDUSTRIA E COMERCIO", " IND E COM", " COMERCIO E INDUSTRIA",
]


# Nomes de empresa no Pipedrive costumam vir em CAIXA ALTA sem acento (padrão
# de cadastro na Receita Federal). A busca por nome da Apollo é sensível a
# acento - "Alimentacao" não bate, só "Alimentação" bate - então, se a busca
# direta falhar, tentamos de novo restaurando os acentos mais comuns em nome
# de empresa brasileira.
_PALAVRAS_COM_ACENTO = {
    "alimentacao": "alimentação", "comercio": "comércio", "industria": "indústria",
    "construcao": "construção", "distribuicao": "distribuição", "servicos": "serviços",
    "seguranca": "segurança", "participacoes": "participações", "administracao": "administração",
    "importacao": "importação", "exportacao": "exportação", "associacao": "associação",
    "producao": "produção", "logistica": "logística", "agropecuaria": "agropecuária",
    "mineracao": "mineração", "geracao": "geração", "comunicacao": "comunicação",
    "manutencao": "manutenção", "vigilancia": "vigilância", "engenharia": "engenharia",
}


def restaurar_acentos(nome: str) -> str:
    palavras = nome.split()
    return " ".join(_PALAVRAS_COM_ACENTO.get(p.lower(), p) for p in palavras)


def limpar_nome_empresa(nome_empresa: str) -> str:
    """Remove sufixos de razão social e normaliza capitalização, pra não
    atrapalhar o match por nome na Apollo (ex.: 'LTDA' ou nome em CAIXA ALTA
    reduzem a chance de achar a empresa certa)."""
    nome = nome_empresa.upper()
    for sufixo in _SUFIXOS_RAZAO_SOCIAL:
        if nome.endswith(sufixo):
            nome = nome[: -len(sufixo)]
    return nome.strip().title()


def _buscar_dominio(nome: str) -> str | None:
    payload = {"q_organization_name": nome, "per_page": 5}
    resp = requests.post(f"{BASE_URL}/mixed_companies/search", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    for org in data.get("organizations") or data.get("accounts") or []:
        if org.get("primary_domain"):
            return org["primary_domain"]
    return None


def resolver_dominio_por_nome(nome_empresa: str) -> str | None:
    """Acha o domínio de e-mail da empresa pelo nome (a maioria das empresas
    do Pipedrive não tem site cadastrado). Tenta o nome limpo primeiro; se
    não achar, tenta de novo restaurando acentos comuns (a busca da Apollo é
    sensível a acento, e nome de empresa no Pipedrive geralmente não tem)."""
    nome_limpo = limpar_nome_empresa(nome_empresa)
    dominio = _buscar_dominio(nome_limpo)
    if dominio:
        return dominio
    nome_acentuado = restaurar_acentos(nome_limpo)
    if nome_acentuado != nome_limpo:
        dominio = _buscar_dominio(nome_acentuado)
    return dominio


def _candidatos_priorizados_por_dominio(dominio: str, max_paginas: int = 5, por_pagina: int = 100) -> list[dict]:
    """Busca funcionários do domínio, filtra por cargo relevante e ordena por
    prioridade (jurídico/trabalhista antes de RH/SST)."""
    candidatos = []
    for pagina in range(1, max_paginas + 1):
        payload = {
            "q_organization_domains_list": [dominio],
            "per_page": por_pagina,
            "page": pagina,
        }
        resp = requests.post(f"{BASE_URL}/mixed_people/api_search", headers=_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        pessoas = resp.json().get("people", [])
        for p in pessoas:
            prioridade = prioridade_cargo(p.get("title"))
            if prioridade is not None:
                candidatos.append({"id": p["id"], "prioridade": prioridade, "has_email": p.get("has_email")})
        if len(pessoas) < por_pagina:
            break  # última página
    # prioridade 1 primeiro; dentro da mesma prioridade, quem já tem e-mail disponível primeiro
    candidatos.sort(key=lambda c: (c["prioridade"], not c["has_email"]))
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


def buscar_contatos_da_empresa(
    nome_empresa: str, dominio: str | None = None, limite: int = MAX_CONTATOS_POR_EMPRESA
) -> list[ContatoEncontrado]:
    """Busca até `limite` contatos de jurídico/RH/SST de uma empresa, por
    nome (resolve o domínio sozinho) ou por domínio já conhecido.
    Prioriza jurídico/advogado trabalhista, e só chama e-mails de contatos
    que efetivamente têm e-mail ou telefone disponível."""
    if not dominio:
        dominio = resolver_dominio_por_nome(nome_empresa)
    if not dominio:
        return []

    candidatos = _candidatos_priorizados_por_dominio(dominio)
    contatos = []
    for candidato in candidatos:
        if len(contatos) >= limite:
            break
        contato = revelar_contato(candidato["id"])
        if contato and (contato.email or contato.telefone):
            contatos.append(contato)
    return contatos
