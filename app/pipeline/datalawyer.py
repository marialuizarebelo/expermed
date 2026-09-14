"""
Integração com a API do Data Lawyer (consulta de processos por CNPJ).

Ainda não temos acesso de desenvolvedor à API deles (o login atual da
Expermed é de usuário do painel, não de API) - falta confirmar com o
comercial da Data Lawyer se o acesso via API está incluso no plano atual
e pegar a chave de teste.

Assim que a credencial chegar (DATALAWYER_API_TOKEN e DATALAWYER_BASE_URL
no .env), preencher as chamadas HTTP reais abaixo, sem mudar a assinatura
das funções - o resto do pipeline já espera esse formato de retorno.
"""

from dataclasses import dataclass

from app.config import DATALAWYER_API_TOKEN, DATALAWYER_BASE_URL


class DataLawyerNaoConfigurado(Exception):
    pass


@dataclass
class ProcessoEncontrado:
    numero_processo: str
    tribunal: str
    assunto_codigo: str | None
    assunto_descricao: str
    data_distribuicao: str | None
    ultima_movimentacao: str | None


def buscar_processos_por_cnpj(cnpj: str) -> list[ProcessoEncontrado]:
    """Busca processos de uma empresa por CNPJ na Data Lawyer.

    Retorna a lista de processos encontrados (número, tribunal, assunto).
    """
    if not DATALAWYER_API_TOKEN or not DATALAWYER_BASE_URL:
        raise DataLawyerNaoConfigurado(
            "DATALAWYER_API_TOKEN / DATALAWYER_BASE_URL ainda não configurados no .env. "
            "Confirme com o comercial da Data Lawyer o acesso via API antes de usar esta função."
        )

    # TODO: implementar a chamada real assim que tivermos a credencial.
    # Provavelmente algo como:
    #   resp = requests.get(
    #       f"{DATALAWYER_BASE_URL}/processos",
    #       params={"cnpj": cnpj},
    #       headers={"Authorization": f"Bearer {DATALAWYER_API_TOKEN}"},
    #   )
    raise NotImplementedError("Chamada à API da Data Lawyer ainda não implementada.")
